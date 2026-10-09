"""Opt-in, container-local preview lifecycle evidence with no private data."""

import json
import os
import tempfile
from pathlib import Path


def process_start(pid: int) -> str:
    """Read Linux process birth time so a reused PID cannot validate a stale marker."""
    return Path("/proc/{}/stat".format(pid)).read_text().rsplit(")", 1)[1].split()[19]


def publish(engine: str, ready: bool) -> None:
    """Atomically publish lifecycle state only for the fixed preview-local path."""
    if os.environ.get("KISARA_PREVIEW_READINESS") != "/tmp/kisara-preview-ready.json":
        return
    path = Path("/tmp/kisara-preview-ready.json")
    pid = os.getpid()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir="/tmp", prefix="kisara-preview-ready.", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({"pid": pid, "start": process_start(pid), "engine": engine,
                       "ready": ready}, stream)
        temporary.replace(path)
    except OSError:
        # A same-PID ready marker must never survive failed invalidation.
        try:
            path.unlink(missing_ok=True)
        except OSError:
            # The SDK can swallow SystemExit, so stop only this opted-in child.
            # Its marker may remain on disk, but the probe rejects its dead PID.
            os._exit(70)
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
