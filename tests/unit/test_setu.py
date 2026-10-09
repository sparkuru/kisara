"""Focused tests for private setu confirmation and file placement."""

import asyncio
import gc
import hashlib
import io
import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Mapping, Sequence, Tuple

import pytest

from kisara.application.services.setu import Setu
from kisara.bot.adapters.onebot_v11 import OneBotError
from kisara.bot.contracts import MessageEvent, MessageSegment
from kisara.config.setu import SetuConfig
from kisara.config.settings import ConfigurationError
from kisara.infrastructure.persistence.setu import SetuStore
from kisara.infrastructure.persistence.setu_files import (
    SetuFileError, SetuFileSaver, _check_url,
)


class FakeGateway:
    """Provide forward nodes, media locations, and captured private replies."""

    def __init__(self) -> None:
        """Set up deterministic protocol responses."""
        self.nodes: Dict[str, Sequence[Mapping[str, Any]]] = {}
        self.sent: List[Tuple[str, str, str]] = []
        self.fail_count = 0

    async def fetch_forward(self, identifier: str) -> Sequence[Mapping[str, Any]]:
        """Return one nested forward payload."""
        return self.nodes[identifier]

    async def send_private(self, user_id: str, text: str,
                           quote_id: str = "") -> str:
        """Capture the outgoing message and return its fake ID."""
        if self.fail_count:
            self.fail_count -= 1
            raise OSError("protocol connection unavailable")
        self.sent.append((user_id, text, quote_id))
        return "prompt-{}".format(len(self.sent))

    async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
        """Expose the configured local test file."""
        return str(media.get("url") or "")


def _config(tmp_path: Path, mode: str = "date_original") -> SetuConfig:
    """Enable the feature for one test sender and a local cache."""
    return replace(
        SetuConfig.disabled(), enabled=True,
        allowed_users=frozenset({"user-1"}), save_root=tmp_path / "archive",
        local_media_root=tmp_path / "cache", save_mode=mode,
    )


def _event(message_id: str, segments: Tuple[MessageSegment, ...],
           text: str = "", quote_id: str = "",
           setu_source_id: str = "") -> MessageEvent:
    """Build one private OneBot message."""
    if text:
        segments = segments + (MessageSegment("text", {"text": text}),)
    return MessageEvent(
        engine="onebot", instance_id="personal", message_id=message_id,
        conversation_kind="private", conversation_id="user-1", sender_id="user-1",
        segments=segments, reply_context={
            "quoted_message_id": quote_id,
            "setu_source_id": setu_source_id,
        },
    )


def _cache_file(config: SetuConfig, kind: str, name: str) -> Path:
    """Create a path under a realistic NapCat media directory."""
    path = config.local_media_root / "nt_qq_test" / "nt_data" / kind / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _forward_image(source: Path) -> MessageSegment:
    """Wrap one image in a merged-forward node."""
    return MessageSegment("forward", {"id": source.name, "content": [{"message": [
        {"type": "image", "data": {"file": source.name, "url": str(source)}},
    ]}]})


@pytest.mark.parametrize("mode", ["date_original", "timestamp_hash"])
def test_nested_forward_confirmation_saves_in_selected_layout(
    tmp_path: Path, mode: str,
) -> None:
    """Nested image and video nodes are counted and saved only after confirmation."""
    async def scenario() -> None:
        """Exercise collection, prompt, and confirmation in one event loop."""
        config = _config(tmp_path, mode)
        image = _cache_file(config, "Pic", "image-hash.jpg")
        video = _cache_file(config, "Video", "video-hash.mp4")
        image.write_bytes(b"image-content")
        video.write_bytes(b"video-content")
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        gateway.nodes["nested"] = [{"message": [
            {"type": "video", "data": {"file": video.name, "url": str(video)}}
        ]}]
        forward = MessageSegment("forward", {"id": "outer", "content": [
            {"message": [
                {"type": "image", "data": {"file": image.name, "url": str(image)}},
                {"type": "forward", "data": {"id": "nested"}},
            ]}
        ]})
        assert not await workflow.handle(_event("first", (forward,)), gateway)
        event = _event("request", (forward,), "/setu", "first", "first")
        assert await asyncio.wait_for(workflow.handle(event, gateway), 15)
        assert not config.save_root.exists()
        store = SetuStore(str(tmp_path / "state"))
        batch = store.awaiting("personal", "user-1", time.time())[0]
        assert batch["first_message_id"] == "first"
        workflow = Setu(config, str(tmp_path / "state"))
        assert gateway.sent[0][2] == "first"
        assert gateway.sent[0][1] == (
            "这条消息共 1 张图片、1 个视频、0 个文件；\n"
            '引用这条消息并回复 "保存" 以保存（超时 60s 后自动取消）。'
        )
        assert await asyncio.wait_for(workflow.handle(
            _event("confirm", (), "确认", "prompt-1"), gateway), 15)
        files = list(config.save_root.rglob("*"))
        names = [path.name for path in files if path.is_file()]
        assert len(names) == 2
        assert all(path.stat().st_mode & 0o777 == 0o640
                   for path in files if path.is_file())
        if mode == "date_original":
            assert sorted(names) == ["image-hash.jpg", "video-hash.mp4"]
            assert any(path.name.count("-") == 2 for path in files if path.is_dir())
        else:
            assert all(len(name.split("-")[-1].split(".")[0]) == 64 for name in names)
        assert "已保存 2 项，失败 0 项" in gateway.sent[-1][1]
        assert gateway.sent[-1][2] == "confirm"
        assert "保存目录：" in gateway.sent[-1][1]
        assert await asyncio.wait_for(workflow.handle(
            _event("repeat", (), "确认", "prompt-1"), gateway), 15)
        assert len([path for path in config.save_root.rglob("*") if path.is_file()]) == 2

    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["date_original", "timestamp_hash"])
def test_napcat_downloaded_file_cache_keeps_archive_name_and_bytes(
    tmp_path: Path, mode: str,
) -> None:
    """A get_file download may live directly in mounted NapCat/temp."""
    config = _config(tmp_path, mode)
    source = config.local_media_root / "NapCat" / "temp" / "native-download"
    source.parent.mkdir(parents=True)
    content = b"downloaded archive\x00\xff"
    source.write_bytes(content)
    result = SetuFileSaver(config).save(
        {"kind": "file", "name": "Original backup.tar.gz"}, str(source), 1000, 100,
    )
    archived = Path(str(result["path"]))
    assert archived.name == "Original backup.tar.gz"
    assert archived.read_bytes() == content
    assert result["size"] == len(content)
    assert result["sha256"] == hashlib.sha256(content).hexdigest()
    assert archived.stat().st_mode & 0o777 == 0o640


@pytest.mark.parametrize("kind", ["image", "video", "record", ""])
def test_napcat_temp_cache_is_only_for_explicit_file_segments(
    tmp_path: Path, kind: str,
) -> None:
    """The native file exception does not change ordinary media source rules."""
    config = _config(tmp_path)
    source = config.local_media_root / "NapCat" / "temp" / "source.zip"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"archive")
    metadata = {"name": "source.zip"}
    if kind:
        metadata["kind"] = kind
    with pytest.raises(SetuFileError, match="media cache"):
        SetuFileSaver(config).save(metadata, str(source), 1000, 100)
    assert not [path for path in config.save_root.rglob("*") if path.is_file()]


@pytest.mark.parametrize("relative", [
    "NapCat/config/private.json", "NapCat/data/private.db",
    "NapCat/temp-extra/archive.zip", "NapCat/temp/nested/archive.zip",
    "temp/archive.zip", "other/NapCat/temp/archive.zip",
])
def test_napcat_file_cache_does_not_allow_other_mounted_directories(
    tmp_path: Path, relative: str,
) -> None:
    """Only the observed direct-child download layout extends the allowlist."""
    config = _config(tmp_path)
    source = config.local_media_root / relative
    source.parent.mkdir(parents=True)
    source.write_bytes(b"archive")
    with pytest.raises(SetuFileError, match="media cache"):
        SetuFileSaver(config).save(
            {"kind": "file", "name": "archive.zip"}, str(source), 1000, 100,
        )
    assert not [path for path in config.save_root.rglob("*") if path.is_file()]


@pytest.mark.parametrize("outside_root", [False, True])
def test_napcat_file_cache_resolves_symlinks_before_authorizing(
    tmp_path: Path, outside_root: bool,
) -> None:
    """A download-directory symlink cannot make private files valid sources."""
    config = _config(tmp_path)
    target = (tmp_path / "private.zip" if outside_root else
              config.local_media_root / "NapCat" / "config" / "private.zip")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"private")
    link = config.local_media_root / "NapCat" / "temp" / "archive.zip"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)
    with pytest.raises(SetuFileError, match="outside"):
        SetuFileSaver(config).save(
            {"kind": "file", "name": "archive.zip"}, str(link), 1000, 100,
        )
    assert not [path for path in config.save_root.rglob("*") if path.is_file()]


def test_each_forward_has_an_immediate_separate_batch(tmp_path: Path) -> None:
    """Distinct forwarded messages never merge; duplicate source IDs are ignored."""
    store = SetuStore(str(tmp_path))
    item = [{"kind": "image", "file": "a.jpg", "url": ""}]
    first = store.add_setu("personal", "user-1", "first", item, 0, 1000)
    second = store.add_setu("personal", "user-1", "second", item, 0, 1001)
    assert first is not None and second is not None
    assert first["id"] != second["id"]
    assert len(store.due(1001)) == 2
    assert store.add_setu("personal", "user-1", "first", item, 0, 1002) is None


def test_real_shape_file_segments_preserve_distinct_ids_for_same_original_name(tmp_path: Path) -> None:
    """NapCat basename aliases cannot replace canonical IDs during collection."""
    async def scenario() -> None:
        """Save two same-named files by different opaque resolver keys."""
        config = _config(tmp_path, "timestamp_hash")
        first = _cache_file(config, "File", "cache-first")
        second = _cache_file(config, "File", "cache-second")
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        locations = {"canonical-first": str(first), "canonical-second": str(second)}
        calls: List[str] = []

        class IdGateway(FakeGateway):
            """Resolve only canonical keys, as the native file cache expects."""

            async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
                """Record canonical resolution and reject basename alias use."""
                identifier = str(media["file"])
                calls.append(identifier)
                assert media["name"] == "\u8d44\u6599.zip"
                return locations[identifier]

        gateway = IdGateway()
        forward = MessageSegment("forward", {"id": "merged", "content": [{"message": [
            {"type": "file", "data": {"file": "\u8d44\u6599.zip", "file_id": identifier,
                                      "file_size": str(path.stat().st_size)}}
            for identifier, path in [("canonical-first", first), ("canonical-second", second)]
        ]}]})
        workflow = Setu(config, str(tmp_path / "state"))
        assert await workflow.handle(_event("direct", (forward,), "\u76f4\u63a5\u4fdd\u5b58", "source", "source"), gateway)
        assert calls == ["canonical-first", "canonical-second"]
        archived = list(config.save_root.iterdir())
        assert len(archived) == 2
        assert {path.read_bytes() for path in archived} == {b"first", b"second"}
        assert (config.save_root / "\u8d44\u6599.zip").read_bytes() == b"first"
        assert "\u5df2\u4fdd\u5b58 2 \u9879\uff0c\u5931\u8d25 0 \u9879" in gateway.sent[-1][1]

    asyncio.run(scenario())


