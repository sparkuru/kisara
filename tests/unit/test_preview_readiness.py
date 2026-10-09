"""Opt-in readiness evidence cannot survive disconnect, fatal errors or dead PIDs."""

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from kisara.bot import preview_readiness
from kisara.config import Settings


ROOT = Path(__file__).resolve().parents[2]


def test_publisher_disabled_and_atomic_private_opt_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Disabled mode performs no filesystem operations; enabled mode carries no secrets."""
    monkeypatch.delenv("KISARA_PREVIEW_READINESS", raising=False)
    monkeypatch.setattr(preview_readiness, "process_start", lambda pid: "birth")
    target = tmp_path / "ready.json"
    monkeypatch.setattr(preview_readiness, "Path", lambda name: target if str(name) == "/tmp/kisara-preview-ready.json" else Path(name))
    preview_readiness.publish("onebot", True)
    assert not target.exists()
    monkeypatch.setenv("KISARA_PREVIEW_READINESS", "/tmp/kisara-preview-ready.json")
    preview_readiness.publish("onebot", False)
    assert json.loads(target.read_text()) == {"pid": os.getpid(), "start": "birth", "engine": "onebot", "ready": False}
    preview_readiness.publish("onebot", True)
    assert json.loads(target.read_text())["ready"] is True and target.stat().st_mode & 0o077 == 0


def test_probe_matches_live_child_birth_and_rejects_after_exit(tmp_path: Path) -> None:
    """A ready child validates; the same marker cannot validate a dead child or watcher."""
    spec = importlib.util.spec_from_file_location("probe", ROOT / "deploy/preview-probe.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    marker = tmp_path / "marker.json"
    (tmp_path / "kisara.py").write_text('''import json, os, pathlib, time
pid = os.getpid()
start = pathlib.Path("/proc/%s/stat" % pid).read_text().rsplit(")",1)[1].split()[19]
pathlib.Path(os.environ["FIXTURE_MARKER"]).write_text(json.dumps({"pid":pid,"start":start,"engine":"onebot","ready":True}))
time.sleep(30)
''')
    child = subprocess.Popen([sys.executable, "-m", "kisara"], cwd=tmp_path,
                             env=dict(os.environ, PYTHONPATH=str(tmp_path), FIXTURE_MARKER=str(marker)))
    try:
        for _ in range(100):
            if marker.exists(): break
            time.sleep(0.01)
        assert probe.ready("onebot", marker) is True
        assert probe.ready("telegram", marker) is False
    finally:
        child.terminate()
        child.wait(timeout=3)
    assert probe.ready("onebot", marker) is False


def test_telegram_poll_failure_and_recovery_clear_fatal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Transient polling failure clears readiness; only nonfatal recovery restores it."""
    pytest.importorskip("telegram")
    from telegram.error import NetworkError
    from kisara.bot.adapters import telegram
    seen = []
    monkeypatch.setattr(telegram, "publish_readiness", lambda engine, ready: seen.append((engine, ready)))
    adapter = telegram.TelegramAdapter(Settings(engine="telegram", instance_id="fixture", allowed_users=frozenset(),
                                                groups_enabled=False, allowed_groups=frozenset(), telegram_token="fixture"), lambda event: None)
    adapter._status = "running"
    adapter._polling_succeeded()
    adapter._polling_error(NetworkError("fixture"))
    adapter._polling_succeeded()
    adapter._fatal_polling_error()
    adapter._polling_succeeded()
    assert seen == [("telegram", True), ("telegram", False), ("telegram", True), ("telegram", False)]


