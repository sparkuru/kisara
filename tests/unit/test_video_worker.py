"""Exercise worker merge validation without provider traffic or optional tools."""

import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from kisara.infrastructure.integrations import video_worker
from kisara.infrastructure.integrations.bilibili import VideoExportError


def fixture_worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, session_valid: bool = True,
                   result_audio: bool = True, duration: float = 60.0) -> list:
    """Fake external extraction and tool execution while exercising worker policy."""
    monkeypatch.chdir(tmp_path)
    calls = []

    class Downloader:
        def __init__(self, options: dict, auto_init: bool) -> None:
            calls.append((options, auto_init))
            self.cookiejar = SimpleNamespace(set_cookie=lambda cookie: calls.append(cookie))

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def add_info_extractor(self, extractor: Any) -> None:
            calls.append("bilibili-only-extractor")

        def urlopen(self, url: str) -> io.BytesIO:
            assert url == "https://api.bilibili.com/x/web-interface/nav"
            return io.BytesIO(json.dumps({"code": 0 if session_valid else -101,
                                         "data": {"isLogin": session_valid}}).encode())

        def extract_info(self, url: str, download: bool, ie_key: str) -> dict:
            assert not download and ie_key == "BiliBili"
            return {"height": 2160, "fps": 60, "duration": 60,
                    "requested_formats": [{"vcodec": "av01", "acodec": "none", "filesize": 8},
                                          {"vcodec": "none", "acodec": "mp4a", "filesize": 2}]}

        def process_info(self, info: dict) -> None:
            (tmp_path / "video.mp4").write_bytes(b"complete")

    monkeypatch.setattr(video_worker.importlib, "import_module", lambda name: (
        SimpleNamespace(YoutubeDL=Downloader) if name == "yt_dlp" else SimpleNamespace(BiliBiliIE=lambda: object())))
    monkeypatch.setattr(video_worker.shutil, "which", lambda name: "/usr/bin/" + name)
    streams = [{"codec_type": "video", "height": 2160}]
    if result_audio:
        streams.append({"codec_type": "audio"})
    monkeypatch.setattr(video_worker.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout=json.dumps({"streams": streams, "format": {"duration": duration}}).encode()))
    return calls


def test_worker_scopes_cookie_disables_automatic_extractors_and_checks_complete_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = fixture_worker(tmp_path, monkeypatch)
    result = video_worker.run({"url": "https://www.bilibili.com/video/av123?p=1", "sessdata": "synthetic",
                               "max_file_bytes": 1000, "workspace_bytes": 2000})
    assert result == {"status": "ok", "height": 2160, "fps": 60.0}
    options, auto_init = calls[0]
    assert auto_init is False and options["plugin_dirs"] == [] and options["cachedir"] is False
    assert options["noplaylist"] is True and options["format"] is video_worker.select_format
    assert options["postprocessors"] == [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}]
    assert "synthetic" not in repr(options)


@pytest.mark.parametrize("audio,duration", [(False, 60), (True, 4), (True, 0)])
def test_worker_rejects_silent_or_truncated_output_for_source_with_audio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, audio: bool, duration: float,
) -> None:
    fixture_worker(tmp_path, monkeypatch, result_audio=audio, duration=duration)
    with pytest.raises(VideoExportError, match="merge_failed"):
        video_worker.run({"url": "https://www.bilibili.com/video/av123?p=1",
                          "max_file_bytes": 1000, "workspace_bytes": 2000})


def test_worker_expired_session_fails_before_extraction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture_worker(tmp_path, monkeypatch, session_valid=False)
    with pytest.raises(VideoExportError, match="invalid_session"):
        video_worker.run({"url": "https://www.bilibili.com/video/av123?p=1", "sessdata": "expired",
                          "max_file_bytes": 1000, "workspace_bytes": 2000})


def test_unknown_length_progress_enforces_actual_byte_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fixture_worker(tmp_path, monkeypatch)
    video_worker.run({"url": "https://www.bilibili.com/video/av123?p=1",
                      "max_file_bytes": 1000, "workspace_bytes": 2000})
    hook = calls[0][0]["progress_hooks"][0]
    with pytest.raises(VideoExportError, match="file_limit"):
        hook({"downloaded_bytes": 1001})
