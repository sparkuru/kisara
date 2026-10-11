"""Telegram-only opt-in automatic media archiving through the local Bot API.

Authorized private users use /tgsetu on, off or status. Activation survives
restart. While on, each received photo/video/document is durably accepted,
then independently published flat under save_root; off stops future acceptance
while previously accepted jobs finish. Album quiet/max-wait windows choose a
shared caption and stable ordinals, never an original multi-selection boundary.
Late members append without renaming earlier files. /tgsetu retry <source-id>
requeues only failed files of that user's logical message/album.

Startup reads config/telegram/features/tgsetu/config.toml; a missing file
disables the feature. Restart after configuration changes.

SDK objects remain in the adapter. Global and feature authorization precedes
metadata effects and retrieval; workers recheck current policy. Files and
private SQLite metadata have separate paths. Owned bounded threads stream/hash
local cache bytes, and cancellation awaits their cleanup before SDK shutdown.
The archive records prepared candidate/hash evidence before publication so an
interrupted job can reconcile complete bytes without a second SDK download.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
import json
import logging
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable, Dict, FrozenSet, Mapping, Optional, Protocol

from kisara.bot.contracts import MessageEvent
from kisara.config.settings import ConfigurationError
from kisara.config.tgsetu import TgSetuConfig
from kisara.infrastructure.persistence.tgsetu import TgSetuQueueError, TgSetuStore
from kisara.infrastructure.persistence.tgsetu_files import TgSetuFileSaver


_log = logging.getLogger("kisara.telegram.tgsetu")


class TgSetuGateway(Protocol):
    """Only the Telegram SDK capabilities needed by an accepted archive job."""

    async def media_path(self, media: Mapping[str, Any]) -> Path:
        """Retrieve canonical file_id and return a confined local cache path."""

    async def send_notice(self, chat_id: str, text: str,
                          reply_to_message_id: str = "") -> str:
        """Send an authorized result and return its confirmed receipt ID."""


class TgSetu:
    """Own durable automatic acceptance and independently retryable file jobs."""

    def __init__(self, config: TgSetuConfig, state_dir: str, instance_id: str,
                 allowed_users: FrozenSet[str]) -> None:
        """Keep policy inert until an authorized action needs private state."""
        self._config = config
        self._state_dir = state_dir
        self._instance_id = instance_id
        self._allowed_users = allowed_users
        self._store: Optional[TgSetuStore] = None
        self._saver = TgSetuFileSaver(config)
        self._executor: Optional[ThreadPoolExecutor] = None
        self._running = False
        if config.enabled:
            state, save, cache = Path(state_dir).resolve(), config.save_root.resolve(), config.cache_root.resolve()
            if (state == save or state == cache or save in state.parents or cache in state.parents
                    or save == cache or save in cache.parents or cache in save.parents):
                raise ConfigurationError("Tgsetu state, cache and archive must be separate directories.")

    @property
    def config(self) -> TgSetuConfig:
        """Expose immutable policy for adapter eligibility and path validation."""
        return self._config

    def _authorized_user(self, user_id: str) -> bool:
        """Require both current allowlists, including nonempty global access."""
        return (self._config.enabled and user_id in self._allowed_users
                and user_id in self._config.allowed_users)

    def is_authorized(self, event: MessageEvent) -> bool:
        """Reject foreign engines/instances/groups before even opening state."""
        return (event.engine == "telegram" and event.instance_id == self._instance_id
                and event.conversation_kind == "private" and self._authorized_user(event.sender_id))

    def _state(self) -> TgSetuStore:
        """Lazily create only authorized feature metadata."""
        if self._store is None:
            self._store = TgSetuStore(self._state_dir)
        return self._store

    async def handle(self, event: MessageEvent, gateway: TgSetuGateway) -> bool:
        """Consume authorized commands/media without downloading in polling."""
        if not self.is_authorized(event):
            return False
        text = event.text.strip()
        parts = text.split()
        if parts and parts[0].casefold() == "/tgsetu":
            return await self._command(event, gateway, parts[1:])
        if parts and parts[0].casefold().startswith("/tgsetu@"):
            return False
        media = []
        for segment in event.segments:
            if segment.kind not in {"image", "video", "file"}:
                continue
            data = dict(segment.data)
            data["kind"] = segment.kind
            if not data.get("file_id"):
                continue
            media.append(data)
        if not media or not re.fullmatch(r"[1-9][0-9]*", event.message_id):
            return False
        if self._store is None and not (Path(self._state_dir) / "tgsetu.sqlite3").exists():
            return False
        store = self._state()
        if not store.is_active(self._instance_id, event.conversation_id, event.sender_id):
            return False
        try:
            now = time.time()
            # Transfer workers may be busy past an album's metadata deadline.
            store.freeze_due(self._instance_id, now, self._config, self._authorized_user)
            accepted = store.enqueue(self._instance_id, event.conversation_id, event.sender_id,
                                     event.message_id, media, now, self._config)
        except (TgSetuQueueError, TypeError, ValueError) as error:
            detail = str(error) if isinstance(error, TgSetuQueueError) else "Invalid media metadata."
            await self._notice(gateway, event.conversation_id, "Not accepted: " + detail, event.message_id)
            return True
        if accepted["accepted"]:
            await self._notice(gateway, event.conversation_id,
                               "Accepted {} file(s) from received message {}.".format(
                                   accepted["accepted"], event.message_id), event.message_id)
        return True

    async def _command(self, event: MessageEvent, gateway: TgSetuGateway,
                       arguments: list) -> bool:
        """Implement durable opt-in/status and scoped explicit failed retry."""
        if arguments not in ([], ["status"], ["on"], ["off"]) and not (
                len(arguments) == 2 and arguments[0] == "retry" and
                re.fullmatch(r"[1-9][0-9]*", arguments[1])):
            await self._notice(gateway, event.conversation_id,
                               "Usage: /tgsetu [on|off|status|retry <source-message-id>]", event.message_id)
            return True
        store = self._state()
        if arguments in (["on"], ["off"]):
            active = arguments == ["on"]
            store.set_active(self._instance_id, event.conversation_id, event.sender_id, active)
            answer = "Tgsetu is on. Received supported media will be archived." if active else (
                "Tgsetu is off. Already accepted files continue; new media is ignored.")
        elif arguments and arguments[0] == "retry":
            try:
                count = store.retry(self._instance_id, event.conversation_id, event.sender_id,
                                    arguments[1], self._config, time.time())
                answer = "Queued {} failed file(s) for retry; saved files are retained.".format(count)
                if not count:
                    answer += " No retryable failures found. Naming failures require a shorter caption/tags and a new message."
            except TgSetuQueueError as error:
                answer = str(error)
        else:
            active = store.is_active(self._instance_id, event.conversation_id, event.sender_id)
            answer = "Tgsetu is {}. Use /tgsetu on or /tgsetu off.".format("on" if active else "off")
        await self._notice(gateway, event.conversation_id, answer, event.message_id)
        return True

    async def run(self, gateway: TgSetuGateway) -> None:
        """Own bounded workers and await cooperative transfer cancellation."""
        if not self._config.enabled or not (self._allowed_users & self._config.allowed_users):
            return
        if self._running:
            raise RuntimeError("Tgsetu worker loop is already running.")
        self._running = True
        store = self._state()
        store.recover()
        self._executor = ThreadPoolExecutor(max_workers=self._config.workers,
                                            thread_name_prefix="tgsetu-copy")
        workers = []
        try:
            await self._blocking(self._saver.clean_stale_temporary)
            workers = [asyncio.create_task(self._worker(gateway)) for _ in range(self._config.workers)]
            await asyncio.gather(*workers)
        finally:
            for worker in workers:
                worker.cancel()
            if workers:
                await asyncio.gather(*workers, return_exceptions=True)
            self._executor.shutdown(wait=True)
            self._executor = None
            self._running = False

    async def _worker(self, gateway: TgSetuGateway) -> None:
        """Claim independent units while keeping same-unit budgets serialized."""
        store = self._state()
        next_prune = 0.0
        while True:
            now = time.time()
            if now >= next_prune:
                store.prune(now)
                next_prune = now + 3600
            store.freeze_due(self._instance_id, now, self._config, self._authorized_user)
            for failed in store.naming_failures(self._instance_id, self._authorized_user):
                await self._result(failed, gateway)
            member = store.claim(self._instance_id, self._authorized_user)
            if member is None:
                await asyncio.sleep(0.05)
                continue
            await self._process(member, gateway)

    async def _process(self, member: Mapping[str, Any], gateway: TgSetuGateway) -> None:
        """Retrieve/copy/checkpoint one claim, preserving partial successes."""
        store = self._state()
        try:
            if not self._authorized_user(str(member["user"])):
                store.fail(member["id"], "AuthorizationChanged", time.time(), queued=True)
                return
            remaining = self._config.max_unit_bytes - member["used_bytes"]
            if remaining <= 0:
                raise TgSetuQueueError("Logical message size limit reached.")
            result = None
            if member["candidate"] and member["sha256"] and member["size"] <= min(
                    remaining, self._config.max_file_bytes):
                result = await self._blocking(self._saver.reconcile, member["candidate"],
                                              member["sha256"], member["size"], cancellable=True)
            if result is None:
                media = json.loads(member["media_json"])
                if member["declared_size"] > min(remaining, self._config.max_file_bytes):
                    raise TgSetuQueueError("Logical message size limit reached.")
                location = await gateway.media_path(media)
                result = await self._blocking(self._save, member, location, remaining, cancellable=True)
            store.complete(member["id"], result, time.time())
        except asyncio.CancelledError:
            store.fail(member["id"], "Interrupted", time.time(), queued=True)
            raise
        except Exception as error:
            store.fail(member["id"], type(error).__name__, time.time())
            _log.warning("Archive item failed (%s)", type(error).__name__)
        await self._result(member, gateway)

    def _save(self, member: Mapping[str, Any], location: Path, remaining: int,
              stop: Optional[threading.Event] = None) -> Dict[str, Any]:
        """Keep temporary bytes and candidate intent inside one owned thread."""
        prepared = self._saver.prepare(location, remaining, stop)
        store = self._state()
        return self._saver.publish(prepared, json.loads(member["plan_json"]), member["first_at"],
                                   functools.partial(store.intent, member["id"]), member["candidate"], stop)

    async def _blocking(self, function: Callable[..., Any], *arguments: Any,
                        cancellable: bool = False) -> Any:
        """Await a bounded thread, signal stop and join it on cancellation."""
        executor = self._executor
        if executor is None:
            raise RuntimeError("Tgsetu transfer executor is not running.")
        stop = threading.Event()
        call = functools.partial(function, *arguments, stop=stop) if cancellable else functools.partial(function, *arguments)
        future = asyncio.get_running_loop().run_in_executor(executor, call)
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            stop.set()
            while not future.done():
                try:
                    await asyncio.shield(future)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if future.done() and not future.cancelled():
                future.exception()
            raise

    async def _result(self, member: Mapping[str, Any], gateway: TgSetuGateway) -> None:
        """Report actual received counts and filenames, with a retry selector."""
        summary = self._state().summary(str(member["unit_id"]))
        text = ("Archive: 1 logical unit; received {} Telegram message(s), {} file(s); saved {}, failed {}, pending {}. "
                "Directory: {}.").format(summary["messages"], summary["files"], summary["saved"],
                                         summary["failed"], summary["pending"], self._config.save_root)
        if summary["paths"]:
            text += "\nSaved: " + "; ".join(Path(path).name for path in summary["paths"])
        if summary["naming_failed"]:
            text += "\n{} naming failure(s): shorten caption/tags and resend as a new message; these files cannot be retried.".format(
                summary["naming_failed"])
        if summary["failed"] > summary["naming_failed"]:
            text += "\nRetry failed files: /tgsetu retry " + str(member["message_id"])
        media = json.loads(member["media_json"])
        if member["album"] and member["captionless"] and media.get("caption"):
            text += "\nLate caption retained; the frozen fallback names were kept."
        await self._notice(gateway, str(member["chat"]), text, str(member["message_id"]))

    async def _notice(self, gateway: TgSetuGateway, chat: str, text: str,
                      source_id: str = "") -> None:
        """A failed notification never changes durable file state or leaks SDK errors."""
        try:
            await gateway.send_notice(chat, text, source_id)
        except Exception as error:
            _log.warning("Archive notice failed (%s)", type(error).__name__)
