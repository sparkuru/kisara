"""Bilibili target admission, cookie scope and best-format decisions."""

import io
from http.cookiejar import CookieJar
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from kisara.infrastructure.integrations import bilibili
from kisara.infrastructure.integrations.bilibili import VideoExportError, candidate_urls, normalize_video_url
from kisara.infrastructure.integrations.video_worker import _session_cookie, select_format


@pytest.mark.parametrize("url,identity,part", [
    ("https://www.bilibili.com/video/BV1drnJ6BE86/", "BV1drnJ6BE86", 1),
    ("http://m.bilibili.com/video/av123?spm_id=tracking&p=2", "av123", 2),
    ("https://bilibili.com/video/bv1drnJ6BE86?p=3", "BV1drnJ6BE86", 3),
])
def test_normalizes_one_video_without_tracking(url: str, identity: str, part: int) -> None:
    target = normalize_video_url(url)
    assert (target.video_id, target.part) == (identity, part)
    assert target.url == "https://www.bilibili.com/video/{}?p={}".format(identity, part)


@pytest.mark.parametrize("url", [
    "https://bilibili.com.evil.test/video/av1", "https://127.0.0.1/video/av1",
    "https://bilibili.com@localhost/video/av1", "file:///video/av1",
    "https://@www.bilibili.com/video/av1",
    "https://www.bilibili.com:80/video/av1", "https://www.bilibili.com/video/av1?p=0",
    "https://www.bilibili.com/video/av1?p=1&p=2", "https://www.bilibili.com/video/av1?p=",
    "https://www.bilibili.com/bangumi/play/ep1", "https://b23.tv/a/another",
    "https://www.bilibili.com/video/av1\n", "https://www.bilibili.com/video/av1?p=-1",
])
def test_rejects_invalid_or_unrelated_sources(url: str) -> None:
    with pytest.raises(VideoExportError):
        normalize_video_url(url)


def test_candidates_preserve_public_punctuation_and_deduplicate() -> None:
    url = "https://www.bilibili.com/video/BV1drnJ6BE86/"
    assert candidate_urls(("watch " + url + "）", url)) == (url,)


def test_short_link_never_sends_cookies_and_checks_location(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = []

    def open_url(request: Request, timeout: float) -> None:
        requests.append(request)
        raise HTTPError(request.full_url, 302, "redirect", {"Location": "http://127.0.0.1/private"}, io.BytesIO())

    monkeypatch.setattr(bilibili, "build_opener", lambda *args: SimpleNamespace(open=open_url))
    with pytest.raises(VideoExportError, match="unsupported_url"):
        bilibili.resolve_video_url("https://b23.tv/example")
    assert len(requests) == 1 and not requests[0].has_header("Cookie")


def test_short_link_resolves_public_video_and_discards_tracking(monkeypatch: pytest.MonkeyPatch) -> None:
    def open_url(request: Request, timeout: float) -> None:
        raise HTTPError(request.full_url, 302, "redirect", {
            "Location": "https://www.bilibili.com/video/BV1rcpL6TEwK/?p=2&share_token=private",
        }, io.BytesIO())
    monkeypatch.setattr(bilibili, "build_opener", lambda *args: SimpleNamespace(open=open_url))
    target = bilibili.resolve_video_url("https://b23.tv/example")
    assert target.url == "https://www.bilibili.com/video/BV1rcpL6TEwK?p=2"


def test_session_cookie_is_scoped_to_https_bilibili() -> None:
    jar = CookieJar()
    jar.set_cookie(_session_cookie("synthetic-session"))
    for url, expected in (("https://api.bilibili.com/x/web-interface/nav", True),
                          ("https://www.bilibili.com/video/av1", True),
                          ("https://b23.tv/example", False),
                          ("https://cdn.bilivideo.com/video", False),
                          ("http://api.bilibili.com/path", False)):
        request = Request(url)
        jar.add_cookie_header(request)
        assert request.has_header("Cookie") is expected


def test_best_format_has_no_1080p_or_h264_quality_cap() -> None:
    formats = [
        {"format_id": "1080", "height": 1080, "fps": 60, "vcodec": "avc1", "acodec": "none", "protocol": "https"},
        {"format_id": "2160", "height": 2160, "fps": 60, "vcodec": "av01", "acodec": "none", "protocol": "https"},
        {"format_id": "audio", "vcodec": "none", "acodec": "mp4a", "tbr": 192, "protocol": "https"},
    ]
    selected = list(select_format({"formats": formats}))[0]
    assert [item["format_id"] for item in selected["requested_formats"]] == ["2160", "audio"]


def test_equal_picture_quality_prefers_compatible_codec_and_silent_source() -> None:
    formats = [
        {"format_id": "av1", "height": 1080, "fps": 30, "vcodec": "av01", "acodec": "none"},
        {"format_id": "avc", "height": 1080, "fps": 30, "vcodec": "avc1", "acodec": "none"},
    ]
    assert list(select_format({"formats": formats}))[0]["format_id"] == "avc"
    with pytest.raises(VideoExportError, match="restricted_video"):
        list(select_format({"formats": [{"vcodec": "none", "acodec": "mp4a"}]}))