@pytest.mark.parametrize("kind", ["image", "video", "record"])
def test_nonfile_extraction_retains_previous_file_precedence(tmp_path: Path, kind: str) -> None:
    """Canonical ID precedence changes only file-kind attachments."""
    async def scenario() -> None:
        """Compare normalized media metadata for ordinary media."""
        workflow = Setu(_config(tmp_path), str(tmp_path / "state"))
        media, unsupported = await workflow._extract((MessageSegment(kind, {
            "file": "existing-media-key", "file_id": "other-id", "file_name": "original.jpg",
        }),), FakeGateway())
        assert unsupported == 0
        assert media[0]["file"] == "existing-media-key"
        assert media[0]["name"] == "original.jpg"

    asyncio.run(scenario())


@pytest.mark.parametrize("limit", ["file", "batch"])
def test_reported_file_sizes_reject_before_resolver(tmp_path: Path, limit: str) -> None:
    """Known excessive sizes never start the longer native file download wait."""
    async def scenario() -> None:
        """Reject a too-large item or a later item exceeding remaining batch bytes."""
        config = replace(_config(tmp_path), max_file_bytes=3, max_batch_bytes=5)
        source = _cache_file(config, "File", "first-id")
        source.write_bytes(b"one")
        calls: List[str] = []

        class CountingGateway(FakeGateway):
            """Observe exactly which sources reach native file resolution."""

            async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
                """Only the first in-limit item is expected to resolve."""
                calls.append(str(media["file"]))
                return str(source)

        items = [{"type": "file", "data": {
            "file": "second.zip", "file_id": "second-id", "file_size": "4" if limit == "file" else "3",
        }}]
        if limit == "batch":
            items.insert(0, {"type": "file", "data": {
                "file": "first.zip", "file_id": "first-id", "file_size": "3",
            }})
        forward = MessageSegment("forward", {"id": "merged", "content": [{"message": items}]})
        gateway = CountingGateway()
        workflow = Setu(config, str(tmp_path / "state"))
        assert await workflow.handle(_event("direct", (forward,), "\u76f4\u63a5\u4fdd\u5b58", "source", "source"), gateway)
        assert calls == ([] if limit == "file" else ["first-id"])
        assert "\u5931\u8d25 1 \u9879" in gateway.sent[-1][1]

    asyncio.run(scenario())


@pytest.mark.parametrize("direct", [False, True])
def test_save_start_notice_counts_categories_and_precedes_resolution_and_copy(
    tmp_path: Path, direct: bool,
) -> None:
    """Only claimed saves announce their pending files before the first side effect."""
    async def scenario() -> None:
        """Check the real mixed-category text and order in normal and direct workflows."""
        config = _config(tmp_path)
        source = _cache_file(config, "File", "cache-id")
        source.write_bytes(b"media")
        order: List[str] = []
        saver = SetuFileSaver(config)
        notice_delivered = [False]

        class RecordingSaver:
            """Verify the notice has completed before bytes are copied."""

            def save(self, item: Dict[str, object], location: str,
                     timestamp: float, remaining_bytes: int) -> Dict[str, object]:
                """Record actual publication after notice delivery and resolution."""
                assert notice_delivered[0]
                order.append("copy")
                return saver.save(item, location, timestamp, remaining_bytes)

        workflow = Setu(config, str(tmp_path / "state"), processor=RecordingSaver())

        class OrderedGateway(FakeGateway):
            """Observe the notice, durable claim, native lookup and final reply."""

            async def send_private(self, user_id: str, text: str, quote_id: str = "") -> str:
                """Finish the claimed start notice before any resolver is invoked."""
                if text.startswith("\u6b63\u5728\u4fdd\u5b58"):
                    assert order == []
                    assert quote_id == ("direct" if direct else "confirm")
                    assert text == "\u6b63\u5728\u4fdd\u5b58\u4ee5\u4e0a 2 \u4e2a\u6587\u4ef6\u30011 \u4e2a\u89c6\u9891\u30013 \u5f20\u56fe\u7247\u30011 \u6761\u8bed\u97f3\u3002"
                    with sqlite3.connect(str(tmp_path / "state" / "setu.sqlite3")) as database:
                        state, prompt_id = database.execute("SELECT state, prompt_id FROM batches").fetchone()
                    assert state == "saving"
                    assert prompt_id == ("source" if direct else "prompt-1")
                    await asyncio.sleep(0)
                    notice_delivered[0] = True
                    order.append("start")
                elif text.startswith("\u5f52\u6863\u5b8c\u6210"):
                    order.append("final")
                return await super().send_private(user_id, text, quote_id)

            async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
                """Require successfully delivered progress before native resolution."""
                assert notice_delivered[0]
                assert order[0] == "start"
                order.append("resolve")
                return str(source)

        gateway = OrderedGateway()
        nodes = [{"type": kind, "data": {"file": "{}-{}.{}".format(kind, index, suffix)}}
                 for kind, count, suffix in (("file", 2, "zip"), ("video", 1, "mp4"),
                                             ("image", 3, "jpg"), ("record", 1, "ogg"))
                 for index in range(count)]
        forward = MessageSegment("forward", {"id": "mixed", "content": [{"message": nodes}]})
        command = "\u76f4\u63a5\u4fdd\u5b58" if direct else "/setu"
        assert await workflow.handle(_event("direct" if direct else "request", (forward,), command,
                                           "source", "source"), gateway)
        if not direct:
            assert not order
            assert not config.save_root.exists()
            assert await workflow.handle(_event("confirm", (), "\u4fdd\u5b58", "prompt-1"), gateway)
        assert order == ["start"] + [entry for _ in range(7) for entry in ("resolve", "copy")] + ["final"]
        assert "\u5df2\u4fdd\u5b58 7 \u9879\uff0c\u5931\u8d25 0 \u9879" in gateway.sent[-1][1]
        notices_before = sum(text.startswith("\u6b63\u5728\u4fdd\u5b58") for _, text, _ in gateway.sent)
        assert await workflow.handle(_event("duplicate", (forward,), "\u76f4\u63a5\u4fdd\u5b58", "source", "source"), gateway)
        assert sum(text.startswith("\u6b63\u5728\u4fdd\u5b58") for _, text, _ in gateway.sent) == notices_before == 1

    asyncio.run(scenario())


@pytest.mark.parametrize("resolver_fails", [False, True])
def test_save_start_send_failure_is_private_and_preserves_actual_save_outcome(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, resolver_fails: bool,
) -> None:
    """Notice failure cannot strand saving or turn an item failure into success."""
    async def scenario() -> None:
        """Attempt progress once, then finish or retain retry according to the transfer."""
        config = _config(tmp_path)
        source = _cache_file(config, "File", "cache-id")
        source.write_bytes(b"archive")
        order: List[str] = []
        private_marker = "https://private.invalid/?token=notice-secret"

        class FailedNoticeGateway(FakeGateway):
            """Fail only the progress send while keeping the final result deliverable."""

            async def send_private(self, user_id: str, text: str, quote_id: str = "") -> str:
                """Return no progress ID and omit exception content from diagnostics."""
                if text.startswith("\u6b63\u5728\u4fdd\u5b58"):
                    order.append("start-attempt")
                    raise OSError(private_marker)
                order.append("final")
                return await super().send_private(user_id, text, quote_id)

            async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
                """Continue only after the attempted send and retain real transfer failure."""
                assert order == ["start-attempt"]
                order.append("resolve")
                if resolver_fails:
                    raise OneBotError(private_marker)
                return str(source)

        gateway = FailedNoticeGateway()
        workflow = Setu(config, str(tmp_path / "state"))
        segment = MessageSegment("file", {"file": "original.zip", "file_id": "canonical-id"})
        assert await workflow.handle(_event("direct", (segment,), "\u76f4\u63a5\u4fdd\u5b58", "source", "source"), gateway)
        assert order == ["start-attempt", "resolve", "final"]
        assert gateway.sent[-1][2] == "direct"
        expected = "\u5df2\u4fdd\u5b58 0 \u9879\uff0c\u5931\u8d25 1 \u9879" if resolver_fails else "\u5df2\u4fdd\u5b58 1 \u9879\uff0c\u5931\u8d25 0 \u9879"
        assert expected in gateway.sent[-1][1]
        with sqlite3.connect(str(tmp_path / "state" / "setu.sqlite3")) as database:
            state, prompt_id = database.execute("SELECT state, prompt_id FROM batches").fetchone()
        assert state == ("awaiting" if resolver_fails else "saved")
        if resolver_fails:
            assert prompt_id == "prompt-1"
        assert "Could not send setu save-start notice (OSError)" in caplog.text
        assert private_marker not in caplog.text

    asyncio.run(scenario())


def test_completed_checkpoints_skip_start_notice_on_claimed_confirmation(tmp_path: Path) -> None:
    """Recovery with all item checkpoints complete never announces more work."""
    async def scenario() -> None:
        """Confirm a recovered batch with no pending transfer and send only the final result."""
        config = _config(tmp_path)
        source = _cache_file(config, "File", "cache-id")
        source.write_bytes(b"archive")
        saved = SetuFileSaver(config).save({"kind": "file", "name": "done.zip"}, str(source), 1000, 100)
        workflow = Setu(config, str(tmp_path / "state"))
        metadata = [{"kind": "file", "name": "done.zip", "file": "id", "size": "7",
                     "saved_path": saved["path"], "saved_size": saved["size"], "sha256": saved["sha256"]}]
        batch = workflow._store.add_setu("personal", "user-1", "source", metadata, 0, time.time())
        assert batch is not None
        workflow._store.mark_awaiting(str(batch["id"]), time.time() + 60)
        workflow._store.set_prompt(str(batch["id"]), "existing-prompt")
        gateway = FakeGateway()
        assert await workflow.handle(_event("confirm", (), "\u4fdd\u5b58", "existing-prompt"), gateway)
        assert len(gateway.sent) == 1
        assert "\u5df2\u4fdd\u5b58 1 \u9879\uff0c\u5931\u8d25 0 \u9879" in gateway.sent[0][1]
        assert gateway.sent[0][2] == "confirm"
        assert Path(str(saved["path"])).read_bytes() == b"archive"

    asyncio.run(scenario())


