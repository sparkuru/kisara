"""OneBot video tooling, spool wiring and safe preview diagnostics."""

import importlib.util
import os
import re
import subprocess
from pathlib import Path

import pytest

from kisara.bot.contracts import MessageEvent, MessageSegment
from kisara.bot.dispatcher import Dispatcher


ROOT = Path(__file__).resolve().parents[2]


def test_effective_native_export_help_is_onebot_only_and_switch_owned() -> None:
    active = Dispatcher(frozenset({"123"}), False, frozenset(), feature_switches={"export_video": True})
    inactive = Dispatcher(frozenset({"123"}), False, frozenset())
    assert "/export-video" in active.router.help("onebot")
    assert "/export-video" not in inactive.router.help("onebot")
    assert "/export-video" not in active.router.help("telegram") + active.router.help("official")
    event = MessageEvent("onebot", "test", "1", "private", "456", "456",
                         (MessageSegment("text", {"text": "/export-video"}),), {})
    assert not active.authorize_native(event, "export_video")


def test_preview_redacts_sessdata_from_real_filter_pipeline(tmp_path: Path) -> None:
    script = '''source "$1/deploy/preview-runtime.sh"
preview_secrets=()
preview_filters=()
preview_redact_values
printf '%s\n' 'session fixture-private-session remains private' | preview_replace_secrets | sed -E "${preview_filters[@]}"
'''
    env = dict(os.environ, ONEBOT_BILIBILI_SESSDATA="fixture-private-session")
    result = subprocess.run(["bash", "-c", script, "bash", str(ROOT)], env=env,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0 and "[redacted]" in result.stdout
    assert "fixture-private-session" not in result.stdout + result.stderr


def test_video_preview_dependency_closure_and_tool_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = importlib.util.spec_from_file_location("video_preview_dependencies", ROOT / "deploy/preview-deps.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.requirements("video") == ["pillow", "websockets", "yt-dlp"]
    constraints = ROOT / "deploy/preview-constraints-py312.txt"
    pins = module.pins(constraints)
    monkeypatch.setattr(module.importlib.metadata, "version", lambda name: pins[name])
    monkeypatch.setattr(module.importlib, "import_module", lambda name: object())
    monkeypatch.setattr(module.shutil, "which", lambda name: None if name == "ffprobe" else "/bin/" + name)
    assert not module.check("video", constraints)
    monkeypatch.setattr(module.shutil, "which", lambda name: "/bin/" + name)
    assert module.check("video", constraints)


def test_compose_spool_is_dedicated_and_cookie_is_only_in_onebot() -> None:
    text = (ROOT / "deploy/compose.yaml").read_text()
    for name in ("kisara", "kisara-dev"):
        section = re.split(r"\n  [a-zA-Z0-9_-]+:\n", text.split("\n  " + name + ":\n", 1)[1], 1)[0]
        assert "KISARA_EXTRA: video" in section
        assert "onebot_export:/tmp/kisara/export" in section
        assert "KISARA_BILIBILI_SESSDATA: ${ONEBOT_BILIBILI_SESSDATA-}" in section
    for name in ("telegram", "official"):
        section = re.split(r"\n  [a-zA-Z0-9_-]+:\n", text.split("\n  " + name + ":\n", 1)[1], 1)[0]
        assert "SESSDATA" not in section and "onebot_export" not in section
    napcat = text.split("\n  napcat:\n", 1)[1].split("\n  music:\n", 1)[0]
    assert "source: onebot_export" in napcat and "read_only: true" in napcat and "nocopy: true" in napcat
    assert "kisara_state:/app/state" not in napcat
