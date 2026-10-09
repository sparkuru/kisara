"""Validate the current preview child's marker, PID, and process identity."""

import json
import pathlib
import socket
import sys


def ready(engine: str, path: pathlib.Path = pathlib.Path("/tmp/kisara-preview-ready.json")) -> bool:
    """Reject stopped, stale, mismatched, dead, or watcher-only processes."""
    try:
        marker = json.loads(path.read_text())
        pid = marker["pid"]
        if not isinstance(pid, int) or pid < 1 or marker["engine"] != engine or marker["ready"] is not True:
            return False
        process = pathlib.Path("/proc/{}".format(pid))
        stat = process.joinpath("stat").read_text().rsplit(")", 1)[1].split()
        command = process.joinpath("cmdline").read_bytes().split(b"\0")
        return (stat[0] != "Z" and stat[19] == marker["start"] and
                b"-m" in command and b"kisara" in command)
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return False


def listeners() -> list[str]:
    """Inspect TCP listeners; embedded Docker DNS is runtime infrastructure."""
    result = []
    for name, family in (("tcp", socket.AF_INET), ("tcp6", socket.AF_INET6)):
        path = pathlib.Path("/proc/net") / name
        if not path.exists():
            continue
        for row in path.read_text().splitlines()[1:]:
            fields = row.split()
            if fields[3] != "0A":
                continue
            address, port = fields[1].split(":")
            words = [address[index:index + 8] for index in range(0, len(address), 8)]
            raw = b"".join(bytes.fromhex(word)[::-1] for word in words)
            host = socket.inet_ntop(family, raw)
            if host == "127.0.0.11":
                continue
            if family == socket.AF_INET6:
                host = "[{}]".format(host)
            result.append("{}|{}".format(host, int(port, 16)))
    return list(dict.fromkeys(result))


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "listeners":
        try:
            sys.stdout.write("\n".join(listeners()))
        except (OSError, ValueError, IndexError):
            sys.exit(1)
        sys.exit(0)
    sys.exit(0 if len(sys.argv) == 2 and ready(sys.argv[1]) else 1)