@pytest.mark.parametrize("reason", ["timed out", "retcode=1200"])
def test_file_protocol_failure_preserves_canonical_metadata_for_retry(tmp_path: Path, reason: str) -> None:
    """Native timeout/rejection remains a failed item and retries the original ID."""
    async def scenario() -> None:
        """Retry an unsuccessful direct archive resolver without a new batch."""
        config = _config(tmp_path)
        source = _cache_file(config, "File", "canonical-id")
        source.write_bytes(b"archive")
        calls: List[str] = []

        class RetryGateway(FakeGateway):
            """Fail the first native resolution, then expose a valid cache source."""

            async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
                """Retain canonical identity across an expected protocol failure."""
                calls.append(str(media["file"]))
                if len(calls) == 1:
                    raise OneBotError(reason)
                return str(source)

        gateway = RetryGateway()
        workflow = Setu(config, str(tmp_path / "state"))
        forward = MessageSegment("forward", {"id": "merged", "content": [{"message": [
            {"type": "file", "data": {"file": "original.tar.gz", "file_id": "canonical-id",
                                      "file_size": "7"}},
        ]}]})
        assert await workflow.handle(_event("direct", (forward,), "\u76f4\u63a5\u4fdd\u5b58", "source", "source"), gateway)
        assert "\u5df2\u4fdd\u5b58 0 \u9879\uff0c\u5931\u8d25 1 \u9879" in gateway.sent[-1][1]
        batches = SetuStore(str(tmp_path / "state")).awaiting("personal", "user-1", time.time())
        assert len(batches) == 1
        assert '"file": "canonical-id"' in str(batches[0]["media_json"])
        assert "OneBotError" in str(batches[0]["media_json"])
        assert batches[0]["prompt_id"] == "prompt-2"
        assert await workflow.handle(_event("retry", (), "\u4fdd\u5b58", str(batches[0]["prompt_id"])), gateway)
        assert calls == ["canonical-id", "canonical-id"]
        assert next(config.save_root.rglob("original.tar.gz")).read_bytes() == b"archive"
        assert "\u5df2\u4fdd\u5b58 1 \u9879\uff0c\u5931\u8d25 0 \u9879" in gateway.sent[-1][1]

    asyncio.run(scenario())


def test_old_collecting_window_is_not_replayed(tmp_path: Path) -> None:
    """A pre-upgrade timed batch must not send an obsolete archive prompt."""
    store = SetuStore(str(tmp_path))
    assert store.add_setu("personal", "user-1", "old", [], 0, 1000)
    with sqlite3.connect(str(tmp_path / "setu.sqlite3")) as database:
        database.execute("PRAGMA user_version = 1")
    upgraded = SetuStore(str(tmp_path))
    assert upgraded.due(float("inf")) == []


def test_plain_image_and_other_command_do_not_start_setu(tmp_path: Path) -> None:
    """Archive selection requires a merged forward and no competing command."""
    async def scenario() -> None:
        config = _config(tmp_path)
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        image = _cache_file(config, "Pic", "plain.jpg")
        assert not await workflow.handle(_event("image", (
            MessageSegment("image", {"file": image.name}),
        )), gateway)
        assert not await workflow.handle(_event("source", (
            _forward_image(image),
        ), "/source"), gateway)
        for command in ("/forward", "forward", ""):
            assert not await workflow.handle(_event(
                "old-{}".format(command), (_forward_image(image),),
                command, "source", "source",
            ), gateway)
        assert not gateway.sent
        assert not SetuStore(str(tmp_path / "state")).due(float("inf"))

    asyncio.run(scenario())


def test_config_validates_feature_limits_and_words(tmp_path: Path) -> None:
    """An invalid independent feature file fails before bot startup."""
    path = tmp_path / "config.toml"
    path.write_text('enabled = true\nquiet_seconds = 10\n')
    with pytest.raises(ConfigurationError, match="Unknown"):
        SetuConfig.load(path)
    defaults = SetuConfig.disabled()
    assert defaults.confirm_words == ("保存",)
    assert defaults.direct_confirm_words == ("直接保存",)
    assert defaults.confirm_timeout_seconds == 60
    for field in ("confirm_words", "direct_confirm_words"):
        path.write_text('enabled = true\n{} = []\n'.format(field))
        with pytest.raises(ConfigurationError, match="empty"):
            SetuConfig.load(path)
    for word in ("保存", "确认", "setu", "/setu", "yes"):
        path.write_text(
            'enabled = true\nconfirm_words = ["yes"]\n'
            'direct_confirm_words = ["{}"]\n'.format(word)
        )
        with pytest.raises(ConfigurationError, match="distinct"):
            SetuConfig.load(path)
    for field in ("confirm_timeout_seconds", "max_depth", "max_nodes"):
        for value in ("0", "-1", "true"):
            path.write_text('enabled = true\n{} = {}\n'.format(field, value))
            with pytest.raises(ConfigurationError, match="positive integer"):
                SetuConfig.load(path)
    for field in ("max_file_bytes", "max_batch_bytes"):
        for value in ("0", "-1", "true"):
            path.write_text('enabled = true\n{} = {}\n'.format(field, value))
            with pytest.raises(ConfigurationError, match="positive size"):
                SetuConfig.load(path)
    path.write_text('enabled = true\nmax_file_bytes = "2M"\nmax_batch_bytes = "1M"\n')
    with pytest.raises(ConfigurationError, match="cover"):
        SetuConfig.load(path)
    path.write_text(
        'enabled = true\nconfirm_words = [" YES ", "确认", "yes"]\n'
        'direct_confirm_words = [" NOW ", "马上保存", "now"]\n'
        'cancel_words = ["保存", "/setu"]\n'
    )
    assert SetuConfig.load(path).confirm_words == ("yes", "确认")
    assert SetuConfig.load(path).direct_confirm_words == ("now", "马上保存")


@pytest.mark.parametrize("word", ["保存", "setu", "/setu"])
def test_quoted_forward_start_words_and_quoted_confirmation(
    tmp_path: Path, word: str,
) -> None:
    """Each start word prompts; only a quoted confirmation saves its batch."""
    async def scenario() -> None:
        config = _config(tmp_path)
        image = _cache_file(config, "Pic", "source.jpg")
        image.write_bytes(b"image-content")
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        request = _event("request", (_forward_image(image),), word, "source", "source")
        assert await workflow.handle(request, gateway)
        assert '引用这条消息并回复 "保存"' in gateway.sent[0][1]
        assert not config.save_root.exists()
        assert not await workflow.handle(_event("empty", (), "", "prompt-1"), gateway)
        assert not config.save_root.exists()
        assert await workflow.handle(_event("plain", (), "确认"), gateway)
        assert gateway.sent[-1][1] == "请引用对应的归档提示后再确认。"
        assert not config.save_root.exists()
        assert await workflow.handle(_event("confirm", (), "确认", "prompt-1"), gateway)
        assert next(config.save_root.rglob("source.jpg")).read_bytes() == b"image-content"
        assert "已保存 1 项，失败 0 项" in gateway.sent[-1][1]
        assert gateway.sent[-1][2] == "confirm"

    asyncio.run(scenario())


def test_setu_without_quote_or_pending_batch_requests_a_forward(tmp_path: Path) -> None:
    """A bare command still explains how to start when nothing awaits confirmation."""
    async def scenario() -> None:
        workflow = Setu(_config(tmp_path), str(tmp_path / "state"))
        gateway = FakeGateway()
        assert await workflow.handle(_event("bare", (), "/setu"), gateway)
        assert gateway.sent[0][1] == "请引用合并转发或文件消息并发送保存、setu 或 /setu。"

    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["date_original", "timestamp_hash"])
@pytest.mark.parametrize("original", ["\u8d44\u6599 BackUp.TAR.GZ", "notes.txt"])
@pytest.mark.parametrize("direct", [False, True])
def test_quoted_ordinary_file_uses_existing_naming_confirmation_and_dedup(
    tmp_path: Path, mode: str, original: str, direct: bool,
) -> None:
    """Quoted files share archive/generic placement, consent and source dedup rules."""
    async def scenario() -> None:
        """Save a dual-field file source, then repeat its source and confirmation."""
        config = _config(tmp_path, mode)
        source = _cache_file(config, "File", "cache-id")
        content = b"ordinary file"
        source.write_bytes(content)
        calls: List[str] = []

        class FileGateway(FakeGateway):
            """Resolve the canonical native key and observe consent timing."""

            async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
                """Check original name and canonical ID after the save is claimed."""
                assert media["name"] == original
                calls.append(str(media["file"]))
                return str(source)

        gateway = FileGateway()
        workflow = Setu(config, str(tmp_path / "state"))
        file_segment = MessageSegment("file", {"file": original, "file_id": "canonical-id",
                                               "file_size": str(len(content))})
        command = "\u76f4\u63a5\u4fdd\u5b58" if direct else "/setu"
        event = _event("request", (file_segment,), command, "source-file", "source-file")
        assert await workflow.handle(event, gateway)
        if not direct:
            assert not calls
            assert not config.save_root.exists()
            assert gateway.sent[-1][2] == "source-file"
            assert "\u8fd9\u6761\u6d88\u606f\u5171 0 \u5f20\u56fe\u7247\u30010 \u4e2a\u89c6\u9891\u30011 \u4e2a\u6587\u4ef6" in gateway.sent[-1][1]
            pending = workflow._store.awaiting("personal", "user-1", time.time())
            assert pending[0]["first_message_id"] == "source-file"
            assert await workflow.handle(_event("confirm", (), "\u4fdd\u5b58", "prompt-1"), gateway)
        assert calls == ["canonical-id"]
        assert gateway.sent[-1][2] == ("request" if direct else "confirm")
        assert "\u5df2\u4fdd\u5b58 1 \u9879\uff0c\u5931\u8d25 0 \u9879" in gateway.sent[-1][1]
        archived = next(path for path in config.save_root.rglob("*") if path.is_file())
        if original.endswith(".TAR.GZ") or mode == "date_original":
            assert archived.name == original
        else:
            assert archived.name.endswith("-" + hashlib.sha256(content).hexdigest() + ".txt")
        assert archived.read_bytes() == content
        inode = archived.stat().st_ino
        assert await workflow.handle(replace(event, message_id="repeat-source"), gateway)
        assert await workflow.handle(_event("repeat-confirm", (), "\u4fdd\u5b58", "prompt-1"), gateway)
        assert calls == ["canonical-id"]
        assert archived.stat().st_ino == inode
        assert len([path for path in config.save_root.rglob("*") if path.is_file()]) == 1

    asyncio.run(scenario())


