"""Apply allowlists, de-duplicate messages, and route shared commands.

/recall is a OneBot-only action: quote a bot message; in groups, the caller
must be an admin, owner, or KISARA_ADMIN_USERS member. The adapter executes
the deletion after this module validates the request. Legacy Chinese and hash
aliases are normalized here before command routing.
Messages without command text, including file-status events, stay silent.
"""

import re
import time
from threading import Lock
from collections import OrderedDict
from typing import Callable, FrozenSet, Mapping, Optional, Union

from kisara.application.services.chat import ChatResponder
from kisara.application.services.daily_news import DailyNews
from kisara.application.services.public import PublicServices, RemoteResult
from kisara.application.services.tarot import TarotReader
from kisara.bot.commands.eat import execute as execute_eat
from kisara.bot.commands.help import execute as execute_help
from kisara.bot.commands.ping import execute as execute_ping
from kisara.bot.commands.roll import execute_validated as execute_roll
from kisara.bot.contracts import (
    CommandInputError, DispatchResult, MessageEvent, OutgoingMessage, is_image_segment,
)
from kisara.infrastructure.integrations.http import RemoteServiceError


class Dispatcher:
    """Route normalized events without depending on a platform SDK."""

    def __init__(
        self,
        allowed_users: FrozenSet[str],
        groups_enabled: bool,
        allowed_groups: FrozenSet[str],
        seen_limit: int = 1024,
        seen_ttl_seconds: float = 3600.0,
        clock: Callable[[], float] = time.monotonic,
        chat_responder: Optional[ChatResponder] = None,
        tarot_reader: Optional[TarotReader] = None,
        public_services: Optional[PublicServices] = None,
        daily_news: Optional[DailyNews] = None,
        admin_users: FrozenSet[str] = frozenset(),
        tarot_group_rates: Optional[Mapping[str, int]] = None,
    ) -> None:
        """Create a dispatcher with bounded in-memory duplicate tracking."""

        self._allowed_users = allowed_users
        self._groups_enabled = groups_enabled
        self._allowed_groups = allowed_groups
        self._seen_limit = seen_limit
        self._seen_ttl_seconds = seen_ttl_seconds
        self._clock = clock
        self._seen_messages = OrderedDict()
        self._seen_lock = Lock()
        self._chat_responder = chat_responder
        self._tarot_reader = tarot_reader
        self._public_services = public_services
        self._daily_news = daily_news
        self._admin_users = admin_users
        self._tarot_group_rates = tarot_group_rates or {}

    def dispatch(self, event: MessageEvent) -> Optional[str]:
        """Return a shared response for an allowed event, if one is due."""

        return self.dispatch_result(event).reply

    def dispatch_payload(
        self, event: MessageEvent
    ) -> Optional[Union[str, OutgoingMessage]]:
        """Return text or a structured reply for the selected adapter."""

        result = self.dispatch_result(event)
        if (result.reply is None and not result.image_urls and not result.music_id
                and not result.recall_message_id):
            return None
        if result.image_urls or result.music_id or result.recall_message_id:
            return OutgoingMessage(
                result.reply or "", result.image_urls, result.music_id,
                result.recall_message_id,
            )
        return result.reply

    def dispatch_result(self, event: MessageEvent) -> DispatchResult:
        """Expose routing and validation status without interpreting reply text."""

        if not self._is_allowed(event):
            return DispatchResult("unhandled", None, "Message is not allowed.")
        if self._is_duplicate(event):
            return DispatchResult("unhandled", None, "Duplicate message.")
        try:
            return self._route(event)
        except CommandInputError as error:
            return DispatchResult("error", str(error), "Invalid command arguments.")
        except RemoteServiceError as error:
            return DispatchResult("error", str(error), "Remote service failed.")

    def _route(self, event: MessageEvent) -> DispatchResult:
        """Execute a recognized command or preserve the fallback reply."""

        content = _normalize_legacy_command(event.text.strip())
        if content.lower() in {"/ping", "ping"}:
            return DispatchResult("handled", execute_ping())
        command_parts = content.split(maxsplit=1)
        command = command_parts[0].lower() if command_parts else ""
        arguments = command_parts[1] if len(command_parts) == 2 else ""
        is_slash_command = command.startswith("/")
        if command.startswith("/"):
            command = command[1:]
        if command in {"roll", "r", "dice"}:
            return DispatchResult("handled", execute_roll(arguments))
        if command in {"eat", "what2eat"}:
            if arguments:
                raise CommandInputError("Usage: /eat")
            return DispatchResult("handled", execute_eat())
        if command in {"help", "ahelp"}:
            if arguments:
                raise CommandInputError("Usage: /help")
            return DispatchResult(
                "handled", execute_help(
                    self._chat_responder is not None,
                    self._tarot_reader is not None,
                    self._public_services is not None,
                    self._daily_news is not None,
                )
            )
        if command in {"tarot", "占卜"} and self._tarot_reader is not None:
            mode = arguments.strip().lower() or "auto"
            if mode not in {"auto", "single", "spread"}:
                raise CommandInputError("Usage: /tarot [single|spread]")
            reading, images = self._tarot_reader.reading_with_images(
                event.sender_id, event.instance_id, mode,
                self._tarot_group_rates.get(event.conversation_id, -1)
            )
            return DispatchResult(
                "handled", reading,
                image_urls=images if event.engine == "onebot" else (),
            )
        if command == "chat" and self._chat_responder is not None:
            if not arguments.strip():
                raise CommandInputError("Usage: /chat <message>")
            response = self._chat_responder.reply(
                arguments, event.sender_id, force=True,
                group_id=event.conversation_id if event.conversation_kind == "group" else "",
            )
            return DispatchResult("handled", response or "No phrasebook reply found.")
        if command == "recall":
            return self._recall(event, arguments)
        if command in {"news", "brief"} and self._daily_news is not None:
            if arguments:
                raise CommandInputError("Usage: /news")
            result = self._daily_news.get()
            images = (result.onebot_image(),) if event.engine == "onebot" else ()
            return DispatchResult("handled", result.text, image_urls=images)
        if self._public_services is not None:
            remote = self._route_public(command, arguments, event)
            if remote is not None:
                return self._remote_result(remote)
        if any(is_image_segment(segment) or segment.kind == "forward"
               for segment in event.segments):
            return DispatchResult("unhandled", None, "Media without a matching command.")
        if not content:
            return DispatchResult("unhandled", None, "Empty message.")
        if self._chat_responder is not None and not is_slash_command:
            response = self._chat_responder.reply(
                content, event.sender_id, mentioned=self._mentions_bot(event),
                group_id=event.conversation_id if event.conversation_kind == "group" else "",
            )
            return DispatchResult("handled" if response else "unhandled", response)
        return DispatchResult(
            "unhandled", "Kisara received: {}".format(content[:500]),
            "No matching command; received only. Try /help.",
        )

    def _route_public(
        self, command: str, arguments: str, event: MessageEvent
    ) -> Optional[RemoteResult]:
        """Route commands backed by public or configured HTTP providers."""

        services = self._public_services
        if services is None:
            return None
        if command in {"wallpaper", "pixiv"}:
            if arguments:
                raise CommandInputError("Usage: /wallpaper")
            return services.wallpaper()
        if command in {"ba", "guide"}:
            if not arguments.strip():
                raise CommandInputError("Usage: /ba <name>")
            return services.blue_archive(arguments.strip())
        if command in {"music", "song"}:
            if not arguments.strip():
                raise CommandInputError("Usage: /music <song>")
            return services.music(arguments.strip())
        if command == "love":
            if arguments:
                raise CommandInputError("Usage: /love")
            return services.love_note()
        if command in {"source", "sauce"}:
            threshold = 70
            if arguments.strip():
                try:
                    threshold = int(arguments.strip())
                except ValueError:
                    raise CommandInputError("Usage: /source [similarity] + image")
            if threshold < 1 or threshold > 99:
                raise CommandInputError("Similarity must be from 1 to 99.")
            image_url = next(
                (str(segment.data.get("url") or "") for segment in event.segments
                 if segment.kind == "image"),
                "",
            )
            if not image_url:
                raise CommandInputError("Attach an image to /source.")
            return services.source_search(image_url, threshold)
        return None

    def _recall(self, event: MessageEvent, arguments: str) -> DispatchResult:
        """Allow a privileged sender to recall a quoted bot message."""

        if arguments:
            raise CommandInputError("Usage: /recall while quoting a bot message")
        if event.engine != "onebot":
            return DispatchResult("error", "Recall requires the OneBot engine.")
        context = event.reply_context
        quoted_id = str(context.get("quoted_message_id") or "")
        quoted_sender = str(context.get("quoted_sender_id") or "")
        self_id = str(context.get("self_id") or "")
        if not quoted_id:
            raise CommandInputError("Quote a bot message to recall it.")
        if not quoted_sender or quoted_sender != self_id:
            raise CommandInputError("Only bot messages can be recalled.")
        if event.conversation_kind == "group":
            role = str(context.get("sender_role") or "")
            if role not in {"admin", "owner"} and event.sender_id not in self._admin_users:
                return DispatchResult("error", "Only a group admin can recall here.")
        return DispatchResult("handled", None, recall_message_id=quoted_id)

    @staticmethod
    def _remote_result(result: RemoteResult) -> DispatchResult:
        """Keep media details alongside the console-friendly reply text."""

        return DispatchResult(
            "handled", result.text, image_urls=result.image_urls,
            music_id=result.music_id,
        )

    def _is_allowed(self, event: MessageEvent) -> bool:
        """Check the sender, conversation kind, and group trigger policy."""

        if event.sender_id not in self._allowed_users:
            return False
        if event.conversation_kind == "group":
            return self._groups_enabled and self._group_is_allowed(event)
        return event.conversation_kind in {"private", "channel"}

    def _group_is_allowed(self, event: MessageEvent) -> bool:
        """Check the group allowlist and trigger for an ordinary message."""

        if event.conversation_id not in self._allowed_groups:
            return False
        if _normalize_legacy_command(event.text.strip()).startswith("/"):
            return True

        if self._chat_responder is not None:
            return True

        self_id = str(event.reply_context.get("self_id", ""))
        for segment in event.segments:
            if segment.kind != "at":
                continue
            mentioned_id = str(segment.data.get("qq", ""))
            if not mentioned_id or not self_id or mentioned_id == self_id:
                return True
        return False


    def _mentions_bot(self, event: MessageEvent) -> bool:
        """Check whether a structured mention targets the current bot."""

        self_id = str(event.reply_context.get("self_id", ""))
        if not self_id:
            return False
        return any(
            segment.kind == "at" and str(segment.data.get("qq", "")) == self_id
            for segment in event.segments
        )

    def _is_duplicate(self, event: MessageEvent) -> bool:
        """Return whether an event was already accepted within the TTL."""

        if not event.message_id:
            return False

        with self._seen_lock:
            return self._is_duplicate_locked(event)

    def _is_duplicate_locked(self, event: MessageEvent) -> bool:
        """Update the duplicate cache while its lock is held."""

        now = self._clock()
        expiry = now - self._seen_ttl_seconds
        while self._seen_messages:
            _, seen_at = next(iter(self._seen_messages.items()))
            if seen_at > expiry:
                break
            self._seen_messages.popitem(last=False)

        key = "\0".join(
            (
                event.engine,
                event.instance_id,
                event.message_id,
            )
        )
        if key in self._seen_messages:
            return True

        self._seen_messages[key] = now
        while len(self._seen_messages) > self._seen_limit:
            self._seen_messages.popitem(last=False)
        return False


