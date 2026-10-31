"""Quoted export routing, file lifetime and isolated process cleanup."""

import asyncio
import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from kisara.application.services.export_video import VideoExport
from kisara.bot.adapters.onebot_v11 import _read_segments
from kisara.bot.contracts import MessageEvent, MessageSegment
from kisara.config.export import ExportConfig
from kisara.infrastructure.integrations import video_download
from kisara.infrastructure.integrations.bilibili import VideoExportError, VideoSendError, VideoTarget
from kisara.infrastructure.integrations.video_download import BilibiliDownloader, DownloadedVideo
from kisara.infrastructure.integrations.video_files import ExportSpool, JOB_GRACE_SECONDS


def event(text: str = "导出", identifier: str = "command-1") -> MessageEvent:
    return MessageEvent("onebot", "test", identifier, "private", "123", "123",
                        (MessageSegment("text", {"text": text}),), {"quoted_message_id": "source"})


class Gateway:
    """Observe service effects with a real temporary media file."""

    def __init__(self, quoted: tuple) -> None:
        self.quoted = quoted
        self.lookups = 0
        self.replies = []
        self.files = []
        self.videos = []
        self.send_error = None

    async def quoted_message(self, incoming: MessageEvent) -> tuple:
        self.lookups += 1
        return self.quoted, "123"

    async def send_reply(self, incoming: MessageEvent, text: str) -> None:
        self.replies.append(text)

    async def send_exported_files(self, incoming: MessageEvent, files: list) -> None:
        self.files.extend(files)

    async def send_exported_video(self, incoming: MessageEvent, video: DownloadedVideo) -> None:
        assert video.path.exists()
        self.videos.append(video)
        if self.send_error is not None:
            raise self.send_error


class Provider:
    """Use owned real spool files while substituting the external download."""

    def __init__(self, root: Path) -> None:
        self.spool = ExportSpool(root)
        self.targets = []

    async def download(self, target: VideoTarget) -> DownloadedVideo:
        self.targets.append(target)
        job = self.spool.create()
        path = job / "video.mp4"
        path.write_bytes(b"complete-video")
        return DownloadedVideo(path, job, 2160, 60, path.stat().st_size)

    def release(self, video: DownloadedVideo, uncertain: bool = False) -> None:
        self.spool.retain(video.job) if uncertain else self.spool.remove(video.job)


def test_card_normalization_uses_qqdocurl_not_launch_or_preview() -> None:
    card = {"app": "com.tencent.miniapp_01", "meta": {"detail_1": {
        "appid": "1109937557", "url": "m.q.qq.com/launch", "preview": "https://example.test/image",
        "qqdocurl": "https://b23.tv/example",
    }}}
    segments = _read_segments([{"type": "json", "data": {"data": json.dumps(card)}}])
    assert segments[-1] == MessageSegment("link", {"url": "https://b23.tv/example", "provider": "bilibili"})
    assert not any(segment.kind == "link" for segment in _read_segments([
        {"type": "json", "data": {"data": "invalid-json"}},
    ]))
    assert not any(segment.kind == "link" for segment in _read_segments([
        {"type": "json", "data": {"data": "[" * 2000 + "]" * 2000}},
    ]))


def test_generic_export_video_deduplicates_and_cleans_after_send(tmp_path: Path) -> None:
    async def run() -> None:
        provider = Provider(tmp_path)
        service = VideoExport(ExportConfig(), provider)
        source = "https://www.bilibili.com/video/BV1drnJ6BE86/"
        gateway = Gateway((MessageSegment("text", {"text": source + " " + source}),))
        assert await service.handle(event(), gateway)
        assert len(provider.targets) == len(gateway.videos) == gateway.lookups == 1
        assert not gateway.videos[0].path.exists()
        assert "2160p" in gateway.replies[-1]
        assert await service.handle(event(), gateway)
        assert gateway.lookups == 1
    asyncio.run(run())


@pytest.mark.parametrize("command", ["导出", "/export", "/export-img", "原图"])
def test_image_export_keeps_original_and_fetches_quote_once(tmp_path: Path, command: str) -> None:
    async def run() -> None:
        gateway = Gateway((MessageSegment("image", {"url": "https://example.test/original.gif"}),))
        provider = Provider(tmp_path)
        assert await VideoExport(ExportConfig(), provider).handle(event(command), gateway)
        assert gateway.lookups == 1
        assert gateway.files == [("https://example.test/original.gif", "export-1.gif")]
        assert not provider.targets
    asyncio.run(run())