@pytest.mark.parametrize("kind", ["file", "image", "video", "text"])
def test_ordinary_attachments_without_quoted_source_do_not_prompt_or_save(
    tmp_path: Path, kind: str,
) -> None:
    """Unsolicited attachments cannot become save batches without a quoted command."""
    async def scenario() -> None:
        """Present one unquoted incoming attachment and verify no batch or reply."""
        config = _config(tmp_path)
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        segment = MessageSegment(kind, {"file": "source.zip", "file_id": "canonical-id"})
        assert not await workflow.handle(_event("ordinary", (segment,)), gateway)
        assert not gateway.sent
        assert not workflow._store.due(float("inf"))
        assert not config.save_root.exists()

    asyncio.run(scenario())


def test_prompt_shows_only_first_configured_action_words(tmp_path: Path) -> None:
    """The prompt displays primary words and still accepts configured aliases."""
    async def scenario() -> None:
        """Start one batch with aliases configured in a deliberate order."""
        config = replace(_config(tmp_path), confirm_words=("yes", "确认"))
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        source = _cache_file(config, "Pic", "ordered.jpg")
        source.write_bytes(b"ordered")
        assert await workflow.handle(_event(
            "request", (_forward_image(source),), "保存", "source", "source",
        ), gateway)
        assert gateway.sent[0][1] == (
            "这条消息共 1 张图片、0 个视频、0 个文件；\n"
            '引用这条消息并回复 "yes" 以保存（超时 60s 后自动取消）。'
        )
        assert await workflow.handle(_event("save", (), "确认", "prompt-1"), gateway)
        assert next(config.save_root.rglob("ordered.jpg")).read_bytes() == b"ordered"

    asyncio.run(scenario())


def test_file_saver_enforces_size_and_source_boundary(tmp_path: Path) -> None:
    """Oversized or unrelated local files never enter the archive."""
    config = replace(_config(tmp_path), max_file_bytes=3, max_batch_bytes=5)
    source = _cache_file(config, "Pic", "source.jpg")
    source.write_bytes(b"four")
    saver = SetuFileSaver(config)
    with pytest.raises(SetuFileError, match="size limit"):
        saver.save({"kind": "image", "name": "source.jpg"}, str(source), 1000, 5)
    assert not list(config.save_root.rglob("*.jpg"))
    other = tmp_path / "private.jpg"
    other.write_bytes(b"ok")
    with pytest.raises(SetuFileError, match="outside"):
        saver.save({"kind": "image", "name": "private.jpg"}, str(other), 1000, 5)
    credential = config.local_media_root / "nt_qq_test" / "nt_data" / "msf" / "secret.db"
    credential.parent.mkdir(parents=True)
    credential.write_bytes(b"ok")
    with pytest.raises(SetuFileError, match="media cache"):
        saver.save({"kind": "image", "name": "secret.db"}, str(credential), 1000, 5)


@pytest.mark.parametrize("mode", ["date_original", "timestamp_hash"])
def test_interrupted_binary_source_never_publishes_partial_archive(tmp_path: Path, mode: str) -> None:
    """A failure while copying a trusted spool removes its incoming temporary file."""
    config = _config(tmp_path, mode)

    class InterruptedSource(io.BytesIO):
        """Return a valid prefix before the backing spool becomes unreadable."""

        def read(self, size: int = -1) -> bytes:
            """Fail the second read rather than returning a successful short file."""
            if self.tell():
                raise OSError("spool read failed")
            return super().read(size)

    source = InterruptedSource(b"partial bytes")
    with pytest.raises(OSError):
        SetuFileSaver(config).save({"kind": "file", "name": "archive.zip"}, source, 1000, 100)
    assert not list(config.save_root.iterdir())
    assert not source.closed


