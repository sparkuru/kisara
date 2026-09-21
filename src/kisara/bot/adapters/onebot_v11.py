"""OneBot 11 forward-WebSocket adapter."""

import asyncio
import json
import logging
import random
import uuid
from typing import Any, Dict, Mapping, Optional, Set, Tuple

import websockets
from websockets.exceptions import ConnectionClosed

from kisara.bot.contracts import MessageEvent, MessageHandler, MessageSegment
from kisara.config import Settings


_log = logging.getLogger("kisara.onebot")
MAX_PENDING_MESSAGE_TASKS = 256
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0


class OneBotError(RuntimeError):
    """Raised when a OneBot connection or API request cannot complete."""


class OneBotV11Adapter:
    """Receive OneBot 11 events and send replies through API echo requests."""

    engine = "onebot"

    def __init__(
        self,
        settings: Settings,
        message_handler: MessageHandler,
        request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        """Create a forward-WebSocket adapter for the selected OneBot instance."""

        self.instance_id = settings.instance_id
        self._ws_url = settings.onebot_ws_url or ""
        self._access_token = settings.onebot_access_token or ""
        self._message_handler = message_handler
        self._request_timeout_seconds = request_timeout_seconds
        self._status = "stopped"
        self._stop_requested = False
        self._websocket: Any = None
        self._pending: Dict[str, asyncio.Future] = {}
        self._message_tasks: Set[asyncio.Task] = set()
        self._conversation_tasks: Dict[str, asyncio.Task] = {}

    def start(self) -> None:
        """Run the reconnecting adapter loop until interrupted or closed."""

        self._stop_requested = False
        self._status = "starting"
        try:
            asyncio.run(self._run())
        finally:
            self._status = "stopped"

    def close(self) -> None:
        """Request that the current connection loop stop after its next await."""

        self._stop_requested = True
        self._status = "stopped"

    @property
    def status(self) -> str:
        """Return the adapter lifecycle status."""

        return self._status

    async def _run(self) -> None:
        """Connect to OneBot and apply bounded exponential reconnect delays."""

        reconnect_delay = 1.0
        while not self._stop_requested:
            try:
                await self._run_connection()
                reconnect_delay = 1.0
            except (ConnectionClosed, OSError, OneBotError, ValueError) as error:
                if self._stop_requested:
                    break
                self._status = "disconnected"
                delay = min(reconnect_delay, 30.0) + random.uniform(0.0, 0.5)
                _log.warning(
                    "OneBot connection unavailable; retrying in %.1fs (%s)",
                    delay,
                    type(error).__name__,
                )
                await asyncio.sleep(delay)
                reconnect_delay = min(reconnect_delay * 2.0, 30.0)

    async def _run_connection(self) -> None:
        """Run one WebSocket session and dispatch events in background tasks."""

        headers = {"Authorization": "Bearer {}".format(self._access_token)}
        async with websockets.connect(
            self._ws_url,
            extra_headers=headers,
            ping_interval=20,
            ping_timeout=20,
            open_timeout=10,
            close_timeout=5,
        ) as websocket:
            self._websocket = websocket
            self._status = "connected"
            _log.info("OneBot WebSocket connected")
            try:
                async for raw_packet in websocket:
                    packet = self._decode_packet(raw_packet)
                    if packet is not None:
                        self._handle_packet(packet)
            finally:
                self._websocket = None
                if not self._stop_requested:
                    self._status = "disconnected"
                await self._cancel_message_tasks()
                self._fail_pending(OneBotError("OneBot connection closed"))
        if not self._stop_requested:
            raise OneBotError("OneBot WebSocket closed")

    def _handle_packet(self, packet: Mapping[str, Any]) -> None:
        """Route API responses and schedule incoming message processing."""

        if "echo" in packet:
            self._resolve_pending(packet)
            return
        if packet.get("post_type") != "message":
            return

        event = self._to_event(packet)
        if event is None:
            return
        if len(self._message_tasks) >= MAX_PENDING_MESSAGE_TASKS:
            _log.warning("Dropping OneBot message because the queue is full")
            return
        conversation_key = self._conversation_key(event)
        previous_task = self._conversation_tasks.get(conversation_key)
        task = asyncio.create_task(
            self._process_ordered_event(event, previous_task)
        )
        self._message_tasks.add(task)
        self._conversation_tasks[conversation_key] = task
        task.add_done_callback(self._message_tasks.discard)
        task.add_done_callback(
            lambda completed_task: self._discard_conversation_task(
                conversation_key, completed_task
            )
        )

    async def _process_ordered_event(
        self,
        event: MessageEvent,
        previous_task: Optional[asyncio.Task],
    ) -> None:
        """Wait for the prior event in a conversation before handling this one."""

        if previous_task is not None:
            await previous_task
        await self._process_event(event)

    def _conversation_key(self, event: MessageEvent) -> str:
        """Build the ordered-processing key required by the message contract."""

        return "\0".join(
            (
                event.engine,
                event.instance_id,
                event.conversation_kind,
                event.conversation_id,
            )
        )

    def _discard_conversation_task(
        self,
        conversation_key: str,
        completed_task: asyncio.Task,
    ) -> None:
        """Remove a conversation chain only if it still points to this task."""

        if self._conversation_tasks.get(conversation_key) is completed_task:
            self._conversation_tasks.pop(conversation_key, None)

    async def _process_event(self, event: MessageEvent) -> None:
        """Run shared routing and reply through the source conversation."""

        try:
            response = self._message_handler(event)
            if response is not None:
                await self.send_reply(event, response)
        except Exception:
            _log.exception("OneBot message handling failed")

    def _to_event(self, packet: Mapping[str, Any]) -> Optional[MessageEvent]:
        """Convert a OneBot message event into the shared message contract."""

        message_type = str(packet.get("message_type", ""))
        if message_type not in {"private", "group"}:
            return None

        sender = packet.get("sender") or {}
        sender_id = _as_identifier(packet.get("user_id"))
        if not sender_id:
            sender_id = _as_identifier(sender.get("user_id"))
        self_id = _as_identifier(packet.get("self_id"))
        if sender_id and sender_id == self_id:
            return None

        group_id = _as_identifier(packet.get("group_id"))
        conversation_id = group_id if message_type == "group" else sender_id
        return MessageEvent(
            engine=self.engine,
            instance_id=self.instance_id,
            message_id=_as_identifier(packet.get("message_id")),
            conversation_kind=message_type,
            conversation_id=conversation_id,
            sender_id=sender_id,
            segments=_read_segments(packet.get("message")),
            reply_context={
                "self_id": self_id,
                "user_id": sender_id,
                "group_id": group_id,
            },
        )

    async def send_reply(self, event: MessageEvent, content: str) -> None:
        """Send a text reply and require a successful OneBot API response."""

        if event.conversation_kind == "private":
            action = "send_private_msg"
            params = {
                "user_id": _as_api_identifier(event.sender_id),
                "message": content,
            }
        else:
            action = "send_group_msg"
            params = {
                "group_id": _as_api_identifier(event.conversation_id),
                "message": content,
            }
        await self._request(action, params)

    async def _request(self, action: str, params: Mapping[str, Any]) -> None:
        """Send a OneBot API request and wait for its correlated response."""

        websocket = self._websocket
        if websocket is None:
            raise OneBotError("OneBot WebSocket is not connected")

        echo = uuid.uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self._pending[echo] = future
        request = {
            "action": action,
            "params": dict(params),
            "echo": echo,
        }
        try:
            await websocket.send(json.dumps(request, ensure_ascii=False))
            response = await asyncio.wait_for(
                future, timeout=self._request_timeout_seconds
            )
            status = str(response.get("status", "ok"))
            retcode = int(response.get("retcode", 0) or 0)
            if status == "failed" or retcode != 0:
                raise OneBotError(
                    "OneBot API request failed: {} (retcode={})".format(
                        action, retcode
                    )
                )
        except asyncio.TimeoutError as error:
            raise OneBotError(
                "OneBot API request timed out: {}".format(action)
            ) from error
        finally:
            self._pending.pop(echo, None)

    def _resolve_pending(self, packet: Mapping[str, Any]) -> None:
        """Resolve the request future identified by a protocol echo value."""

        echo = str(packet.get("echo", ""))
        future = self._pending.get(echo)
        if future is None or future.done():
            return
        future.set_result(packet)

    def _fail_pending(self, error: OneBotError) -> None:
        """Fail all requests waiting on a connection that has gone away."""

        pending = tuple(self._pending.values())
        self._pending.clear()
        for future in pending:
            if not future.done():
                future.set_exception(error)

    async def _cancel_message_tasks(self) -> None:
        """Cancel event handlers before the connection context is closed."""

        tasks = tuple(self._message_tasks)
        self._message_tasks.clear()
        self._conversation_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _decode_packet(raw_packet: Any) -> Optional[Mapping[str, Any]]:
        """Decode a text or byte WebSocket payload into a JSON mapping."""

        if isinstance(raw_packet, bytes):
            raw_packet = raw_packet.decode("utf-8")
        try:
            packet = json.loads(raw_packet)
        except (TypeError, ValueError):
            _log.warning("Ignoring invalid OneBot JSON packet")
            return None
        if not isinstance(packet, dict):
            _log.warning("Ignoring non-object OneBot packet")
            return None
        return packet


def _read_segments(raw_segments: Any) -> Tuple[MessageSegment, ...]:
    """Normalize OneBot message segments while preserving non-text data."""

    if isinstance(raw_segments, str):
        return (MessageSegment(kind="text", data={"text": raw_segments}),)
    if not isinstance(raw_segments, list):
        return ()

    segments = []
    for raw_segment in raw_segments:
        if not isinstance(raw_segment, dict):
            continue
        kind = str(raw_segment.get("type", ""))
        data = raw_segment.get("data") or {}
        if kind and isinstance(data, dict):
            segments.append(MessageSegment(kind=kind, data=dict(data)))
    return tuple(segments)


def _as_identifier(value: Any) -> str:
    """Convert a platform identifier to its string namespace representation."""

    if value is None:
        return ""
    return str(value)


def _as_api_identifier(value: str) -> Any:
    """Use numeric identifiers on the wire while keeping strings internally."""

    if value.isdigit():
        return int(value)
    return value
