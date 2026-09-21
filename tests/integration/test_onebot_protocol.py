"""Protocol-level tests for OneBot request handling without a live server."""

import asyncio
import json
from typing import Any, Dict, List

from kisara.bot.adapters.onebot_v11 import OneBotError, OneBotV11Adapter
from kisara.config import Settings


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
