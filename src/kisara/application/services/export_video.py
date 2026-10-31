"""Export a quoted Bilibili share as a native OneBot video.

Allowed OneBot users quote a mini-program card or video URL and send 导出 or
/export-video. Images retain /export-img and their original-file behavior.
The adapter checks global/group permission and quote ownership before invoking
provider work. Public command exceptions never authorize this native workflow.
An optional deployment SESSDATA selects session-accessible formats; without it
the provider selects the highest anonymously available quality. Downloads use
one bounded worker and temporary shared transport files, not a video archive.
Unknown native sends retain their files for a grace period and never auto-retry.
"""

import asyncio
import time
from collections import OrderedDict
from typing import Optional, Protocol, Sequence

from kisara.application.services.export_img import ExportImgGateway, handle_export_img
from kisara.bot.contracts import MessageEvent, is_image_segment
from kisara.config.export import ExportConfig
from kisara.infrastructure.integrations.bilibili import (
    VideoExportError, VideoSendError, candidate_urls, resolve_video_url, supported_url,
)
from kisara.infrastructure.integrations.video_download import BilibiliDownloader, DownloadedVideo


class VideoExportGateway(ExportImgGateway, Protocol):
    """Keep native delivery and protocol normalization in the source adapter."""

    async def send_exported_video(self, event: MessageEvent, video: DownloadedVideo) -> None:
        """Require a confirmed native receipt, or report outcome certainty."""


def is_video_export_intent(event: MessageEvent) -> bool:
    """Recognize explicit video commands and generic export requests."""
    text = event.text.strip().casefold()
    return ((text.split(maxsplit=1) or [""])[0] in {"/export", "export", "/export-video", "export-video"}
            or any(word in text for word in ("导出", "转视频", "转成视频", "转为视频")))


def _image_only(event: MessageEvent) -> bool:
    """Preserve explicit original-image wording even when a quote has links."""
    text = event.text.strip().casefold()
    return text in {"/export-img", "export-img"} or any(
        word in text for word in ("原图", "转图", "转图片", "转成图片", "转为图片"))


