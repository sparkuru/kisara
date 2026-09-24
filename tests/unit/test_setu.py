"""Focused tests for private setu confirmation and file placement."""

import asyncio
import sqlite3
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import pytest

from kisara.application.services.setu import Setu
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
            "这条合并转发共 1 张图片、1 个视频、0 个文件；\n"
            '引用这条消息并回复 "确认" 以保存，或回复 "取消" 以撤销。'
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
        assert "保存目录：" in gateway.sent[-1][1]
        assert await asyncio.wait_for(workflow.handle(
            _event("repeat", (), "确认", "prompt-1"), gateway), 15)
        assert len([path for path in config.save_root.rglob("*") if path.is_file()]) == 2

    asyncio.run(scenario())


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
    path.write_text('enabled = true\nconfirm_words = ["保存"]\ncancel_words = ["保存"]\n')
    with pytest.raises(ConfigurationError, match="distinct"):
        SetuConfig.load(path)
    path.write_text('enabled = true\ncancel_words = ["/setu"]\n')
    with pytest.raises(ConfigurationError, match="cannot be a cancellation"):
        SetuConfig.load(path)
    path.write_text(
        'enabled = true\nconfirm_words = ["yes", "确认"]\n'
        'cancel_words = ["cancel", "取消"]\n'
    )
    assert SetuConfig.load(path).confirm_words == ("yes", "确认")
    assert SetuConfig.load(path).cancel_words == ("cancel", "取消")


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
        assert '引用这条消息并回复 "确认"' in gateway.sent[0][1]
        assert not config.save_root.exists()
        assert not await workflow.handle(_event("empty", (), "", "prompt-1"), gateway)
        assert not config.save_root.exists()
        assert await workflow.handle(_event("plain", (), "确认"), gateway)
        assert gateway.sent[-1][1] == "请引用对应的归档提示后再确认。"
        assert not config.save_root.exists()
        assert await workflow.handle(_event("confirm", (), "确认", "prompt-1"), gateway)
        assert next(config.save_root.rglob("source.jpg")).read_bytes() == b"image-content"
        assert "已保存 1 项，失败 0 项" in gateway.sent[-1][1]

    asyncio.run(scenario())


def test_setu_without_quote_or_pending_batch_requests_a_forward(tmp_path: Path) -> None:
    """A bare command still explains how to start when nothing awaits confirmation."""
    async def scenario() -> None:
        workflow = Setu(_config(tmp_path), str(tmp_path / "state"))
        gateway = FakeGateway()
        assert await workflow.handle(_event("bare", (), "/setu"), gateway)
        assert gateway.sent[0][1] == "请引用合并转发并发送保存、setu 或 /setu。"

    asyncio.run(scenario())


def test_prompt_shows_only_first_configured_action_words(tmp_path: Path) -> None:
    """The prompt displays primary words and still accepts configured aliases."""
    async def scenario() -> None:
        """Start one batch with aliases configured in a deliberate order."""
        config = replace(_config(tmp_path), confirm_words=("yes", "确认"),
                         cancel_words=("cancel", "取消"))
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        source = _cache_file(config, "Pic", "ordered.jpg")
        source.write_bytes(b"ordered")
        assert await workflow.handle(_event(
            "request", (_forward_image(source),), "保存", "source", "source",
        ), gateway)
        assert gateway.sent[0][1] == (
            "这条合并转发共 1 张图片、0 个视频、0 个文件；\n"
            '引用这条消息并回复 "yes" 以保存，或回复 "cancel" 以撤销。'
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


def test_media_url_accepts_observed_qq_host() -> None:
    """Forwarded pictures can use the QQ multimedia download host."""
    _check_url("https://multimedia.nt.qq.com.cn/download")
    with pytest.raises(SetuFileError, match="host"):
        _check_url("https://multimedia.nt.qq.com.cn.example.org/download")


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
        assert "可再次回复“确认”重试失败项。" in gateway.sent[-1][1]
        archived_first = next(config.save_root.rglob("first.jpg"))
        original_inode = archived_first.stat().st_ino
        second.write_bytes(b"second")
        assert await workflow.handle(_event("save-2", (), "确认", "prompt-1"), gateway)
        assert "已保存 2 项，失败 0 项" in gateway.sent[-1][1]
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


def test_quoted_cancellation_only_cancels_selected_batch(tmp_path: Path) -> None:
    """A quoted cancellation removes only its matching pending batch."""
    async def scenario() -> None:
        """Reject a plain cancellation, then cancel the quoted prompt."""
        config = _config(tmp_path)
        workflow = Setu(config, str(tmp_path / "state"))
        gateway = FakeGateway()
        source = _cache_file(config, "Pic", "cancel.jpg")
        source.write_bytes(b"cancel")
        assert await workflow.handle(_event(
            "request", (_forward_image(source),), "setu", "source", "source",
        ), gateway)
        assert await workflow.handle(_event("plain", (), "取消"), gateway)
        assert len(SetuStore(str(tmp_path / "state")).awaiting(
            "personal", "user-1", time.time(),
        )) == 1
        assert await workflow.handle(_event("cancel", (), "取消", "prompt-1"), gateway)
        assert gateway.sent[-1][1] == "已取消这批附件的保存。"
        assert not SetuStore(str(tmp_path / "state")).awaiting(
            "personal", "user-1", time.time(),
        )
        assert not config.save_root.exists()

    asyncio.run(scenario())