@pytest.mark.parametrize("mode", ["date_original", "timestamp_hash"])
@pytest.mark.parametrize("direct", [False, True])
def test_partial_native_stream_closes_spool_and_retries_without_replacing_success(
    tmp_path: Path, mode: str, direct: bool, monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Failed native streams remain retryable without publishing partial content."""
    async def scenario() -> None:
        """Keep one saved image while a file stream fails once, then succeeds."""
        config = replace(_config(tmp_path, mode), max_file_bytes=8, max_batch_bytes=10)
        image = _cache_file(config, "Pic", "saved.jpg")
        image.write_bytes(b"one")
        native = config.local_media_root / "NapCat" / "temp" / "owner-only"
        native.parent.mkdir(parents=True)
        native.write_bytes(b"next")
        original_open = Path.open
        private_marker = "private-native-stream-token"

        def owner_only_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            """Model a readable directory containing a file owned by another UID."""
            if path == native and mode == "rb":
                raise PermissionError(private_marker)
            return original_open(path, mode, *args, **kwargs)

        monkeypatch.setattr(Path, "open", owner_only_open)
        spools: List[BinaryIO] = []
        resolved: List[str] = []

        class StreamGateway(FakeGateway):
            """Fail one native stream without changing the source metadata."""

            async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
                """Resolve an existing image or the canonical owner-only native file."""
                resolved.append(str(media["file"]))
                return str(image if media["kind"] == "image" else native)

            async def download_file(self, media: Mapping[str, Any], output: BinaryIO,
                                    maximum: int) -> None:
                """Enforce remaining bytes and return only complete content on retry."""
                assert media["file"] == "canonical-id"
                assert maximum == 7
                spools.append(output)
                output.write(b"ne")
                if len(spools) == 1:
                    raise OneBotError(private_marker)
                output.write(b"xt")

        workflow = Setu(config, str(tmp_path / "state"))
        gateway = StreamGateway()
        forward = MessageSegment("forward", {"id": "mixed", "content": [{"message": [
            {"type": "image", "data": {"file": "image-id", "url": str(image)}},
            {"type": "file", "data": {"file": "archive.tar.gz", "file_id": "canonical-id",
                                      "file_size": "4"}},
        ]}]})
        command = "\u76f4\u63a5\u4fdd\u5b58" if direct else "/setu"
        assert await workflow.handle(_event("request", (forward,), command, "source", "source"), gateway)
        if not direct:
            assert not spools
            assert await workflow.handle(_event("confirm", (), "\u4fdd\u5b58", "prompt-1"), gateway)
        assert "\u5df2\u4fdd\u5b58 1 \u9879\uff0c\u5931\u8d25 1 \u9879" in gateway.sent[-1][1]
        assert len(spools) == 1 and spools[0].closed
        saved = next(path for path in config.save_root.rglob("*") if path.is_file())
        inode = saved.stat().st_ino
        assert saved.read_bytes() == b"one"
        assert not list(config.save_root.glob(".incoming-*"))
        pending = workflow._store.awaiting("personal", "user-1", time.time())[0]
        metadata = json.loads(pending["media_json"])
        assert metadata[0]["saved_size"] == 3
        assert "saved_path" not in metadata[1]
        assert metadata[1]["error"] == "OneBotError"
        assert await workflow.handle(_event("retry", (), "\u4fdd\u5b58", str(pending["prompt_id"])), gateway)
        assert "\u5df2\u4fdd\u5b58 2 \u9879\uff0c\u5931\u8d25 0 \u9879" in gateway.sent[-1][1]
        assert gateway.sent[-1][2] == "retry"
        assert all(spool.closed for spool in spools)
        assert resolved == ["image-id", "canonical-id", "canonical-id"]
        assert saved.stat().st_ino == inode
        assert next(config.save_root.rglob("archive.tar.gz")).read_bytes() == b"next"
        assert len([path for path in config.save_root.rglob("*") if path.is_file()]) == 2
        assert not list(config.save_root.glob(".incoming-*"))
        assert private_marker not in caplog.text

    asyncio.run(scenario())


def test_cancelled_spool_publication_cleans_incoming_and_has_no_unobserved_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Closing a cancelled spool must not leave an unobserved worker exception."""
    async def scenario() -> None:
        """Cancel while a worker owns the copied input, then let it clean up."""
        config = _config(tmp_path)
        source = config.local_media_root / "NapCat" / "temp" / "owner-only"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"archive")
        original_open = Path.open
        original_copy = SetuFileSaver._copy
        entered = threading.Event()
        release = threading.Event()
        spools: List[BinaryIO] = []
        loop = asyncio.get_running_loop()
        errors: List[Dict[str, Any]] = []
        original_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda active_loop, context: errors.append(context))

        def owner_only_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            """Use the native stream because the mounted source is unreadable."""
            if path == source and mode == "rb":
                raise PermissionError("owner-only native source")
            return original_open(path, mode, *args, **kwargs)

        def blocked_copy(self: SetuFileSaver, location: Any, output: BinaryIO,
                         maximum: int, kind: str) -> tuple:
            """Hold only spool copying so cancellation closes a still-borrowed input."""
            if not isinstance(location, str):
                entered.set()
                if not release.wait(5):
                    raise OSError("test worker was not released")
            return original_copy(self, location, output, maximum, kind)

        class StreamGateway(FakeGateway):
            """Return a complete stream before the disk-publication worker is held."""

            async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
                """Expose the approved but owner-only native file."""
                return str(source)

            async def download_file(self, media: Mapping[str, Any], output: BinaryIO,
                                    maximum: int) -> None:
                """Capture the owned spool and finish transfer without publication."""
                spools.append(output)
                output.write(b"archive")

        monkeypatch.setattr(Path, "open", owner_only_open)
        monkeypatch.setattr(SetuFileSaver, "_copy", blocked_copy)
        workflow = Setu(config, str(tmp_path / "state"))
        segment = MessageSegment("file", {"file": "archive.zip", "file_id": "canonical-id",
                                          "file_size": "7"})
        task = asyncio.create_task(workflow.handle(
            _event("request", (segment,), "\u76f4\u63a5\u4fdd\u5b58", "source", "source"), StreamGateway(),
        ))
        try:
            assert await loop.run_in_executor(None, entered.wait, 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert len(spools) == 1 and spools[0].closed
            release.set()

            async def wait_for_worker() -> None:
                """Wait until the worker's cleanup callback releases its transfer slot."""
                while workflow._transfer_slots is not None and workflow._transfer_slots._value != 4:
                    await asyncio.sleep(0.01)

            await asyncio.wait_for(wait_for_worker(), 5)
            gc.collect()
            await asyncio.sleep(0)
            assert not errors
            assert not list(config.save_root.rglob("*.zip"))
            assert not list(config.save_root.glob(".incoming-*"))
        finally:
            release.set()
            loop.set_exception_handler(original_handler)

    asyncio.run(scenario())


def test_cancellation_after_worker_failure_consumes_completed_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A completed error must be observed when cancellation preempts polling."""
    async def scenario() -> None:
        """Cancel just after the worker callback completes and before its next poll."""
        loop = asyncio.get_running_loop()
        errors: List[Dict[str, Any]] = []
        original_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda active_loop, context: errors.append(context))

        class FailingSaver:
            """Fail before publication so the worker completion contains an error."""

            def save(self, item: Dict[str, object], location: Any,
                     timestamp: float, remaining_bytes: int) -> Dict[str, object]:
                """Expose a synthetic error that must never reach the loop logger."""
                raise OSError("private-worker-error-token")

        workflow = Setu(_config(tmp_path), str(tmp_path / "state"), processor=FailingSaver())
        original_release = asyncio.Semaphore.release

        def release_and_cancel(semaphore: asyncio.Semaphore) -> None:
            """Queue cancellation after resolve has set its completed exception."""
            original_release(semaphore)
            loop.call_soon(task.cancel)

        monkeypatch.setattr(asyncio.Semaphore, "release", release_and_cancel)
        task = asyncio.create_task(workflow._save_file(
            {"kind": "file", "name": "archive.zip"}, "synthetic-source", 1000, 100,
        ))
        try:
            with pytest.raises(asyncio.CancelledError):
                await task
            gc.collect()
            await asyncio.sleep(0)
            assert not errors
            assert workflow._transfer_slots is not None
            assert workflow._transfer_slots._value == 4
        finally:
            loop.set_exception_handler(original_handler)

    asyncio.run(scenario())


def test_media_url_accepts_observed_qq_host() -> None:
    """Forwarded pictures can use the QQ multimedia download host."""
    _check_url("https://multimedia.nt.qq.com.cn/download")
    with pytest.raises(SetuFileError, match="host"):
        _check_url("https://multimedia.nt.qq.com.cn.example.org/download")


@pytest.mark.parametrize("mode", ["date_original", "timestamp_hash"])
@pytest.mark.parametrize("suffix", [
    ".tar", ".tar.gz", ".tgz", ".zip", ".7z", ".rar",
    ".tar.bz2", ".tbz2", ".tar.xz", ".txz", ".tar.zst", ".tzst",
])
def test_archive_formats_keep_complete_original_names(
    tmp_path: Path, mode: str, suffix: str,
) -> None:
    """Archive attachments preserve case, Unicode, spaces, bytes and permissions."""
    config = _config(tmp_path, mode)
    source = _cache_file(config, "File", "opaque-cache-id")
    content = b"unchanged archive bytes\x00\xff"
    source.write_bytes(content)
    original = "\u8d44\u6599 BackUp" + suffix.upper()
    saver = SetuFileSaver(config)
    result = saver.save({"kind": "file", "name": original}, str(source), 1000, 100)
    archived = Path(str(result["path"]))
    assert archived.name == original
    expected_parent = config.save_root / "1970-01-01" if mode == "date_original" else config.save_root
    assert archived.parent == expected_parent
    assert archived.read_bytes() == content
    assert result["size"] == len(content)
    assert result["sha256"] == hashlib.sha256(content).hexdigest()
    assert archived.stat().st_mode & 0o777 == 0o640
    inode = archived.stat().st_ino
    repeated = saver.save({"kind": "file", "name": original}, str(source), 1001, 100)
    assert repeated == result
    assert archived.stat().st_ino == inode
    assert not list(config.save_root.glob(".incoming-*"))


@pytest.mark.parametrize("mode", ["date_original", "timestamp_hash"])
def test_archive_conflicts_stamp_full_suffix_and_reuse_prior_variant(
    tmp_path: Path, mode: str,
) -> None:
    """Conflicting archives retain all content and retries reuse stamped files."""
    config = _config(tmp_path, mode)
    source = _cache_file(config, "File", "cache-id")
    saver = SetuFileSaver(config)
    metadata = {"kind": "file", "name": "\u8d44\u6599 BackUp.TAR.GZ"}
    source.write_bytes(b"first")
    original = Path(str(saver.save(metadata, str(source), 1000, 100)["path"]))
    stamp = "19700101-081640-000000"
    occupied = original.with_name("\u8d44\u6599 BackUp_" + stamp + ".TAR.GZ")
    occupied.write_bytes(b"occupied")
    source.write_bytes(b"second")
    second = saver.save(metadata, str(source), 1000, 100)
    stamped = Path(str(second["path"]))
    assert stamped.name == "\u8d44\u6599 BackUp_19700101-081640-000001.TAR.GZ"
    assert stamped.parent == original.parent
    assert original.read_bytes() == b"first"
    assert occupied.read_bytes() == b"occupied"
    assert stamped.read_bytes() == b"second"
    assert saver.save(metadata, str(source), 1005, 100) == second
    assert len(list(original.parent.iterdir())) == 3


@pytest.mark.parametrize("same_content", [False, True])
def test_concurrent_archive_publication_never_overwrites_or_duplicates(
    tmp_path: Path, same_content: bool, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parallel workers publish distinct bytes or reuse matching stamped bytes."""
    config = _config(tmp_path, "timestamp_hash")
    config.save_root.mkdir()
    original = config.save_root / "backup.tar.gz"
    original.write_bytes(b"earlier")
    sources = [_cache_file(config, "File", str(index)) for index in range(2)]
    contents = [b"first", b"first" if same_content else b"second"]
    for source, content in zip(sources, contents):
        source.write_bytes(content)
    barrier = threading.Barrier(2)
    copy = SetuFileSaver._copy

    def synchronized_copy(self: SetuFileSaver, location: str, output: Any,
                          maximum: int, kind: str) -> tuple:
        """Finish both transfers before either worker can select a destination."""
        result = copy(self, location, output, maximum, kind)
        barrier.wait(timeout=5)
        return result

    monkeypatch.setattr(SetuFileSaver, "_copy", synchronized_copy)

    def save(index: int) -> Dict[str, object]:
        """Save from an independent worker and timestamp."""
        return SetuFileSaver(config).save(
            {"kind": "file", "name": original.name}, str(sources[index]),
            1000 + index if same_content else 1000, 100,
        )

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(save, range(2)))
    assert original.read_bytes() == b"earlier"
    for result, content in zip(results, contents):
        assert Path(str(result["path"])).read_bytes() == content
    assert len({str(result["path"]) for result in results}) == (1 if same_content else 2)
    assert len(list(config.save_root.iterdir())) == (2 if same_content else 3)


@pytest.mark.parametrize("occupied_kind", ["directory", "symlink", "broken_symlink"])
def test_archive_does_not_reuse_or_overwrite_nonregular_destinations(
    tmp_path: Path, occupied_kind: str,
) -> None:
    """Occupied paths are conflicts even when a symlink points to equal bytes."""
    config = _config(tmp_path, "timestamp_hash")
    source = _cache_file(config, "File", "cache-id")
    source.write_bytes(b"archive")
    config.save_root.mkdir()
    occupied = config.save_root / "backup.zip"
    external = tmp_path / "external.zip"
    external.write_bytes(b"archive")
    if occupied_kind == "directory":
        occupied.mkdir()
    else:
        occupied.symlink_to(external if occupied_kind == "symlink" else tmp_path / "missing.zip")
    stamped_symlink = config.save_root / "backup_19700101-081640-000000.zip"
    stamped_symlink.symlink_to(external)
    result = SetuFileSaver(config).save(
        {"kind": "file", "name": "backup.zip"}, str(source), 1000, 100,
    )
    archived = Path(str(result["path"]))
    assert archived.name == "backup_19700101-081640-000001.zip"
    assert not archived.is_symlink()
    assert archived.read_bytes() == b"archive"
    assert external.read_bytes() == b"archive"
    assert stamped_symlink.is_symlink()
    assert occupied.is_dir() if occupied_kind == "directory" else occupied.is_symlink()


@pytest.mark.parametrize("name", [
    "../backup.zip", "/backup.tar", "folder\\backup.7z", "bad\n.zip",
    "bad\x00.tar.gz", "bad:backup.tgz", "bad\ud800.zip", "x" * 256 + ".zip",
])
def test_identifiable_archive_with_unsafe_or_unrepresentable_name_fails(
    tmp_path: Path, name: str,
) -> None:
    """Invalid original archive names fail rather than becoming renamed successes."""
    config = _config(tmp_path)
    source = _cache_file(config, "File", "cache-id")
    source.write_bytes(b"archive")
    with pytest.raises((SetuFileError, OSError)):
        SetuFileSaver(config).save({"kind": "file", "name": name}, str(source), 1000, 100)
    assert not config.save_root.exists() or not any(
        path.is_file() for path in config.save_root.rglob("*")
    )


@pytest.mark.parametrize("location_kind", ["too_large", "batch_limit", "empty", "outside", "http", "host"])
def test_archive_keeps_transfer_rejections_without_partial_files(
    tmp_path: Path, location_kind: str,
) -> None:
    """Archive naming does not bypass existing transfer or location restrictions."""
    config = replace(_config(tmp_path), max_file_bytes=3)
    source = _cache_file(config, "File", "cache-id")
    source.write_bytes(b"four" if location_kind == "too_large" else b"ok")
    location = str(source)
    remaining = 1 if location_kind == "batch_limit" else 100
    if location_kind == "empty":
        source.write_bytes(b"")
    if location_kind == "outside":
        outside = tmp_path / "private.zip"
        outside.write_bytes(b"ok")
        location = str(outside)
    if location_kind in {"http", "host"}:
        location = "http://qq.com/archive" if location_kind == "http" else "https://example.org/archive"
    with pytest.raises(SetuFileError):
        SetuFileSaver(config).save({"kind": "file", "name": "backup.zip"}, location, 1000, remaining)
    assert not list(config.save_root.iterdir())


