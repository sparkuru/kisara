"""Flat Telegram archive naming and bounded, no-replace Linux publication.

Only configured local Bot API cache paths are readable. Complete temporary
bytes are synced before a hard-link publication under an archive directory
lock. The caller persists the selected path/hash before the link and records
completion afterward, enabling reconciliation after a crash in that interval.
"""

from dataclasses import dataclass
import fcntl
import hashlib
import mimetypes
import os
from pathlib import Path
import re
import stat
import tempfile
import threading
import time
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from kisara.config.tgsetu import TgSetuConfig


class TgSetuFileError(ValueError):
    """A controlled naming, source or transfer policy rejection."""


class TgSetuCancelled(TgSetuFileError):
    """An owned worker stopped before publishing a file."""


@dataclass(frozen=True)
class PreparedFile:
    """Complete temporary content on the archive filesystem."""

    path: Path
    sha256: str
    size: int


def _clean(value: str) -> str:
    """Normalize whitespace and unsafe path/control characters."""
    value = re.sub(r'[\x00-\x1f\x7f/\\<>:"|?*]', " ", value)
    return re.sub(r"\s+", " ", value).strip(". ")


def media_extension(media: Mapping[str, Any]) -> Tuple[str, str]:
    """Split the original basename, retaining recognized compound suffixes."""
    name = _clean(str(media.get("name") or ""))
    compounds = (".tar.bz2", ".tar.zst", ".tar.gz", ".tar.xz", ".tar.lz4")
    suffix = next((name[-len(item):] for item in compounds if name.lower().endswith(item)), "")
    suffix = suffix or Path(name).suffix
    if suffix:
        return name[:-len(suffix)], suffix
    mime = str(media.get("mime_type") or "").lower()
    fixed = {"image/jpeg": ".jpg", "image/png": ".png", "video/mp4": ".mp4",
             "video/quicktime": ".mov", "application/octet-stream": ".bin"}
    suffix = fixed.get(mime) or mimetypes.guess_extension(mime) or ""
    suffix = suffix or (".jpg" if media.get("kind") == "image" else ".bin")
    return name, suffix


def naming_plan(media: Mapping[str, Any], title: str, tags: Tuple[str, ...],
                fallback: str, ordinal: int = 0) -> Dict[str, Any]:
    """Build immutable components; descriptions never supply an extension."""
    original, extension = media_extension(media)
    title = _clean(title)
    normalized_tags = list(dict.fromkeys(_clean(tag.lstrip("#")) for tag in tags))
    normalized_tags = [tag for tag in normalized_tags if tag]
    if media.get("kind") == "file" and original:
        stem = original + ("-" + title if title else "")
    else:
        stem = title or original or fallback
    plan = {"stem": stem, "extension": extension, "tags": normalized_tags,
            "ordinal": ordinal}
    plan["name"] = render_name(plan)
    return plan


def render_name(plan: Mapping[str, Any], conflict: str = "", maximum: int = 255) -> str:
    """Fit UTF-8 NAME_MAX while retaining tags, ordinals and the full suffix."""
    stem = str(plan["stem"])
    ordinal = "-{:03d}".format(int(plan.get("ordinal") or 0)) if plan.get("ordinal") else ""
    tags = "".join("-@" + str(tag) for tag in plan.get("tags", []))
    tail = ordinal + ("-" + conflict if conflict else "") + tags + str(plan["extension"])
    # Reserve a stable content-conflict suffix even for the initial name.
    reserve = 40 if not conflict else 0
    available = maximum - len(tail.encode("utf-8")) - reserve
    if available < 18:
        raise TgSetuFileError("Naming suffixes exceed the filesystem filename limit.")
    if len(stem.encode("utf-8")) > available:
        digest = hashlib.sha256((stem + tail).encode("utf-8")).hexdigest()[:12]
        stem = stem.encode("utf-8")[:available - 13].decode("utf-8", "ignore").rstrip() + "-" + digest
    result = stem + tail
    if not result or result in {".", ".."} or Path(result).name != result:
        raise TgSetuFileError("Invalid archive filename.")
    return result


def _check_cancel(stop: Optional[threading.Event]) -> None:
    """Cooperatively cancel owned blocking file work."""
    if stop is not None and stop.is_set():
        raise TgSetuCancelled("Archive worker stopped before publication.")


def _open_cache_file(path: Path, root: Path) -> int:
    """Open relative components without symlinks or a path-validation race."""
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise TgSetuFileError("Media path is outside the local Bot API cache.") from error
    if not path.is_absolute() or not relative.parts or any(part in {".", ".."} for part in relative.parts):
        raise TgSetuFileError("Media path is outside the local Bot API cache.")
    descriptor = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        source = os.open(relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=descriptor)
        if not stat.S_ISREG(os.fstat(source).st_mode):
            os.close(source)
            raise TgSetuFileError("Media source is not a regular file.")
        return source
    finally:
        os.close(descriptor)


