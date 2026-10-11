"""Telegram Bot API long polling, normalization and native document replies.

/tgsetu is an opt-in private-chat workflow, authorized by the registered native
feature gate before durable acceptance or retrieval. The injected service owns
activation, naming and file publication; this adapter normalizes ordinary media,
resolves SDK cache paths and owns archive worker shutdown before SDK shutdown.

Only this selected adapter imports python-telegram-bot (community wrapper for
Telegram's official Bot API). Access and command feature checks live in the
shared dispatcher. Owned scheduler cancellation precedes SDK stop/shutdown;
blocking services run in an executor. SDK errors are logged as safe categories.
Explicit opt-in message summaries disclose only authorized conversations, with
redacted, escaped previews and confirmed text/document sends.
"""

import asyncio
import logging
import re
import signal
import unicodedata
from collections import OrderedDict
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Union

from telegram import ReplyParameters
from telegram.error import BadRequest, Conflict, Forbidden, InvalidToken, RetryAfter, TelegramError
from telegram.ext import Application, ExtBot, MessageHandler as SDKMessageHandler, filters
from telegram.request import HTTPXRequest

from kisara.application.services.news_push import DeliveryRejected, TelegramNewsPush
from kisara.application.services.tgsetu import TgSetu
from kisara.bot.contracts import MessageEvent, MessageHandler, MessageSegment, OutgoingMessage
from kisara.config.settings import Settings
from kisara.bot.preview_readiness import publish as publish_readiness
from kisara.infrastructure.persistence.telegram_news import TelegramNewsStore


_log = logging.getLogger("kisara.telegram")


def quiet_sdk_logging() -> None:
    """Prevent token-bearing SDK request/exception logs from reaching handlers."""
    names = ["telegram", "httpx", "httpcore"]
    names += [name for name in logging.root.manager.loggerDict
              if name.startswith(("telegram.", "httpx.", "httpcore."))]
    for name in names:
        logger = logging.getLogger(name)
        logger.setLevel(logging.CRITICAL + 1)
        logger.propagate = False
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())


def _normalize_command(text: str, username: str) -> Optional[str]:
    """Strip this bot's target while rejecting commands addressed elsewhere."""
    text = text.strip()
    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        command = parts[0]
        if "@" in command:
            command, target = command.split("@", 1)
            if target.lower() != username.lower():
                return None
        if command.lower() == "/news_clear":
            command = "/news-clear"
        text = command + (" " + parts[1] if len(parts) == 2 else "")
    return text


def _caption_metadata(message: object) -> tuple:
    """Parse ordered hashtag entities using Telegram's UTF-16 offsets."""
    caption = getattr(message, "caption", None) or ""
    encoded = caption.encode("utf-16-le")
    tags, spans = [], []
    for entity in sorted(getattr(message, "caption_entities", None) or (),
                         key=lambda value: value.offset):
        if entity.type != "hashtag":
            continue
        start, end = entity.offset * 2, (entity.offset + entity.length) * 2
        if start < 0 or end > len(encoded) or start >= end:
            continue
        try:
            parser = getattr(message, "parse_caption_entity", None)
            value = parser(entity) if callable(parser) else encoded[start:end].decode("utf-16-le")
        except (UnicodeError, ValueError):
            continue
        if not value.startswith("#") or len(value) < 2:
            continue
        tag = value[1:]
        if tag not in tags:
            tags.append(tag)
        spans.append((start, end))
    parts, offset = [], 0
    for start, end in spans:
        if start >= offset:
            parts.append(encoded[offset:start])
        offset = max(offset, end)
    parts.append(encoded[offset:])
    return caption, b"".join(parts).decode("utf-16-le").strip(), tuple(tags)


