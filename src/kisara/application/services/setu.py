"""Private setu confirmation and save workflow."""

import asyncio
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence, Set

from kisara.bot.contracts import MessageEvent, MessageSegment
from kisara.config.setu import SetuConfig
from kisara.infrastructure.persistence.setu_files import SetuFileError, SetuFileSaver
from kisara.infrastructure.persistence.setu import SetuStore


_log = logging.getLogger("kisara.setu")
MEDIA_KINDS = {"image", "video", "file", "record"}
SETU_COMMAND = "/setu"


class SetuGateway(Protocol):
    """Expose only the OneBot capabilities needed by this workflow."""

    async def fetch_forward(self, identifier: str) -> Sequence[Mapping[str, Any]]:
        """Return the child messages of one merged forward."""

    async def send_private(self, user_id: str, text: str,
                           quote_id: str = "") -> str:
        """Send a private message and return its platform message ID."""

    async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
        """Return a URL or approved local path for one media item."""


class SetuProcessor(Protocol):
    """Replace the final attachment-processing step without changing collection."""

    def save(self, source: Dict[str, object], location: str,
             timestamp: float, remaining_bytes: int) -> Dict[str, object]:
        """Process and store one confirmed attachment."""


class Setu:
    """Own one confirmation and save workflow per merged forward."""

    def __init__(self, config: SetuConfig, state_dir: str,
                 processor: Optional[SetuProcessor] = None) -> None:
        """Initialize durable workflow state and the selected storage strategy."""
        self._config = config
        self._store = SetuStore(state_dir)
        self._saver = processor or SetuFileSaver(config)
        self._transfer_slots: Optional[asyncio.Semaphore] = None
        self._transfer_loop: Optional[asyncio.AbstractEventLoop] = None

    async def handle(self, event: MessageEvent, gateway: SetuGateway) -> bool:
        """Consume an authorized merged forward or a pending confirmation."""
        if event.engine != "onebot" or event.conversation_kind != "private":
            return False
        if event.sender_id not in self._config.allowed_users:
            return False
        now = time.time()
        word = event.text.strip().casefold()
        forwards = tuple(segment for segment in event.segments if segment.kind == "forward")
        if word == SETU_COMMAND and event.reply_context.get("setu_source_id") and forwards:
            media, unsupported = await self._extract(forwards, gateway)
            if not media and not unsupported:
                await gateway.send_private(event.sender_id, "这条转发中没有可保存的附件。")
                return True
            source_id = str(event.reply_context["setu_source_id"])
            batch = self._store.add_setu(
                event.instance_id, event.sender_id, source_id, media, unsupported, now,
            )
            if batch is not None:
                await self._prompt(batch, gateway, now)
                _log.info("Prompted setu for private user %s", event.sender_id)
            return True
        if word in self._config.confirm_words | self._config.cancel_words | {SETU_COMMAND}:
            if word == SETU_COMMAND and not self._store.awaiting(
                event.instance_id, event.sender_id, now,
            ):
                await gateway.send_private(event.sender_id, "请引用合并转发并发送 /setu。")
            else:
                await self._confirmation(event, gateway, word, now)
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
                        "file": str(data.get("file") or data.get("file_id") or ""),
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
        """Send one question quoting the merged forward."""
        if not self._store.mark_awaiting(batch["id"], now + self._config.confirm_timeout_seconds):
            return
        await self._send_prompt(batch, gateway, now)

    async def _send_prompt(self, batch: Mapping[str, Any],
                           gateway: SetuGateway, now: float) -> None:
        """Send or retry the question while preserving the batch identity."""
        media = json.loads(batch["media_json"])
        self._store.retry_prompt_after(batch["id"], now + 30)
        counts = {kind: sum(item["kind"] == kind for item in media) for kind in MEDIA_KINDS}
        summary = "这条合并转发共 {} 张图片、{} 个视频、{} 个文件、{} 条语音。".format(
            counts["image"], counts["video"], counts["file"], counts["record"],
        )
        if batch["unsupported"]:
            summary += "另有 {} 个未能解析的节点。".format(batch["unsupported"])
        cancel_word = "取消" if "取消" in self._config.cancel_words else sorted(self._config.cancel_words)[0]
        summary += "回复{}确认，或回复“{}”取消。".format(
            self._confirmation_options(), cancel_word,
        )
        try:
            prompt_id = await gateway.send_private(
                batch["user_id"], summary, batch["first_message_id"]
            )
            self._store.set_prompt(batch["id"], prompt_id or "unknown")
        except Exception:
            _log.exception("Could not send setu confirmation")

    async def _confirmation(self, event: MessageEvent,
                            gateway: SetuGateway, word: str,
                            now: float) -> None:
        """Apply a quoted reply or use the newest prompted batch."""
        batches = self._store.awaiting(event.instance_id, event.sender_id, now)
        quoted = str(event.reply_context.get("quoted_message_id") or "")
        matches = [batch for batch in batches if batch["prompt_id"] == quoted] if quoted else []
        selected = matches[0] if len(matches) == 1 else (
            next((batch for batch in reversed(batches) if batch["prompt_id"]), None)
            if not quoted else None
        )
        if selected is None:
            answer = "没有可确认的归档批次。" if not batches else "请引用对应的归档提示后再确认。"
            await gateway.send_private(event.sender_id, answer)
            return
        if word in self._config.cancel_words:
            self._store.finish(selected["id"], "cancelled")
            await gateway.send_private(event.sender_id, "已取消这批附件的保存。")
            return
        if not self._store.claim_save(selected["id"], now):
            await gateway.send_private(event.sender_id, "这批附件正在处理或已经处理。")
            return
        await self._save(selected, gateway)

    async def _save(self, batch: Mapping[str, Any], gateway: SetuGateway) -> None:
        """Checkpoint each item so a restart can retry only unfinished media."""
        media = json.loads(batch["media_json"])
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
        self._store.finish(batch["id"], "saved" if not failures else "awaiting")
        answer = "归档完成：共 {} 项，已保存 {} 项，失败 {} 项。".format(
            len(media), saved, failures)
        directories = sorted({str(Path(item["saved_path"]).parent)
                              for item in media if item.get("saved_path")})
        answer += "保存目录：{}。".format("、".join(directories) if directories
                                       else str(self._config.save_root))
        if failures:
            answer += "可再次回复{}重试失败项。".format(self._confirmation_options())
        await gateway.send_private(batch["user_id"], answer)

    def _confirmation_options(self) -> str:
        """List the built-in command and every configured confirmation word."""
        words = sorted(self._config.confirm_words - {SETU_COMMAND, "保存"})
        if "保存" in self._config.confirm_words:
            words.insert(0, "保存")
        return "、".join("“{}”".format(word) for word in (SETU_COMMAND, *words))

    async def _save_file(self, item: Dict[str, Any], location: str,
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
        while not completed.done():
            await asyncio.sleep(0.05)
        return completed.result()


def _segments(raw: object) -> List[MessageSegment]:
    """Normalize nested OneBot nodes without importing the transport adapter."""
    if not isinstance(raw, list):
        return []
    return [MessageSegment(str(item["type"]), item["data"])
            for item in raw if isinstance(item, dict) and isinstance(item.get("data"), dict)
            and isinstance(item.get("type"), str)]
