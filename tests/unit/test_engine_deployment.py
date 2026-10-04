"""Targeted engine lifecycle and Compose credential isolation without Docker effects."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def repository(tmp_path: Path, profiles: str) -> tuple:
    (tmp_path / "deploy").mkdir()
    for name in ("engines.sh", "onebot.sh", "compose.yaml"):
        shutil.copy2(ROOT / "deploy" / name, tmp_path / "deploy" / name)
    for name in ("deploy.sh", "start.sh", "preview.sh"):
        shutil.copy2(ROOT / name, tmp_path / name)
    (tmp_path / ".env").write_text("COMPOSE_PROFILES={}\n".format(profiles))
    binary = tmp_path / "bin"
    binary.mkdir()
    docker = binary / "docker"
    docker.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ["CALL_LOG"], "a") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\\n")
if "OWNERSHIP_LOG" in os.environ:
    with open(os.environ["OWNERSHIP_LOG"], "a") as stream:
        stream.write(json.dumps({name: os.environ.get(name) for name in
                                ("KISARA_HOST_GID", "KISARA_SETU_GID", "ONEBOT_SETU_GID")}) + "\\n")
''')
    docker.chmod(0o755)
    env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"], CALL_LOG=str(tmp_path / "calls.jsonl"))
    env.pop("KISARA_ENGINE", None)
    env.pop("COMPOSE_PROFILES", None)
    return env, tmp_path / "calls.jsonl"


def calls(path: Path) -> list:
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


@pytest.mark.parametrize("profiles,services", [("onebot", ["napcat", "kisara"]),
                                              ("telegram", ["telegram"]),
                                              ("onebot,telegram", ["napcat", "kisara", "telegram"]),
                                              ("official", ["official"]),
                                              ("telegram,music", ["telegram", "music"])])
def test_selected_engines_start_only_targets(tmp_path: Path, profiles: str, services: list) -> None:
    env, log = repository(tmp_path, profiles)
    subprocess.run([str(tmp_path / "deploy.sh")], env=env, check=True)
    operation = calls(log)[-1]
    assert operation[-len(services):] == services
    assert "--detach" in operation and "--build" in operation
    if profiles == "telegram":
        assert not (tmp_path / "data/napcat").exists()
        assert not any("napcat" in call or "kisara" in call[call.index("stop"):] for call in calls(log) if "stop" in call)


@pytest.mark.parametrize("action", ["down", "restart", "logs", "ps"])
def test_telegram_lifecycle_does_not_touch_qq(tmp_path: Path, action: str) -> None:
    env, log = repository(tmp_path, "onebot,telegram")
    subprocess.run([str(tmp_path / "deploy.sh"), action, "telegram"], env=env, check=True)
    operation = calls(log)[-1]
    assert operation[-1] == "telegram"
    assert "napcat" not in operation and "kisara-dev" not in operation
    assert "down" not in operation


def test_explicit_whole_project_down(tmp_path: Path) -> None:
    env, log = repository(tmp_path, "telegram")
    subprocess.run([str(tmp_path / "deploy.sh"), "down-all"], env=env, check=True)
    assert calls(log)[-1][-1] == "down"


def test_conflicting_qq_ownership_rejected(tmp_path: Path) -> None:
    env, log = repository(tmp_path, "onebot,onebot-dev")
    result = subprocess.run([str(tmp_path / "deploy.sh")], env=env, capture_output=True, text=True)
    assert result.returncode == 2 and "cannot own" in result.stderr
    assert calls(log) == []


def test_start_explicit_env_overrides_profiles(tmp_path: Path) -> None:
    env, log = repository(tmp_path, "onebot,telegram")
    env["KISARA_ENGINE"] = "telegram"
    subprocess.run([str(tmp_path / "start.sh")], env=env, check=True, stdin=subprocess.DEVNULL)
    assert calls(log)[-1][-1] == "telegram"


def test_start_no_argument_uses_env_file_selection(tmp_path: Path) -> None:
    env, log = repository(tmp_path, "telegram")
    subprocess.run([str(tmp_path / "start.sh")], env=env, check=True, stdin=subprocess.DEVNULL)
    assert calls(log)[-1][-1] == "telegram"


@pytest.mark.parametrize("value", ['telegram   ', 'telegram # selected engine',
                                   '"telegram" # selected engine', "'telegram'   "])
def test_dotenv_profile_comments_and_spaces(tmp_path: Path, value: str) -> None:
    env, log = repository(tmp_path, value)
    subprocess.run([str(tmp_path / "start.sh")], env=env, check=True, stdin=subprocess.DEVNULL)
    assert calls(log)[-1][-1] == "telegram"
    assert not (tmp_path / "data/napcat").exists()


def test_legacy_onebot_stop_scoped(tmp_path: Path) -> None:
    env, log = repository(tmp_path, "onebot,telegram")
    subprocess.run([str(tmp_path / "deploy/onebot.sh"), "down"], env=env, check=True)
    assert calls(log)[-1][-4:] == ["stop", "kisara", "kisara-dev", "napcat"]


def test_config_profile_and_secret_mapping_contract() -> None:
    text = (ROOT / "deploy/compose.yaml").read_text()
    telegram = text.split("  telegram:\n", 1)[1].split("  official:\n", 1)[0]
    official = text.split("  official:\n", 1)[1].split("\nnetworks:\n", 1)[0]
    assert "TELEGRAM_BOT_TOKEN:" in telegram and "ONEBOT_ACCESS_TOKEN:" not in telegram and "AppSecret:" not in telegram
    assert "telegram_state:/app/state" in telegram and "../config/telegram:/app/config:ro" in telegram
    assert "AppSecret:" in official and "TELEGRAM_BOT_TOKEN:" not in official and "ONEBOT_ACCESS_TOKEN:" not in official
    assert "kisara_state:/app/state" in text and "../data/napcat/QQ:/app/.config/QQ" in text
    assert "env_file:" not in text


@pytest.mark.parametrize("entrypoint", ["deploy.sh", "deploy/onebot.sh"])
def test_ownership_fallback_does_not_mask_dotenv_gid(tmp_path: Path, entrypoint: str) -> None:
    """Host defaults use a separate fallback, leaving dotenv aliases available."""
    env, log = repository(tmp_path, "onebot")
    env.pop("KISARA_SETU_GID", None)
    env.pop("ONEBOT_SETU_GID", None)
    ownership_log = tmp_path / "ownership.jsonl"
    env["OWNERSHIP_LOG"] = str(ownership_log)
    with (tmp_path / ".env").open("a") as stream:
        stream.write("ONEBOT_SETU_GID=2345\nKISARA_SETU_GID=3456\n")
    subprocess.run([str(tmp_path / entrypoint), "up"], env=env, check=True)
    assert calls(log)[-1][-2:] == ["napcat", "kisara"]
    exported = json.loads(ownership_log.read_text().splitlines()[-1])
    assert exported["KISARA_HOST_GID"] == str(os.getgid())
    assert exported["KISARA_SETU_GID"] is None
    assert exported["ONEBOT_SETU_GID"] is None
