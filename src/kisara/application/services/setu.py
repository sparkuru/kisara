"""Archive confirmed media from a quoted private OneBot forward or file message.

Copy config/features/setu/config.toml.example to config.toml, enable it, and
list allowed_users already present in KISARA_ALLOWED_USERS. A missing file
disables the feature. Ordinary media and unquoted forwards get no automatic
archive reply. Quote a merged forward or file message with 保存, setu, or /setu to create one
confirmation prompt; nested forwards obey max_depth and max_nodes. Quote the
prompt and reply 保存 to save before confirm_timeout_seconds (default 60s).
Quote either source with direct_confirm_words (default 直接保存) to save immediately
without a question. The prompt displays the first configured confirmation word;
later words and 确认 remain accepted aliases. Cancellation words are ignored.
Legacy cancel_words config is accepted but inert. Setu replies use pangu spacing.
Downloads start only after confirmation; the result reports saved and failed
counts and the actual save directory, quoting the user command that started the save.
Once saving is claimed, a start notice quotes that command and counts only
unfinished attachments before their first lookup or transfer. Its best-effort
delivery does not replace the confirmation or retry-result identity.
Repeating confirmation retries failed items without replacing completed files.
For a direct save, quote its result to retry failures with the confirmation word.
If a file batch fails after its confirmation deadline, a fresh configured
confirmation window from completion keeps that file retry actionable.
After expiry, a fresh command quoting the original source rearms its unfinished
batch with matching metadata and preserved checkpoints; old confirmations stay
expired. Direct duplicate replies distinguish active saves from completion.

save_mode=date_original uses YYYY-MM-DD/original-name; timestamp_hash uses a
China Standard Time timestamp and SHA-256 filename for non-archive media.
File-kind archives retain their safe original basename in both layouts;
different-content name conflicts add _timestamp before the complete extension.
Matching original or stamped archives are reused without extracting content.
Archive publication uses Linux/Unix directory locks and non-overwriting links.
max_file_bytes and max_batch_bytes bound transfers. SetuStore persists batch metadata in
KISARA_STATE_DIR/setu.sqlite3, separate from the saved media. Compose mounts
host data/kisara/setu at /app/setu for preview and deployment; save_root must
name that writable container directory. The startup script prepares group
access; direct Compose users may set KISARA_SETU_GID to their primary group ID.
The OneBot development path shares the same archive and SQLite state.

NapCat may expose video through local QQ cache paths. The read-only mount at
/app/.config/QQ, local_media_root, and a media-directory allowlist constrain
copies; remote media must come from approved HTTPS QQ domains. Unreadable
sources are reported as failures. The offline console has no OneBot media.
File attachments prefer raw file_id for resolution and retain the raw file
basename separately as name. Their get_file call may await a complete NapCat download
under a separate bounded deadline; ordinary chat requests keep their short wait.
File downloads directly under mounted NapCat/temp are also approved. When a
native file is owner-only, a canonical-ID OneBot chunk stream provides its bytes
without permission changes. Bounded private spooling and validated size/order/
completion precede the same saver, archive publication and retry checkpoints.
The older forward_archive configuration and data path must be moved to setu
when upgrading; the new setu.sqlite3 starts with an empty batch history.
"""

import asyncio
import json
import logging
import threading
import time
import tempfile
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Mapping, Optional, Protocol, Sequence, Set, Union

from kisara.bot.contracts import MessageEvent, MessageSegment
from kisara.config.setu import SetuConfig
from kisara.infrastructure.persistence.setu_files import SetuFileError, SetuFileSaver
from kisara.infrastructure.persistence.setu import SetuStore
from kisara.utils.pangu import pangu


_log = logging.getLogger("kisara.setu")
MEDIA_KINDS = {"image", "video", "file", "record"}
SETU_COMMAND = "/setu"
SETU_START_WORDS = frozenset({"保存", "setu", SETU_COMMAND})


class SetuGateway(Protocol):
    """Expose only the OneBot capabilities needed by this workflow."""

    async def fetch_forward(self, identifier: str) -> Sequence[Mapping[str, Any]]:
        """Return the child messages of one merged forward."""

    async def send_private(self, user_id: str, text: str,
                           quote_id: str = "") -> str:
        """Send a private message and return its platform message ID."""

    async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
        """Return a URL or approved local path for one media item."""

    async def download_file(self, media: Mapping[str, Any], output: BinaryIO,
                            maximum: int) -> None:
        """Copy a canonical file through the bounded native OneBot stream."""


