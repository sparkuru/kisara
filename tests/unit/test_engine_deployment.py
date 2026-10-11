"""Targeted engine lifecycle and Compose credential isolation without Docker effects."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest


ROOT = Path(__file__).resolve().parents[2]


def repository(tmp_path: Path, profiles: str) -> tuple:
    (tmp_path / "deploy").mkdir()
    for name in ("engines.sh", "onebot.sh", "compose.yaml", "dotenv.sh"):
        shutil.copy2(ROOT / "deploy" / name, tmp_path / "deploy" / name)
    shutil.copy2(ROOT / "kisara.sh", tmp_path / "kisara.sh")
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
                                ("KISARA_HOST_GID", "KISARA_SETU_GID", "ONEBOT_SETU_GID", "TELEGRAM_TGSETU_GID")}) + "\\n")
if "ps" in sys.argv and "--quiet" in sys.argv:
    print("api-container")
if "inspect" in sys.argv:
    print("unhealthy" if os.environ.get("API_UNHEALTHY") else "healthy")
''')
    docker.chmod(0o755)
    env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"], CALL_LOG=str(tmp_path / "calls.jsonl"))
    env.pop("KISARA_ENGINE", None)
    env.pop("COMPOSE_PROFILES", None)
    for key in ("TELEGRAM_LOCAL_MODE", "TELEGRAM_API_BASE_URL", "TELEGRAM_API_ID", "TELEGRAM_API_HASH"):
        env.pop(key, None)
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
    subprocess.run([str(tmp_path / "kisara.sh"), "up"], env=env, check=True)
    operation = calls(log)[-1]
    assert operation[-len(services):] == services
    assert "--detach" in operation and "--build" in operation
    if profiles == "telegram":
        assert not (tmp_path / "data/napcat").exists()
        assert not any("napcat" in call or "kisara" in call[call.index("stop"):] for call in calls(log) if "stop" in call)


@pytest.mark.parametrize("action", ["down", "restart", "logs", "ps"])
def test_telegram_lifecycle_does_not_touch_qq(tmp_path: Path, action: str) -> None:
    env, log = repository(tmp_path, "onebot,telegram")
    subprocess.run([str(tmp_path / "kisara.sh"), action, "telegram"], env=env, check=True)
    operation = calls(log)[-1]
    assert operation[-1] == "telegram"
    assert "napcat" not in operation and "kisara-dev" not in operation
    assert "down" not in operation


def test_explicit_whole_project_down(tmp_path: Path) -> None:
    env, log = repository(tmp_path, "telegram")
    subprocess.run([str(tmp_path / "kisara.sh"), "down-all"], env=env, check=True)
    assert calls(log)[-1][-1] == "down"


def test_conflicting_qq_ownership_rejected(tmp_path: Path) -> None:
    env, log = repository(tmp_path, "onebot,onebot-dev")
    result = subprocess.run([str(tmp_path / "kisara.sh"), "up"], env=env, capture_output=True, text=True)
    assert result.returncode == 2 and "cannot own" in result.stderr
    assert calls(log) == []


def test_up_no_target_uses_env_file_selection(tmp_path: Path) -> None:
    env, log = repository(tmp_path, "telegram")
    subprocess.run([str(tmp_path / "kisara.sh"), "up"], env=env, check=True, stdin=subprocess.DEVNULL)
    assert calls(log)[-1][-1] == "telegram"


@pytest.mark.parametrize("value", ['telegram   ', 'telegram # selected engine',
                                   '"telegram" # selected engine', "'telegram'   "])
def test_dotenv_profile_comments_and_spaces(tmp_path: Path, value: str) -> None:
    env, log = repository(tmp_path, value)
    subprocess.run([str(tmp_path / "kisara.sh"), "up"], env=env, check=True, stdin=subprocess.DEVNULL)
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
    assert "telegram_state:/app/state" in telegram and "../config/telegram:/app/config/telegram:ro" in telegram
    assert "AppSecret:" in official and "TELEGRAM_BOT_TOKEN:" not in official and "ONEBOT_ACCESS_TOKEN:" not in official
    assert "kisara_state:/app/state" in text and "../data/napcat/QQ:/app/.config/QQ" in text
    assert "env_file:" not in text


@pytest.mark.parametrize("service,engine", [("kisara", "onebot"),
                                            ("kisara-dev", "onebot"),
                                            ("telegram", "telegram"),
                                            ("official", "official")])
def test_compose_engine_config_mounts_match_direct_runtime(service: str, engine: str) -> None:
    """Expose only selected-engine config and the existing shared font path."""
    text = (ROOT / "deploy/compose.yaml").read_text()
    block = re.split(r"\n(?=  \S)", text.split("  " + service + ":\n", 1)[1], maxsplit=1)[0]
    binds = [line.strip()[2:] for line in block.splitlines()
             if line.strip().startswith("- ../config")]
    assert binds == ["../config/{0}:/app/config/{0}:ro".format(engine),
                     "../config/fonts:/app/config/fonts:ro"]


@pytest.mark.skipif(shutil.which("git") is None, reason="Git CLI is not installed")
def test_engine_private_configs_ignored_without_hiding_examples(tmp_path: Path) -> None:
    """Exercise actual ignore matching in an isolated repository."""
    shutil.copy2(ROOT / ".gitignore", tmp_path / ".gitignore")
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    private = ["config/groups.json", "config/features/news/config.toml"]
    examples = []
    for engine in ("onebot", "telegram", "official"):
        private.extend(["config/{}/groups.json".format(engine),
                        "config/{}/features/news/config.toml".format(engine)])
        examples.extend(["config/{}/groups.example.json".format(engine),
                         "config/{}/features/news/config.toml.example".format(engine)])
    for name in private + examples:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n")
    result = subprocess.run(["git", "check-ignore", "--stdin"], cwd=tmp_path,
                            input="\n".join(private + examples) + "\n",
                            capture_output=True, text=True, check=True)
    assert result.stdout.splitlines() == private


@pytest.mark.parametrize("entrypoint", ["kisara.sh", "deploy/onebot.sh"])
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
    assert exported["KISARA_SETU_GID"] == "3456"
    assert exported["ONEBOT_SETU_GID"] == "2345"


@pytest.mark.parametrize("override", [None, "environment-project"])
def test_legacy_onebot_project_name_uses_dotenv_with_environment_precedence(tmp_path: Path, override: Optional[str]) -> None:
    """The legacy helper selects the actual configured project after loading dotenv."""
    env, log = repository(tmp_path, "onebot")
    env.pop("COMPOSE_PROJECT_NAME", None)
    if override is not None:
        env["COMPOSE_PROJECT_NAME"] = override
    with (tmp_path / ".env").open("a") as stream:
        stream.write("COMPOSE_PROJECT_NAME=file-project\n")
    result = subprocess.run([str(tmp_path / "deploy/onebot.sh"), "ps"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    operation = calls(log)[-1]
    assert operation[operation.index("--project-name") + 1] == (override or "file-project")


def local_api_environment(env: dict) -> None:
    """Select local deployment using synthetic credentials only."""
    env.update(TELEGRAM_LOCAL_MODE="true", TELEGRAM_API_BASE_URL="http://telegram-bot-api:8081",
               TELEGRAM_API_ID="12345", TELEGRAM_API_HASH="a" * 32)


def test_local_api_starts_healthy_before_telegram(tmp_path: Path) -> None:
    env, log = repository(tmp_path, "telegram")
    local_api_environment(env)
    subprocess.run([str(tmp_path / "kisara.sh"), "up"], env=env, check=True)
    operations = calls(log)
    api_start = next(index for index, call in enumerate(operations) if "up" in call and call[-1] == "telegram-bot-api")
    health = next(index for index, call in enumerate(operations) if "inspect" in call)
    bot_start = next(index for index, call in enumerate(operations) if "up" in call and call[-1] == "telegram")
    assert api_start < health < bot_start
    assert "telegram-local" in operations[api_start]
    assert (tmp_path / "data/kisara/tgsetu").stat().st_mode & 0o7777 == 0o2770
    assert not (tmp_path / "data/napcat").exists()


@pytest.mark.parametrize("action", ["down", "restart", "logs", "ps"])
def test_local_api_lifecycle_remains_selected_and_preserves_data(tmp_path: Path, action: str) -> None:
    env, log = repository(tmp_path, "onebot,telegram")
    local_api_environment(env)
    archive = tmp_path / "data/kisara/tgsetu"
    archive.mkdir(parents=True)
    sentinel = archive / "retained.mp4"
    sentinel.write_bytes(b"retained")
    subprocess.run([str(tmp_path / "kisara.sh"), action, "telegram"], env=env, check=True)
    operation = calls(log)[-1]
    if action == "restart":
        assert operation[-1] == "telegram"
        operations = calls(log)
        api_restart = next(index for index, call in enumerate(operations) if "restart" in call and call[-1] == "telegram-bot-api")
        health = next(index for index, call in enumerate(operations) if "inspect" in call)
        bot_restart = next(index for index, call in enumerate(operations) if "restart" in call and call[-1] == "telegram")
        assert api_restart < health < bot_restart
    else:
        assert operation[-2:] == ["telegram-bot-api", "telegram"]
    assert "napcat" not in operation and "down" not in operation
    assert sentinel.read_bytes() == b"retained"


@pytest.mark.parametrize("mode", ["TRUE", "1", "yes", "on"])
def test_local_api_truthy_setting_does_not_affect_other_engine(tmp_path: Path, mode: str) -> None:
    env, log = repository(tmp_path, "onebot")
    env["TELEGRAM_LOCAL_MODE"] = mode
    subprocess.run([str(tmp_path / "kisara.sh"), "up"], env=env, check=True)
    assert all("telegram-bot-api" not in call for call in calls(log))
    assert not (tmp_path / "data/kisara/tgsetu").exists()


@pytest.mark.parametrize("invalid", ["credentials", "endpoint", "unhealthy"])
def test_local_api_failure_prevents_bot_start_without_exposing_credentials(tmp_path: Path, invalid: str) -> None:
    env, log = repository(tmp_path, "telegram")
    local_api_environment(env)
    if invalid == "credentials":
        env["TELEGRAM_API_HASH"] = "private-invalid-hash"
    elif invalid == "endpoint":
        env["TELEGRAM_API_BASE_URL"] = "https://api.telegram.org"
    else:
        env["API_UNHEALTHY"] = "1"
    result = subprocess.run([str(tmp_path / "kisara.sh"), "up"], env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert not any("up" in call and call[-1] == "telegram" for call in calls(log))
    assert env["TELEGRAM_API_HASH"] not in result.stdout + result.stderr


def test_local_server_credential_and_storage_isolation_contract() -> None:
    text = (ROOT / "deploy/compose.yaml").read_text()
    server = text.split("  telegram-bot-api:\n", 1)[1].split("  telegram:\n", 1)[0]
    telegram = text.split("  telegram:\n", 1)[1].split("  official:\n", 1)[0]
    assert "profiles: [telegram-local]" in server and "ports:" not in server
    assert "TELEGRAM_API_ID:" in server and "TELEGRAM_API_HASH:" in server
    assert "TELEGRAM_BOT_TOKEN:" not in server
    assert "TELEGRAM_API_HASH:" not in telegram and "TELEGRAM_API_ID:" not in telegram
    assert "telegram_bot_api_cache:/var/lib/telegram-bot-api\n" in server
    assert "telegram_bot_api_cache:/var/lib/telegram-bot-api:ro" in telegram
    assert "../data/kisara/tgsetu:/app/tgsetu" in telegram
    assert "${TELEGRAM_TGSETU_GID-${KISARA_HOST_GID:-1000}}" in telegram
    image = (ROOT / "deploy/telegram-bot-api.Dockerfile").read_text()
    assert "e3e9dd8e5b3d7ab8537cd5a10dc31d5ffa8f82d1" in image
    assert "git submodule update --init --recursive" in image
    assert "USER 10001:10001" in image and "TDLib-LICENSE_1_0.txt" in image


def test_cloud_bot_image_seeds_shared_cache_with_server_identity() -> None:
    """A cloud-first empty volume remains writable when local mode is later enabled."""
    image = (ROOT / "deploy/Dockerfile").read_text()
    assert "--uid 10001 --gid 10001 kisara" in image
    assert "mkdir -p /app/state /app/setu /app/tgsetu /var/lib/telegram-bot-api" in image
    assert "chown -R kisara:kisara /app /opt/kisara /var/lib/telegram-bot-api" in image


def test_unhealthy_api_prevents_telegram_restart(tmp_path: Path) -> None:
    env, log = repository(tmp_path, "telegram")
    local_api_environment(env)
    env["API_UNHEALTHY"] = "1"
    result = subprocess.run([str(tmp_path / "kisara.sh"), "restart"], env=env,
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert any("restart" in call and call[-1] == "telegram-bot-api" for call in calls(log))
    assert not any("restart" in call and call[-1] == "telegram" for call in calls(log))
