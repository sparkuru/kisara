"""Protocol-level tests for OneBot request handling without a live server."""

import asyncio
import base64
import io
import json
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from kisara.application.services.setu import Setu
from kisara.bot.adapters import onebot_v11
from kisara.bot.adapters.onebot_v11 import OneBotError, OneBotV11Adapter
from kisara.bot.contracts import MessageEvent, MessageSegment, OutgoingMessage
from kisara.config import Settings
from kisara.config.setu import SetuConfig
from kisara.infrastructure.persistence import setu_files
from kisara.infrastructure.persistence.news_delivery import NewsDeliveryStore
from kisara.infrastructure.persistence.setu import SetuStore


class FakeWebSocket:
    """Capture outgoing requests for deterministic adapter tests."""

    def __init__(self) -> None:
        self.sent: List[Dict[str, Any]] = []

    async def send(self, payload: str) -> None:
        """Record a JSON request as if it were sent over WebSocket."""

        self.sent.append(json.loads(payload))


def _adapter(timeout: float = 0.1) -> OneBotV11Adapter:
    """Build an adapter with a short test timeout and no network connection."""

    settings = Settings(
        engine="onebot",
        instance_id="test",
        allowed_users=frozenset(),
        groups_enabled=False,
        allowed_groups=frozenset(),
        onebot_ws_url="ws://napcat:3001",
        onebot_access_token="test-token",
    )
    return OneBotV11Adapter(
        settings,
        lambda event: None,
        request_timeout_seconds=timeout,
    )


async def _wait_for_requests(
    websocket: FakeWebSocket, count: int, delay: float = 0,
) -> None:
    """Wait until the adapter has emitted the expected request count."""

    for _ in range(100):
        if len(websocket.sent) >= count:
            return
        await asyncio.sleep(delay)
    raise AssertionError("adapter did not emit the expected requests")


async def _ack_save_start(adapter: OneBotV11Adapter, websocket: FakeWebSocket,
                          index: int, quote_id: str, text: str) -> int:
    """Verify the quoted notice gates all later requests, then acknowledge it."""
    await _wait_for_requests(websocket, index + 1, delay=0.01)
    notice = websocket.sent[index]
    assert notice["action"] == "send_private_msg"
    assert notice["params"]["message"] == [
        {"type": "reply", "data": {"id": quote_id}},
        {"type": "text", "data": {"text": text}},
    ]
    assert len(websocket.sent) == index + 1
    adapter._resolve_pending({
        "echo": notice["echo"], "status": "ok", "retcode": 0,
        "data": {"message_id": 600},
    })
    return index + 1


def test_requests_correlate_out_of_order_echoes() -> None:
    """Concurrent requests must resolve by echo instead of arrival order."""

    asyncio.run(_test_requests_correlate_out_of_order_echoes())