def file_matches(path: Path, digest: str, size: int,
                 stop: Optional[threading.Event] = None) -> bool:
    """Verify complete, regular existing bytes without following a symlink."""
    try:
        descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except (FileNotFoundError, OSError):
        return False
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_size != size:
        os.close(descriptor)
        return False
    with os.fdopen(descriptor, "rb") as stream:
        hasher = hashlib.sha256()
        copied = 0
        while True:
            _check_cancel(stop)
            chunk = stream.read(65536)
            if not chunk:
                break
            copied += len(chunk)
            if copied > size:
                return False
            hasher.update(chunk)
    return hasher.hexdigest() == digest


class TgSetuFileSaver:
    """Copy and publish individual files under the owning worker's lifetime."""

    def __init__(self, config: TgSetuConfig) -> None:
        """Keep archive and cache policy without creating directories."""
        self._config = config

    def prepare(self, source: Path, remaining: int,
                stop: Optional[threading.Event] = None) -> PreparedFile:
        """Stream at most the effective cap, hashing/syncing complete bytes."""
        maximum = min(self._config.max_file_bytes, remaining)
        if maximum <= 0:
            raise TgSetuFileError("Logical message size limit reached.")
        _check_cancel(stop)
        descriptor = _open_cache_file(source, self._config.cache_root.resolve())
        root = self._config.save_root
        temporary: Optional[Path] = None
        try:
            root.mkdir(parents=True, exist_ok=True)
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = -1
                if os.fstat(stream.fileno()).st_size > maximum:
                    raise TgSetuFileError("Media exceeds the configured size limit.")
                with tempfile.NamedTemporaryFile(dir=str(root), prefix=".tgsetu-incoming-", delete=False) as output:
                    temporary = Path(output.name)
                    hasher, size = hashlib.sha256(), 0
                    while True:
                        _check_cancel(stop)
                        chunk = stream.read(65536)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > maximum:
                            raise TgSetuFileError("Media exceeds the configured size limit.")
                        output.write(chunk)
                        hasher.update(chunk)
                    if not size:
                        raise TgSetuFileError("Media is empty.")
                    output.flush()
                    os.fchmod(output.fileno(), 0o640)
                    os.fsync(output.fileno())
            return PreparedFile(temporary, hasher.hexdigest(), size)
        except BaseException:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def publish(self, prepared: PreparedFile, plan: Mapping[str, Any], timestamp: float,
                persist_intent: Callable[[str, str, int], None],
                candidate_name: str = "", stop: Optional[threading.Event] = None) -> Dict[str, Any]:
        """Persist the final candidate under flock, then link without replacement."""
        root = self._config.save_root
        descriptor = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
        conflict = prepared.sha256[:16]
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            candidates = [candidate_name] if candidate_name else []
            candidates.extend([str(plan["name"]), render_name(plan, conflict)])
            candidates = list(dict.fromkeys(candidates))
            for attempt in range(1024):
                _check_cancel(stop)
                name = candidates[attempt] if attempt < len(candidates) else render_name(
                    plan, conflict + "-" + str(attempt))
                destination = root / name
                if Path(name).name != name:
                    raise TgSetuFileError("Invalid stored candidate name.")
                if file_matches(destination, prepared.sha256, prepared.size, stop):
                    persist_intent(name, prepared.sha256, prepared.size)
                    os.fsync(descriptor)
                    return {"path": str(destination), "size": prepared.size, "sha256": prepared.sha256}
                persist_intent(name, prepared.sha256, prepared.size)
                _check_cancel(stop)
                try:
                    os.link(str(prepared.path), str(destination))
                except FileExistsError:
                    continue
                os.fsync(descriptor)
                return {"path": str(destination), "size": prepared.size, "sha256": prepared.sha256}
            raise TgSetuFileError("Archive filename collision limit reached.")
        finally:
            os.close(descriptor)
            prepared.path.unlink(missing_ok=True)

    def reconcile(self, name: str, digest: str, size: int,
                  stop: Optional[threading.Event] = None) -> Optional[Dict[str, Any]]:
        """Recover an already published complete candidate before downloading."""
        if not name or Path(name).name != name:
            return None
        root = self._config.save_root
        if not root.exists():
            return None
        descriptor = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            candidate = root / name
            if file_matches(candidate, digest, size, stop):
                os.fsync(descriptor)
                return {"path": str(candidate), "size": size, "sha256": digest}
            return None
        finally:
            os.close(descriptor)

    def clean_stale_temporary(self, now: Optional[float] = None) -> None:
        """Remove only owned, day-old private transfer remnants, never archives."""
        root = self._config.save_root
        if not root.is_dir():
            return
        cutoff = (time.time() if now is None else now) - 86400
        for candidate in root.glob(".tgsetu-incoming-*"):
            info = candidate.lstat()
            if stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_mtime < cutoff:
                candidate.unlink(missing_ok=True)
