"""Private Bilibili downloader worker; stdin owns secrets, stdout is a safe result.

The optional video extra requires Python >=3.10. Importing the main application
does not import yt-dlp. No general command-line flags, user config, browser
cookies, plugins or external downloader hooks are accepted by this worker.
"""

import contextlib
import http.cookiejar
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping

from kisara.infrastructure.integrations.bilibili import VideoExportError, normalize_video_url
from kisara.infrastructure.integrations.video_files import directory_bytes


class _QuietLogger:
    """Prevent provider errors from leaking signed URLs or cookies."""

    def debug(self, message: str) -> None:
        """Discard provider diagnostics."""

    def warning(self, message: str) -> None:
        """Discard provider diagnostics."""

    def error(self, message: str) -> None:
        """Discard provider diagnostics."""


def select_format(context: Mapping[str, Any]) -> Iterator[Dict[str, Any]]:
    """Prefer resolution/fps before codec compatibility, without a quality cap."""
    formats = context.get("formats") or []
    videos = [item for item in formats if item.get("vcodec") not in {None, "none"}]
    if not videos:
        raise VideoExportError("restricted_video")
    video = max(videos, key=_video_rank)
    if video.get("acodec") not in {None, "none"}:
        yield video
        return
    audios = [item for item in formats if item.get("vcodec") == "none" and item.get("acodec") not in {None, "none"}]
    if not audios:
        yield video
        return
    audio = max(audios, key=lambda item: (float(item.get("abr") or item.get("tbr") or 0),
                                         float(item.get("asr") or 0), int(item.get("audio_channels") or 0)))
    yield {
        "format_id": str(video["format_id"]) + "+" + str(audio["format_id"]),
        "ext": "mp4", "requested_formats": [video, audio],
        "protocol": video["protocol"] + "+" + audio["protocol"],
        "height": video.get("height"), "width": video.get("width"), "fps": video.get("fps"),
    }


def _video_rank(item: Mapping[str, Any]) -> tuple:
    """Use codec preference only after the source's picture-quality dimensions."""
    codec = str(item.get("vcodec") or "")
    return (int(item.get("height") or 0), float(item.get("fps") or 0),
            float(item.get("quality") or 0), int(codec.startswith(("avc", "h264"))),
            float(item.get("tbr") or 0))


def _session_cookie(value: str) -> http.cookiejar.Cookie:
    """Limit authentication to Bilibili hosts, never CDN or short-link hosts."""
    return http.cookiejar.Cookie(0, "SESSDATA", value, None, False,
                                 ".bilibili.com", True, True, "/", True,
                                 True, None, True, None, None, {}, False)


def run(request: Mapping[str, Any]) -> Dict[str, Any]:
    """Extract, download, remux and validate exactly one admitted video target."""
    target = normalize_video_url(str(request.get("url") or ""))
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise VideoExportError("missing_tooling")
    max_bytes = request.get("max_file_bytes")
    workspace = request.get("workspace_bytes")
    if type(max_bytes) is not int or type(workspace) is not int or not 0 < max_bytes <= 1024 ** 3 or not 0 < workspace <= 2 * 1024 ** 3:
        raise VideoExportError("file_limit")
    session = request.get("sessdata", "")
    if not isinstance(session, str) or len(session) > 4096 or any(ord(c) < 33 or ord(c) > 126 or c == ";" for c in session):
        raise VideoExportError("invalid_session")
    os.environ["YTDLP_NO_PLUGINS"] = "1"
    try:
        package = importlib.import_module("yt_dlp")
        extractor = importlib.import_module("yt_dlp.extractor.bilibili")
    except ImportError:
        raise VideoExportError("missing_tooling") from None
    root = Path.cwd()

    def progress(status: Mapping[str, Any]) -> None:
        """Check unknown-length streams as well as provider size estimates."""
        if int(status.get("downloaded_bytes") or 0) > max_bytes:
            raise VideoExportError("file_limit")
        if directory_bytes(root) > workspace:
            raise VideoExportError("workspace_limit")

    options = {
        "logger": _QuietLogger(), "quiet": True, "no_warnings": True,
        "noplaylist": True, "lazy_playlist": True, "playlistend": 1,
        "format": select_format, "merge_output_format": "mp4",
        "outtmpl": str(root / "video.%(ext)s"), "overwrites": False,
        "continuedl": False, "writeinfojson": False, "writethumbnail": False,
        "writesubtitles": False, "writeautomaticsub": False,
        "socket_timeout": 15, "retries": 1, "fragment_retries": 1,
        "concurrent_fragment_downloads": 1, "buffersize": 65536,
        "http_chunk_size": 1024 * 1024, "progress_hooks": [progress],
        "postprocessor_hooks": [progress], "cachedir": False, "plugin_dirs": [],
        "enable_file_urls": False,
        "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}],
    }
    with package.YoutubeDL(options, auto_init=False) as downloader:
        downloader.add_info_extractor(extractor.BiliBiliIE())
        if session:
            downloader.cookiejar.set_cookie(_session_cookie(session))
            with downloader.urlopen("https://api.bilibili.com/x/web-interface/nav") as response:
                status = json.loads(response.read(200001))
            if status.get("code") != 0 or not (status.get("data") or {}).get("isLogin"):
                raise VideoExportError("invalid_session")
        info = downloader.extract_info(target.url, download=False, ie_key="BiliBili")
        if not isinstance(info, dict) or "entries" in info or info.get("is_live"):
            raise VideoExportError("unsupported_video")
        selected = info.get("requested_formats") or [info]
        estimates = [item.get("filesize") or item.get("filesize_approx") for item in selected]
        if all(isinstance(size, (float, int)) for size in estimates) and sum(estimates) > max_bytes:
            raise VideoExportError("file_limit")
        had_audio = any(item.get("acodec") not in {None, "none"} for item in selected)
        downloader.process_info(info)
    path = root / "video.mp4"
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= max_bytes:
        raise VideoExportError("file_limit" if path.is_file() else "merge_failed")
    if directory_bytes(root) > workspace:
        raise VideoExportError("workspace_limit")
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
        "-of", "json", str(path),
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30, check=False)
    if probe.returncode or len(probe.stdout) > 65536:
        raise VideoExportError("merge_failed")
    metadata = json.loads(probe.stdout)
    streams = metadata.get("streams") or []
    videos = [item for item in streams if item.get("codec_type") == "video"]
    if not videos or (had_audio and not any(item.get("codec_type") == "audio" for item in streams)):
        raise VideoExportError("merge_failed")
    actual_duration = float((metadata.get("format") or {}).get("duration") or 0)
    expected_duration = float(info.get("duration") or 0)
    if actual_duration <= 0 or (expected_duration and abs(actual_duration - expected_duration) > max(3, expected_duration * .05)):
        raise VideoExportError("merge_failed")
    return {"status": "ok", "height": int(videos[0].get("height") or 0),
            "fps": float(info.get("fps") or 0)}


def main() -> int:
    """Emit one bounded result and discard every raw third-party diagnostic."""
    result = {"status": "error", "error": "provider_unavailable"}
    try:
        raw = sys.stdin.buffer.read(16385)
        if len(raw) > 16384:
            raise VideoExportError("invalid_session")
        request = json.loads(raw)
        if not isinstance(request, dict):
            raise VideoExportError("unsupported_video")
        with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            result = run(request)
    except VideoExportError as error:
        result = {"status": "error", "error": error.code}
    except Exception:
        pass
    sys.stdout.write(json.dumps(result, separators=(",", ":")))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