async def _test_requests_correlate_out_of_order_echoes() -> None:
    """Exercise concurrent request correlation in an event loop."""

    adapter = _adapter()
    websocket = FakeWebSocket()
    adapter._websocket = websocket

    first = asyncio.create_task(
        adapter._request("send_private_msg", {"user_id": 1, "message": "a"})
    )
    second = asyncio.create_task(
        adapter._request("send_private_msg", {"user_id": 2, "message": "b"})
    )
    await _wait_for_requests(websocket, 2)

    adapter._resolve_pending(
        {"echo": websocket.sent[1]["echo"], "status": "ok", "retcode": 0}
    )
    adapter._resolve_pending(
        {"echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0}
    )
    await asyncio.gather(first, second)


def test_failed_response_is_reported() -> None:
    """A non-zero OneBot return code must not be treated as success."""

    asyncio.run(_test_failed_response_is_reported())


async def _test_failed_response_is_reported() -> None:
    """Exercise failed response handling in an event loop."""

    adapter = _adapter()
    websocket = FakeWebSocket()
    adapter._websocket = websocket
    request = asyncio.create_task(
        adapter._request("send_private_msg", {"user_id": 1, "message": "a"})
    )
    await _wait_for_requests(websocket, 1)
    adapter._resolve_pending(
        {"echo": websocket.sent[0]["echo"], "status": "failed", "retcode": 100}
    )

    try:
        await request
    except OneBotError as error:
        assert "request failed" in str(error)
    else:
        raise AssertionError("failed response did not raise OneBotError")


def test_request_timeout_is_reported() -> None:
    """A missing response must terminate the wait with a clear error."""

    asyncio.run(_test_request_timeout_is_reported())


async def _test_request_timeout_is_reported() -> None:
    """Exercise timeout handling in an event loop."""

    adapter = _adapter(timeout=0.001)
    websocket = FakeWebSocket()
    adapter._websocket = websocket

    try:
        await adapter._request(
            "send_private_msg", {"user_id": 1, "message": "a"}
        )
    except OneBotError as error:
        assert "timed out" in str(error)
    else:
        raise AssertionError("missing response did not time out")


def test_file_resolution_outlasts_chat_deadline_without_changing_it() -> None:
    """A delayed file reply survives while a concurrent unanswered chat call expires."""
    async def scenario() -> None:
        """Simulate transfer delay in milliseconds rather than sleeping for minutes."""
        adapter = _adapter(timeout=0.005)
        websocket = FakeWebSocket()
        adapter._websocket = websocket
        transfer = asyncio.create_task(adapter.media_location({
            "kind": "file", "file": "canonical-id", "size": "109092709",
        }))
        chat = asyncio.create_task(adapter._request("get_msg", {"message_id": "short-chat"}))
        await _wait_for_requests(websocket, 2)
        with pytest.raises(OneBotError, match="timed out"):
            await chat
        await asyncio.sleep(0.02)
        assert not transfer.done()
        request = next(item for item in websocket.sent if item["action"] == "get_file")
        adapter._resolve_pending({
            "echo": request["echo"], "status": "ok", "retcode": 0,
            "data": {"file": "/approved/cache/file"},
        })
        assert await transfer == "/approved/cache/file"
        assert adapter._request_timeout_seconds == 0.005
        assert not adapter._pending

    asyncio.run(scenario())


@pytest.mark.parametrize("failure", ["timeout", "rejected", "invalid_response", "out_of_range"])
def test_file_request_failure_logs_safe_category_and_cleans_pending(
    failure: str, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transfer diagnostics omit parameters, identifiers, URLs and server messages."""
    async def scenario() -> None:
        """Exercise a bounded file timeout or a native download failure response."""
        adapter = _adapter(timeout=0.005)
        websocket = FakeWebSocket()
        adapter._websocket = websocket
        monkeypatch.setattr(onebot_v11, "_file_request_timeout", lambda size: 0.01)
        private_marker = "private-file-token-123"
        task = asyncio.create_task(adapter.media_location({
            "kind": "file", "file": private_marker, "size": "109092709",
        }))
        await _wait_for_requests(websocket, 1)
        request = websocket.sent[0]
        oversized_retcode = 10 ** 40 + 123456789
        if failure != "timeout":
            adapter._resolve_pending({
                "echo": request["echo"], "status": "failed",
                "retcode": private_marker if failure == "invalid_response" else
                           oversized_retcode if failure == "out_of_range" else 1200,
                "message": "https://private.example/?token=" + private_marker,
                "wording": private_marker,
            })
        with pytest.raises(OneBotError) as caught:
            await task
        onebot_v11._log.error(
            "Outer request boundary",
            exc_info=(type(caught.value), caught.value, caught.value.__traceback__),
        )
        assert not adapter._pending
        adapter._resolve_pending({"echo": request["echo"], "data": {"file": private_marker}})
        assert "action=get_file" in caplog.text
        assert "reason=" + ("rejected" if failure == "out_of_range" else failure) in caplog.text
        if failure == "timeout":
            assert "timeout_seconds=0.010" in caplog.text
        if failure == "rejected":
            assert "retcode=1200" in caplog.text
        if failure == "out_of_range":
            assert "retcode=invalid" in caplog.text
            assert str(oversized_retcode) not in caplog.text
        assert private_marker not in caplog.text
        assert "private.example" not in caplog.text
        assert request["echo"] not in caplog.text

    asyncio.run(scenario())


@pytest.mark.parametrize("failure", [
    "timeout", "disconnect", "cancel", "rejected", "invalid_retcode",
    "invalid_packet", "write_failure",
])
def test_partial_native_stream_failure_releases_correlation_and_ignores_late_packets(
    failure: str, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failed streams cannot retain callbacks or write through a retired echo."""
    async def scenario() -> None:
        """Interrupt a partial download and then complete an unrelated chat request."""
        adapter = _adapter(timeout=0.05)
        websocket = FakeWebSocket()
        adapter._websocket = websocket
        monkeypatch.setattr(onebot_v11, "_file_request_timeout", lambda size: 0.05)
        private_marker = "private-stream-token-123"

        class Output(io.BytesIO):
            """Simulate a spool write failure after a valid first chunk."""

            def write(self, content: bytes) -> int:
                """Keep the first chunk and fail the next write when requested."""
                if failure == "write_failure" and self.tell():
                    raise OSError(private_marker)
                return super().write(content)

        output = Output()
        task = asyncio.create_task(adapter.download_file({
            "kind": "file", "file": private_marker, "size": "2",
        }, output, 2))
        await _wait_for_requests(websocket, 1)
        echo = websocket.sent[0]["echo"]
        adapter._resolve_pending({"echo": echo, "data": {
            "type": "stream", "data_type": "file_info", "file_size": 2,
        }})
        adapter._resolve_pending({"echo": echo, "data": {
            "type": "stream", "data_type": "file_chunk", "index": 0,
            "data": "YQ==", "size": 1,
        }})
        assert output.getvalue() == b"a"
        if failure == "disconnect":
            adapter._fail_pending(OneBotError("OneBot connection closed"))
        elif failure == "cancel":
            task.cancel()
        elif failure in {"rejected", "invalid_retcode"}:
            adapter._resolve_pending({
                "echo": echo, "status": "failed",
                "retcode": private_marker if failure == "invalid_retcode" else 1200,
                "message": "https://private.example/?token=" + private_marker,
            })
        elif failure == "invalid_packet":
            adapter._resolve_pending({"echo": echo, "data": private_marker})
        elif failure == "write_failure":
            adapter._resolve_pending({"echo": echo, "data": {
                "type": "stream", "data_type": "file_chunk", "index": 1,
                "data": "Yg==", "size": 1,
            }})
        with pytest.raises(asyncio.CancelledError if failure == "cancel" else OneBotError):
            await task
        assert not adapter._pending
        assert not adapter._pending_streams
        adapter._resolve_pending({"echo": echo, "data": {
            "type": "stream", "data_type": "file_chunk", "index": 1,
            "data": "Yg==", "size": 1,
        }})
        adapter._resolve_pending({"echo": echo, "data": {
            "type": "response", "data_type": "file_complete", "total_chunks": 2,
            "total_bytes": 2,
        }})
        assert output.getvalue() == b"a"
        assert private_marker not in caplog.text
        assert "private.example" not in caplog.text
        assert echo not in caplog.text
        chat = asyncio.create_task(adapter._request("get_msg", {"message_id": "other"}))
        await _wait_for_requests(websocket, 2)
        adapter._resolve_pending({"echo": websocket.sent[1]["echo"], "status": "ok", "retcode": 0})
        assert (await chat)["status"] == "ok"
        assert not adapter._pending
        assert not adapter._pending_streams

    asyncio.run(scenario())


def test_media_reply_uses_onebot_segments() -> None:
    """A normalized rich reply should become image and music segments."""

    asyncio.run(_test_media_reply_uses_onebot_segments())


async def _test_media_reply_uses_onebot_segments() -> None:
    """Capture a media send without a live WebSocket server."""

    adapter = _adapter()
    websocket = FakeWebSocket()
    adapter._websocket = websocket
    event = MessageEvent(
        engine="onebot", instance_id="test", message_id="1",
        conversation_kind="private", conversation_id="123", sender_id="123",
        segments=(), reply_context={},
    )
    reply = OutgoingMessage(
        "Here it is", ("https://i.pixiv.re/42.jpg",), "1234"
    )
    task = asyncio.create_task(adapter.send_reply(event, reply))
    await _wait_for_requests(websocket, 1)
    message = websocket.sent[0]["params"]["message"]
    assert [segment["type"] for segment in message] == ["text", "image", "music"]
    adapter._resolve_pending(
        {"echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0}
    )
    await task


def test_quoted_image_is_loaded_for_source_search() -> None:
    """An image in a quoted message should reach the shared handler."""

    asyncio.run(_test_quoted_image_is_loaded_for_source_search())


async def _test_quoted_image_is_loaded_for_source_search() -> None:
    """Resolve the standard get_msg response through the echo path."""

    adapter = _adapter()
    websocket = FakeWebSocket()
    adapter._websocket = websocket
    event = MessageEvent(
        engine="onebot", instance_id="test", message_id="2",
        conversation_kind="private", conversation_id="123", sender_id="123",
        segments=(MessageSegment("text", {"text": "/source"}),),
        reply_context={"quoted_message_id": "42", "self_id": "999"},
    )
    task = asyncio.create_task(adapter._enrich_quoted_message(event))
    await _wait_for_requests(websocket, 1)
    assert websocket.sent[0]["action"] == "get_msg"
    adapter._resolve_pending({
        "echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0,
        "data": {"message_type": "private", "sender": {"user_id": 999},
                 "message": [{"type": "image", "data": {"url": "https://example.com/image.jpg"}}]},
    })
    enriched = await task
    assert enriched.reply_context["quoted_sender_id"] == "999"
    assert enriched.segments[-1].data["url"] == "https://example.com/image.jpg"


def _quoted_event(text: str) -> MessageEvent:
    """Create an allowed private quote for the protocol workflow tests."""
    return MessageEvent(
        engine="onebot", instance_id="test", message_id="100",
        conversation_kind="private", conversation_id="123", sender_id="123",
        segments=(MessageSegment("reply", {"id": "42"}),
                  MessageSegment("text", {"text": text})),
        reply_context={"quoted_message_id": "42", "self_id": "999"},
    )


def test_export_quote_sends_original_files_without_archiving(tmp_path: Path) -> None:
    """Export takes priority over setu and makes quoted media saveable."""
    asyncio.run(_test_export_quote_sends_original_files_without_archiving(tmp_path))


async def _test_export_quote_sends_original_files_without_archiving(tmp_path: Path) -> None:
    """Drive quote lookup and one file send per image through API responses."""
    adapter = _adapter()
    adapter._allowed_users = frozenset({"123"})
    config = replace(SetuConfig.disabled(), enabled=True,
                     allowed_users=frozenset({"123"}))
    adapter._setu = Setu(config, str(tmp_path))
    websocket = FakeWebSocket()
    adapter._websocket = websocket
    task = asyncio.create_task(adapter._process_event(_quoted_event("请导出这张表情包")))
    await _wait_for_requests(websocket, 1)
    assert websocket.sent[0]["action"] == "get_msg"
    adapter._resolve_pending({
        "echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0,
        "data": {"message_type": "private", "user_id": 123,
                 "message": [{"type": "image", "data": {
                     "url": "https://example.com/sticker.gif", "sub_type": 1}},
                     {"type": "mface", "data": {
                         "url": "https://example.com/market-sticker.gif"}},
                     {"type": "file", "data": {
                         "file_name": "original.png", "url": "https://example.com/original.png"}},
                     {"type": "file", "data": {
                         "file_name": "notes.txt", "url": "https://example.com/notes.txt"}},
                     {"type": "forward", "data": {"id": "merged"}}]},
    })
    for index, (url, name) in enumerate((
        ("https://example.com/sticker.gif", "export-1.gif"),
        ("https://example.com/market-sticker.gif", "export-2.gif"),
        ("https://example.com/original.png", "export-3.png"),
    ), start=1):
        await _wait_for_requests(websocket, index + 1)
        sent = websocket.sent[index]
        assert sent["action"] == "send_private_msg"
        assert sent["params"]["message"] == [
            {"type": "file", "data": {"file": url, "name": name}},
        ]
        adapter._resolve_pending({"echo": sent["echo"], "status": "ok", "retcode": 0})
    await task
    assert not SetuStore(str(tmp_path)).due(float("inf"))


def test_quoted_image_from_another_private_chat_is_rejected() -> None:
    """A forged reply ID cannot export media from an unrelated conversation."""
    asyncio.run(_test_quoted_image_from_another_private_chat_is_rejected())


async def _test_quoted_image_from_another_private_chat_is_rejected() -> None:
    """Reject an otherwise valid image with an unrelated sender ID."""
    adapter = _adapter()
    adapter._allowed_users = frozenset({"123"})
    websocket = FakeWebSocket()
    adapter._websocket = websocket
    task = asyncio.create_task(adapter._process_event(_quoted_event("/export-img")))
    await _wait_for_requests(websocket, 1)
    adapter._resolve_pending({
        "echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0,
        "data": {"message_type": "private", "user_id": 456,
                 "message": [{"type": "image", "data": {
                     "url": "https://example.com/private.jpg"}}]},
    })
    await _wait_for_requests(websocket, 2)
    sent = websocket.sent[1]
    assert sent["params"]["message"] == "引用的消息中没有图片。"
    adapter._resolve_pending({"echo": sent["echo"], "status": "ok", "retcode": 0})
    await task


@pytest.mark.parametrize("word", ["保存", "setu", "/setu"])
def test_quoted_setu_prompts_once_for_source_forward(tmp_path: Path, word: str) -> None:
    """Each quoted start word prompts once for its source forward."""
    asyncio.run(_test_quoted_setu_prompts_once_for_source_forward(tmp_path, word))


async def _test_quoted_setu_prompts_once_for_source_forward(
    tmp_path: Path, word: str,
) -> None:
    """Resolve the quoted forward and inspect the resulting archive prompt."""
    adapter = _adapter()
    adapter._allowed_users = frozenset({"123"})
    config = replace(SetuConfig.disabled(), enabled=True,
                     allowed_users=frozenset({"123"}))
    adapter._setu = Setu(config, str(tmp_path))
    websocket = FakeWebSocket()
    adapter._websocket = websocket
    task = asyncio.create_task(adapter._process_event(_quoted_event(word)))
    await _wait_for_requests(websocket, 1)
    adapter._resolve_pending({
        "echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0,
        "data": {"message_type": "private", "user_id": 123,
                 "message": [{"type": "forward", "data": {"id": "merged", "content": [
                     {"message": [{"type": "image", "data": {
                         "file": "image.jpg"}}]},
                 ]}}]},
    })
    await _wait_for_requests(websocket, 2)
    prompt = websocket.sent[1]
    assert prompt["params"]["message"][0] == {"type": "reply", "data": {"id": "42"}}
    assert prompt["params"]["message"][1]["data"]["text"] == (
        "这条消息共 1 张图片、0 个视频、0 个文件；\n"
        '引用这条消息并回复 "保存" 以保存（超时 60s 后自动取消）。'
    )
    adapter._resolve_pending({
        "echo": prompt["echo"], "status": "ok", "retcode": 0,
        "data": {"message_id": 500},
    })
    await task
    batches = SetuStore(str(tmp_path)).awaiting("test", "123", time.time())
    assert len(batches) == 1
    assert batches[0]["first_message_id"] == "42"
    repeat = replace(_quoted_event(word), message_id="101")
    repeat_task = asyncio.create_task(adapter._process_event(repeat))
    await _wait_for_requests(websocket, 3)
    adapter._resolve_pending({
        "echo": websocket.sent[2]["echo"], "status": "ok", "retcode": 0,
        "data": {"message_type": "private", "user_id": 123,
                 "message": [{"type": "forward", "data": {"id": "merged", "content": [
                     {"message": [{"type": "image", "data": {"file": "image.jpg"}}]},
                 ]}}]},
    })
    await repeat_task
    assert len(websocket.sent) == 3


@pytest.mark.parametrize("word", ["直接保存", "archive-now"])
def test_quoted_direct_save_returns_result_without_question(
    tmp_path: Path, word: str,
) -> None:
    """Default and configured direct commands fetch a quote and save immediately."""
    asyncio.run(_test_quoted_direct_save_returns_result_without_question(tmp_path, word))


async def _test_quoted_direct_save_returns_result_without_question(
    tmp_path: Path, word: str,
) -> None:
    """Drive an allowed local media source through quote lookup and result send."""
    adapter = _adapter(timeout=2)
    adapter._allowed_users = frozenset({"123"})
    config = replace(
        SetuConfig.disabled(), enabled=True, allowed_users=frozenset({"123"}),
        direct_confirm_words=(word,), save_root=tmp_path / "archive",
        local_media_root=tmp_path / "cache",
    )
    source = config.local_media_root / "nt_qq_test" / "nt_data" / "Pic" / "direct.jpg"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"direct-media")
    adapter._setu = Setu(config, str(tmp_path / "state"))
    websocket = FakeWebSocket()
    adapter._websocket = websocket
    task = asyncio.create_task(adapter._process_event(_quoted_event(word)))
    await _wait_for_requests(websocket, 1)
    assert websocket.sent[0]["action"] == "get_msg"
    adapter._resolve_pending({
        "echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0,
        "data": {"message_type": "private", "user_id": 123,
                 "message": [{"type": "forward", "data": {"id": "direct", "content": [
                     {"message": [{"type": "image", "data": {
                         "file": source.name, "url": str(source)}}]},
                 ]}}]},
    })
    index = await _ack_save_start(adapter, websocket, 1, "100", "正在保存以上 1 张图片。")
    assert not config.save_root.exists()
    await _wait_for_requests(websocket, index + 1, delay=0.01)
    result = websocket.sent[index]
    assert result["action"] == "send_private_msg"
    assert result["params"]["message"][0] == {
        "type": "reply", "data": {"id": "100"},
    }
    assert len(result["params"]["message"]) == 2
    result_text = result["params"]["message"][1]["data"]["text"]
    assert "已保存 1 项，失败 0 项" in result_text
    assert "引用这条消息并回复" not in result_text
    assert next(config.save_root.rglob("direct.jpg")).read_bytes() == b"direct-media"
    adapter._resolve_pending({
        "echo": result["echo"], "status": "ok", "retcode": 0,
        "data": {"message_id": 500},
    })
    await task
    assert len(websocket.sent) == 3


def test_quoted_setu_confirmation_result_quotes_command(tmp_path: Path) -> None:
    """A confirmed save replies to the user's confirmation, not the bot prompt."""
    asyncio.run(_test_quoted_setu_confirmation_result_quotes_command(tmp_path))


async def _test_quoted_setu_confirmation_result_quotes_command(tmp_path: Path) -> None:
    """Drive a forward, prompt, and confirmation through OneBot messages."""
    adapter = _adapter(timeout=2)
    adapter._allowed_users = frozenset({"123"})
    config = replace(
        SetuConfig.disabled(), enabled=True, allowed_users=frozenset({"123"}),
        save_root=tmp_path / "archive", local_media_root=tmp_path / "cache",
    )
    source = config.local_media_root / "nt_qq_test" / "nt_data" / "Pic" / "confirmed.jpg"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"confirmed-media")
    adapter._setu = Setu(config, str(tmp_path / "state"))
    websocket = FakeWebSocket()
    adapter._websocket = websocket
    start_task = asyncio.create_task(adapter._process_event(_quoted_event("保存")))
    await _wait_for_requests(websocket, 1)
    adapter._resolve_pending({
        "echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0,
        "data": {"message_type": "private", "user_id": 123,
                 "message": [{"type": "forward", "data": {"id": "confirmed", "content": [
                     {"message": [{"type": "image", "data": {
                         "file": source.name, "url": str(source)}}]},
                 ]}}]},
    })
    await _wait_for_requests(websocket, 2, delay=0.01)
    prompt = websocket.sent[1]
    assert prompt["params"]["message"][0] == {
        "type": "reply", "data": {"id": "42"},
    }
    adapter._resolve_pending({
        "echo": prompt["echo"], "status": "ok", "retcode": 0,
        "data": {"message_id": 500},
    })
    await start_task

    confirmation = replace(
        _quoted_event("保存"), message_id="101",
        segments=(MessageSegment("reply", {"id": "500"}),
                  MessageSegment("text", {"text": "保存"})),
        reply_context={"quoted_message_id": "500", "self_id": "999"},
    )
    confirm_task = asyncio.create_task(adapter._process_event(confirmation))
    await _wait_for_requests(websocket, 3)
    assert websocket.sent[2]["action"] == "get_msg"
    adapter._resolve_pending({
        "echo": websocket.sent[2]["echo"], "status": "ok", "retcode": 0,
        "data": {"message_type": "private", "user_id": 999,
                 "message": [{"type": "text", "data": {"text": "保存？"}}]},
    })
    index = await _ack_save_start(adapter, websocket, 3, "101", "正在保存以上 1 张图片。")
    assert not config.save_root.exists()
    await _wait_for_requests(websocket, index + 1, delay=0.01)
    result = websocket.sent[index]
    assert result["action"] == "send_private_msg"
    assert result["params"]["message"][0] == {
        "type": "reply", "data": {"id": "101"},
    }
    assert "已保存 1 项，失败 0 项" in result["params"]["message"][1]["data"]["text"]
    adapter._resolve_pending({
        "echo": result["echo"], "status": "ok", "retcode": 0,
        "data": {"message_id": 501},
    })
    await confirm_task
    assert next(config.save_root.rglob("confirmed.jpg")).read_bytes() == b"confirmed-media"


@pytest.mark.parametrize("mode", ["date_original", "timestamp_hash"])
@pytest.mark.parametrize("resolution", ["provided", "file", "temp", "stream", "url"])
@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("source_kind", ["forward", "file"])
def test_archive_forward_resolves_original_name_and_bytes_through_onebot(
    tmp_path: Path, mode: str, resolution: str, direct: bool,
    source_kind: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """File IDs and cache/URL locations save the original archive name after consent."""
    content = b"archive protocol bytes\x00\xff"
    remote_url = "https://multimedia.nt.qq.com.cn/download/archive"
    if resolution == "url":
        opener = SimpleNamespace(open=lambda location, timeout: io.BytesIO(content))
        monkeypatch.setattr(setu_files.urllib.request, "build_opener", lambda *args: opener)

    async def scenario() -> None:
        """Exercise quote lookup, optional prompt, file resolution and quoted result."""
        adapter = _adapter(timeout=2)
        adapter._allowed_users = frozenset({"123"})
        config = replace(
            SetuConfig.disabled(), enabled=True, allowed_users=frozenset({"123"}),
            save_mode=mode, save_root=tmp_path / "archive", local_media_root=tmp_path / "cache",
        )
        source = config.local_media_root / "nt_qq_test" / "nt_data" / "File" / "cache-id"
        if resolution in {"temp", "stream"}:
            source = config.local_media_root / "NapCat" / "temp" / "cache-id"
        source.parent.mkdir(parents=True)
        source.write_bytes(content)
        if resolution == "stream":
            original_open = Path.open

            def owner_only_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
                """Model the native 0600 source under the bot's different UID."""
                if path == source and mode == "rb":
                    raise PermissionError("native file is owner-only")
                return original_open(path, mode, *args, **kwargs)

            monkeypatch.setattr(Path, "open", owner_only_open)
        adapter._setu = Setu(config, str(tmp_path / "state"))
        websocket = FakeWebSocket()
        adapter._websocket = websocket
        original = "\u8d44\u6599 BackUp.TAR.GZ"
        file_data = {"file": original, "file_id": "opaque-file-id", "file_size": str(len(content))}
        if resolution == "provided":
            file_data["url"] = str(source)
        command = "\u76f4\u63a5\u4fdd\u5b58" if direct else "/setu"
        task = asyncio.create_task(adapter._process_event(_quoted_event(command)))
        await _wait_for_requests(websocket, 1)
        quoted_source = [{"type": "file", "data": file_data}]
        if source_kind == "forward":
            quoted_source = [{"type": "forward", "data": {"id": "archive-forward", "content": [
                {"message": quoted_source},
            ]}}]
        adapter._resolve_pending({
            "echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0,
            "data": {"message_type": "private", "user_id": 123, "message": quoted_source},
        })
        count = 1
        quote_id = "100"
        if not direct:
            await _wait_for_requests(websocket, 2, delay=0.01)
            prompt = websocket.sent[1]
            assert prompt["action"] == "send_private_msg"
            assert "1 \u4e2a\u6587\u4ef6" in prompt["params"]["message"][1]["data"]["text"]
            assert not config.save_root.exists()
            assert all(request["action"] != "get_file" for request in websocket.sent)
            adapter._resolve_pending({
                "echo": prompt["echo"], "status": "ok", "retcode": 0,
                "data": {"message_id": 500},
            })
            await task
            confirmation = replace(
                _quoted_event("\u4fdd\u5b58"), message_id="101",
                segments=(MessageSegment("reply", {"id": "500"}),
                          MessageSegment("text", {"text": "\u4fdd\u5b58"})),
                reply_context={"quoted_message_id": "500", "self_id": "999"},
            )
            task = asyncio.create_task(adapter._process_event(confirmation))
            await _wait_for_requests(websocket, 3)
            adapter._resolve_pending({
                "echo": websocket.sent[2]["echo"], "status": "ok", "retcode": 0,
                "data": {"message_type": "private", "user_id": 999,
                         "message": [{"type": "text", "data": {"text": "prompt"}}]},
            })
            count = 3
            quote_id = "101"
        assert not config.save_root.exists()
        count = await _ack_save_start(adapter, websocket, count, quote_id, "正在保存以上 1 个文件。")
        assert not config.save_root.exists()
        if resolution != "provided":
            await _wait_for_requests(websocket, count + 1, delay=0.01)
            request = websocket.sent[count]
            assert request["action"] == "get_file"
            assert request["params"] == {"file": "opaque-file-id", "file_id": "opaque-file-id"}
            adapter._resolve_pending({
                "echo": request["echo"], "status": "ok", "retcode": 0,
                "data": {"file" if resolution in {"temp", "stream"} else resolution:
                         remote_url if resolution == "url" else str(source)},
            })
            count += 1
        if resolution == "stream":
            await _wait_for_requests(websocket, count + 1, delay=0.01)
            request = websocket.sent[count]
            assert request["action"] == "download_file_stream"
            assert request["params"] == {
                "file": "opaque-file-id", "file_id": "opaque-file-id", "chunk_size": 65536,
            }
            echo = request["echo"]
            adapter._resolve_pending({"echo": echo, "status": "ok", "retcode": 0, "data": {
                "type": "stream", "data_type": "file_info", "file_size": len(content),
            }})
            assert not task.done()
            adapter._resolve_pending({"echo": echo, "status": "ok", "retcode": 0, "data": {
                "type": "stream", "data_type": "file_chunk", "index": 0,
                "data": base64.b64encode(content).decode("ascii"), "size": len(content),
            }})
            assert not task.done()
            assert not list(config.save_root.rglob(original))
            adapter._resolve_pending({"echo": echo, "status": "ok", "retcode": 0, "data": {
                "type": "response", "data_type": "file_complete", "total_chunks": 1,
                "total_bytes": len(content),
            }})
            count += 1
        await _wait_for_requests(websocket, count + 1, delay=0.01)
        result = websocket.sent[count]
        assert result["action"] == "send_private_msg"
        assert result["params"]["message"][0] == {"type": "reply", "data": {"id": quote_id}}
        assert "\u5df2\u4fdd\u5b58 1 \u9879\uff0c\u5931\u8d25 0 \u9879" in result["params"]["message"][1]["data"]["text"]
        archived = next(config.save_root.rglob(original))
        assert archived.read_bytes() == content
        assert str(archived.parent) in result["params"]["message"][1]["data"]["text"]
        adapter._resolve_pending({
            "echo": result["echo"], "status": "ok", "retcode": 0,
            "data": {"message_id": 501},
        })
        await task
        assert all(request["action"] != "get_forward_msg" for request in websocket.sent)

    asyncio.run(scenario())


@pytest.mark.parametrize("conversation_kind, global_allowed, feature_allowed", [
    ("private", False, True), ("private", True, False), ("group", True, True),
])
def test_direct_save_does_not_fetch_unauthorized_or_group_quotes(
    tmp_path: Path, conversation_kind: str, global_allowed: bool, feature_allowed: bool,
) -> None:
    """The configured direct trigger preserves sender and private-chat boundaries."""
    async def scenario() -> None:
        """Reject archive routing before making any OneBot API call."""
        adapter = _adapter()
        adapter._allowed_users = frozenset({"123"}) if global_allowed else frozenset()
        adapter._setu = Setu(replace(
            SetuConfig.disabled(), enabled=True,
            allowed_users=frozenset({"123"}) if feature_allowed else frozenset(),
            direct_confirm_words=("archive-now",),
        ), str(tmp_path))
        websocket = FakeWebSocket()
        adapter._websocket = websocket
        event = replace(_quoted_event("archive-now"), conversation_kind=conversation_kind)
        if conversation_kind == "group":
            adapter._groups_enabled = True
            adapter._allowed_groups = frozenset({event.conversation_id})
            assert adapter._is_authorized(event)
        await adapter._process_event(event)
        assert not websocket.sent
        assert not SetuStore(str(tmp_path)).due(float("inf"))

    asyncio.run(scenario())


def test_direct_save_rejects_quoted_forward_from_another_private_chat(tmp_path: Path) -> None:
    """A configured alias cannot save attachments from an unrelated conversation."""
    async def scenario() -> None:
        """Return an unrelated sender for an otherwise valid forwarded message."""
        adapter = _adapter()
        adapter._allowed_users = frozenset({"123"})
        adapter._setu = Setu(replace(
            SetuConfig.disabled(), enabled=True, allowed_users=frozenset({"123"}),
            direct_confirm_words=("archive-now",),
        ), str(tmp_path))
        websocket = FakeWebSocket()
        adapter._websocket = websocket
        task = asyncio.create_task(adapter._process_event(_quoted_event("archive-now")))
        await _wait_for_requests(websocket, 1)
        adapter._resolve_pending({
            "echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0,
            "data": {"message_type": "private", "user_id": 456,
                     "message": [{"type": "forward", "data": {"id": "foreign", "content": [
                         {"message": [{"type": "image", "data": {"file": "private.jpg"}}]},
                     ]}}]},
        })
        await _wait_for_requests(websocket, 2)
        response = websocket.sent[1]
        assert response["params"]["message"] == [
            {"type": "text", "data": {"text": "请引用合并转发或文件消息并发送保存、setu 或 /setu。"}},
        ]
        adapter._resolve_pending({"echo": response["echo"], "status": "ok", "retcode": 0})
        await task
        assert not SetuStore(str(tmp_path)).due(float("inf"))

    asyncio.run(scenario())


@pytest.mark.parametrize("command", ["/setu", "\u76f4\u63a5\u4fdd\u5b58", "\u4fdd\u5b58"])
@pytest.mark.parametrize("with_quote", [False, True])
def test_global_denial_blocks_feature_allowed_guidance_and_pending_confirmation(
    tmp_path: Path, command: str, with_quote: bool,
) -> None:
    """Global authorization protects every setu path even with a pending feature batch."""
    async def scenario() -> None:
        """Present a denied event and leave an existing confirmation unclaimed."""
        adapter = _adapter()
        adapter._allowed_users = frozenset()
        config = replace(SetuConfig.disabled(), enabled=True, allowed_users=frozenset({"123"}),
                         save_root=tmp_path / "archive")
        workflow = Setu(config, str(tmp_path / "state"))
        adapter._setu = workflow
        batch = workflow._store.add_setu("test", "123", "source", [
            {"kind": "file", "file": "canonical-id", "name": "original.zip"},
        ], 0, time.time())
        assert batch is not None
        workflow._store.mark_awaiting(str(batch["id"]), time.time() + 60)
        workflow._store.set_prompt(str(batch["id"]), "42")
        websocket = FakeWebSocket()
        adapter._websocket = websocket
        event = _quoted_event(command)
        if not with_quote:
            event = replace(event, segments=(MessageSegment("text", {"text": command}),),
                            reply_context={})
        assert workflow.is_authorized(event)
        await adapter._process_event(event)
        assert not websocket.sent
        pending = workflow._store.awaiting("test", "123", time.time())
        assert len(pending) == 1
        assert pending[0]["state"] == "awaiting"
        assert not config.save_root.exists()

    asyncio.run(scenario())


@pytest.mark.parametrize("quoted_kind", ["image", "video", "text"])
def test_nonfile_ordinary_quotes_do_not_start_setu_archive(tmp_path: Path, quoted_kind: str) -> None:
    """The ordinary quote extension is limited to file segments."""
    async def scenario() -> None:
        """Return a different ordinary message kind and expect only source guidance."""
        adapter = _adapter()
        adapter._allowed_users = frozenset({"123"})
        config = replace(SetuConfig.disabled(), enabled=True, allowed_users=frozenset({"123"}),
                         save_root=tmp_path / "archive")
        adapter._setu = Setu(config, str(tmp_path / "state"))
        websocket = FakeWebSocket()
        adapter._websocket = websocket
        task = asyncio.create_task(adapter._process_event(_quoted_event("/setu")))
        await _wait_for_requests(websocket, 1)
        adapter._resolve_pending({
            "echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0,
            "data": {"message_type": "private", "user_id": 123,
                     "message": [{"type": quoted_kind, "data": {"file": "ordinary.jpg", "text": "plain"}}]},
        })
        await _wait_for_requests(websocket, 2)
        guidance = websocket.sent[1]
        assert guidance["action"] == "send_private_msg"
        assert guidance["params"]["message"] == [{"type": "text", "data": {
            "text": "\u8bf7\u5f15\u7528\u5408\u5e76\u8f6c\u53d1\u6216\u6587\u4ef6\u6d88\u606f\u5e76\u53d1\u9001\u4fdd\u5b58\u3001setu \u6216 /setu\u3002",
        }}]
        adapter._resolve_pending({"echo": guidance["echo"], "status": "ok", "retcode": 0})
        await task
        assert len(websocket.sent) == 2
        assert not adapter._setu._store.due(float("inf"))
        assert not adapter._setu._store.awaiting("test", "123", time.time())
        assert not config.save_root.exists()

    asyncio.run(scenario())


def test_quoted_file_source_excludes_attachment_on_current_command(tmp_path: Path) -> None:
    """Only the explicitly quoted attachment belongs to the quoted source batch."""
    async def scenario() -> None:
        """Save one quoted file without collecting another attachment on the command."""
        adapter = _adapter(timeout=2)
        adapter._allowed_users = frozenset({"123"})
        config = replace(SetuConfig.disabled(), enabled=True, allowed_users=frozenset({"123"}),
                         save_root=tmp_path / "archive", local_media_root=tmp_path / "cache")
        adapter._setu = Setu(config, str(tmp_path / "state"))
        source = config.local_media_root / "nt_qq_test" / "nt_data" / "File" / "quoted-cache"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"quoted archive")
        current = source.with_name("current-cache")
        current.write_bytes(b"unquoted archive")
        event = _quoted_event("\u76f4\u63a5\u4fdd\u5b58")
        event = replace(event, segments=event.segments + (MessageSegment("file", {
            "file": "unquoted.zip", "file_id": "unquoted-id", "url": str(current),
        }),))
        websocket = FakeWebSocket()
        adapter._websocket = websocket
        task = asyncio.create_task(adapter._process_event(event))
        await _wait_for_requests(websocket, 1)
        adapter._resolve_pending({
            "echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0,
            "data": {"message_type": "private", "user_id": 123, "message": [
                {"type": "file", "data": {"file": "quoted.zip", "file_id": "quoted-id", "url": str(source)}},
            ]},
        })
        index = await _ack_save_start(adapter, websocket, 1, "100", "正在保存以上 1 个文件。")
        assert not config.save_root.exists()
        await _wait_for_requests(websocket, index + 1, delay=0.01)
        result = websocket.sent[index]
        assert "\u5df2\u4fdd\u5b58 1 \u9879\uff0c\u5931\u8d25 0 \u9879" in result["params"]["message"][1]["data"]["text"]
        adapter._resolve_pending({"echo": result["echo"], "status": "ok", "retcode": 0,
                                  "data": {"message_id": 500}})
        await task
        files = [path for path in config.save_root.rglob("*") if path.is_file()]
        assert len(files) == 1
        assert files[0].name == "quoted.zip"
        assert files[0].read_bytes() == b"quoted archive"

    asyncio.run(scenario())


def test_setu_prompt_quotes_first_message_and_returns_prompt_id() -> None:
    """A delayed private prompt must quote its first source message."""
    asyncio.run(_test_setu_prompt_quotes_first_message_and_returns_prompt_id())


async def _test_setu_prompt_quotes_first_message_and_returns_prompt_id() -> None:
    """Check OneBot reply encoding and prompt ID extraction."""
    adapter = _adapter()
    websocket = FakeWebSocket()
    adapter._websocket = websocket
    task = asyncio.create_task(adapter.send_private("123", "Save?", "456"))
    await _wait_for_requests(websocket, 1)
    request = websocket.sent[0]
    assert request["action"] == "send_private_msg"
    assert request["params"]["message"][0] == {"type": "reply", "data": {"id": "456"}}
    adapter._resolve_pending({
        "echo": request["echo"], "status": "ok", "retcode": 0,
        "data": {"message_id": 789},
    })
    assert await task == "789"


def test_setu_fetches_forward_nodes() -> None:
    """Nested forward expansion must use the correlated OneBot API path."""
    asyncio.run(_test_setu_fetches_forward_nodes())


async def _test_setu_fetches_forward_nodes() -> None:
    """Capture get_forward_msg and return its message list."""
    adapter = _adapter()
    websocket = FakeWebSocket()
    adapter._websocket = websocket
    task = asyncio.create_task(adapter.fetch_forward("abc"))
    await _wait_for_requests(websocket, 1)
    request = websocket.sent[0]
    assert request["action"] == "get_forward_msg"
    assert request["params"]["id"] == "abc"
    adapter._resolve_pending({
        "echo": request["echo"], "status": "ok", "retcode": 0,
        "data": {"messages": [{"message": [{"type": "image", "data": {"file": "a.jpg"}}]}]},
    })
    assert len(await task) == 1


class NewsSession(FakeWebSocket):
    """Drive a connected scheduler through incoming protocol responses and closure."""

    def __init__(self) -> None:
        """Create a controllable WebSocket session without network traffic."""
        super().__init__()
        self.incoming: asyncio.Queue = asyncio.Queue()
        self.request_sent = asyncio.Event()

    async def __aenter__(self) -> "NewsSession":
        """Expose the fake session to the normal connection lifecycle."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Leave cleanup to the adapter's connection finally block."""

    def __aiter__(self) -> "NewsSession":
        """Read injected packets until the session is disconnected."""
        return self

    async def __anext__(self) -> str:
        """A None sentinel closes the simulated connection."""
        packet = await self.incoming.get()
        if packet is None:
            raise StopAsyncIteration
        return json.dumps(packet)

    async def send(self, payload: str) -> None:
        """Notify the test when the real request path writes a packet."""
        await super().send(payload)
        self.request_sent.set()


def test_private_news_disconnect_cancels_and_reconnect_recovers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Personal-only sessions cancel unconfirmed sends, retry and retain successes."""
    asyncio.run(_test_private_news_disconnect_cancels_and_reconnect_recovers(monkeypatch, tmp_path))


async def _test_private_news_disconnect_cancels_and_reconnect_recovers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Run three sessions through cancellation, confirmation and restart deduplication."""
    store = NewsDeliveryStore(str(tmp_path))
    settings = Settings(
        "onebot", "test", frozenset({"123"}), False, frozenset(),
        onebot_ws_url="ws://fake", onebot_access_token="test-token",
        news_push_users=frozenset({"123"}),
    )
    factory_calls = []

    def factory() -> OutgoingMessage:
        """Build the shared dated text and image outside the event loop."""
        factory_calls.append(True)
        return OutgoingMessage("2026-09-27", ("base64://news",))

    adapter = OneBotV11Adapter(settings, lambda event: None,
                              daily_news_factory=factory, delivery_store=store)
    due = datetime(2026, 9, 27, 10, 30, tzinfo=timezone(timedelta(hours=8)))
    monkeypatch.setattr(onebot_v11, "datetime", SimpleNamespace(now=lambda zone: due))
    sessions = [NewsSession(), NewsSession(), NewsSession()]
    remaining = iter(sessions)
    monkeypatch.setattr(onebot_v11.websockets, "connect", lambda *args, **kwargs: next(remaining))
    starts = []
    finishes = []
    active = []
    started = asyncio.Event()
    run_news = adapter._run_daily_news

    async def tracked_news() -> None:
        """Assert cleanup finishes before another connected scheduler can start."""
        assert not active
        active.append(asyncio.current_task())
        starts.append(True)
        started.set()
        try:
            await run_news()
        finally:
            finishes.append(True)
            active.clear()

    monkeypatch.setattr(adapter, "_run_daily_news", tracked_news)
    first = asyncio.create_task(adapter._run_connection())
    await asyncio.wait_for(sessions[0].request_sent.wait(), timeout=2)
    assert sessions[0].sent[0]["action"] == "send_private_msg"
    assert not store.was_private_sent("2026-09-27", "123")
    await sessions[0].incoming.put(None)
    with pytest.raises(OneBotError, match="closed"):
        await asyncio.wait_for(first, timeout=2)
    assert len(finishes) == 1 and not active and not adapter._pending

    second = asyncio.create_task(adapter._run_connection())
    await asyncio.wait_for(sessions[1].request_sent.wait(), timeout=2)
    request = sessions[1].sent[0]
    assert request["action"] == "send_private_msg"
    assert request["params"] == {
        "user_id": 123, "message": [
            {"type": "text", "data": {"text": "2026-09-27"}},
            {"type": "image", "data": {"file": "base64://news"}},
        ],
    }
    await sessions[1].incoming.put({"echo": request["echo"], "status": "ok", "retcode": 0})
    for _ in range(100):
        if store.was_private_sent("2026-09-27", "123"):
            break
        await asyncio.sleep(0.001)
    assert store.was_private_sent("2026-09-27", "123")
    await sessions[1].incoming.put(None)
    with pytest.raises(OneBotError, match="closed"):
        await asyncio.wait_for(second, timeout=2)
    assert len(finishes) == 2 and not active

    adapter._delivery_store = NewsDeliveryStore(str(tmp_path))
    started.clear()
    third = asyncio.create_task(adapter._run_connection())
    await asyncio.wait_for(started.wait(), timeout=2)
    await asyncio.sleep(0)
    await sessions[2].incoming.put(None)
    with pytest.raises(OneBotError, match="closed"):
        await asyncio.wait_for(third, timeout=2)
    assert not sessions[2].sent
    assert len(factory_calls) == 2
    assert len(starts) == len(finishes) == 3
    assert not active and not adapter._pending


def test_empty_news_targets_do_not_start_connection_scheduler(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Injected dependencies alone do not enable scheduled sending."""
    async def scenario() -> None:
        """Close an empty-target session after giving background tasks a chance to run."""
        adapter = _adapter()
        adapter._daily_news_factory = lambda: OutgoingMessage("news")
        adapter._delivery_store = NewsDeliveryStore(str(tmp_path))
        session = NewsSession()
        started = []

        async def news() -> None:
            """Detect an incorrectly enabled scheduler."""
            started.append(True)

        monkeypatch.setattr(adapter, "_run_daily_news", news)
        monkeypatch.setattr(onebot_v11.websockets, "connect", lambda *args, **kwargs: session)
        connection = asyncio.create_task(adapter._run_connection())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await session.incoming.put(None)
        with pytest.raises(OneBotError, match="closed"):
            await asyncio.wait_for(connection, timeout=2)
        assert not started and not session.sent

    asyncio.run(scenario())
