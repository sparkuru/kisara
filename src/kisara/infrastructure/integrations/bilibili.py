"""Normalize Bilibili video identities and resolve bounded, cookie-free short links.

Only ordinary BV/av video targets are accepted. Resolution never carries a
session, expands a collection, or enables a generic website downloader.
"""

import re
from dataclasses import dataclass
from typing import Iterable, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class VideoExportError(RuntimeError):
    """Carry only a controlled category across the provider boundary."""

    def __init__(self, code: str) -> None:
        """Exclude upstream messages, signed URLs and cookie contents."""
        self.code = code
        super().__init__(code)


class VideoSendError(RuntimeError):
    """Distinguish a definite native rejection from an unknown send outcome."""

    def __init__(self, uncertain: bool = True) -> None:
        """Retain only outcome certainty for media lifetime decisions."""
        self.uncertain = uncertain
        super().__init__("video_send_unknown" if uncertain else "video_send_rejected")


@dataclass(frozen=True)
class VideoTarget:
    """A canonical public video page, including exactly one anthology part."""

    video_id: str
    part: int = 1

    @property
    def url(self) -> str:
        """Discard tracking arguments while preserving the selected part."""
        return "https://www.bilibili.com/video/{}?{}".format(self.video_id, urlencode({"p": self.part}))


def candidate_urls(texts: Iterable[str]) -> Tuple[str, ...]:
    """Extract bounded web URLs without interpreting arbitrary text as a target."""
    found = []
    for text in texts:
        for match in re.finditer(r"https?://[^\s<>\"'\\]+", text[:32768], re.IGNORECASE):
            value = match.group().rstrip(".,;!?，。；！？）)]}】")
            if value not in found:
                found.append(value)
            if len(found) > 20:
                raise VideoExportError("too_many_urls")
    return tuple(found)


def supported_url(value: str) -> bool:
    """Recognize a Bilibili source without making a network request."""
    try:
        _checked_url(value)
        return True
    except VideoExportError:
        return False


def _checked_url(value: str) -> Tuple[str, str]:
    """Validate the complete authority before any redirect or extraction I/O."""
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        valid = (len(value) <= 2048 and parsed.scheme in {"http", "https"}
                 and "@" not in parsed.netloc and not parsed.username and not parsed.password
                 and parsed.port in {None, 443 if parsed.scheme == "https" else 80}
                 and not any(char.isspace() or ord(char) < 32 or char == "\\" for char in value))
    except ValueError:
        valid, host = False, ""
    if not valid or host not in {"b23.tv", "www.bilibili.com", "bilibili.com", "m.bilibili.com"}:
        raise VideoExportError("unsupported_url")
    if host == "b23.tv":
        if not re.fullmatch(r"/[A-Za-z0-9]+/?", parsed.path):
            raise VideoExportError("unsupported_url")
    elif not re.fullmatch(r"/video/(?:[bB][vV][A-Za-z0-9]{10}|[aA][vV][1-9][0-9]*)/?", parsed.path):
        raise VideoExportError("unsupported_url")
    return host, value


def normalize_video_url(value: str) -> VideoTarget:
    """Convert a validated ordinary video page into one stable identity."""
    host, _ = _checked_url(value)
    if host == "b23.tv":
        raise VideoExportError("short_link_unresolved")
    parsed = urlsplit(value)
    video_id = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    video_id = video_id[:2].upper() + video_id[2:] if video_id[:2].lower() == "bv" else video_id.lower()
    query = parse_qs(parsed.query, keep_blank_values=True)
    parts = query.get("p", ["1"])
    if len(parts) != 1 or not re.fullmatch(r"[1-9][0-9]{0,5}", parts[0]):
        raise VideoExportError("invalid_part")
    return VideoTarget(video_id, int(parts[0]))


class _NoRedirect(HTTPRedirectHandler):
    """Make every redirect pass through the explicit source allowlist."""

    def redirect_request(self, *args: object, **kwargs: object) -> None:
        """Leave redirects to the bounded resolver loop."""
        return None


def resolve_video_url(value: str, timeout: float = 10.0) -> VideoTarget:
    """Resolve at most five cookie-free redirects to a permitted video page."""
    host, _ = _checked_url(value)
    if host != "b23.tv":
        return normalize_video_url(value)
    opener = build_opener(_NoRedirect())
    current = value
    for _ in range(5):
        _checked_url(current)
        try:
            with opener.open(Request(current, headers={"User-Agent": "Mozilla/5.0"}), timeout=timeout) as response:
                return normalize_video_url(response.geturl())
        except HTTPError as error:
            try:
                if error.code not in {301, 302, 303, 307, 308}:
                    raise VideoExportError("provider_unavailable") from None
                location = error.headers.get("Location", "")
                if not location:
                    raise VideoExportError("unsupported_url")
                current = urljoin(current, location)
                host, _ = _checked_url(current)
                if host != "b23.tv":
                    return normalize_video_url(current)
            finally:
                error.close()
        except (OSError, URLError):
            raise VideoExportError("provider_unavailable") from None
    raise VideoExportError("redirect_limit")