@pytest.mark.parametrize("kind,name", [
    ("image", "pretend.zip"), ("video", "pretend.tar.gz"),
    ("record", "pretend.7z"), ("file", "notes.txt"), ("file", "opaque-id"),
    ("", "pretend.zip"),
])
def test_nonarchive_hash_placement_and_repeated_save_remain_unchanged(
    tmp_path: Path, kind: str, name: str,
) -> None:
    """Only file-kind archives override the established hash placement strategy."""
    config = _config(tmp_path, "timestamp_hash")
    source = _cache_file(config, "File", "cache-id")
    source.write_bytes(b"same content")
    metadata = {"kind": kind, "file": name}
    saver = SetuFileSaver(config)
    result = saver.save(metadata, str(source), 1000, 100)
    archived = Path(str(result["path"]))
    suffix = Path(name).suffix or ".bin"
    assert archived.name == "19700101-081640-" + hashlib.sha256(b"same content").hexdigest() + suffix
    inode = archived.stat().st_ino
    assert saver.save(metadata, str(source), 1000, 100) == result
    assert archived.stat().st_ino == inode
    assert len(list(config.save_root.iterdir())) == 1


@pytest.mark.parametrize("mode", ["date_original", "timestamp_hash"])
@pytest.mark.parametrize("direct", [False, True])
def test_mixed_nested_archives_use_existing_confirm_direct_and_partial_retry(
    tmp_path: Path, mode: str, direct: bool,
) -> None:
    """Mixed nested forwards retain counts, command quotes and completed items."""
    async def scenario() -> None:
        """Save two archives around a failed transfer alongside an existing image."""
        config = _config(tmp_path, mode)
        image = _cache_file(config, "Pic", "picture.jpg")
        first = _cache_file(config, "File", "opaque-first")
        second = _cache_file(config, "File", "opaque-second")
        image.write_bytes(b"picture")
        first.write_bytes(b"archive one")
        gateway = FakeGateway()
        gateway.nodes["nested"] = [{"message": [
            {"type": "file", "data": {"file_id": "opaque-first", "file_name": "\u8d44\u6599.TAR.GZ",
                                      "url": str(first)}},
            {"type": "file", "data": {"file": "opaque-second", "name": "second.7z",
                                      "url": str(second)}},
        ]}]
        forward = MessageSegment("forward", {"id": "outer", "content": [{"message": [
            {"type": "image", "data": {"file": image.name, "url": str(image)}},
            {"type": "forward", "data": {"id": "nested"}},
        ]}]})
        workflow = Setu(config, str(tmp_path / "state"))
        command = "\u76f4\u63a5\u4fdd\u5b58" if direct else "/setu"
        assert await workflow.handle(_event("request", (forward,), command, "source", "source"), gateway)
        if not direct:
            assert "1 \u5f20\u56fe\u7247\u30010 \u4e2a\u89c6\u9891\u30012 \u4e2a\u6587\u4ef6" in gateway.sent[-1][1]
            assert not config.save_root.exists()
            assert await workflow.handle(_event("confirm", (), "\u4fdd\u5b58", "prompt-1"), gateway)
        assert "\u5df2\u4fdd\u5b58 2 \u9879\uff0c\u5931\u8d25 1 \u9879" in gateway.sent[-1][1]
        assert gateway.sent[-1][2] == ("request" if direct else "confirm")
        archived = next(config.save_root.rglob("\u8d44\u6599.TAR.GZ"))
        inode = archived.stat().st_ino
        assert archived.read_bytes() == b"archive one"
        second.write_bytes(b"archive two")
        pending = workflow._store.awaiting("personal", "user-1", time.time())[0]
        assert await workflow.handle(_event("retry", (), "\u4fdd\u5b58", str(pending["prompt_id"])), gateway)
        assert "\u5df2\u4fdd\u5b58 3 \u9879\uff0c\u5931\u8d25 0 \u9879" in gateway.sent[-1][1]
        assert gateway.sent[-2][1:] == ("正在保存以上 1 个文件。", "retry")
        assert gateway.sent[-1][2] == "retry"
        assert archived.stat().st_ino == inode
        assert next(config.save_root.rglob("second.7z")).read_bytes() == b"archive two"
        assert len([path for path in config.save_root.rglob("*") if path.is_file()]) == 3

    asyncio.run(scenario())


def test_failed_item_can_be_retried_without_replacing_completed_file(tmp_path: Path) -> None:
    """A partial archive keeps successes and retries only the failed source."""
    async def scenario() -> None:
        """Confirm twice around a temporarily unavailable attachment."""
        config = _config(tmp_path)
        first = _cache_file(config, "Pic", "first.jpg")
        second = _cache_file(config, "Pic", "second.jpg")
        first.write_bytes(b"first")
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        event = _event("request", (MessageSegment("forward", {"id": "pair", "content": [
            {"message": [
                {"type": "image", "data": {"file": first.name, "url": str(first)}},
                {"type": "image", "data": {"file": second.name, "url": str(second)}},
            ]},
        ]}),), "/setu", "media", "media")
        assert await workflow.handle(event, gateway)
        assert await workflow.handle(_event("save-1", (), "确认", "prompt-1"), gateway)
        assert "已保存 1 项，失败 1 项" in gateway.sent[-1][1]
        assert gateway.sent[-1][2] == "save-1"
        assert "可再次回复“保存”重试失败项。" in gateway.sent[-1][1]
        archived_first = next(config.save_root.rglob("first.jpg"))
        original_inode = archived_first.stat().st_ino
        second.write_bytes(b"second")
        assert await workflow.handle(_event("save-2", (), "确认", "prompt-1"), gateway)
        assert "已保存 2 项，失败 0 项" in gateway.sent[-1][1]
        assert gateway.sent[-1][2] == "save-2"
        assert archived_first.stat().st_ino == original_inode
        assert next(config.save_root.rglob("second.jpg")).read_bytes() == b"second"

    asyncio.run(scenario())


def test_failed_prompt_is_retried_after_reconnect(tmp_path: Path) -> None:
    """An unsent question remains pending and can be delivered later."""
    async def scenario() -> None:
        """Fail the initial prompt and then deliver the same batch question."""
        config = _config(tmp_path)
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        event = _event("request", (MessageSegment("forward", {"id": "forward-1", "content": [
            {"message": [{"type": "image", "data": {"file": "a.jpg"}}]},
        ]}),), "/setu", "first", "first")
        gateway.fail_count = 1
        assert await workflow.handle(event, gateway)
        store = SetuStore(str(tmp_path / "state"))
        assert not gateway.sent
        retry = store.unprompted(time.time() + 31)
        assert len(retry) == 1
        await workflow._send_prompt(retry[0], gateway, time.time() + 31)
        assert gateway.sent[0][2] == "first"
        assert not store.unprompted(time.time() + 32)

    asyncio.run(scenario())


def test_confirmation_requires_matching_prompt_quote(tmp_path: Path) -> None:
    """Plain text and another quote cannot select either pending batch."""
    async def scenario() -> None:
        """Keep two prompts pending and select only the explicitly quoted one."""
        config = _config(tmp_path)
        first = _cache_file(config, "Pic", "first.jpg")
        second = _cache_file(config, "Pic", "second.jpg")
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        workflow = Setu(config, str(tmp_path / "state"))
        store = SetuStore(str(tmp_path / "state"))
        gateway = FakeGateway()
        for index, source in enumerate((first, second), 1):
            event = _event("request-{}".format(index), (_forward_image(source),),
                           "/setu", str(index), str(index))
            assert await workflow.handle(event, gateway)

        assert await workflow.handle(_event("plain", (), "确认"), gateway)
        assert await workflow.handle(_event("wrong", (), "确认", "other"), gateway)
        assert not config.save_root.exists()
        assert await workflow.handle(_event("save", (), "确认", "prompt-2"), gateway)
        assert next(config.save_root.rglob("second.jpg")).read_bytes() == b"second"
        assert not list(config.save_root.rglob("first.jpg"))
        pending = store.awaiting("personal", "user-1", time.time())
        assert len(pending) == 1
        assert pending[0]["first_message_id"] == "1"

    asyncio.run(scenario())