def _normalize_legacy_command(content: str) -> str:
    """Accept the short Chinese and hash commands used by the old bot."""

    if not content or content.startswith("/"):
        return content
    has_hash = content.startswith("#")
    value = (content[1:] if has_hash else content).strip()
    exact = {
        "占卜": "/tarot",
        "简报": "/news",
        "新闻": "/news",
        "每日新闻": "/news",
        "news": "/news",
        "日报": "/news",
        "舔狗日志": "/love",
        "舔狗日记": "/love",
        "舔狗": "/love",
        "天狗": "/love",
        "沸羊羊": "/love",
        "来张壁纸": "/wallpaper",
        "随机壁纸": "/wallpaper",
        "壁纸": "/wallpaper",
        "p站": "/wallpaper",
        "P站": "/wallpaper",
        "pixiv": "/wallpaper",
        "撤回": "/recall",
        "撤": "/recall",
    }
    if value in exact:
        return exact[value]
    if re.fullmatch(r"咱?(今天|明天|[早中午晚][上饭餐午]|早上|夜宵|今晚)吃(什么|啥|点啥)", value):
        return "/eat"
    for prefix, command in (
        ("roll", "roll"), ("dice", "roll"), ("骰子", "roll"),
        ("色子", "roll"), ("r", "roll"),
        ("识图", "source"), ("搜图", "source"), ("出处", "source"),
        ("来源", "source"),
        ("点歌", "music"), ("来首", "music"), ("听歌", "music"),
        ("点首", "music"), ("bgm", "music"),
        ("ba攻略", "ba"), ("ba", "ba"),
    ):
        if value.lower().startswith(prefix.lower()):
            raw_suffix = value[len(prefix):]
            if prefix in {"roll", "dice", "r", "ba", "ba攻略"} and not has_hash:
                continue
            if prefix in {"roll", "dice", "r", "bgm"} and raw_suffix:
                if not (raw_suffix[0].isspace() or raw_suffix[0].isdigit()):
                    continue
            suffix = raw_suffix.strip()
            return "/{}{}".format(command, " " + suffix if suffix else "")
    return content