def normalize_update(update: object, instance_id: str, username: str) -> Optional[MessageEvent]:
    """Normalize user text or one ordinary media item without SDK objects."""
    message = getattr(update, "message", None)
    if message is None or getattr(message, "sender_chat", None) is not None:
        return None
    if getattr(message, "is_topic_message", False):
        return None
    chat = getattr(message, "chat", None)
    user = getattr(message, "from_user", None)
    if chat is None or user is None or getattr(user, "is_bot", False):
        return None
    kind = getattr(chat, "type", "")
    if kind not in {"private", "group", "supergroup"}:
        return None
    segments = []
    text = getattr(message, "text", None)
    if isinstance(text, str):
        text = _normalize_command(text, username)
        if text is None:
            return None
        segments.append(MessageSegment("text", {"text": text}))
    else:
        # Animation can also carry a document field; archive ordinary documents only.
        if any(getattr(message, name, None) for name in (
            "animation", "sticker", "audio", "voice", "video_note", "paid_media", "live_photo",
        )):
            return None
        photo = getattr(message, "photo", None) or ()
        media_kind, media = "", None
        if photo:
            media_kind = "image"
            media = max(photo, key=lambda value: (
                getattr(value, "width", 0) * getattr(value, "height", 0),
                getattr(value, "file_size", None) or 0,
            ))
        elif getattr(message, "video", None) is not None:
            media_kind, media = "video", message.video
        elif getattr(message, "document", None) is not None:
            media_kind, media = "file", message.document
        if media is None:
            return None
        caption, title, tags = _caption_metadata(message)
        if _normalize_command(caption, username) is None:
            return None
        segments.append(MessageSegment(media_kind, {
            "file_id": media.file_id, "file_unique_id": media.file_unique_id,
            "name": getattr(media, "file_name", None) or "",
            "mime_type": getattr(media, "mime_type", None) or ("image/jpeg" if photo else ""),
            "size": getattr(media, "file_size", None),
            "caption": caption, "title": title, "tags": tags,
            "media_group_id": str(getattr(message, "media_group_id", None) or ""),
        }))
    reply_context = {"chat_id": chat.id, "message_id": message.message_id}
    quoted = getattr(message, "reply_to_message", None)
    if quoted is not None:
        reply_context["reply_to_message_id"] = str(quoted.message_id)
    return MessageEvent(
        engine="telegram", instance_id=instance_id, message_id=str(message.message_id),
        conversation_kind="private" if kind == "private" else "group",
        conversation_id=str(chat.id), sender_id=str(user.id),
        segments=tuple(segments), reply_context=reply_context,
    )


def split_text(text: str, limit: int = 4096) -> tuple:
    """Split plain text within Telegram's UTF-16 character budget."""
    chunks = []
    chunk = []
    size = 0
    for character in text:
        width = 2 if ord(character) > 0xffff else 1
        if size + width > limit:
            chunks.append("".join(chunk))
            chunk, size = [], 0
        chunk.append(character)
        size += width
    if chunk:
        chunks.append("".join(chunk))
    return tuple(chunks)


def message_preview(text: str, token: Optional[str], limit: int = 120) -> str:
    """Redact credentials first, then bound an escaped single-line preview."""
    redacted = text.replace(token, "[redacted]") if token else text
    redacted = re.sub(
        r"(?i)(api\.telegram\.org/(?:file/)?bot)[^/\s?#]+",
        r"\1[redacted]", redacted,
    )
    pieces = []
    length = 0
    for character in redacted:
        if character == "\n":
            piece = "\\n"
        elif character == "\r":
            piece = "\\r"
        elif character == "\t":
            piece = "\\t"
        elif character == "\\":
            piece = "\\\\"
        elif unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}:
            piece = "\\u{:04x}".format(ord(character))
        else:
            piece = character
        if length + len(piece) > limit:
            preview = "".join(pieces)
            return preview[:limit - 1] + "…"
        pieces.append(piece)
        length += len(piece)
    return "".join(pieces)


