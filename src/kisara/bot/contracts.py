"""Protocol-neutral message and adapter contracts."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Protocol, Tuple, Union


class CommandInputError(ValueError):
    """A recognized command received invalid arguments."""


@dataclass(frozen=True)
class DispatchResult:
    """A routing outcome independent of the user-facing reply text."""

    status: str
    reply: Optional[str]
    reason: str = ""
    image_urls: Tuple[str, ...] = ()
    music_id: Optional[str] = None
    recall_message_id: Optional[str] = None


@dataclass(frozen=True)
class OutgoingMessage:
    """A protocol-neutral reply containing text and remote images."""

    text: str
    image_urls: Tuple[str, ...] = ()
    music_id: Optional[str] = None
    recall_message_id: Optional[str] = None


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


def is_image_segment(segment: MessageSegment) -> bool:
    """Recognize native images, stickers, and image files."""
    if segment.kind in {"image", "mface", "marketface"}:
        return True
    if segment.kind != "file":
        return False
    media_type = str(segment.data.get("mime_type") or segment.data.get("mime") or "")
    name = str(segment.data.get("file_name") or segment.data.get("name") or "")
    return media_type.lower().startswith("image/") or Path(name).suffix.lower() in {
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".apng",
    }


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


MessageHandler = Callable[[MessageEvent], Optional[Union[str, OutgoingMessage]]]


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

    async def send_reply(
        self, event: MessageEvent, content: Union[str, OutgoingMessage]
    ) -> None:
        """Send a reply using the source event's adapter-specific context."""