@pytest.mark.parametrize("word", ["取消", "cancel"])
def test_cancellation_words_leave_pending_batch_intact(tmp_path: Path, word: str) -> None:
    """Removed cancellation commands cannot change a pending archive."""
    async def scenario() -> None:
        """Ignore both plain text and a quote carrying a cancellation word."""
        config = _config(tmp_path)
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        source = _cache_file(config, "Pic", "cancel.jpg")
        source.write_bytes(b"cancel")
        assert await workflow.handle(_event(
            "request", (_forward_image(source),), "setu", "source", "source",
        ), gateway)
        assert not await workflow.handle(_event("plain", (), word), gateway)
        assert len(SetuStore(str(tmp_path / "state")).awaiting(
            "personal", "user-1", time.time(),
        )) == 1
        assert not await workflow.handle(_event("cancel", (), word, "prompt-1"), gateway)
        assert len(gateway.sent) == 1
        assert len(SetuStore(str(tmp_path / "state")).awaiting(
            "personal", "user-1", time.time(),
        )) == 1
        assert not config.save_root.exists()

    asyncio.run(scenario())


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize("mark_expired", [False, True])
def test_fresh_source_resumes_expired_unfinished_batch_without_losing_checkpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, direct: bool, partial: bool,
    mark_expired: bool,
) -> None:
    """Fresh source intent restores retry while old confirmations remain expired."""
    current_time = [1000.0]
    monkeypatch.setattr("kisara.application.services.setu.time.time", lambda: current_time[0])

    async def scenario() -> None:
        """Retain the original date, saved item and cap accounting on a new source action."""
        config = replace(_config(tmp_path), max_file_bytes=8, max_batch_bytes=11)
        source = _cache_file(config, "File", "canonical-pending")
        source.write_bytes(b"pending!")
        saver = SetuFileSaver(config)
        remaining: List[int] = []

        class RecordingSaver:
            """Observe the effective cap while using the actual bounded file saver."""

            def save(self, item: Dict[str, object], location: str,
                     timestamp: float, remaining_bytes: int) -> Dict[str, object]:
                """Record remaining batch bytes after retained successful checkpoints."""
                remaining.append(remaining_bytes)
                return saver.save(item, location, timestamp, remaining_bytes)

        previous = [{"kind": "file", "file": "pending.tar.gz", "name": "pending.tar.gz",
                     "url": "", "size": "8", "error": "OneBotError"}]
        fresh = [MessageSegment("file", {"file": "pending.tar.gz", "file_id": "canonical-pending",
                                         "file_size": "8", "url": str(source)})]
        completed: Dict[str, Any] = {}
        inode = 0
        if partial:
            saved_source = _cache_file(config, "File", "saved-cache")
            saved_source.write_bytes(b"one")
            result = saver.save({"kind": "file", "name": "saved.zip"}, str(saved_source), 1000, 11)
            inode = Path(str(result["path"])).stat().st_ino
            completed = {"kind": "file", "file": "legacy-saved-id", "name": "saved.zip",
                         "url": "legacy-saved-url", "size": "3", "saved_path": result["path"],
                         "saved_size": result["size"], "sha256": result["sha256"]}
            previous.insert(0, completed)
            fresh.insert(0, MessageSegment("file", {"file": "saved.zip", "file_id": "new-saved-id",
                                                    "file_size": "3", "url": str(saved_source)}))
        workflow = Setu(config, str(tmp_path / "state"), processor=RecordingSaver())
        batch = workflow._store.add_setu("personal", "user-1", "source", previous, 0, 1000)
        assert batch is not None
        workflow._store.mark_awaiting(str(batch["id"]), 1060)
        workflow._store.set_prompt(str(batch["id"]), "old-prompt")
        assert workflow._store.claim_save(str(batch["id"]), 1001)
        workflow._store.finish(str(batch["id"]), "awaiting")
        current_time[0] = 172000.0
        if mark_expired:
            workflow._store.expire(current_time[0])
        gateway = FakeGateway()
        assert await workflow.handle(_event("old-confirm", (), "\u4fdd\u5b58", "old-prompt"), gateway)
        assert gateway.sent[-1][1] == "\u6ca1\u6709\u53ef\u786e\u8ba4\u7684\u5f52\u6863\u6279\u6b21\u3002"
        assert not remaining
        command = "\u76f4\u63a5\u4fdd\u5b58" if direct else "/setu"
        assert await workflow.handle(_event("fresh", tuple(fresh), command, "source", "source"), gateway)
        if not direct:
            assert not remaining
            pending = workflow._store.awaiting("personal", "user-1", current_time[0])[0]
            assert pending["id"] == batch["id"]
            assert pending["first_at"] == 1000.0
            assert pending["expires_at"] == current_time[0] + 60
            new_prompt = str(pending["prompt_id"])
            assert new_prompt != "old-prompt"
            assert await workflow.handle(_event("stale-confirm", (), "\u4fdd\u5b58", "old-prompt"), gateway)
            assert not remaining
            assert await workflow.handle(_event("fresh-confirm", (), "\u4fdd\u5b58", new_prompt), gateway)
        assert remaining == [8 if partial else 11]
        assert gateway.sent[-2][1] == "正在保存以上 1 个文件。"
        assert "\u5931\u8d25 0 \u9879" in gateway.sent[-1][1]
        assert next(config.save_root.rglob("pending.tar.gz")).parent.name == "1970-01-01"
        with sqlite3.connect(str(tmp_path / "state" / "setu.sqlite3")) as database:
            rows = database.execute("SELECT id, first_at, state, media_json FROM batches").fetchall()
        assert len(rows) == 1
        assert rows[0][:3] == (batch["id"], 1000.0, "saved")
        refreshed = json.loads(rows[0][3])
        assert refreshed[-1]["file"] == "canonical-pending"
        assert "error" not in refreshed[-1]
        if partial:
            assert refreshed[0] == completed
            assert Path(str(completed["saved_path"])).stat().st_ino == inode
        assert len([path for path in config.save_root.rglob("*") if path.is_file()]) == (2 if partial else 1)

    asyncio.run(scenario())


@pytest.mark.parametrize("change", ["kind", "name", "size", "extra", "reordered"])
def test_expired_source_refresh_rejects_changed_ordered_metadata(tmp_path: Path, change: str) -> None:
    """A source retry cannot replace the batch with unrelated or reordered files."""
    store = SetuStore(str(tmp_path / "state"))
    previous = [{"kind": "file", "file": "old-1", "name": "first.zip", "size": "5", "url": ""},
                {"kind": "file", "file": "old-2", "name": "second.zip", "size": "6", "url": ""}]
    batch = store.add_setu("personal", "user-1", "source", previous, 0, 1000)
    assert batch is not None
    store.mark_awaiting(str(batch["id"]), 1060)
    store.expire(2000)
    fresh = [dict(item, file="new-id") for item in previous]
    if change in {"kind", "name", "size"}:
        fresh[0][change] = "different"
    if change == "extra":
        fresh.append(dict(fresh[0]))
    if change == "reordered":
        fresh.reverse()
    action, row = store.prepare_source("personal", "user-1", "source", fresh, 2000, 60, True)
    assert action == "changed"
    assert row is not None and row["state"] == "expired"
    assert json.loads(row["media_json"]) == previous
    assert not store.awaiting("personal", "user-1", 2000)


@pytest.mark.parametrize("state,expected", [
    ("saving", "\u6b63\u5728\u4fdd\u5b58"), ("saved", "\u5df2\u7ecf\u4fdd\u5b58\u5b8c\u6210"),
    ("missing", "\u8bb0\u5f55\u5df2\u8fc7\u671f"), ("cancelled", "\u65e0\u6cd5\u7eed\u5b58"),
])
def test_duplicate_direct_source_reports_actual_state(tmp_path: Path, state: str, expected: str) -> None:
    """Seen identity alone never becomes an already-saved reply."""
    async def scenario() -> None:
        """Distinguish an active, complete, missing or nonretryable original batch."""
        config = _config(tmp_path)
        workflow = Setu(config, str(tmp_path / "state"))
        media = [{"kind": "file", "file": "id", "name": "original.zip", "size": "7", "url": ""}]
        batch = workflow._store.add_setu("personal", "user-1", "source", media, 0, time.time())
        assert batch is not None
        workflow._store.finish(str(batch["id"]), state if state != "missing" else "expired")
        if state == "missing":
            with sqlite3.connect(str(tmp_path / "state" / "setu.sqlite3")) as database:
                database.execute("DELETE FROM batches WHERE id = ?", (batch["id"],))
        gateway = FakeGateway()
        segment = MessageSegment("file", {"file": "original.zip", "file_id": "id", "file_size": "7"})
        assert await workflow.handle(_event("direct", (segment,), "\u76f4\u63a5\u4fdd\u5b58", "source", "source"), gateway)
        assert expected in gateway.sent[-1][1]
        assert not config.save_root.exists()
        with sqlite3.connect(str(tmp_path / "state" / "setu.sqlite3")) as database:
            assert database.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == (0 if state == "missing" else 1)

    asyncio.run(scenario())


def test_concurrent_expired_direct_source_retry_has_one_save_claim(tmp_path: Path) -> None:
    """Concurrent fresh source retries cannot claim the same expired batch twice."""
    store = SetuStore(str(tmp_path / "state"))
    media = [{"kind": "file", "file": "legacy", "name": "original.zip", "size": "7", "url": ""}]
    batch = store.add_setu("personal", "user-1", "source", media, 0, 1000)
    assert batch is not None
    store.mark_awaiting(str(batch["id"]), 1060)
    store.expire(2000)
    barrier = threading.Barrier(2)

    def prepare(index: int) -> str:
        """Race callers with corrected canonical IDs under independent transactions."""
        barrier.wait(timeout=5)
        action, row = store.prepare_source(
            "personal", "user-1", "source", [dict(media[0], file="canonical-id")], 2000, 60, True,
        )
        assert row is not None and row["id"] == batch["id"]
        return action

    with ThreadPoolExecutor(max_workers=2) as workers:
        actions = list(workers.map(prepare, range(2)))
    assert sorted(actions) == ["save", "saving"]
    assert not store.claim_save(str(batch["id"]), 2000)


def test_overlapping_fresh_source_retries_save_once_and_report_busy(tmp_path: Path) -> None:
    """A second fresh retry reports saving while the first native resolver is active."""
    async def scenario() -> None:
        """Hold one resolver so two explicit source commands overlap deterministically."""
        config = _config(tmp_path)
        source = _cache_file(config, "File", "canonical-id")
        source.write_bytes(b"archive")
        entered = asyncio.Event()
        release = asyncio.Event()
        calls: List[str] = []

        class BlockingGateway(FakeGateway):
            """Expose one deliberately held native resolution."""

            async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
                """Resolve only once and wait for the competing command to finish."""
                calls.append(str(media["file"]))
                entered.set()
                await release.wait()
                return str(source)

        workflow = Setu(config, str(tmp_path / "state"))
        media = [{"kind": "file", "file": "original.zip", "name": "original.zip", "size": "7", "url": ""}]
        batch = workflow._store.add_setu("personal", "user-1", "source", media, 0, 1000)
        assert batch is not None
        workflow._store.mark_awaiting(str(batch["id"]), 1060)
        workflow._store.expire(2000)
        gateway = BlockingGateway()
        segment = MessageSegment("file", {"file": "original.zip", "file_id": "canonical-id", "file_size": "7"})
        event = _event("first", (segment,), "\u76f4\u63a5\u4fdd\u5b58", "source", "source")
        first = asyncio.create_task(workflow.handle(event, gateway))
        await asyncio.wait_for(entered.wait(), 5)
        try:
            assert await workflow.handle(replace(event, message_id="second"), gateway)
            assert "\u6b63\u5728\u4fdd\u5b58" in gateway.sent[-1][1]
            assert calls == ["canonical-id"]
        finally:
            release.set()
        assert await first
        assert await workflow.handle(replace(event, message_id="third"), gateway)
        assert "\u5df2\u7ecf\u4fdd\u5b58\u5b8c\u6210" in gateway.sent[-1][1]
        assert calls == ["canonical-id"]
        files = [path for path in config.save_root.rglob("*") if path.is_file()]
        assert len(files) == 1 and files[0].read_bytes() == b"archive"
        with sqlite3.connect(str(tmp_path / "state" / "setu.sqlite3")) as database:
            assert database.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == 1

    asyncio.run(scenario())


def test_normal_unexpired_source_duplicate_retains_original_window_and_metadata(tmp_path: Path) -> None:
    """A duplicate normal source does not renew a still-valid prompt or rewrite metadata."""
    store = SetuStore(str(tmp_path / "state"))
    media = [{"kind": "file", "file": "old-id", "name": "original.zip", "size": "7", "url": ""}]
    batch = store.add_setu("personal", "user-1", "source", media, 0, 1000)
    assert batch is not None
    store.mark_awaiting(str(batch["id"]), 1060)
    store.set_prompt(str(batch["id"]), "original-prompt")
    action, row = store.prepare_source(
        "personal", "user-1", "source", [dict(media[0], file="fresh-id")], 1050, 60, False,
    )
    assert action == "awaiting"
    assert row is not None
    assert row["expires_at"] == 1060
    assert row["prompt_id"] == "original-prompt"
    assert json.loads(row["media_json"]) == media


