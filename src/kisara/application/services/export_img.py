"""Export quoted OneBot images or stickers as saveable file attachments.

An allowed user quotes an image or sticker and sends /export-img or a supported
legacy export phrase. Each original is sent as a file attachment, preserving
bytes and animation; QQ may otherwise classify a resent image as a sticker.
This flow does not enter the merged-forward setu archive and works even when
setu is disabled. It stores no application files or database records.
"""

from pathlib import PurePosixPath
from typing import Any, Mapping, Protocol, Sequence, Tuple
from urllib.parse import urlsplit

from kisara.bot.contracts import MessageEvent, MessageSegment, is_image_segment


class ExportImgGateway(Protocol):
    """Provide the quoted-message and media operations needed by export."""

    async def quoted_message(
        self, event: MessageEvent,
    ) -> Tuple[Tuple[MessageSegment, ...], str]:
        """Return a quoted message only when it belongs to this conversation."""

    async def media_location(self, media: Mapping[str, Any], refresh: bool = False) -> str:
        """Resolve one image to a location NapCat can read."""

    async def send_reply(self, event: MessageEvent, content: str) -> None:
        """Send a status or error message."""

    async def send_exported_files(
        self, event: MessageEvent, files: Sequence[Tuple[str, str]],
    ) -> None:
        """Send each original picture as a file attachment."""


def is_export_intent(event: MessageEvent) -> bool:
    """Recognize an explicit request to export a quoted image."""
    text = event.text.strip().casefold()
    return text in {"/export-img", "export-img"} or any(
        phrase in text for phrase in ("导出", "转图片", "转成图片", "转为图片", "转图", "原图")
    )


async def handle_export_img(event: MessageEvent, gateway: ExportImgGateway) -> bool:
    """Export only images from the quoted message when the command matches."""
    if not is_export_intent(event):
        return False
    if not event.reply_context.get("quoted_message_id"):
        await gateway.send_reply(event, "请引用要导出的图片或表情包。")
        return True

    quoted, _ = await gateway.quoted_message(event)
    images = tuple(segment for segment in quoted if is_image_segment(segment))
    if not images:
        await gateway.send_reply(event, "引用的消息中没有图片。")
        return True

    files = []
    for index, segment in enumerate(images, start=1):
        location = str(segment.data.get("url") or "")
        if not location:
            try:
                location = await gateway.media_location({"kind": segment.kind, **segment.data})
            except RuntimeError:
                location = ""
        if location:
            files.append((location, _export_name(segment, location, index)))

    if files:
        await gateway.send_exported_files(event, files)
    else:
        await gateway.send_reply(event, "无法读取引用的图片。")
    return True


def _export_name(segment: MessageSegment, location: str, index: int) -> str:
    """Use the source image extension without exposing an opaque QQ file ID."""
    for value in (
        segment.data.get("file_name"), segment.data.get("name"),
        segment.data.get("file"), urlsplit(location).path,
    ):
        name = PurePosixPath(str(value or "").replace("\\", "/")).name
        suffix = PurePosixPath(name).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".apng"}:
            return "export-{}{}".format(index, suffix)
    return "export-{}.bin".format(index)