class SetuProcessor(Protocol):
    """Replace the final attachment-processing step without changing collection."""

    def save(self, source: Dict[str, object], location: Union[str, BinaryIO],
             timestamp: float, remaining_bytes: int) -> Dict[str, object]:
        """Process and store one confirmed attachment."""


class Setu:
    """Own one confirmation and save workflow per quoted forward or file message."""

    def __init__(self, config: SetuConfig, state_dir: str,
                 processor: Optional[SetuProcessor] = None) -> None:
        """Initialize durable workflow state and the selected storage strategy."""
        self._config = config
        self._store = SetuStore(state_dir)
        self._saver = processor or SetuFileSaver(config)
        self._transfer_slots: Optional[asyncio.Semaphore] = None
        self._transfer_loop: Optional[asyncio.AbstractEventLoop] = None

    def is_start_word(self, text: str) -> bool:
        """Share quoted-source trigger recognition with the transport adapter."""
        word = text.strip().casefold()
        return word in SETU_START_WORDS or word in self._config.direct_confirm_words

    def is_authorized(self, event: MessageEvent) -> bool:
        """Apply feature permission before the adapter resolves a quoted source."""
        return (event.engine == "onebot" and event.conversation_kind == "private" and
                event.sender_id in self._config.allowed_users)

    async def handle(self, event: MessageEvent, gateway: SetuGateway) -> bool:
        """Consume an authorized quoted source or a pending confirmation."""
        if not self.is_authorized(event):
            return False
        now = time.time()
        word = event.text.strip().casefold()
        sources = tuple(segment for segment in event.segments if segment.kind in {"forward", "file"})
        if self.is_start_word(word) and event.reply_context.get("setu_source_id") and sources:
            media, unsupported = await self._extract(sources, gateway)
            if not media and not unsupported:
                await self._reply(gateway, event.sender_id, "这条消息中没有可保存的附件。")
                return True
            source_id = str(event.reply_context["setu_source_id"])
            self._store.add_setu(
                event.instance_id, event.sender_id, source_id, media, unsupported, now,
            )
            direct = word in self._config.direct_confirm_words
            action, batch = self._store.prepare_source(
                event.instance_id, event.sender_id, source_id, media, now,
                self._config.confirm_timeout_seconds, direct,
            )
            if action == "save" and batch is not None:
                await self._save(batch, gateway, event.message_id, direct=True)
            elif action == "prompt" and batch is not None:
                await self._prompt(batch, gateway, now)
                _log.info("Prompted setu for private user %s", event.sender_id)
            elif direct or action in {"changed", "missing", "expired"}:
                replies = {
                    "saving": "这批附件正在保存，请稍后再试。",
                    "saved": "这批附件已经保存完成。",
                    "changed": "原附件信息已变化，无法安全续存；请引用新的文件消息。",
                    "missing": "这条消息的归档记录已过期，无法续存；请重新发送文件后引用保存。",
                    "expired": "这批附件无法续存，请引用新的文件消息。",
                }
                await self._reply(gateway, event.sender_id, replies[action])
            return True
        if word in self._config.confirm_words or word in {"保存", "确认"}:
            await self._confirmation(event, gateway, now)
            return True
        if self.is_start_word(word):
            await self._reply(gateway, event.sender_id, "请引用合并转发或文件消息并发送保存、setu 或 /setu。")
            return True
        return False

    async def run(self, gateway: SetuGateway) -> None:
        """Retry interrupted prompts while the adapter is connected."""
        self._store.recover_saving()
        while True:
            try:
                now = time.time()
                self._store.expire(now)
                for batch in self._store.due(now):
                    await self._prompt(batch, gateway, now)
                for batch in self._store.unprompted(now):
                    await self._send_prompt(batch, gateway, now)
            except Exception:
                _log.exception("Setu scheduler failed")
            await asyncio.sleep(1)

    async def _extract(self, segments: Sequence[MessageSegment],
                       gateway: SetuGateway) -> tuple:
        """Walk nested forwards with bounded recursion and node count."""
        media: List[Dict[str, Any]] = []
        unsupported = 0
        nodes = 0
        visited: Set[str] = set()

        async def walk(items: Sequence[MessageSegment], depth: int) -> None:
            """Visit media and recursively retrieved forward nodes."""
            nonlocal unsupported, nodes
            for item in items:
                nodes += 1
                if nodes > self._config.max_nodes:
                    unsupported += 1
                    return
                if item.kind in MEDIA_KINDS:
                    data = item.data
                    media.append({
                        "kind": item.kind,
                        "file": str((data.get("file_id") or data.get("file") or "")
                                    if item.kind == "file" else
                                    (data.get("file") or data.get("file_id") or "")),
                        "name": str(data.get("file_name") or data.get("name") or
                                    data.get("file") or ""),
                        "url": str(data.get("url") or ""),
                        "size": str(data.get("file_size") or data.get("size") or ""),
                    })
                    continue
                if item.kind != "forward":
                    continue
                identifier = str(item.data.get("id") or "")
                if not identifier or depth >= self._config.max_depth or identifier in visited:
                    unsupported += 1
                    continue
                visited.add(identifier)
                try:
                    children = item.data.get("content")
                    if not isinstance(children, list):
                        children = await gateway.fetch_forward(identifier)
                    for child in children:
                        if nodes >= self._config.max_nodes:
                            unsupported += 1
                            return
                        if not isinstance(child, Mapping):
                            unsupported += 1
                            continue
                        raw = child.get("message") or child.get("content")
                        if raw is None and child.get("type") == "node":
                            data = child.get("data")
                            raw = data.get("content") if isinstance(data, Mapping) else None
                        if raw is None and "type" in child:
                            raw = [child]
                        await walk(_segments(raw), depth + 1)
                except Exception:
                    _log.exception("Could not expand forwarded message")
                    unsupported += 1
                finally:
                    visited.remove(identifier)

        await walk(segments, 0)
        return media, unsupported

    async def _prompt(self, batch: Mapping[str, Any],
                      gateway: SetuGateway, now: float) -> None:
        """Send one question quoting the selected source message."""
        if not self._store.mark_awaiting(batch["id"], now + self._config.confirm_timeout_seconds):
            return
        await self._send_prompt(batch, gateway, now)

    async def _send_prompt(self, batch: Mapping[str, Any],
                           gateway: SetuGateway, now: float) -> None:
        """Send or retry the question while preserving the batch identity."""
        media = json.loads(batch["media_json"])
        self._store.retry_prompt_after(batch["id"], now + 30)
        counts = {kind: sum(item["kind"] == kind for item in media) for kind in MEDIA_KINDS}
        summary = (
            "这条消息共 {} 张图片、{} 个视频、{} 个文件；\n"
            '引用这条消息并回复 "{}" 以保存（超时 {}s 后自动取消）。'
        ).format(
            counts["image"], counts["video"], counts["file"],
            self._config.confirm_words[0], self._config.confirm_timeout_seconds,
        )
        try:
            prompt_id = await self._reply(
                gateway,
                batch["user_id"], summary, batch["first_message_id"]
            )
            self._store.set_prompt(batch["id"], prompt_id or "unknown")
        except Exception:
            _log.exception("Could not send setu confirmation")

    async def _confirmation(self, event: MessageEvent,
                            gateway: SetuGateway, now: float) -> None:
        """Apply a confirmation only to the quoted prompt."""
        batches = self._store.awaiting(event.instance_id, event.sender_id, now)
        quoted = str(event.reply_context.get("quoted_message_id") or "")
        matches = [batch for batch in batches if batch["prompt_id"] == quoted] if quoted else []
        selected = matches[0] if len(matches) == 1 else None
        if selected is None:
            answer = "没有可确认的归档批次。" if not batches else "请引用对应的归档提示后再确认。"
            await self._reply(gateway, event.sender_id, answer)
            return
        if not self._store.claim_save(selected["id"], now):
            await self._reply(gateway, event.sender_id, "这批附件正在处理或已经处理。")
            return
        await self._save(selected, gateway, event.message_id)

    async def _save(self, batch: Mapping[str, Any], gateway: SetuGateway,
                    command_id: str, direct: bool = False) -> None:
        """Checkpoint each item so a restart can retry only unfinished media."""
        media = json.loads(batch["media_json"])
        pending = [item for item in media if not item.get("saved_path")]
        categories = []
        for kind, label in (("file", "个文件"), ("video", "个视频"),
                            ("image", "张图片"), ("record", "条语音")):
            count = sum(item["kind"] == kind for item in pending)
            if count:
                categories.append("{} {}".format(count, label))
        if categories:
            try:
                await self._reply(gateway, batch["user_id"],
                                  "正在保存以上{}。".format("、".join(categories)), command_id)
            except Exception as error:
                _log.warning("Could not send setu save-start notice (%s)", type(error).__name__)
        total = sum(int(item.get("saved_size", 0)) for item in media)
        failures = 0
        for item in media:
            if item.get("saved_path"):
                continue
            try:
                size_text = str(item.get("size") or "")
                reported_size = int(size_text) if size_text.isdigit() else 0
                if reported_size > self._config.max_file_bytes or \
                        total + reported_size > self._config.max_batch_bytes:
                    raise ValueError("Media exceeds the configured size limit.")
                location = await gateway.media_location(item)
                try:
                    result = await self._save_file(
                        item, location, batch["first_at"],
                        self._config.max_batch_bytes - total,
                    )
                except PermissionError:
                    if item["kind"] != "file":
                        raise
                    maximum = min(self._config.max_file_bytes,
                                  self._config.max_batch_bytes - total)
                    with tempfile.SpooledTemporaryFile(max_size=1048576, mode="w+b") as stream:
                        await gateway.download_file(item, stream, maximum)
                        stream.seek(0)
                        result = await self._save_file(
                            item, stream, batch["first_at"], maximum,
                        )
                except Exception:
                    refreshed = await gateway.media_location(item, refresh=True)
                    if refreshed == location:
                        raise
                    result = await self._save_file(
                        item, refreshed, batch["first_at"],
                        self._config.max_batch_bytes - total,
                    )
                item["saved_path"] = result["path"]
                item["saved_size"] = result["size"]
                item["sha256"] = result["sha256"]
                item.pop("error", None)
                total += int(result["size"])
            except Exception as error:
                failures += 1
                item["error"] = type(error).__name__
                detail = str(error) if isinstance(error, SetuFileError) else type(error).__name__
                _log.warning("Could not archive one media item: %s", detail)
            self._store.update_media(batch["id"], media)
        saved = sum(bool(item.get("saved_path")) for item in media)
        retry_window = self._config.confirm_timeout_seconds if failures and any(
            item["kind"] == "file" for item in media
        ) else 0
        self._store.finish(
            batch["id"], "saved" if not failures else "awaiting",
            completed_at=time.time() if retry_window else None,
            retry_window_seconds=retry_window,
        )
        answer = "归档完成：共 {} 项，已保存 {} 项，失败 {} 项。".format(
            len(media), saved, failures)
        directories = sorted({str(Path(item["saved_path"]).parent)
                              for item in media if item.get("saved_path")})
        answer += "保存目录：{}。".format("、".join(directories) if directories
                                       else str(self._config.save_root))
        if failures:
            answer += ("请引用这条结果消息并回复“{}”重试失败项。" if direct else
                       "可再次回复“{}”重试失败项。").format(
                self._config.confirm_words[0],
            )
        result_id = await self._reply(gateway, batch["user_id"], answer, command_id)
        if direct and failures and result_id:
            self._store.set_prompt(batch["id"], result_id)

    async def _reply(self, gateway: SetuGateway, user_id: str, text: str,
                     quote_id: str = "") -> str:
        """Apply plain-text spacing to every setu reply."""
        return await gateway.send_private(user_id, pangu(text), quote_id)

    async def _save_file(self, item: Dict[str, Any], location: Union[str, BinaryIO],
                         timestamp: float, remaining: int) -> Dict[str, object]:
        """Run bounded file transfer without blocking the OneBot event loop."""
        loop = asyncio.get_running_loop()
        if self._transfer_loop is not loop:
            self._transfer_loop = loop
            self._transfer_slots = asyncio.Semaphore(4)
        slots = self._transfer_slots
        assert slots is not None
        await slots.acquire()
        completed = loop.create_future()

        def worker() -> None:
            """Return a transfer result to the owning event loop."""
            try:
                result = self._saver.save(item, location, timestamp, remaining)
                error = None
            except Exception as caught:
                result = None
                error = caught

            def resolve() -> None:
                """Release the slot even if the waiting message was cancelled."""
                slots.release()
                if completed.done():
                    return
                if error is not None:
                    completed.set_exception(error)
                else:
                    completed.set_result(result)

            if not loop.is_closed():
                loop.call_soon_threadsafe(resolve)

        threading.Thread(target=worker, name="setu-save", daemon=True).start()
        try:
            while not completed.done():
                await asyncio.sleep(0.05)
            return completed.result()
        except asyncio.CancelledError:
            if completed.done() and not completed.cancelled():
                completed.exception()
            else:
                completed.cancel()
            raise


def _segments(raw: object) -> List[MessageSegment]:
    """Normalize nested OneBot nodes without importing the transport adapter."""
    if not isinstance(raw, list):
        return []
    return [MessageSegment(str(item["type"]), item["data"])
            for item in raw if isinstance(item, dict) and isinstance(item.get("data"), dict)
            and isinstance(item.get("type"), str)]