class ManagedPollingBot(ExtBot):
    """Report fatal revoked-token polling through the public ExtBot extension seam."""

    __slots__ = ("_fatal_callback", "_owned_requests", "_polling_callback")

    def __init__(self, token: str, fatal_callback: Callable[[], None],
                 polling_callback: Optional[Callable[[], None]] = None,
                 api_base_url: str = "https://api.telegram.org", local_mode: bool = False) -> None:
        request = HTTPXRequest(connect_timeout=10, read_timeout=30,
                               write_timeout=30, pool_timeout=10)
        updates_request = HTTPXRequest(connect_timeout=10, read_timeout=35,
                                       write_timeout=30, pool_timeout=10)
        super().__init__(token=token, request=request, get_updates_request=updates_request,
                         base_url=api_base_url.rstrip("/") + "/bot",
                         base_file_url=api_base_url.rstrip("/") + "/file/bot",
                         local_mode=local_mode)
        object.__setattr__(self, "_owned_requests", (request, updates_request))
        object.__setattr__(self, "_fatal_callback", fatal_callback)
        object.__setattr__(self, "_polling_callback", polling_callback)

    async def initialize(self) -> None:
        """Close clients when initialization fails before SDK ownership is established."""
        try:
            await super().initialize()
        except BaseException:
            # Application.shutdown() skips an incompletely initialized application.
            results = await asyncio.gather(*(request.shutdown() for request in self._owned_requests),
                                           return_exceptions=True)
            if any(isinstance(result, BaseException) for result in results):
                _log.warning("Telegram request cleanup failed during initialization")
            raise

    async def get_updates(self, *args: object, **kwargs: object) -> tuple:
        try:
            updates = await super().get_updates(*args, **kwargs)
            if self._polling_callback is not None:
                self._polling_callback()
            return updates
        except InvalidToken:
            self._fatal_callback()
            # The fatal owner stops polling; avoid an unobserved SDK child-task exception.
            return ()