@pytest.mark.parametrize("prompt_first", [False, True])
def test_direct_save_skips_question_and_preserves_source_identity(
    tmp_path: Path, prompt_first: bool,
) -> None:
    """Direct save consumes new or pending media once and sends its result."""
    async def scenario() -> None:
        """Save one source and repeat its direct command without creating files."""
        config = _config(tmp_path)
        source = _cache_file(config, "Pic", "direct.jpg")
        source.write_bytes(b"direct")
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        if prompt_first:
            assert await workflow.handle(_event(
                "prompt", (_forward_image(source),), "/setu", "source", "source",
            ), gateway)
        sent_before = len(gateway.sent)
        event = _event("direct", (_forward_image(source),),
                       "直接保存", "source", "source")
        assert await workflow.handle(event, gateway)
        assert len(gateway.sent) == sent_before + 2
        assert gateway.sent[sent_before][1:] == ("正在保存以上 1 张图片。", "direct")
        assert "已保存 1 项，失败 0 项" in gateway.sent[-1][1]
        assert gateway.sent[-1][2] == "direct"
        assert "引用这条消息并回复" not in gateway.sent[-1][1]
        archived = next(config.save_root.rglob("direct.jpg"))
        assert archived.read_bytes() == b"direct"
        original_inode = archived.stat().st_ino
        assert await workflow.handle(replace(event, message_id="repeat"), gateway)
        assert archived.stat().st_ino == original_inode
        assert len([path for path in config.save_root.rglob("*") if path.is_file()]) == 1
        assert not SetuStore(str(tmp_path / "state")).awaiting(
            "personal", "user-1", time.time(),
        )

    asyncio.run(scenario())


@pytest.mark.parametrize("change", [
    {"sender_id": "other-user"}, {"conversation_kind": "group"}, {"engine": "console"},
])
def test_direct_save_preserves_service_authorization_boundaries(
    tmp_path: Path, change: Dict[str, str],
) -> None:
    """A quoted direct command still requires an allowed private OneBot sender."""
    async def scenario() -> None:
        """Present a valid source in a rejected event and leave storage untouched."""
        config = _config(tmp_path)
        source = _cache_file(config, "Pic", "restricted.jpg")
        source.write_bytes(b"restricted")
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        event = replace(_event("direct", (_forward_image(source),),
                               "直接保存", "source", "source"), **change)
        assert not await workflow.handle(event, gateway)
        assert not gateway.sent
        assert not config.save_root.exists()
        assert not SetuStore(str(tmp_path / "state")).due(float("inf"))

    asyncio.run(scenario())


def test_direct_partial_result_quote_retries_only_failed_item(tmp_path: Path) -> None:
    """A direct result becomes the quote target for retrying unfinished media."""
    async def scenario() -> None:
        """Retry after the missing attachment becomes available."""
        config = _config(tmp_path)
        first = _cache_file(config, "Pic", "direct-first.jpg")
        second = _cache_file(config, "Pic", "direct-second.jpg")
        first.write_bytes(b"first")
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        forward = MessageSegment("forward", {"id": "pair", "content": [
            {"message": [
                {"type": "image", "data": {"file": first.name, "url": str(first)}},
                {"type": "image", "data": {"file": second.name, "url": str(second)}},
            ]},
        ]})
        assert await workflow.handle(_event(
            "direct", (forward,), "直接保存", "source", "source",
        ), gateway)
        assert len(gateway.sent) == 2
        assert gateway.sent[0][1:] == ("正在保存以上 2 张图片。", "direct")
        assert "已保存 1 项，失败 1 项" in gateway.sent[-1][1]
        assert gateway.sent[-1][2] == "direct"
        assert "请引用这条结果消息并回复“保存”重试失败项。" in gateway.sent[-1][1]
        batch = SetuStore(str(tmp_path / "state")).awaiting(
            "personal", "user-1", time.time(),
        )[0]
        assert batch["prompt_id"] == "prompt-2"
        archived = next(config.save_root.rglob("direct-first.jpg"))
        original_inode = archived.stat().st_ino
        second.write_bytes(b"second")
        assert await workflow.handle(_event("notice-is-not-result", (), "保存", "prompt-1"), gateway)
        assert archived.stat().st_ino == original_inode
        assert not list(config.save_root.rglob("direct-second.jpg"))
        assert await workflow.handle(_event("retry", (), "保存", str(batch["prompt_id"])), gateway)
        assert gateway.sent[-2][1:] == ("正在保存以上 1 张图片。", "retry")
        assert "已保存 2 项，失败 0 项" in gateway.sent[-1][1]
        assert gateway.sent[-1][2] == "retry"
        assert archived.stat().st_ino == original_inode
        assert next(config.save_root.rglob("direct-second.jpg")).read_bytes() == b"second"

    asyncio.run(scenario())


@pytest.mark.parametrize("kind", ["image", "file"])
def test_ordinary_prompt_expires_at_sixty_seconds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str,
) -> None:
    """The default confirmation deadline excludes replies at exactly 60 seconds."""
    current_time = [1000.0]
    monkeypatch.setattr("kisara.application.services.setu.time.time",
                        lambda: current_time[0])

    async def scenario() -> None:
        """Advance a fake clock across the boundary without waiting."""
        config = _config(tmp_path)
        source = _cache_file(config, "Pic" if kind == "image" else "File",
                             "expired.jpg" if kind == "image" else "expired.zip")
        source.write_bytes(b"expired")
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        forward = MessageSegment("forward", {"id": "expired", "content": [{"message": [
            {"type": kind, "data": {"file": source.name, "url": str(source)}},
        ]}]})
        assert await workflow.handle(_event(
            "request", (forward,), "/setu", "source", "source",
        ), gateway)
        store = SetuStore(str(tmp_path / "state"))
        assert store.awaiting("personal", "user-1", 1059.999)
        current_time[0] = 1060.0
        assert await workflow.handle(_event("late", (), "保存", "prompt-1"), gateway)
        assert gateway.sent[-1][1] == "没有可确认的归档批次。"
        assert not config.save_root.exists()
        assert not store.awaiting("personal", "user-1", current_time[0])

    asyncio.run(scenario())


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("outcome", ["retry", "expire"])
@pytest.mark.parametrize("source_kind", ["forward", "file"])
def test_long_file_failure_renews_completion_window_for_actual_retry_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, direct: bool, outcome: str,
    source_kind: str,
) -> None:
    """File retries remain usable after download outlasts the original confirmation."""
    current_time = [1000.0]
    monkeypatch.setattr("kisara.application.services.setu.time.time", lambda: current_time[0])

    async def scenario() -> None:
        """Advance a deterministic clock through native failure, retry and expiry."""
        config = _config(tmp_path)
        source = _cache_file(config, "File", "canonical-id")
        source.write_bytes(b"archive")
        calls: List[str] = []

        class SlowGateway(FakeGateway):
            """Model a native download that fails after 125 seconds."""

            async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
                """Fail past the prompt deadline once and resolve only a valid retry."""
                calls.append(str(media["file"]))
                if len(calls) == 1:
                    current_time[0] = 1125.0
                    raise OneBotError("native download failed")
                return str(source)

        gateway = SlowGateway()
        workflow = Setu(config, str(tmp_path / "state"))
        forward = MessageSegment("forward", {"id": "slow", "content": [{"message": [
            {"type": "file", "data": {"file": "original.tar.gz", "file_id": "canonical-id",
                                      "file_size": "7"}},
        ]}]})
        if source_kind == "file":
            forward = MessageSegment("file", {"file": "original.tar.gz", "file_id": "canonical-id",
                                              "file_size": "7"})
        command = "\u76f4\u63a5\u4fdd\u5b58" if direct else "/setu"
        assert await workflow.handle(_event("request", (forward,), command, "source", "source"), gateway)
        if not direct:
            current_time[0] = 1001.0
            assert await workflow.handle(_event("confirm", (), "\u4fdd\u5b58", "prompt-1"), gateway)
        assert "\u5df2\u4fdd\u5b58 0 \u9879\uff0c\u5931\u8d25 1 \u9879" in gateway.sent[-1][1]
        store = SetuStore(str(tmp_path / "state"))
        pending = store.awaiting("personal", "user-1", current_time[0])
        assert len(pending) == 1
        assert pending[0]["expires_at"] == 1185.0
        retry_quote = "prompt-2" if direct else "prompt-1"
        assert pending[0]["prompt_id"] == retry_quote
        assert store.awaiting("personal", "user-1", 1184.999)
        assert not store.awaiting("personal", "user-1", 1185.0)
        current_time[0] = 1184.999 if outcome == "retry" else 1185.0
        if outcome == "expire":
            store.expire(current_time[0])
        assert await workflow.handle(_event("retry", (), "\u4fdd\u5b58", retry_quote), gateway)
        if outcome == "retry":
            assert calls == ["canonical-id", "canonical-id"]
            assert "\u5df2\u4fdd\u5b58 1 \u9879\uff0c\u5931\u8d25 0 \u9879" in gateway.sent[-1][1]
            assert next(config.save_root.rglob("original.tar.gz")).read_bytes() == b"archive"
        else:
            assert calls == ["canonical-id"]
            assert gateway.sent[-1][1] == "\u6ca1\u6709\u53ef\u786e\u8ba4\u7684\u5f52\u6863\u6279\u6b21\u3002"
            assert not config.save_root.exists()

    asyncio.run(scenario())


@pytest.mark.parametrize("kind,finished_at", [("file", 1040.0), ("image", 1125.0)])
def test_short_file_and_image_failure_do_not_renew_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, finished_at: float,
) -> None:
    """Deadline renewal applies exclusively to file failures after original expiry."""
    current_time = [1000.0]
    monkeypatch.setattr("kisara.application.services.setu.time.time", lambda: current_time[0])

    async def scenario() -> None:
        """Inspect the persisted expiry after a short file or long image failure."""
        config = _config(tmp_path)

        class FailingGateway(FakeGateway):
            """Advance completion time and fail media resolution."""

            async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
                """Fail at the selected completion time without downloading."""
                current_time[0] = finished_at
                raise OneBotError("download failed")

        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FailingGateway()
        forward = MessageSegment("forward", {"id": "failure", "content": [{"message": [
            {"type": kind, "data": {"file": "source.zip" if kind == "file" else "source.jpg"}},
        ]}]})
        assert await workflow.handle(_event("direct", (forward,), "\u76f4\u63a5\u4fdd\u5b58", "source", "source"), gateway)
        with sqlite3.connect(str(tmp_path / "state" / "setu.sqlite3")) as database:
            assert database.execute("SELECT expires_at FROM batches").fetchone()[0] == 1060.0
        pending = workflow._store.awaiting("personal", "user-1", current_time[0])
        assert bool(pending) == (finished_at < 1060.0)

    asyncio.run(scenario())
