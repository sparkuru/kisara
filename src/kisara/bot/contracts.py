"""Protocol-neutral message and adapter contracts."""

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Protocol, Tuple


@dataclass(frozen=True)
class MessageSegment:
    """A structured segment from an incoming platform message."""

    kind: str
    data: Mapping[str, Any]

    @property
    def text(self) -> str:
        """Return the text carried by this segment, if any."""

        if self.kind != "text":
            return ""
        return str(self.data.get("text", ""))


@dataclass(frozen=True)
class MessageEvent:
    """A normalized incoming message shared by all protocol adapters."""

    engine: str
    instance_id: str
    message_id: str
    conversation_kind: str
    conversation_id: str
    sender_id: str
    segments: Tuple[MessageSegment, ...]
    reply_context: Mapping[str, Any]

    @property
    def text(self) -> str:
        """Return the concatenated text segments in the message."""

        return "".join(segment.text for segment in self.segments)


MessageHandler = Callable[[MessageEvent], Optional[str]]


class MessageAdapter(Protocol):
    """Lifecycle contract implemented by a selected protocol adapter."""

    engine: str
    instance_id: str

    @property
    def status(self) -> str:
        """Return the adapter lifecycle status without exposing protocol state."""

    def start(self) -> None:
        """Start receiving messages until the adapter stops."""

    def close(self) -> None:
        """Release adapter resources."""

    async def send_reply(self, event: MessageEvent, content: str) -> None:
        """Send a reply using the source event's adapter-specific context."""