@pytest.mark.parametrize("uncertain", [True, False])
def test_unknown_send_retains_file_without_retry_and_expires_only_owned_data(tmp_path: Path, uncertain: bool) -> None:
    async def run() -> None:
        provider = Provider(tmp_path)
        service = VideoExport(ExportConfig(), provider)
        gateway = Gateway((MessageSegment("text", {"text": "https://www.bilibili.com/video/av123"}),))
        gateway.send_error = VideoSendError(uncertain)
        await service.handle(event(), gateway)
        video = gateway.videos[0]
        assert video.path.exists() is uncertain
        assert len(gateway.videos) == 1
        unrelated = tmp_path / "user-file"
        unrelated.write_text("keep")
        if uncertain:
            stamp = time.time() - JOB_GRACE_SECONDS - 1
            os.utime(video.job / ".owned", (stamp, stamp))
        provider.spool.prepare()
        assert not video.path.exists() and unrelated.read_text() == "keep"
    asyncio.run(run())


def test_cancel_during_native_send_keeps_media_and_releases_busy_slot(tmp_path: Path) -> None:
    async def run() -> None:
        provider = Provider(tmp_path)
        service = VideoExport(ExportConfig(), provider)
        gateway = Gateway((MessageSegment("text", {"text": "https://www.bilibili.com/video/av123"}),))
        gateway.send_error = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await service.handle(event(), gateway)
        assert gateway.videos[0].path.exists() and not service._active
    asyncio.run(run())


def test_disabled_busy_and_url_limit_do_not_download(tmp_path: Path) -> None:
    async def run() -> None:
        provider = Provider(tmp_path)
        gateway = Gateway((MessageSegment("text", {"text": "https://www.bilibili.com/video/av123"}),))
        service = VideoExport(replace(ExportConfig(), video_enabled=False), provider)
        await service.handle(event(), gateway)
        assert not provider.targets
        service = VideoExport(ExportConfig(), provider)
        service._active = True
        await service.handle(event(identifier="another"), gateway)
        assert not provider.targets
        service = VideoExport(replace(ExportConfig(), max_urls=1), provider)
        gateway.quoted = (MessageSegment("text", {"text": "https://www.bilibili.com/video/av1 https://www.bilibili.com/video/av2"}),)
        await service.handle(event(identifier="third"), gateway)
        assert not provider.targets and "过多" in gateway.replies[-1]
    asyncio.run(run())


def test_explicit_disabled_command_and_bad_arguments_do_not_fetch_history(tmp_path: Path) -> None:
    async def run() -> None:
        gateway = Gateway(())
        provider = Provider(tmp_path)
        service = VideoExport(replace(ExportConfig(), video_enabled=False), provider)
        await service.handle(event("/export-video"), gateway)
        await service.handle(event("/export-video extra", "arguments"), gateway)
        assert gateway.lookups == 0 and not provider.targets
        assert "关闭" in gateway.replies[0] and "额外参数" in gateway.replies[1]
    asyncio.run(run())


def test_spool_refuses_symlink_and_preserves_unknown_directories(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere"
    target.mkdir()
    link = tmp_path / "spool"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(VideoExportError, match="unsafe_spool"):
        ExportSpool(link).prepare()
    root = tmp_path / "real"
    root.mkdir()
    unknown = root / ("job-" + "a" * 32)
    unknown.mkdir()
    (unknown / "important").write_text("keep")
    ExportSpool(root).prepare()
    assert (unknown / "important").exists()


@pytest.mark.parametrize("behavior,expected", [
    ("ok", None), ("oversized", "file_limit"), ("output", "worker_failed"),
    ("badjson", "worker_failed"), ("invalid_session", "invalid_session"),
])
def test_real_subprocess_contract_and_failed_job_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, behavior: str, expected: str,
) -> None:
    original_exec = asyncio.create_subprocess_exec
    called = []
    code = '''import json,sys
from pathlib import Path
request=json.load(sys.stdin)
mode=MODE
if mode=="invalid_session":
 print(json.dumps({"status":"error","error":"invalid_session"}));sys.exit(1)
Path("video.mp4").write_bytes(b"video" if mode!="oversized" else b"x"*100)
print("x"*9000 if mode=="output" else "broken" if mode=="badjson" else json.dumps({"status":"ok","height":2160,"fps":60}))
'''.replace("MODE", repr(behavior))

    async def spawn(*args: Any, **kwargs: Any) -> Any:
        called.append((args, kwargs))
        return await original_exec(sys.executable, "-c", code, **kwargs)

    monkeypatch.setattr(video_download.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "another-private-secret")
    async def run() -> None:
        config = replace(ExportConfig(), sessdata="synthetic-private-session", max_file_bytes=10)
        provider = BilibiliDownloader(config, ExportSpool(tmp_path))
        if expected:
            with pytest.raises(VideoExportError, match=expected):
                await provider.download(VideoTarget("av123"))
            assert not list(tmp_path.iterdir())
        else:
            video = await provider.download(VideoTarget("av123"))
            assert video.path.read_bytes() == b"video" and video.height == 2160
            provider.release(video)
        assert "synthetic-private-session" not in repr(called[0])
        assert "another-private-secret" not in repr(called[0])
    asyncio.run(run())