def test_telegram_startup_does_not_overwrite_early_poll_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Application startup alone cannot claim readiness after an early failed poll."""
    pytest.importorskip("telegram")
    from telegram.error import NetworkError
    from kisara.bot.adapters import telegram
    seen = []
    monkeypatch.setattr(telegram, "publish_readiness", lambda engine, ready: seen.append(ready))
    monkeypatch.setattr(telegram, "ManagedPollingBot", lambda *args: SimpleNamespace())

    async def run() -> None:
        started = asyncio.Event()
        adapter = telegram.TelegramAdapter(Settings(engine="telegram", instance_id="fixture", allowed_users=frozenset(),
                                                    groups_enabled=False, allowed_groups=frozenset(), telegram_token="fixture"), lambda event: None)

        async def start_polling(**kwargs: object) -> None:
            kwargs["error_callback"](NetworkError("fixture startup poll unavailable"))

        async def start() -> None:
            started.set()

        app = SimpleNamespace(initialize=AsyncMock(), start=start,
                              updater=SimpleNamespace(start_polling=start_polling),
                              add_handler=lambda *args: None, add_error_handler=lambda *args: None)
        builder = SimpleNamespace(bot=lambda value: builder, update_queue=lambda value: builder,
                                  concurrent_updates=lambda value: builder, build=lambda: app)
        monkeypatch.setattr(telegram, "Application", SimpleNamespace(builder=lambda: builder))
        monkeypatch.setattr(adapter, "_shutdown", AsyncMock())
        task = asyncio.create_task(adapter._run())
        try:
            await asyncio.wait_for(started.wait(), 1)
            assert adapter.status == "running" and seen == [False]
            adapter._polling_succeeded()
            assert seen == [False, True]
        finally:
            adapter.close()
            await asyncio.wait_for(task, 1)
        assert seen[-1] is False

    asyncio.run(run())


def test_official_gateway_return_clears_ready_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    """The installed SDK's public connection seam clears every returning session."""
    botpy = pytest.importorskip("botpy")
    from kisara.bot.adapters import official
    seen = []
    monkeypatch.setattr(official, "publish_readiness", lambda engine, ready: seen.append((engine, ready)))
    monkeypatch.setattr(botpy.Client, "bot_connect", AsyncMock())
    async def run() -> None:
        adapter = official.OfficialAdapter(Settings(engine="official", instance_id="fixture", allowed_users=frozenset(),
                                                    groups_enabled=False, allowed_groups=frozenset(), app_id="fixture", app_secret="fixture"), lambda event: None)
        await adapter.bot_connect(SimpleNamespace())
        assert seen == [("official", False), ("official", False)]
        adapter.close()

    asyncio.run(run())
    assert seen[-1] == ("official", False)


def test_existing_ready_replace_and_unlink_failure_stop_only_preview_child(tmp_path: Path) -> None:
    """An unremovable old ready marker cannot keep a live child falsely ready."""
    marker = tmp_path / "ready.json"
    package = tmp_path / "kisara"
    package.mkdir()
    (package / "__init__.py").write_text("")
    source = ROOT / "src/kisara/bot/preview_readiness.py"
    (package / "__main__.py").write_text('''import importlib.util, os, pathlib
spec = importlib.util.spec_from_file_location("instrumentation", os.environ["READINESS_SOURCE"])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
marker = pathlib.Path(os.environ["FIXTURE_MARKER"])
module.Path = lambda name: marker if str(name) == "/tmp/kisara-preview-ready.json" else pathlib.Path(name)
os.environ["KISARA_PREVIEW_READINESS"] = "/tmp/kisara-preview-ready.json"
module.publish("onebot", True)
def fail(*args, **kwargs): raise OSError("fixture locked filesystem")
pathlib.Path.replace = fail
original_unlink = pathlib.Path.unlink
def unlink(path, *args, **kwargs):
    if path == marker: fail()
    original_unlink(path, *args, **kwargs)
pathlib.Path.unlink = unlink
module.publish("onebot", False)
raise RuntimeError("failed invalidation must stop the opted-in child")
''')
    child = subprocess.run([sys.executable, "-m", "kisara"], cwd=tmp_path,
                           env=dict(os.environ, PYTHONPATH=str(tmp_path), FIXTURE_MARKER=str(marker), READINESS_SOURCE=str(source)),
                           capture_output=True, text=True)
    assert child.returncode == 70 and child.stdout == "" and child.stderr == ""
    assert json.loads(marker.read_text())["ready"] is True
    spec = importlib.util.spec_from_file_location("probe", ROOT / "deploy/preview-probe.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    assert probe.ready("onebot", marker) is False


def test_tcp_listener_decoder_preserves_ipv4_ipv6_scope_and_excludes_dns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Linux socket fixtures establish byte order, listening state and scope facts."""
    spec = importlib.util.spec_from_file_location("listener_probe", ROOT / "deploy/preview-probe.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    (tmp_path / "tcp").write_text(
        "header\n0: 0100007F:1F90 00000000:0000 0A\n"
        "1: 00000000:2328 00000000:0000 0A\n"
        "2: 0B00007F:0035 00000000:0000 0A\n"
        "3: 0100007F:1F90 00000000:0000 0A\n"
        "4: 0100007F:1234 00000000:0000 01\n")
    (tmp_path / "tcp6").write_text(
        "header\n0: 00000000000000000000000001000000:1F91 00000000:0000 0A\n"
        "1: B80D0120000000000000000010000000:1F92 00000000:0000 0A\n")
    monkeypatch.setattr(probe, "pathlib", SimpleNamespace(Path=lambda value: tmp_path))
    assert probe.listeners() == ["127.0.0.1|8080", "0.0.0.0|9000", "[::1]|8081", "[2001:db8::10]|8082"]
