"""Pluggable file placement and bounded media transfer for forward archives."""

import hashlib
import os
import re
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import BinaryIO, Dict, Protocol
from urllib.parse import urlsplit

from kisara.config.forward_archive import ForwardArchiveConfig


CHINA_TIME = timezone(timedelta(hours=8))
ALLOWED_MEDIA_HOSTS = ("qq.com", "qpic.cn", "gtimg.cn", "multimedia.nt.qq.com.cn")


class ArchiveFileError(ValueError):
    """A media source cannot be safely copied into the archive."""


class FilePlacement(Protocol):
    """Choose a destination after the file's full content hash is known."""

    def destination(self, root: Path, timestamp: float, original: str,
                    digest: str, kind: str) -> Path:
        """Return a candidate path beneath the configured archive root."""


class DateOriginalPlacement:
    """Keep a dated folder and a sanitized original filename."""

    def destination(self, root: Path, timestamp: float, original: str,
                    digest: str, kind: str) -> Path:
        """Choose YYYY-MM-DD/original-name."""
        day = datetime.fromtimestamp(timestamp, CHINA_TIME).strftime("%Y-%m-%d")
        return root / day / _safe_name(original, kind)


class TimestampHashPlacement:
    """Put timestamp and full SHA-256 identity in the archive root."""

    def destination(self, root: Path, timestamp: float, original: str,
                    digest: str, kind: str) -> Path:
        """Choose YYYYMMDD-HHMMSS-sha256.extension."""
        stamp = datetime.fromtimestamp(timestamp, CHINA_TIME).strftime("%Y%m%d-%H%M%S")
        suffix = Path(_safe_name(original, kind)).suffix
        return root / "{}-{}{}".format(stamp, digest, suffix)


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Reject redirects away from QQ media hosts."""

    def redirect_request(self, request: urllib.request.Request, fp: object,
                         code: int, msg: str, headers: object,
                         newurl: str) -> urllib.request.Request:
        """Validate each redirect before urllib follows it."""
        _check_url(newurl)
        redirected = super().redirect_request(request, fp, code, msg, headers, newurl)
        if redirected is None:
            raise ArchiveFileError("Media redirect was rejected.")
        return redirected


class ArchiveFileSaver:
    """Download or copy media and delegate only naming to a placement strategy."""

    def __init__(self, config: ForwardArchiveConfig) -> None:
        """Select one of the configured storage layouts."""
        self._config = config
        self._placement: FilePlacement = (
            DateOriginalPlacement() if config.save_mode == "date_original"
            else TimestampHashPlacement()
        )

    def save(self, source: Dict[str, object], location: str,
             timestamp: float, remaining_bytes: int) -> Dict[str, object]:
        """Stream one source to a temporary file and atomically place it."""
        if remaining_bytes <= 0:
            raise ArchiveFileError("Batch size limit reached.")
        maximum = min(self._config.max_file_bytes, remaining_bytes)
        root = self._config.save_root
        root.mkdir(parents=True, exist_ok=True)
        temporary: Path
        with tempfile.NamedTemporaryFile(dir=str(root), prefix=".incoming-", delete=False) as output:
            temporary = Path(output.name)
            try:
                digest, size = self._copy(location, output, maximum)
                os.chmod(temporary, 0o640)
            except Exception:
                temporary.unlink(missing_ok=True)
                raise
        try:
            original = str(source.get("name") or source.get("file") or "")
            kind = str(source.get("kind") or "file")
            destination = self._placement.destination(root, timestamp, original, digest, kind)
            destination.parent.mkdir(parents=True, exist_ok=True)
            candidate = destination
            index = 1
            while candidate.exists():
                if candidate.is_file() and _file_hash(candidate) == digest:
                    return {"path": str(candidate), "size": size, "sha256": digest}
                candidate = destination.with_name(
                    "{}-{}{}".format(destination.stem, index, destination.suffix)
                )
                index += 1
            os.replace(str(temporary), str(candidate))
            return {"path": str(candidate), "size": size, "sha256": digest}
        finally:
            temporary.unlink(missing_ok=True)

    def _copy(self, location: str, output: BinaryIO, maximum: int) -> tuple:
        """Copy from an approved HTTPS URL or the read-only NapCat cache."""
        parsed = urlsplit(location)
        if parsed.scheme == "https":
            _check_url(location)
            opener = urllib.request.build_opener(_SafeRedirect())
            with opener.open(location, timeout=20) as source:
                return _stream(source, output, maximum)
        if parsed.scheme:
            raise ArchiveFileError("Unsupported media location scheme.")
        root = self._config.local_media_root.resolve()
        path = Path(location).resolve()
        if root not in path.parents or not path.is_file():
            raise ArchiveFileError("Media path is outside the NapCat cache or unavailable.")
        relative = path.relative_to(root)
        parts = relative.parts
        if (len(parts) < 4 or not parts[0].startswith("nt_qq") or
                parts[1] != "nt_data" or
                parts[2] not in {"Video", "Pic", "Audio", "File", "Record"}):
            raise ArchiveFileError("Media path is outside the NapCat media cache.")
        with path.open("rb") as source:
            return _stream(source, output, maximum)


def _stream(source: BinaryIO, output: BinaryIO, maximum: int) -> tuple:
    """Copy in chunks while enforcing the effective limit."""
    hasher = hashlib.sha256()
    size = 0
    while True:
        chunk = source.read(65536)
        if not chunk:
            break
        size += len(chunk)
        if size > maximum:
            raise ArchiveFileError("Media exceeds the configured size limit.")
        hasher.update(chunk)
        output.write(chunk)
    if not size:
        raise ArchiveFileError("Media is empty.")
    return hasher.hexdigest(), size


def _check_url(location: str) -> None:
    """Accept HTTPS only on known QQ media domains."""
    parsed = urlsplit(location)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ArchiveFileError("Media URL is not an approved HTTPS address.")
    if not any(host == domain or host.endswith("." + domain)
               for domain in ALLOWED_MEDIA_HOSTS):
        raise ArchiveFileError("Media URL host is not approved.")


def _safe_name(name: str, kind: str) -> str:
    """Preserve the original basename while removing path and control syntax."""
    basename = name.replace("\\", "/").split("/")[-1].strip()
    basename = re.sub(r'[\x00-\x1f<>:"|?*]', "_", basename).strip(". ")[:180]
    if not basename:
        basename = "media"
    if not Path(basename).suffix:
        basename += ".jpg" if kind == "image" else ".mp4" if kind == "video" else ".bin"
    return basename


def _file_hash(path: Path) -> str:
    """Compare an existing file before deciding whether a collision is real."""
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