def test_real_worker_timeout_kills_descendant_and_cleans_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_exec = asyncio.create_subprocess_exec
    child_record = tmp_path / "child-pid"
    root = tmp_path / "spool"
    code = '''import json,subprocess,sys,time
from pathlib import Path
json.load(sys.stdin)
child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"])
Path(RECORD).write_text(str(child.pid))
Path("video.part").write_bytes(b"partial")
time.sleep(60)
'''.replace("RECORD", repr(str(child_record)))

    async def spawn(*args: Any, **kwargs: Any) -> Any:
        return await original_exec(sys.executable, "-c", code, **kwargs)

    monkeypatch.setattr(video_download.asyncio, "create_subprocess_exec", spawn)
    async def run() -> None:
        provider = BilibiliDownloader(replace(ExportConfig(), timeout_seconds=1), ExportSpool(root))
        with pytest.raises(VideoExportError, match="timeout"):
            await provider.download(VideoTarget("av123"))
        assert not list(root.iterdir())
        pid = int(child_record.read_text())
        stat = Path("/proc/{}/stat".format(pid))
        assert not stat.exists() or stat.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    asyncio.run(run())


def test_real_worker_cancel_reaps_process_and_removes_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_exec = asyncio.create_subprocess_exec
    started = asyncio.Event()
    processes = []
    code = 'import json,sys,time;from pathlib import Path;json.load(sys.stdin);Path("video.part").write_bytes(b"partial");time.sleep(60)'

    async def spawn(*args: Any, **kwargs: Any) -> Any:
        process = await original_exec(sys.executable, "-c", code, **kwargs)
        processes.append(process)
        started.set()
        return process

    monkeypatch.setattr(video_download.asyncio, "create_subprocess_exec", spawn)
    async def run() -> None:
        provider = BilibiliDownloader(ExportConfig(), ExportSpool(tmp_path))
        task = asyncio.create_task(provider.download(VideoTarget("av123")))
        await started.wait()
        await asyncio.sleep(.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert processes[0].returncode is not None and not list(tmp_path.iterdir())
    asyncio.run(run())


def test_exited_worker_with_stdout_held_by_descendant_still_times_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the result-pipe EOF wait inside the worker's overall deadline."""
    original_exec = asyncio.create_subprocess_exec
    child_record = tmp_path / "child-pid"
    root = tmp_path / "spool"
    code = '''import json,subprocess,sys
from pathlib import Path
json.load(sys.stdin)
child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"])
Path(RECORD).write_text(str(child.pid))
Path("video.mp4").write_bytes(b"complete")
print(json.dumps({"status":"ok","height":1080,"fps":30}),flush=True)
'''.replace("RECORD", repr(str(child_record)))

    async def spawn(*args: Any, **kwargs: Any) -> Any:
        return await original_exec(sys.executable, "-c", code, **kwargs)

    monkeypatch.setattr(video_download.asyncio, "create_subprocess_exec", spawn)

    async def run() -> None:
        provider = BilibiliDownloader(replace(ExportConfig(), timeout_seconds=1), ExportSpool(root))
        with pytest.raises(VideoExportError, match="timeout"):
            await asyncio.wait_for(provider.download(VideoTarget("av123")), timeout=4)
        assert not list(root.iterdir())
        pid = int(child_record.read_text())
        process_stat = Path("/proc/{}/stat".format(pid))
        assert not process_stat.exists() or process_stat.read_text().rsplit(")", 1)[1].split()[0] == "Z"

    asyncio.run(run())
