"""OneBot 11 forward-WebSocket adapter."""

import asyncio
import json
import logging
import random
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Set, Tuple, Union

import websockets
from websockets.exceptions import ConnectionClosed

from kisara.bot.contracts import (
    MessageEvent, MessageHandler, MessageSegment, OutgoingMessage,
)
from kisara.application.services.export_img import handle_export_img
from kisara.application.services.setu import Setu
from kisara.config import Settings
from kisara.infrastructure.persistence.news_delivery import NewsDeliveryStore


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
        daily_news_factory: Optional[Callable[[], OutgoingMessage]] = None,
        delivery_store: Optional[NewsDeliveryStore] = None,
        setu: Optional[Setu] = None,
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
        self._daily_news_factory = daily_news_factory
        self._delivery_store = delivery_store
        self._news_push_groups = tuple(sorted(settings.news_push_groups))
        self._news_push_users = tuple(sorted(settings.news_push_users))
        self._news_push_hour = settings.news_push_hour
        self._news_push_minute = settings.news_push_minute
        self._allowed_users = settings.allowed_users
        self._allowed_groups = settings.allowed_groups
        self._groups_enabled = settings.groups_enabled
        self._setu = setu

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
            news_task = None
            setu_task = None
            if (self._daily_news_factory and self._delivery_store and
                    (self._news_push_groups or self._news_push_users)):
                news_task = asyncio.create_task(self._run_daily_news())
            if self._setu is not None:
                setu_task = asyncio.create_task(self._setu.run(self))
            try:
                async for raw_packet in websocket:
                    packet = self._decode_packet(raw_packet)
                    if packet is not None:
                        self._handle_packet(packet)
            finally:
                if news_task is not None:
                    news_task.cancel()
                    await asyncio.gather(news_task, return_exceptions=True)
                if setu_task is not None:
                    setu_task.cancel()
                    await asyncio.gather(setu_task, return_exceptions=True)
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
            if self._is_authorized(event) and await handle_export_img(event, self):
                return
            if self._setu is not None:
                if (self._is_authorized(event) and
                        event.conversation_kind == "private" and
                        event.reply_context.get("quoted_message_id") and
                        self._setu.is_start_word(event.text)):
                    quoted, _ = await self.quoted_message(event)
                    forwards = tuple(segment for segment in quoted if segment.kind == "forward")
                    if forwards:
                        context = dict(event.reply_context)
                        context["setu_source_id"] = context["quoted_message_id"]
                        event = replace(event, segments=event.segments + forwards,
                                        reply_context=context)
                if await self._setu.handle(event, self):
                    return
            if event.reply_context.get("quoted_message_id") and not event.text.strip():
                return
            if self._should_enrich_quote(event):
                event = await self._enrich_quoted_message(event)
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, self._message_handler, event)
            if isinstance(response, OutgoingMessage) and response.recall_message_id:
                try:
                    await self._request("delete_msg", {
                        "message_id": _as_api_identifier(response.recall_message_id),
                    })
                except OneBotError:
                    _log.exception("Could not recall quoted bot message")
                    await self.send_reply(event, "Could not recall that bot message.")
                    return
                if response.text or response.image_urls or response.music_id:
                    await self.send_reply(event, response)
            elif response is not None:
                await self.send_reply(event, response)
        except Exception:
            _log.exception("OneBot message handling failed")

    def _should_enrich_quote(self, event: MessageEvent) -> bool:
        """Limit history lookups to authorized image search and recall commands."""

        if not self._is_authorized(event):
            return False
        if not event.reply_context.get("quoted_message_id"):
            return False
        parts = event.text.strip().split(maxsplit=1)
        if not parts:
            return False
        command = parts[0].lower().lstrip("/")
        if command in {"source", "sauce"}:
            return not any(segment.kind == "image" for segment in event.segments)
        return command == "recall"

    def _is_authorized(self, event: MessageEvent) -> bool:
        """Apply the same sender and conversation allowlists as normal routing."""
        if event.sender_id not in self._allowed_users:
            return False
        if event.conversation_kind == "group":
            return self._groups_enabled and event.conversation_id in self._allowed_groups
        return event.conversation_kind == "private"

    async def quoted_message(
        self, event: MessageEvent,
    ) -> Tuple[Tuple[MessageSegment, ...], str]:
        """Retrieve a quoted message only from the current conversation."""
        quoted_id = str(event.reply_context.get("quoted_message_id") or "")
        if not quoted_id:
            return (), ""
        try:
            response = await self._request("get_msg", {
                "message_id": _as_api_identifier(quoted_id),
            })
        except OneBotError:
            _log.warning("Quoted message %s could not be retrieved", quoted_id)
            return (), ""
        data = response.get("data")
        if not isinstance(data, dict) or data.get("message_type") not in {
            None, event.conversation_kind,
        }:
            return (), ""
        group_id = _as_identifier(data.get("group_id"))
        if event.conversation_kind == "group" and group_id != event.conversation_id:
            return (), ""
        sender = data.get("sender")
        quoted_sender = _as_identifier(data.get("user_id"))
        if not quoted_sender and isinstance(sender, dict):
            quoted_sender = _as_identifier(sender.get("user_id"))
        if event.conversation_kind == "private":
            target_id = _as_identifier(data.get("target_id"))
            participants = {quoted_sender, target_id} - {""}
            if not participants or not participants.issubset({
                event.sender_id, str(event.reply_context.get("self_id") or ""),
            }):
                return (), ""
        return _read_segments(data.get("message")), quoted_sender

    async def _enrich_quoted_message(self, event: MessageEvent) -> MessageEvent:
        """Fetch a quoted message for image search or ownership validation."""

        quoted_segments, quoted_sender = await self.quoted_message(event)
        if not quoted_segments and not quoted_sender:
            return event
        context = dict(event.reply_context)
        context["quoted_sender_id"] = quoted_sender
        segments = event.segments
        if not any(segment.kind == "image" for segment in segments):
            segments += tuple(segment for segment in quoted_segments
                              if segment.kind == "image")
        return replace(event, reply_context=context, segments=segments)

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
        segments = _read_segments(packet.get("message"))
        quoted_id = next(
            (_as_identifier(segment.data.get("id")) for segment in segments
             if segment.kind == "reply"),
            "",
        )
        return MessageEvent(
            engine=self.engine,
            instance_id=self.instance_id,
            message_id=_as_identifier(packet.get("message_id")),
            conversation_kind=message_type,
            conversation_id=conversation_id,
            sender_id=sender_id,
            segments=segments,
            reply_context={
                "self_id": self_id,
                "user_id": sender_id,
                "group_id": group_id,
                "sender_role": str(sender.get("role", "")) if isinstance(sender, dict) else "",
                "quoted_message_id": quoted_id,
            },
        )

    async def send_reply(
        self, event: MessageEvent, content: Union[str, OutgoingMessage],
    ) -> None:
        """Send text or image segments and require a successful API response."""

        await self._send_message(event, self._encode_message(content))

    async def _send_message(self, event: MessageEvent, message: Any) -> None:
        """Route one prepared OneBot message to the source conversation."""
        if event.conversation_kind == "private":
            action = "send_private_msg"
            params = {
                "user_id": _as_api_identifier(event.sender_id),
                "message": message,
            }
        else:
            action = "send_group_msg"
            params = {
                "group_id": _as_api_identifier(event.conversation_id),
                "message": message,
            }
        await self._request(action, params)

    async def send_exported_files(
        self, event: MessageEvent, files: Sequence[Tuple[str, str]],
    ) -> None:
        """Send each quoted picture as a saveable OneBot file attachment."""
        for location, name in files:
            await self._send_message(event, [{
                "type": "file", "data": {"file": location, "name": name},
            }])

    async def fetch_forward(self, identifier: str) -> Tuple[Mapping[str, Any], ...]:
        """Fetch nested forward nodes through the OneBot API."""
        if not identifier:
            raise OneBotError("Forward message has no identifier")
        response = await self._request("get_forward_msg", {"message_id": identifier, "id": identifier})
        data = response.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
            raise OneBotError("Forward message response has no nodes")
        return tuple(node for node in data["messages"] if isinstance(node, dict))

    async def send_private(self, user_id: str, text: str, quote_id: str = "") -> str:
        """Send a private text message, optionally quoting the first source message."""
        message = []
        if quote_id:
            message.append({"type": "reply", "data": {"id": quote_id}})
        message.append({"type": "text", "data": {"text": text}})
        response = await self._request("send_private_msg", {
            "user_id": _as_api_identifier(user_id), "message": message,
        })
        data = response.get("data")
        return _as_identifier(data.get("message_id")) if isinstance(data, dict) else ""

    async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
        """Resolve an attachment to a URL or a mounted NapCat cache path."""
        current = str(media.get("url") or "")
        if current and not refresh:
            return current
        file_id = str(media.get("file") or "")
        if not file_id:
            return current
        action = {
            "image": "get_image", "record": "get_record",
        }.get(str(media.get("kind") or ""), "get_file")
        params = {"file": file_id}
        if action == "get_file":
            params["file_id"] = file_id
        try:
            response = await self._request(action, params)
        except OneBotError:
            if current:
                return current
            raise
        data = response.get("data")
        if isinstance(data, dict):
            resolved = str(data.get("url") or data.get("file") or "")
            if resolved:
                return resolved
        return current

    @staticmethod
    def _encode_message(content: Union[str, OutgoingMessage]) -> Any:
        """Render a shared reply into OneBot text and media segments."""

        if isinstance(content, str):
            return content
        segments = []
        if content.text:
            segments.append({"type": "text", "data": {"text": content.text}})
        for image_url in content.image_urls:
            segments.append({"type": "image", "data": {"file": image_url}})
        if content.music_id:
            segments.append({
                "type": "music", "data": {"type": "163", "id": content.music_id},
            })
        return segments

    async def _run_daily_news(self) -> None:
        """Push each day's brief to pending groups and users after its due time."""

        factory = self._daily_news_factory
        store = self._delivery_store
        if factory is None or store is None:
            return
        zone = timezone(timedelta(hours=8))
        while not self._stop_requested:
            now = datetime.now(zone)
            due = now.replace(
                hour=self._news_push_hour, minute=self._news_push_minute,
                second=0, microsecond=0,
            )
            if now < due:
                await asyncio.sleep((due - now).total_seconds())
                continue
            day = now.date().isoformat()
            pending = list(self._news_push_groups)
            pending_users = list(self._news_push_users)
            try:
                pending = [group for group in self._news_push_groups
                           if not store.was_sent(day, group)]
                pending_users = [user for user in self._news_push_users
                                 if not store.was_private_sent(day, user)]
                if pending or pending_users:
                    loop = asyncio.get_running_loop()
                    content = await loop.run_in_executor(None, factory)
                    for group in pending:
                        try:
                            await self._request("send_group_msg", {
                                "group_id": _as_api_identifier(group),
                                "message": self._encode_message(content),
                            })
                            store.mark_sent(day, group)
                        except Exception:
                            _log.exception("Daily brief send failed for group %s", group)
                    for user in pending_users:
                        try:
                            await self._request("send_private_msg", {
                                "user_id": _as_api_identifier(user),
                                "message": self._encode_message(content),
                            })
                            store.mark_private_sent(day, user)
                        except Exception:
                            _log.exception("Daily brief private send failed")
            except Exception:
                _log.exception("Daily brief is unavailable; retrying later")
            await asyncio.sleep(900 if pending or pending_users else max(
                1.0, (due + timedelta(days=1) - datetime.now(zone)).total_seconds()
            ))

    async def _request(
        self, action: str, params: Mapping[str, Any]
    ) -> Mapping[str, Any]:
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
            return response
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