class TelegramAdapter:
    """A separately owned Telegram polling process and optional news scheduler."""

    engine = "telegram"

    def __init__(self, settings: Settings, handler: MessageHandler,
                 daily_news_factory: Optional[Callable[[], OutgoingMessage]] = None,
                 delivery_store: Optional[TelegramNewsStore] = None,
                 tgsetu: Optional[TgSetu] = None,
                 native_authorizer: Optional[Callable[[MessageEvent, str], bool]] = None) -> None:
        self.instance_id = settings.instance_id
        self._settings = settings
        self._handler = handler
        self._tgsetu = tgsetu
        self._native_authorizer = native_authorizer
        self._tgsetu_task = None
        self._notice_task = None
        self._notice_pending = None
        self._notice_event = None
        self._factory = daily_news_factory
        self._store = delivery_store
        self._application = None
        self._loop = None
        self._stop_event = None
        self._scheduler_task = None
        self._status = "stopped"
        self._fatal_polling = False
        self._fatal_archive = False

    @property
    def status(self) -> str:
        """Expose only bounded lifecycle state."""
        return self._status

    def start(self) -> None:
        """Run the owned event loop until signal or close request."""
        quiet_sdk_logging()
        publish_readiness(self.engine, False)
        try:
            asyncio.run(self._run())
        finally:
            publish_readiness(self.engine, False)

    def close(self) -> None:
        """Request shutdown without closing an active SDK from another thread."""
        publish_readiness(self.engine, False)
        if self._loop is not None and self._stop_event is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._stop_event.set)

    async def _run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        for name in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(name, self._stop_event.set)
        application = None
        try:
            bot = ManagedPollingBot(self._settings.telegram_token, self._fatal_polling_error,
                                    self._polling_succeeded,
                                    api_base_url=self._settings.telegram_api_base_url,
                                    local_mode=self._settings.telegram_local_mode)
            application = (Application.builder().bot(bot)
                           .update_queue(asyncio.Queue(maxsize=128)).concurrent_updates(False).build())
            self._application = application
            application.add_handler(SDKMessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL)
                                                       & ~filters.UpdateType.EDITED_MESSAGE, self._on_update))
            application.add_error_handler(self._on_error)
            self._status = "starting"
            await application.initialize()
            await application.updater.start_polling(timeout=25, bootstrap_retries=0,
                                                    drop_pending_updates=False,
                                                    error_callback=self._polling_error)
            if self._tgsetu is not None:
                self._notice_pending = OrderedDict()
                self._notice_event = asyncio.Event()
            await application.start()
            self._status = "running"
            _log.info("Telegram polling ready")
            if self._tgsetu is not None:
                self._notice_task = asyncio.create_task(self._run_notices())
                self._tgsetu_task = asyncio.create_task(self._run_tgsetu())
            if self._factory is not None and self._store is not None and self._settings.news_push_enabled:
                targets = tuple(("private", value) for value in sorted(self._settings.news_push_users))
                targets += tuple(("group", value) for value in sorted(self._settings.news_push_groups))
                if targets:
                    scheduler = TelegramNewsPush(targets, self._settings.news_push_hour,
                                                 self._settings.news_push_minute, self._factory,
                                                 self._send_news, self._store)
                    self._scheduler_task = asyncio.create_task(self._run_scheduler(scheduler))
            await self._stop_event.wait()
            if self._fatal_archive:
                raise RuntimeError("Telegram media worker stopped unexpectedly")
            if self._fatal_polling:
                raise RuntimeError("Telegram polling stopped after a fatal credential/ownership error")
        finally:
            self._status = "stopping"
            publish_readiness(self.engine, False)
            if self._scheduler_task is not None:
                self._scheduler_task.cancel()
                try:
                    await self._scheduler_task
                except asyncio.CancelledError:
                    pass
                self._scheduler_task = None
            try:
                if application is not None:
                    await self._shutdown(application)
            finally:
                await self._stop_tgsetu()
                await self._stop_notices()
                for name in (signal.SIGINT, signal.SIGTERM):
                    self._loop.remove_signal_handler(name)
                self._status = "stopped"

    async def _shutdown(self, application: Application) -> None:
        """Continue cleanup when a failed poll task raises during updater.stop()."""
        failed = False
        operations = []
        if application.updater.running:
            operations.append(application.updater.stop)
        if application.running:
            operations.append(application.stop)
        operations.extend((self._stop_tgsetu, self._stop_notices, application.shutdown))
        for operation in operations:
            try:
                await operation()
            except Exception as error:
                failed = True
                _log.warning("Telegram SDK cleanup failed (%s)", type(error).__name__)
        if failed:
            raise RuntimeError("Telegram cleanup failed") from None

    async def _run_tgsetu(self) -> None:
        """Own archive work independently from update handling and SDK polling."""
        try:
            await self._tgsetu.run(self)
        except asyncio.CancelledError:
            raise
        except Exception:
            _log.error("Telegram media worker stopped; restart to recover pending work")
            self._fatal_archive = True
            self._stop_event.set()

    async def _stop_tgsetu(self) -> None:
        """Await archive worker cancellation before the SDK clients close."""
        if self._tgsetu_task is not None:
            self._tgsetu_task.cancel()
            try:
                await self._tgsetu_task
            except asyncio.CancelledError:
                pass
            self._tgsetu_task = None

    async def _run_notices(self) -> None:
        """Pace and coalesce archive notices without delaying media acceptance."""
        while True:
            await self._notice_event.wait()
            self._notice_event.clear()
            while self._notice_pending:
                (chat_id, source_id), text = self._notice_pending.popitem(last=False)
                try:
                    await self._send_archive_notice(chat_id, text, source_id)
                except Exception as error:
                    _log.warning("Telegram archive notice failed (%s)", type(error).__name__)
                # A serial sender bounds both per-chat and global message rates.
                await asyncio.sleep(1.05)

    async def _stop_notices(self) -> None:
        """Cancel and await notice delivery before closing SDK requests."""
        if self._notice_task is not None:
            self._notice_task.cancel()
            try:
                await self._notice_task
            except asyncio.CancelledError:
                pass
            self._notice_task = None
        if self._notice_pending:
            _log.warning("Telegram archive notices pending at shutdown; file state is retained")
        self._notice_pending = None
        self._notice_event = None

    def _fatal_polling_error(self) -> None:
        publish_readiness(self.engine, False)
        self._fatal_polling = True
        _log.error("Telegram polling credentials invalid; stopping")
        if self._stop_event is not None:
            self._stop_event.set()

    async def _run_scheduler(self, scheduler: TelegramNewsPush) -> None:
        try:
            await scheduler.run()
        except asyncio.CancelledError:
            raise
        except Exception:
            _log.error("Telegram news scheduler stopped; restart to recover claims")
            self._stop_event.set()

    def _polling_error(self, error: TelegramError) -> None:
        """PTB requires a synchronous polling error callback."""
        publish_readiness(self.engine, False)
        _log.warning("Telegram polling failed (%s)", type(error).__name__)
        if isinstance(error, (Conflict, InvalidToken)) and self._stop_event is not None:
            self._fatal_polling = True
            self._stop_event.set()

    def _polling_succeeded(self) -> None:
        """Restore preview evidence only after recovery of the running poller."""
        if self._status == "running" and not self._fatal_polling:
            publish_readiness(self.engine, True)

    @staticmethod
    async def _on_error(update: object, context: object) -> None:
        _log.warning("Telegram update processing failed (%s)", type(context.error).__name__)

    async def _on_update(self, update: object, context: object) -> None:
        event = normalize_update(update, self.instance_id, context.bot.username or "")
        if event is None:
            return
        media = any(segment.kind in {"image", "video", "file"} for segment in event.segments)
        command = event.text.split(maxsplit=1)[0].lower() if event.text else ""
        if self._tgsetu is not None and (media or command == "/tgsetu"):
            # Native authorization consumes deduplication once; never fall through.
            if self._native_authorizer is not None and self._native_authorizer(event, "tgsetu"):
                try:
                    await self._tgsetu.handle(event, self)
                except Exception as error:
                    _log.warning("Telegram media handling failed (%s)", type(error).__name__)
            return
        if media:
            return
        log_allowed = self._message_log_allowed(event)
        if log_allowed:
            _log.info("Received %s message user=%s chat=%s: %s",
                      event.conversation_kind, event.sender_id, event.conversation_id,
                      message_preview(event.text, self._settings.telegram_token))
        try:
            reply = await asyncio.get_running_loop().run_in_executor(None, self._handler, event)
            if reply is not None:
                await self.send_reply(event, reply)
            elif log_allowed:
                _log.info("No reply for %s message user=%s chat=%s",
                          event.conversation_kind, event.sender_id, event.conversation_id)
        except Exception as error:
            _log.warning("Telegram command failed (%s)", type(error).__name__)

    def _message_log_allowed(self, event: MessageEvent) -> bool:
        """Gate disclosure using access settings without authorizing any operation."""
        if not self._settings.telegram_message_log_enabled:
            return False
        if event.sender_id not in self._settings.allowed_users:
            return False
        return event.conversation_kind == "private" or (
            event.conversation_kind == "group" and self._settings.groups_enabled
            and event.conversation_id in self._settings.allowed_groups
        )

    def _scheduled_log_kind(self, target: str) -> Optional[str]:
        """Allow scheduled delivery summaries only for authorized destinations."""
        if not self._settings.telegram_message_log_enabled:
            return None
        if target in self._settings.allowed_users:
            return "private"
        if self._settings.groups_enabled and target in self._settings.allowed_groups:
            return "group"
        return None

    async def send_reply(self, event: MessageEvent, content: Union[str, OutgoingMessage]) -> None:
        """Reply within the original chat using plain text or captioned PNG document."""
        payload = OutgoingMessage(content) if isinstance(content, str) else content
        chat_id = event.reply_context["chat_id"]
        reply = ReplyParameters(message_id=int(event.reply_context["message_id"]),
                                allow_sending_without_reply=True)
        log_kind = event.conversation_kind if self._message_log_allowed(event) else None
        await self._send_payload(chat_id, payload, reply, log_kind=log_kind)

    async def _send_payload(self, chat_id: Union[int, str], content: OutgoingMessage,
                            reply: Optional[ReplyParameters] = None,
                            log_kind: Optional[str] = None) -> str:
        bot = self._application.bot
        if content.attachments:
            if len(content.attachments) != 1:
                raise ValueError("Telegram news needs exactly one document")
            attachment = content.attachments[0]
            if len(content.text.encode("utf-16-le")) // 2 > 1024:
                raise ValueError("Telegram document caption is too long")
            result = await bot.send_document(chat_id=chat_id, document=BytesIO(attachment.content),
                                             filename=attachment.filename, caption=content.text,
                                             parse_mode=None, reply_parameters=reply)
            if log_kind is not None:
                _log.info("Sent %s document chat=%s message=%s file=%s bytes=%s type=%s caption=%s",
                          log_kind, chat_id, result.message_id,
                          message_preview(attachment.filename, self._settings.telegram_token),
                          len(attachment.content),
                          message_preview(attachment.media_type, self._settings.telegram_token),
                          message_preview(content.text, self._settings.telegram_token))
            return str(result.message_id)
        message_id = ""
        preview = message_preview(content.text, self._settings.telegram_token) if log_kind else ""
        chunks = split_text(content.text)
        for index, chunk in enumerate(chunks, 1):
            result = await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=None, reply_parameters=reply)
            message_id = str(result.message_id)
            if log_kind is not None:
                _log.info("Sent %s text chat=%s message=%s part=%s/%s: %s",
                          log_kind, chat_id, message_id, index, len(chunks), preview)
        return message_id

    async def media_path(self, media: Mapping[str, Any]) -> Path:
        """Resolve an SDK file only inside the explicitly mounted local cache."""
        if self._tgsetu is None or not self._settings.telegram_local_mode:
            raise ValueError("Telegram local media retrieval is unavailable")
        file_id = media.get("file_id")
        if not isinstance(file_id, str) or not file_id:
            raise ValueError("Telegram media has no retrieval identity")
        result = await self._application.bot.get_file(
            file_id, read_timeout=300, connect_timeout=10, pool_timeout=10,
        )
        raw_path = result.file_path
        if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
            raise ValueError("Telegram did not return a local cache path")
        cache_root = self._tgsetu.config.cache_root.resolve(strict=True)
        source = Path(raw_path)
        resolved = source.resolve(strict=True)
        try:
            resolved.relative_to(cache_root)
        except ValueError:
            raise ValueError("Telegram file is outside the configured cache") from None
        if resolved == cache_root or not resolved.is_file():
            raise ValueError("Telegram cache source is not a file")
        # Preserve components for the saver's race-safe, no-symlink fd walk.
        return source

    async def send_notice(self, chat_id: str, text: str, reply_to_message_id: str = "") -> str:
        """Queue a bounded notice, or return a receipt for a direct send."""
        if self._notice_pending is not None:
            key = (chat_id, reply_to_message_id)
            if key not in self._notice_pending and len(self._notice_pending) >= 256:
                _log.warning("Telegram archive notice queue is full; file state is retained")
                raise ValueError("Telegram archive notice queue is full")
            self._notice_pending[key] = text
            self._notice_event.set()
            return ""
        return await self._send_archive_notice(chat_id, text, reply_to_message_id)

    async def _send_archive_notice(self, chat_id: str, text: str,
                                   source_id: str = "") -> str:
        """Retry only explicit short rate-limit rejections, never unknown outcomes."""
        reply = (
            ReplyParameters(message_id=int(source_id), allow_sending_without_reply=True)
            if source_id else None
        )
        receipt = ""
        for index, chunk in enumerate(split_text(text)):
            if index:
                await asyncio.sleep(1.05)
            for attempt in range(3):
                try:
                    result = await self._application.bot.send_message(
                        chat_id=int(chat_id), text=chunk, parse_mode=None, reply_parameters=reply,
                    )
                    receipt = str(result.message_id)
                    break
                except RetryAfter as error:
                    retry = error.retry_after
                    seconds = retry.total_seconds() if hasattr(retry, "total_seconds") else float(retry)
                    if attempt == 2 or seconds > 30:
                        raise
                    await asyncio.sleep(max(0.0, seconds))
        return receipt

    async def _send_news(self, target: str, content: OutgoingMessage) -> str:
        """Classify only explicit API rejections; network results remain uncertain."""
        try:
            return await self._send_payload(int(target), content,
                                            log_kind=self._scheduled_log_kind(target))
        except RetryAfter as error:
            value = error.retry_after
            seconds = value.total_seconds() if hasattr(value, "total_seconds") else float(value)
            raise DeliveryRejected(retry_after=seconds) from None
        except (Forbidden, BadRequest):
            raise DeliveryRejected(permanent=True) from None
