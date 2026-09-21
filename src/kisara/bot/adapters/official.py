"""Adapter for Tencent's official botpy platform."""

from typing import Any, Optional

import botpy
from botpy import logging as bot_logging

from kisara.bot.contracts import MessageEvent, MessageHandler, MessageSegment
from kisara.config import Settings


_log = bot_logging.get_logger()


class OfficialAdapter(botpy.Client):
    """Translate botpy channel events into the shared message contract."""

    engine = "official"

    def __init__(self, settings: Settings, message_handler: MessageHandler) -> None:
        """Create an official-platform client for the selected instance."""

        intents = botpy.Intents(public_guild_messages=True)
        super().__init__(intents=intents, ext_handlers=False)
        self.instance_id = settings.instance_id
        self._app_id = settings.app_id or ""
        self._app_secret = settings.app_secret or ""
        self._message_handler = message_handler
        self._status = "stopped"

    def start(self) -> None:
        """Start the blocking botpy client."""

        self._status = "starting"
        try:
            super().run(appid=self._app_id, secret=self._app_secret)
        finally:
            self._status = "stopped"

    def close(self) -> None:
        """Leave shutdown to the blocking botpy run loop."""

        self._status = "stopped"

    @property
    def status(self) -> str:
        """Return the adapter lifecycle status."""

        return self._status

    async def on_ready(self) -> None:
        """Log the bot identity after the gateway connection is ready."""

        self._status = "connected"
        _log.info("Official bot is ready: %s", self.robot.name)

    async def on_at_message_create(self, message: Any) -> None:
        """Normalize a botpy mention event and send the shared response."""

        event = self._to_event(message)
        if event is None:
            return
        try:
            response = self._message_handler(event)
            if response is not None:
                await self.send_reply(event, response)
        except Exception:
            _log.exception("Official message handling failed")

    async def send_reply(self, event: MessageEvent, content: str) -> None:
        """Send text through the original botpy message context."""

        message = event.reply_context.get("message")
        if message is None:
            raise RuntimeError("Official reply context is missing the message")
        await message.reply(content=content)

    def _to_event(self, message: Any) -> Optional[MessageEvent]:
        """Convert the SDK message object without exposing it to application code."""

        author = getattr(message, "author", None)
        sender_id = _read_identifier(author, "id")
        channel_id = _read_identifier(message, "channel_id")
        guild_id = _read_identifier(message, "guild_id")
        conversation_id = channel_id or guild_id or sender_id
        self_id = _read_identifier(getattr(self, "robot", None), "id")
        if sender_id and self_id and sender_id == self_id:
            return None
        content = str(getattr(message, "content", "") or "")
        segments = (
            (MessageSegment(kind="text", data={"text": content}),)
            if content
            else ()
        )

        return MessageEvent(
            engine=self.engine,
            instance_id=self.instance_id,
            message_id=_read_identifier(message, "id"),
            conversation_kind="channel",
            conversation_id=conversation_id,
            sender_id=sender_id,
            segments=segments,
            reply_context={
                "message": message,
                "self_id": self_id,
                "channel_id": channel_id,
                "guild_id": guild_id,
            },
        )


def _read_identifier(value: Optional[Any], name: str) -> str:
    """Read an SDK identifier as a string without assuming its numeric type."""

    if value is None:
        return ""
    identifier = getattr(value, name, "")
    if identifier is None:
        return ""
    return str(identifier)
