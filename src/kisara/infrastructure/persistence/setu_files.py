"""Bounded setu transfers with original-name, non-overwriting archive storage.

Archive file attachments retain their full basename in either layout. Only
different-content archive name conflicts receive a timestamp before the full
extension; images and other attachments retain the configured placement rules.
"""

import fcntl
import hashlib
import os
import re
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import BinaryIO, Dict, Optional, Protocol, Union
from urllib.parse import urlsplit

from kisara.config.setu import SetuConfig


CHINA_TIME = timezone(timedelta(hours=8))
ALLOWED_MEDIA_HOSTS = ("qq.com", "qpic.cn", "gtimg.cn", "multimedia.nt.qq.com.cn")
ARCHIVE_SUFFIXES = (
    ".tar.bz2", ".tar.zst", ".tar.gz", ".tar.xz", ".tbz2", ".tzst",
    ".tar", ".tgz", ".zip", ".7z", ".rar", ".txz",
)


class SetuFileError(ValueError):
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
            raise SetuFileError("Media redirect was rejected.")
        return redirected


class SetuFileSaver:
    """Transfer media using configured placement or archive original-name rules."""

    def __init__(self, config: SetuConfig) -> None:
        """Select one of the configured storage layouts."""
        self._config = config
        self._placement: FilePlacement = (
            DateOriginalPlacement() if config.save_mode == "date_original"
            else TimestampHashPlacement()
        )

    def save(self, source: Dict[str, object], location: Union[str, BinaryIO],
             timestamp: float, remaining_bytes: int) -> Dict[str, object]:
        """Stream one source to a temporary file and atomically place it."""
        if remaining_bytes <= 0:
            raise SetuFileError("Batch size limit reached.")
        original = str(source.get("name") or source.get("file") or "")
        kind = str(source.get("kind") or "file")
        archive_suffix = _archive_suffix(original) if source.get("kind") == "file" else ""
        if archive_suffix:
            _validate_archive_name(original)
        maximum = min(self._config.max_file_bytes, remaining_bytes)
        root = self._config.save_root
        root.mkdir(parents=True, exist_ok=True)
        temporary: Path
        with tempfile.NamedTemporaryFile(dir=str(root), prefix=".incoming-", delete=False) as output:
            temporary = Path(output.name)
            try:
                digest, size = self._copy(location, output, maximum,
                                          str(source.get("kind") or ""))
                os.chmod(temporary, 0o640)
            except Exception:
                temporary.unlink(missing_ok=True)
                raise
        try:
            if archive_suffix:
                destination = root / original
                if self._config.save_mode == "date_original":
                    day = datetime.fromtimestamp(timestamp, CHINA_TIME).strftime("%Y-%m-%d")
                    destination = root / day / original
                destination.parent.mkdir(parents=True, exist_ok=True)
                candidate = _publish_archive(temporary, destination, archive_suffix, digest, timestamp)
                return {"path": str(candidate), "size": size, "sha256": digest}
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

    def _copy(self, location: Union[str, BinaryIO], output: BinaryIO,
              maximum: int, kind: str) -> tuple:
        """Copy an internal stream, approved HTTPS URL, or mounted media cache."""
        if not isinstance(location, str):
            return _stream(location, output, maximum)
        parsed = urlsplit(location)
        if parsed.scheme == "https":
            _check_url(location)
            opener = urllib.request.build_opener(_SafeRedirect())
            with opener.open(location, timeout=20) as source:
                return _stream(source, output, maximum)
        if parsed.scheme:
            raise SetuFileError("Unsupported media location scheme.")
        root = self._config.local_media_root.resolve()
        path = Path(location).resolve()
        if root not in path.parents or not path.is_file():
            raise SetuFileError("Media path is outside the NapCat cache or unavailable.")
        relative = path.relative_to(root)
        parts = relative.parts
        qq_media = (len(parts) >= 4 and parts[0].startswith("nt_qq") and
                    parts[1] == "nt_data" and
                    parts[2] in {"Video", "Pic", "Audio", "File", "Record"})
        downloaded_file = (kind == "file" and len(parts) == 3 and
                           parts[:2] == ("NapCat", "temp"))
        if not qq_media and not downloaded_file:
            raise SetuFileError("Media path is outside the NapCat media cache.")
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
            raise SetuFileError("Media exceeds the configured size limit.")
        hasher.update(chunk)
        output.write(chunk)
    if not size:
        raise SetuFileError("Media is empty.")
    return hasher.hexdigest(), size


def _check_url(location: str) -> None:
    """Accept HTTPS only on known QQ media domains."""
    parsed = urlsplit(location)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise SetuFileError("Media URL is not an approved HTTPS address.")
    if not any(host == domain or host.endswith("." + domain)
               for domain in ALLOWED_MEDIA_HOSTS):
        raise SetuFileError("Media URL host is not approved.")


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


def _archive_suffix(name: str) -> str:
    """Return the complete recognized suffix while retaining its original case."""
    for suffix in ARCHIVE_SUFFIXES:
        if name.lower().endswith(suffix):
            return name[-len(suffix):]
    return ""


def _validate_archive_name(name: str) -> None:
    """Reject unsafe archive basenames instead of silently changing them."""
    if not name or name in {".", ".."} or re.search(r'[\x00-\x1f\x7f/\\<>:"|?*]', name):
        raise SetuFileError("Archive filename is missing or unsafe.")
    try:
        name.encode("utf-8")
    except UnicodeEncodeError as error:
        raise SetuFileError("Archive filename cannot be represented.") from error


def _matching_archive(destination: Path, suffix: str, digest: str) -> Optional[Path]:
    """Find identical content under the original or one of its stamped names."""
    stem = destination.name[:-len(suffix)]
    pattern = re.compile(re.escape(stem) + r"_\d{8}-\d{6}-\d{6}" + re.escape(suffix))
    for candidate in destination.parent.iterdir():
        if candidate.name != destination.name and not pattern.fullmatch(candidate.name):
            continue
        if not candidate.is_symlink() and candidate.is_file() and _file_hash(candidate) == digest:
            return candidate
    return None


def _publish_archive(temporary: Path, destination: Path, suffix: str,
                     digest: str, timestamp: float) -> Path:
    """Serialize archive reuse and publish complete bytes without replacement.

    Lock the existing directory on Linux/Unix so independent workers cannot
    create duplicate stamped copies of equal content. Hard-link publication
    also rejects an occupied destination if an unrelated writer races us.
    """
    descriptor = os.open(str(destination.parent), os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        matching = _matching_archive(destination, suffix, digest)
        if matching is not None:
            return matching
        candidate = destination
        stamp = datetime.fromtimestamp(timestamp, CHINA_TIME)
        stem = destination.name[:-len(suffix)]
        while True:
            try:
                os.link(str(temporary), str(candidate))
                return candidate
            except FileExistsError:
                matching = _matching_archive(destination, suffix, digest)
                if matching is not None:
                    return matching
                candidate = destination.with_name("{}_{}{}".format(
                    stem, stamp.strftime("%Y%m%d-%H%M%S-%f"), suffix,
                ))
                stamp += timedelta(microseconds=1)
    finally:
        os.close(descriptor)
