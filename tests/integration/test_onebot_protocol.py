"""Protocol-level tests for OneBot request handling without a live server."""

import asyncio
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List

from kisara.application.services.setu import Setu
from kisara.bot.adapters.onebot_v11 import OneBotError, OneBotV11Adapter
from kisara.bot.contracts import MessageEvent, MessageSegment, OutgoingMessage
from kisara.config import Settings
from kisara.config.setu import SetuConfig
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
    websocket: FakeWebSocket, count: int
) -> None:
    """Wait until the adapter has emitted the expected request count."""

    for _ in range(100):
        if len(websocket.sent) >= count:
            return
        await asyncio.sleep(0)
    raise AssertionError("adapter did not emit the expected requests")


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


def test_quoted_setu_prompts_once_for_source_forward(tmp_path: Path) -> None:
    """A quoted forward prompts immediately and repeated quotes do not duplicate it."""
    asyncio.run(_test_quoted_setu_prompts_once_for_source_forward(tmp_path))


async def _test_quoted_setu_prompts_once_for_source_forward(tmp_path: Path) -> None:
    """Resolve the quoted forward and inspect the resulting archive prompt."""
    adapter = _adapter()
    adapter._allowed_users = frozenset({"123"})
    config = replace(SetuConfig.disabled(), enabled=True,
                     allowed_users=frozenset({"123"}))
    adapter._setu = Setu(config, str(tmp_path))
    websocket = FakeWebSocket()
    adapter._websocket = websocket
    task = asyncio.create_task(adapter._process_event(_quoted_event("/setu")))
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
    assert "1 张图片" in prompt["params"]["message"][1]["data"]["text"]
    adapter._resolve_pending({
        "echo": prompt["echo"], "status": "ok", "retcode": 0,
        "data": {"message_id": 500},
    })
    await task
    batches = SetuStore(str(tmp_path)).awaiting("test", "123", time.time())
    assert len(batches) == 1
    assert batches[0]["first_message_id"] == "42"
    repeat = replace(_quoted_event("/setu"), message_id="101")
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
