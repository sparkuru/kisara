"""Focused tests for private forward collection and archive placement."""

import asyncio
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import pytest

from kisara.application.services.forward_archive import ForwardArchive
from kisara.bot.contracts import MessageEvent, MessageSegment
from kisara.config.forward_archive import ForwardArchiveConfig
from kisara.config.settings import ConfigurationError
from kisara.infrastructure.persistence.forward_archive import ForwardArchiveStore
from kisara.infrastructure.persistence.archive_files import (
    ArchiveFileError, ArchiveFileSaver, _check_url,
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


def _config(tmp_path: Path, mode: str = "date_original") -> ForwardArchiveConfig:
    """Enable the feature for one test sender and a local cache."""
    return replace(
        ForwardArchiveConfig.disabled(), enabled=True,
        allowed_users=frozenset({"user-1"}), quiet_seconds=10,
        max_collection_seconds=60, save_root=tmp_path / "archive",
        local_media_root=tmp_path / "cache", save_mode=mode,
    )


def _event(message_id: str, segments: Tuple[MessageSegment, ...],
           text: str = "", quote_id: str = "") -> MessageEvent:
    """Build one private OneBot message."""
    if text:
        segments = segments + (MessageSegment("text", {"text": text}),)
    return MessageEvent(
        engine="onebot", instance_id="personal", message_id=message_id,
        conversation_kind="private", conversation_id="user-1", sender_id="user-1",
        segments=segments, reply_context={"quoted_message_id": quote_id},
    )


def _cache_file(config: ForwardArchiveConfig, kind: str, name: str) -> Path:
    """Create a path under a realistic NapCat media directory."""
    path = config.local_media_root / "nt_qq_test" / "nt_data" / kind / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


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
        workflow = ForwardArchive(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        gateway.nodes["nested"] = [{"message": [
            {"type": "video", "data": {"file": video.name, "url": str(video)}}
        ]}]
        event = _event("first", (MessageSegment("forward", {"id": "outer", "content": [
            {"message": [
                {"type": "image", "data": {"file": image.name, "url": str(image)}},
                {"type": "forward", "data": {"id": "nested"}},
            ]}
        ]}),))
        assert await asyncio.wait_for(workflow.handle(event, gateway), 15)
        assert not config.save_root.exists()
        store = ForwardArchiveStore(str(tmp_path / "state"))
        batch = store.due(float("inf"))[0]
        assert batch["first_message_id"] == "first"
        workflow = ForwardArchive(config, str(tmp_path / "state"))
        await asyncio.wait_for(workflow._prompt(batch, gateway, batch["deadline"]), 15)
        assert gateway.sent[0][2] == "first"
        assert "1 张图片、1 个视频" in gateway.sent[0][1]
        assert await asyncio.wait_for(workflow.handle(
            _event("confirm", (), "保存", "prompt-1"), gateway), 15)
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
        assert await asyncio.wait_for(workflow.handle(_event("repeat", (), "保存"), gateway), 15)
        assert len([path for path in config.save_root.rglob("*") if path.is_file()]) == 2

    asyncio.run(scenario())


def test_collection_uses_first_message_maximum_and_quiet_deadline(tmp_path: Path) -> None:
    """Each new message moves the quiet deadline without moving the fixed cap."""
    store = ForwardArchiveStore(str(tmp_path))
    item = [{"kind": "image", "file": "a.jpg", "url": ""}]
    assert store.add_message("personal", "user-1", "first", item, 0, 1000, 10, 60, 5)
    assert store.add_message("personal", "user-1", "second", item, 0, 1008, 10, 60, 5)
    assert store.due(1017) == []
    batch = store.due(1018)[0]
    assert batch["first_at"] == 1000
    assert batch["last_at"] == 1008
    assert batch["deadline"] == 1018
    assert not store.add_message("personal", "user-1", "second", item, 0, 1009, 10, 60, 5)
    assert store.add_message("personal", "user-1", "third", item, 0, 1020, 10, 60, 5)
    assert len(store.due(float("inf"))) == 2
    capped = ForwardArchiveStore(str(tmp_path / "cap"))
    capped.add_message("personal", "user-1", "a", item, 0, 1000, 40, 60, 5)
    capped.add_message("personal", "user-1", "b", item, 0, 1030, 40, 60, 5)
    assert capped.due(1059) == []
    assert capped.due(1060)[0]["deadline"] == 1060


def test_config_validates_feature_limits_and_words(tmp_path: Path) -> None:
    """An invalid independent feature file fails before bot startup."""
    path = tmp_path / "config.toml"
    path.write_text('enabled = true\nquiet_seconds = 61\nmax_collection_seconds = 60\n')
    with pytest.raises(ConfigurationError, match="quiet_seconds"):
        ForwardArchiveConfig.load(path)
    path.write_text('enabled = true\nconfirm_words = ["保存"]\ncancel_words = ["保存"]\n')
    with pytest.raises(ConfigurationError, match="distinct"):
        ForwardArchiveConfig.load(path)


def test_file_saver_enforces_size_and_source_boundary(tmp_path: Path) -> None:
    """Oversized or unrelated local files never enter the archive."""
    config = replace(_config(tmp_path), max_file_bytes=3, max_batch_bytes=5)
    source = _cache_file(config, "Pic", "source.jpg")
    source.write_bytes(b"four")
    saver = ArchiveFileSaver(config)
    with pytest.raises(ArchiveFileError, match="size limit"):
        saver.save({"kind": "image", "name": "source.jpg"}, str(source), 1000, 5)
    assert not list(config.save_root.rglob("*.jpg"))
    other = tmp_path / "private.jpg"
    other.write_bytes(b"ok")
    with pytest.raises(ArchiveFileError, match="outside"):
        saver.save({"kind": "image", "name": "private.jpg"}, str(other), 1000, 5)
    credential = config.local_media_root / "nt_qq_test" / "nt_data" / "msf" / "secret.db"
    credential.parent.mkdir(parents=True)
    credential.write_bytes(b"ok")
    with pytest.raises(ArchiveFileError, match="media cache"):
        saver.save({"kind": "image", "name": "secret.db"}, str(credential), 1000, 5)


def test_media_url_accepts_observed_qq_host() -> None:
    """Forwarded pictures can use the QQ multimedia download host."""
    _check_url("https://multimedia.nt.qq.com.cn/download")
    with pytest.raises(ArchiveFileError, match="host"):
        _check_url("https://multimedia.nt.qq.com.cn.example.org/download")


def test_failed_item_can_be_retried_without_replacing_completed_file(tmp_path: Path) -> None:
    """A partial archive keeps successes and retries only the failed source."""
    async def scenario() -> None:
        """Confirm twice around a temporarily unavailable attachment."""
        config = _config(tmp_path)
        first = _cache_file(config, "Pic", "first.jpg")
        second = _cache_file(config, "Pic", "second.jpg")
        first.write_bytes(b"first")
        workflow = ForwardArchive(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        event = _event("media", (
            MessageSegment("image", {"file": first.name, "url": str(first)}),
            MessageSegment("image", {"file": second.name, "url": str(second)}),
        ))
        assert await workflow.handle(event, gateway)
        batch = ForwardArchiveStore(str(tmp_path / "state")).due(float("inf"))[0]
        await workflow._prompt(batch, gateway, batch["deadline"])
        assert await workflow.handle(_event("save-1", (), "保存", "prompt-1"), gateway)
        assert "已保存 1 项，失败 1 项" in gateway.sent[-1][1]
        archived_first = next(config.save_root.rglob("first.jpg"))
        original_inode = archived_first.stat().st_ino
        second.write_bytes(b"second")
        assert await workflow.handle(_event("save-2", (), "保存", "prompt-1"), gateway)
        assert "已保存 2 项，失败 0 项" in gateway.sent[-1][1]
        assert archived_first.stat().st_ino == original_inode
        assert next(config.save_root.rglob("second.jpg")).read_bytes() == b"second"

    asyncio.run(scenario())


def test_failed_prompt_is_retried_after_reconnect(tmp_path: Path) -> None:
    """An unsent question remains pending and can be delivered later."""
    async def scenario() -> None:
        """Fail the initial prompt and then deliver the same batch question."""
        config = _config(tmp_path)
        workflow = ForwardArchive(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        event = _event("first", (MessageSegment("image", {"file": "a.jpg"}),))
        assert await workflow.handle(event, gateway)
        store = ForwardArchiveStore(str(tmp_path / "state"))
        batch = store.due(float("inf"))[0]
        gateway.fail_count = 1
        await workflow._prompt(batch, gateway, batch["deadline"])
        assert not gateway.sent
        retry = store.unprompted(batch["deadline"] + 31)
        assert len(retry) == 1
        await workflow._send_prompt(retry[0], gateway, batch["deadline"] + 31)
        assert gateway.sent[0][2] == "first"
        assert not store.unprompted(batch["deadline"] + 32)

    asyncio.run(scenario())


def test_plain_confirmation_selects_latest_prompted_batch(tmp_path: Path) -> None:
    """A stale failed batch does not block confirmation of a newer forward."""
    async def scenario() -> None:
        """Keep two prompts pending and confirm the latest without a quote."""
        config = _config(tmp_path)
        first = _cache_file(config, "Pic", "first.jpg")
        second = _cache_file(config, "Pic", "second.jpg")
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        workflow = ForwardArchive(config, str(tmp_path / "state"))
        store = ForwardArchiveStore(str(tmp_path / "state"))
        gateway = FakeGateway()
        for index, source in enumerate((first, second), 1):
            event = _event(str(index), (
                MessageSegment("image", {"file": source.name, "url": str(source)}),
            ))
            assert await workflow.handle(event, gateway)
            collecting = store.due(float("inf"))
            assert len(collecting) == 1
            await workflow._prompt(collecting[0], gateway, collecting[0]["deadline"])

        assert await workflow.handle(_event("save", (), "保存"), gateway)
        assert next(config.save_root.rglob("second.jpg")).read_bytes() == b"second"
        assert not list(config.save_root.rglob("first.jpg"))
        pending = store.awaiting("personal", "user-1", time.time())
        assert len(pending) == 1
        assert pending[0]["first_message_id"] == "1"

    asyncio.run(scenario())
