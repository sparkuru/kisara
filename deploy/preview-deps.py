"""Check or install the observed, pinned preview runtime without building Kisara.

Run inside the existing Python 3.12 wrapper/image. Source loads through PYTHONPATH;
no build backend, dev extra, runtime credential injection, or port publication.
"""

import importlib
import importlib.metadata
import pathlib
import subprocess
import sys


def requirements(extra: str) -> list[str]:
    """Select the runtime closure observed in the installed distribution metadata."""
    groups = {
        "": ["pillow", "websockets"],
        "official": ["qq-botpy", "aiohttp", "PyYAML", "APScheduler", "tzlocal",
                     "aiohappyeyeballs", "aiosignal", "attrs", "frozenlist",
                     "multidict", "propcache", "typing_extensions", "yarl", "idna"],
        "telegram": ["python-telegram-bot", "httpx", "anyio", "certifi", "httpcore",
                     "h11", "idna", "typing_extensions"],
    }
    if extra not in groups:
        raise ValueError("Unsupported preview extra")
    return groups[""] + (groups[extra] if extra else [])


def pins(path: pathlib.Path) -> dict[str, str]:
    """Read exact version constraints, rejecting ambiguous entries."""
    result = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        name, version = line.split("==")
        result[name.lower().replace("_", "-")] = version
    return result


def check(extra: str, constraints: pathlib.Path) -> bool:
    """Require every selected exact distribution and its adapter entry imports."""
    versions = pins(constraints)
    try:
        for name in requirements(extra):
            if importlib.metadata.version(name) != versions[name.lower().replace("_", "-")]:
                return False
        for module in ["PIL", "websockets"] + ({"official": ["botpy"], "telegram": ["telegram"]}.get(extra, [])):
            importlib.import_module(module)
    except (ImportError, KeyError):
        return False
    return True


def main() -> int:
    """Use check/install commands internally; preparation output is captured by Bash."""
    if sys.version_info[:2] != (3, 12) or len(sys.argv) not in (3, 4):
        return 2
    action, extra = sys.argv[1:3]
    constraints = pathlib.Path(sys.argv[3]) if len(sys.argv) == 4 else pathlib.Path(__file__).with_name("preview-constraints-py312.txt")
    if action == "check":
        return 0 if check(extra, constraints) else 1
    if action not in {"install", "install-system"}:
        return 2
    versions = pins(constraints)
    selected = ["{}=={}".format(name, versions[name.lower().replace("_", "-")]) for name in requirements(extra)]
    # The complete selected closure is pinned; pip does not resolve extra downloads.
    user_flags = ["--user"] if action == "install" else []
    result = subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", *user_flags,
                             "--constraint", str(constraints), *selected], check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