class VideoExport:
    """Coordinate one request at a time without blocking other conversations."""

    def __init__(self, config: ExportConfig, downloader: Optional[BilibiliDownloader] = None) -> None:
        """Inject operational policy and an optionally isolated provider."""
        self.config = config
        self.downloader = downloader or BilibiliDownloader(config)
        self._active = False
        self._seen = OrderedDict()

    async def handle(self, event: MessageEvent, gateway: VideoExportGateway) -> bool:
        """Route images/video from a single ownership-checked quote lookup."""
        if _image_only(event) or not is_video_export_intent(event):
            return await handle_export_img(event, gateway)
        command = (event.text.strip().casefold().split(maxsplit=1) or [""])[0]
        if command in {"/export", "export", "/export-video", "export-video"} and event.text.strip().casefold() != command:
            await gateway.send_reply(event, "请引用消息后发送 /export 或 /export-video，不需要额外参数。")
            return True
        explicit = command in {"/export-video", "export-video"} or "视频" in event.text
        if explicit and not self.config.video_enabled:
            await gateway.send_reply(event, "视频导出已关闭；原图导出仍可使用。")
            return True
        key = (event.engine, event.instance_id, event.conversation_kind,
               event.conversation_id, event.message_id)
        now = time.monotonic()
        while self._seen and (len(self._seen) >= 1024 or next(iter(self._seen.values())) <= now - 3600):
            self._seen.popitem(last=False)
        if event.message_id and key in self._seen:
            return True
        if event.message_id:
            self._seen[key] = now
        if not event.reply_context.get("quoted_message_id"):
            await gateway.send_reply(event, "请引用要导出的 Bilibili 视频、图片或表情包。")
            return True
        quoted, _ = await gateway.quoted_message(event)
        texts = [str(segment.data.get("url") or "") if segment.kind == "link"
                 else str(segment.data.get("text") or "") for segment in quoted
                 if segment.kind in {"link", "text"}]
        try:
            sources = tuple(url for url in candidate_urls(texts) if supported_url(url))
        except VideoExportError as error:
            await gateway.send_reply(event, _failure(error.code))
            return True
        if not sources and not explicit and any(is_image_segment(segment) for segment in quoted):
            return await handle_export_img(event, gateway, quoted=quoted)
        if not sources:
            await gateway.send_reply(event, "引用的消息中未找到支持的 Bilibili 视频链接或小程序卡片。")
            return True
        if not self.config.video_enabled:
            await gateway.send_reply(event, "视频导出已关闭；原图导出仍可使用。")
            return True
        if self._active:
            await gateway.send_reply(event, "另一个视频正在导出，请稍后重新引用消息发起请求。")
            return True
        self._active = True
        try:
            await self._export(event, gateway, sources)
        finally:
            self._active = False
        return True

    async def _export(self, event: MessageEvent, gateway: VideoExportGateway, sources: Sequence[str]) -> None:
        """Resolve once, deduplicate and return each complete selected video."""
        targets = []
        loop = asyncio.get_running_loop()
        try:
            for source in sources:
                target = await loop.run_in_executor(None, resolve_video_url, source)
                if target not in targets:
                    targets.append(target)
            if len(targets) > self.config.max_urls:
                raise VideoExportError("too_many_urls")
        except VideoExportError as error:
            await gateway.send_reply(event, _failure(error.code))
            return
        await gateway.send_reply(event, "开始导出 {} 个视频，获取当前会话可用的最高画质。".format(len(targets)))
        for target in targets:
            video = None
            uncertain = False
            sending = False
            try:
                video = await self.downloader.download(target)
                sending = True
                await gateway.send_exported_video(event, video)
                sending = False
                await gateway.send_reply(event, "已导出 {} 第 {} P：{}p{}。".format(
                    target.video_id, target.part, video.height,
                    " / {:g} fps".format(video.fps) if video.fps else ""))
            except VideoSendError as error:
                uncertain = error.uncertain
                await gateway.send_reply(event, "视频发送结果未知，请先检查是否已收到；不会自动重发。"
                                         if uncertain else "视频发送被平台拒绝，请稍后重试。")
            except asyncio.CancelledError:
                uncertain = sending
                raise
            except VideoExportError as error:
                await gateway.send_reply(event, _failure(error.code))
            finally:
                if video is not None:
                    self.downloader.release(video, uncertain=uncertain)


def _failure(code: str) -> str:
    """Return bounded operational guidance without exposing provider payloads."""
    return {
        "invalid_session": "Bilibili 登录凭据已失效或被拒绝，请更新 SESSDATA 后重试。",
        "missing_tooling": "视频导出组件不可用，需要 Python 3.10+、video 依赖及 FFmpeg/ffprobe。",
        "too_many_urls": "引用的消息包含过多视频链接，请拆分后重试。",
        "file_limit": "最高画质视频超过文件大小限制，请调整导出配置后重试。",
        "workspace_limit": "视频临时存储空间不足，请稍后重试或调整导出限制。",
        "timeout": "视频导出超时，已停止下载，请稍后重试。",
        "unsafe_spool": "视频临时目录不可安全使用，请检查部署目录和权限。",
        "unsupported_video": "暂不支持该视频类型；请使用普通 Bilibili 视频链接。",
        "merge_failed": "视频合并或完整性检查失败，未发送不完整文件。",
        "restricted_video": "当前会话没有可用的视频格式，可能受到权限或地区限制。",
        "invalid_part": "视频分 P 参数无效，请检查链接。",
        "unsupported_url": "链接跳转到了不支持的地址，请使用 Bilibili 普通视频链接。",
    }.get(code, "无法获取 Bilibili 视频，可能已删除、受限或暂时不可访问，请稍后重试。")
