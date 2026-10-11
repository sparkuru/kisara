"""Hako bot environment tests record arguments without a Docker daemon."""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("engine", ["telegram", "official"])
def test_hako_bot_omits_server_only_api_credentials(tmp_path: Path, engine: str) -> None:
    """Keep SDK settings while excluding local server credentials from bot flags."""
    shutil.copy2(ROOT / "hako", tmp_path / "hako")
    (tmp_path / "deploy").mkdir()
    shutil.copy2(ROOT / "deploy/dotenv.sh", tmp_path / "deploy/dotenv.sh")
    (tmp_path / ".env").write_text(
        "TELEGRAM_API_ID=12345\nTELEGRAM_API_HASH=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
        "TELEGRAM_BOT_TOKEN=fixture-token\nTELEGRAM_API_BASE_URL=http://telegram-bot-api:8081\n"
        "TELEGRAM_LOCAL_MODE=true\nOFFICIAL_APP_ID=fixture-id\nOFFICIAL_APP_SECRET=fixture-secret\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    docker = binary / "docker"
    docker.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ["CALL_LOG"], "w") as stream:
    json.dump(sys.argv[1:], stream)
''')
    docker.chmod(0o755)
    log = tmp_path / "calls.json"
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("KISARA_", "HAKO_", "TELEGRAM_", "OFFICIAL_"))}
    env.update(PATH=str(binary) + os.pathsep + os.environ["PATH"], CALL_LOG=str(log),
               HAKO_SERVICE="bot", KISARA_ENGINE=engine)
    result = subprocess.run([str(tmp_path / "hako"), "python", "-m", "kisara"],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    arguments = json.loads(log.read_text())
    assert "TELEGRAM_API_ID" not in arguments and "TELEGRAM_API_HASH" not in arguments
    assert "TELEGRAM_API_BASE_URL" in arguments and "TELEGRAM_LOCAL_MODE" in arguments
    assert "TELEGRAM_BOT_TOKEN" in arguments
    assert "OFFICIAL_APP_ID" in arguments and "OFFICIAL_APP_SECRET" in arguments
    assert "KISARA_ENGINE=" + engine in arguments
    assert arguments[arguments.index("-v") + 1] == str(tmp_path) + ":/app"
    assert arguments[arguments.index("-w") + 1] == "/app"
    assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" not in result.stdout + result.stderr
    assert "fixture-token" not in result.stdout + result.stderr
    assert "fixture-secret" not in result.stdout + result.stderr
