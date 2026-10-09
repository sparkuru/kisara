"""Tests for OneBot 11 event normalization."""

import asyncio
import base64
import io
from typing import Any, Dict, Mapping, Optional

import pytest

from kisara.bot.adapters.onebot_v11 import (
    OneBotError, OneBotV11Adapter, _FileDownload, _file_request_timeout,
)
from kisara.config import Settings


def _adapter() -> OneBotV11Adapter:
    """Build an adapter without opening a network connection."""

    settings = Settings(
        engine="onebot",
        instance_id="personal",
        allowed_users=frozenset(),
        groups_enabled=False,
        allowed_groups=frozenset(),
        onebot_ws_url="ws://napcat:3001",
        onebot_access_token="test-token",
    )
    return OneBotV11Adapter(settings, lambda event: None)


def test_onebot_private_event_preserves_string_identifiers() -> None:
    """Private events should expose protocol identifiers as strings."""

    event = _adapter()._to_event(
        {
            "post_type": "message",
            "message_type": "private",
            "self_id": 999,
            "user_id": 123,
            "message_id": 456,
            "message": [{"type": "text", "data": {"text": "/ping"}}],
        }
    )

    assert event is not None
    assert event.sender_id == "123"
    assert event.conversation_id == "123"
    assert event.message_id == "456"
    assert event.text == "/ping"


def test_onebot_group_event_keeps_mentions_as_segments() -> None:
    """Group conversion should preserve structured mention information."""

    event = _adapter()._to_event(
        {
            "post_type": "message",
            "message_type": "group",
            "self_id": 999,
            "user_id": 123,
            "group_id": 456,
            "message_id": 789,
            "message": [
                {"type": "at", "data": {"qq": "999"}},
                {"type": "text", "data": {"text": " hello"}},
            ],
        }
    )

    assert event is not None
    assert event.conversation_kind == "group"
    assert event.conversation_id == "456"
    assert event.segments[0].kind == "at"
    assert event.text == " hello"


def test_onebot_self_event_is_ignored() -> None:
    """The adapter must not feed its own messages into shared routing."""

    event = _adapter()._to_event(
        {
            "post_type": "message",
            "message_type": "private",
            "self_id": 999,
            "user_id": 999,
            "message_id": 1,
            "message": "loop",
        }
    )

    assert event is None


@pytest.mark.parametrize("size,expected", [
    (None, 125.0), ("", 125.0), ("invalid", 125.0), ("-1", 125.0),
    ("1024", 125.0), ("109092709", 10.0 + 109092709 / (256 * 1024) + 5.0),
    (str(2 * 1024 ** 3), 1805.0), ("9" * 1000, 1805.0),
])
def test_file_resolution_wait_covers_native_bounds(size: Any, expected: float) -> None:
    """Size-based transfer waits stay within observed NapCat limits plus margin."""
    assert _file_request_timeout(size) == expected


@pytest.mark.parametrize("kind", ["file", "image", "video", "record"])
def test_only_file_kind_resolution_has_a_transfer_deadline(kind: str) -> None:
    """File get_file has a dedicated deadline; other media use the chat default."""
    async def scenario() -> None:
        """Capture resolver calls without opening a protocol connection."""
        adapter = _adapter()
        requests: list = []

        async def request(action: str, params: Mapping[str, Any],
                          timeout_seconds: Optional[float] = None) -> Dict[str, Any]:
            """Return a local location while observing the explicit response deadline."""
            requests.append((action, dict(params), timeout_seconds))
            return {"data": {"file": "/approved/cache/path"}}

        adapter._request = request
        assert await adapter.media_location({"kind": kind, "file": "canonical-id", "size": "109092709"}) == "/approved/cache/path"
        action, params, timeout = requests[0]
        assert action == {"image": "get_image", "record": "get_record"}.get(kind, "get_file")
        assert params["file"] == "canonical-id"
        assert timeout == (_file_request_timeout("109092709") if kind == "file" else None)

    asyncio.run(scenario())


@pytest.mark.parametrize("bad_data", [
    None,
    {"type": "stream", "data_type": "file_info", "file_size": 0},
    {"type": "stream", "data_type": "file_info", "file_size": 5},
    {"type": "stream", "data_type": "file_info", "file_size": "4"},
    {"type": "stream", "data_type": "file_chunk", "index": 0, "data": "YQ==", "size": 1},
    {"type": "response", "data_type": "file_complete", "total_chunks": 0, "total_bytes": 0},
])
def test_native_file_stream_rejects_invalid_initial_metadata(bad_data: Any) -> None:
    """Do not write chunks before a positive bounded size was received."""
    output = io.BytesIO()
    stream = _FileDownload(output, 4)
    with pytest.raises(OneBotError):
        stream.consume({"status": "ok", "retcode": 0, "data": bad_data})
    assert output.getvalue() == b""


@pytest.mark.parametrize("bad_data", [
    {"type": "stream", "data_type": "file_info", "file_size": 4},
    {"type": "stream", "data_type": "file_chunk", "index": 1, "data": "YQ==", "size": 1},
    {"type": "stream", "data_type": "file_chunk", "index": True, "data": "YQ==", "size": 1},
    {"type": "stream", "data_type": "file_chunk", "index": 0, "data": "!", "size": 1},
    {"type": "stream", "data_type": "file_chunk", "index": 0, "data": "YQ==", "size": 2},
    {"type": "stream", "data_type": "file_chunk", "index": 0, "data": "YWJjZGU=", "size": 5},
    {"type": "stream", "data_type": "file_chunk", "index": 0, "data": "a" * 87385, "size": 1},
    {"type": "response", "data_type": "file_complete", "total_chunks": 0, "total_bytes": 4},
    {"type": "response", "data_type": "file_complete", "total_chunks": True, "total_bytes": 0},
    {"type": "reset", "data_type": "file_complete", "total_chunks": 0, "total_bytes": 0},
])
def test_native_file_stream_rejects_invalid_chunks_and_completion(bad_data: Any) -> None:
    """Enforce order, encoding, chunk caps and complete actual byte counts."""
    output = io.BytesIO()
    stream = _FileDownload(output, 4)
    assert not stream.consume({"data": {
        "type": "stream", "data_type": "file_info", "file_size": 4,
    }})
    with pytest.raises(OneBotError):
        stream.consume({"status": "ok", "retcode": 0, "data": bad_data})
    assert output.getvalue() == b""
    assert not stream.complete


def test_native_file_stream_preserves_chunked_bytes_and_requires_exact_completion() -> None:
    """Two ordered chunks only complete at their declared final size."""
    output = io.BytesIO()
    stream = _FileDownload(output, 10)
    assert not stream.consume({"data": {
        "type": "stream", "data_type": "file_info", "file_size": 4,
    }})
    for index, chunk in enumerate((b"a\x00", b"\xffb")):
        assert not stream.consume({"data": {
            "type": "stream", "data_type": "file_chunk", "index": index,
            "data": base64.b64encode(chunk).decode("ascii"), "size": len(chunk),
        }})
    assert output.getvalue() == b"a\x00\xffb"
    with pytest.raises(OneBotError):
        stream.consume({"data": {"type": "response", "data_type": "file_complete",
                                "total_chunks": 1, "total_bytes": 4}})
    assert stream.consume({"data": {"type": "response", "data_type": "file_complete",
                                  "total_chunks": 2, "total_bytes": 4}})
    assert stream.complete
