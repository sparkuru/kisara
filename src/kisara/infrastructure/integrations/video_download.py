"""Run the Bilibili worker with bounded output, storage and process lifetime."""

import asyncio
import json
import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from kisara.config.export import ExportConfig
from kisara.infrastructure.integrations.bilibili import VideoExportError, VideoTarget
from kisara.infrastructure.integrations.video_files import ExportSpool, WORKSPACE_BYTES, directory_bytes


@dataclass(frozen=True)
class DownloadedVideo:
    """A complete owned file that must survive until the native send finishes."""

    path: Path
    job: Path
    height: int
    fps: float
    size: int


class BilibiliDownloader:
    """Keep downloader implementation and credentials outside the adapter loop."""

    def __init__(self, config: ExportConfig, spool: Optional[ExportSpool] = None) -> None:
        """Inject validated policy and an optionally isolated transport spool."""
        self.config = config
        self.spool = spool or ExportSpool()

    async def download(self, target: VideoTarget) -> DownloadedVideo:
        """Run one cancellable worker, returning only a validated complete file."""
        if sys.version_info < (3, 10):
            raise VideoExportError("missing_tooling")
        process = None
        job = None
        output_task = None
        succeeded = False
        try:
            job = self.spool.create().absolute()
            environment = {key: os.environ[key] for key in (
                "PATH", "PYTHONPATH", "PYTHONUSERBASE", "LANG", "SSL_CERT_FILE", "SSL_CERT_DIR",
            ) if key in os.environ}
            environment.update(HOME=str(job), YTDLP_NO_PLUGINS="1", PYTHONDONTWRITEBYTECODE="1")
            if "PYTHONPATH" in environment:
                environment["PYTHONPATH"] = os.pathsep.join(str(Path(part).absolute()) for part in
                                                            environment["PYTHONPATH"].split(os.pathsep) if part)
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "kisara.infrastructure.integrations.video_worker",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, cwd=str(job), env=environment,
                start_new_session=True,
            )
            output_task = asyncio.create_task(_read_result(process.stdout))
            request = json.dumps({
                "url": target.url, "sessdata": self.config.sessdata,
                "max_file_bytes": self.config.max_file_bytes,
                "workspace_bytes": WORKSPACE_BYTES - directory_bytes(self.spool.root) + directory_bytes(job),
            }).encode("utf-8")
            process.stdin.write(request)
            await process.stdin.drain()
            process.stdin.close()
            await asyncio.wait_for(self._wait(process, output_task), self.config.timeout_seconds)
            raw = await output_task
            try:
                result = json.loads(raw)
            except (ValueError, UnicodeError):
                raise VideoExportError("worker_failed") from None
            if not isinstance(result, dict):
                raise VideoExportError("worker_failed")
            if result.get("status") != "ok" or process.returncode != 0:
                code = result.get("error")
                allowed = {"missing_tooling", "invalid_session", "provider_unavailable", "restricted_video",
                           "file_limit", "workspace_limit", "merge_failed", "unsupported_video"}
                raise VideoExportError(code if isinstance(code, str) and code in allowed else "worker_failed")
            path = job / "video.mp4"
            info = path.lstat()
            if path.is_symlink() or not path.is_file() or info.st_size < 1:
                raise VideoExportError("worker_failed")
            if info.st_size > self.config.max_file_bytes:
                raise VideoExportError("file_limit")
            height, fps = result.get("height"), result.get("fps")
            if type(height) is not int or not 1 <= height <= 32768 or not isinstance(fps, (float, int)) or not 0 <= fps <= 1000:
                raise VideoExportError("worker_failed")
            path.chmod(0o644)
            succeeded = True
            return DownloadedVideo(path, job, height, float(fps), info.st_size)
        except asyncio.TimeoutError:
            raise VideoExportError("timeout") from None
        except (OSError, ValueError):
            raise VideoExportError("worker_failed") from None
        finally:
            if process is not None:
                await _terminate(process)
            if output_task is not None and not output_task.done():
                output_task.cancel()
                await asyncio.gather(output_task, return_exceptions=True)
            if job is not None and not succeeded:
                self.spool.remove(job)

    async def _wait(self, process: Any, output: Any) -> None:
        """Monitor aggregate spool use while the owned process is running."""
        while process.returncode is None:
            if output.done() and output.exception() is not None:
                raise output.exception()
            if directory_bytes(self.spool.root) > WORKSPACE_BYTES:
                raise VideoExportError("workspace_limit")
            await asyncio.sleep(0.1)
        await process.wait()
        await output

    def release(self, video: DownloadedVideo, uncertain: bool = False) -> None:
        """Retain unknown native sends and clean completed/definitely failed jobs."""
        if uncertain:
            self.spool.retain(video.job)
        else:
            self.spool.remove(video.job)


async def _read_result(stream: Any) -> bytes:
    """Never accumulate an unbounded or raw worker diagnostic stream."""
    data = bytearray()
    while True:
        chunk = await stream.read(4096)
        if not chunk:
            return bytes(data)
        data.extend(chunk)
        if len(data) > 4096:
            raise VideoExportError("worker_failed")


async def _terminate(process: Any) -> None:
    """Reap the owned worker and its merger descendants on every exit path."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        try:
            await asyncio.wait_for(asyncio.shield(process.wait()), timeout=2.0)
        except asyncio.TimeoutError:
            continue
    await process.wait()
