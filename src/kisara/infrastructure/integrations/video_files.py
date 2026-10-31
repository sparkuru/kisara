"""Owned temporary transport jobs shared read-only with the OneBot gateway."""

import os
import re
import shutil
import stat
import time
import uuid
from pathlib import Path

from kisara.infrastructure.integrations.bilibili import VideoExportError


WORKSPACE_BYTES = 2 * 1024 ** 3
JOB_GRACE_SECONDS = 3600


def directory_bytes(root: Path) -> int:
    """Count bounded regular files, rejecting links and unexpected directory trees."""
    total = 0
    count = 0
    for path in root.rglob("*"):
        count += 1
        info = path.lstat()
        if count > 1024 or stat.S_ISLNK(info.st_mode):
            raise VideoExportError("unsafe_spool")
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
        elif not stat.S_ISDIR(info.st_mode):
            raise VideoExportError("unsafe_spool")
    return total


class ExportSpool:
    """Create and prune only application-owned transport directories."""

    def __init__(self, root: Path = Path("/tmp/kisara/export")) -> None:
        """Defer filesystem access until an authorized export needs it."""
        self.root = root

    def prepare(self) -> None:
        """Reject unsafe roots, prune expired jobs and preserve all unknown data."""
        absolute = self.root.absolute()
        for parent in (absolute,) + tuple(absolute.parents):
            if parent.is_symlink():
                raise VideoExportError("unsafe_spool")
        absolute.mkdir(parents=True, exist_ok=True, mode=0o755)
        info = absolute.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o022 or not absolute.is_dir():
            raise VideoExportError("unsafe_spool")
        for path in absolute.iterdir():
            if self.owned(path) and time.time() - (path / ".owned").stat().st_mtime > JOB_GRACE_SECONDS:
                self.remove(path)
        if directory_bytes(absolute) >= WORKSPACE_BYTES:
            raise VideoExportError("workspace_limit")

    def create(self) -> Path:
        """Allocate a unique directory containing only this request's files."""
        self.prepare()
        job = self.root / ("job-" + uuid.uuid4().hex)
        job.mkdir(mode=0o755)
        job.chmod(0o755)
        (job / ".owned").write_text("kisara-export-v1")
        return job

    def owned(self, job: Path) -> bool:
        """Recognize an exact owned directory without following marker links."""
        marker = job / ".owned"
        try:
            return (job.parent.absolute() == self.root.absolute()
                    and re.fullmatch(r"job-[0-9a-f]{32}", job.name) is not None
                    and not job.is_symlink() and job.is_dir() and job.stat().st_uid == os.getuid()
                    and not marker.is_symlink() and marker.is_file()
                    and marker.stat().st_uid == os.getuid() and marker.stat().st_size == 16
                    and marker.read_text() == "kisara-export-v1")
        except (OSError, UnicodeError):
            return False

    def remove(self, job: Path) -> None:
        """Delete only a verified owned job, never an arbitrary caller path."""
        if not self.owned(job):
            raise VideoExportError("unsafe_spool")
        directory_bytes(job)
        shutil.rmtree(job)

    def retain(self, job: Path) -> None:
        """Start a grace period for a send that may still be using the video."""
        if not self.owned(job):
            raise VideoExportError("unsafe_spool")
        os.utime(job / ".owned", None)
