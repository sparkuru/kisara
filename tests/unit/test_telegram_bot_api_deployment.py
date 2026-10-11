"""Local Bot API helpers use fake binaries, never credentials or live accounts."""

import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]


def api_fixture(tmp_path: Path) -> dict:
    """Record only public arguments and the effective cache umask."""
    binary = tmp_path / "telegram-bot-api"
    binary.write_text('''#!/usr/bin/env bash
set -eu
umask > "$API_UMASK"
printf '%s\\n' "$@" > "$API_ARGUMENTS"
''')
    binary.chmod(0o755)
    env = {key: value for key, value in os.environ.items() if not key.startswith("TELEGRAM_")}
    env.update(PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
               API_UMASK=str(tmp_path / "umask"), API_ARGUMENTS=str(tmp_path / "arguments"))
    return env


def test_local_api_keeps_credentials_out_of_arguments(tmp_path: Path) -> None:
    env = api_fixture(tmp_path)
    env.update(TELEGRAM_API_ID="12345", TELEGRAM_API_HASH="a" * 32)
    result = subprocess.run([str(ROOT / "deploy/telegram-bot-api-entrypoint.sh")],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout == "" and result.stderr == ""
    arguments = (tmp_path / "arguments").read_text().splitlines()
    assert "--local" in arguments and "--dir=/var/lib/telegram-bot-api" in arguments
    assert "--verbosity=0" in arguments and "--memory-verbosity=0" in arguments
    assert all("api-id" not in argument and "api-hash" not in argument for argument in arguments)
    assert (tmp_path / "umask").read_text().strip() == "0077"


@pytest.mark.parametrize("argument", ["--help", "--version"])
def test_local_api_binary_smoke_requires_no_credentials(tmp_path: Path, argument: str) -> None:
    env = api_fixture(tmp_path)
    result = subprocess.run([str(ROOT / "deploy/telegram-bot-api-entrypoint.sh"), argument],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0
    assert (tmp_path / "arguments").read_text().splitlines() == [argument]


@pytest.mark.parametrize("invalid", ["missing", "api-id", "api-hash", "argument"])
def test_local_api_invalid_input_fails_before_start(tmp_path: Path, invalid: str) -> None:
    env = api_fixture(tmp_path)
    args = []
    if invalid != "missing":
        env.update(TELEGRAM_API_ID="12345", TELEGRAM_API_HASH="a" * 32)
    if invalid == "api-id":
        env["TELEGRAM_API_ID"] = "private-invalid-id"
    elif invalid == "api-hash":
        env["TELEGRAM_API_HASH"] = "private-invalid-hash"
    elif invalid == "argument":
        args = ["--verbosity=10"]
    result = subprocess.run([str(ROOT / "deploy/telegram-bot-api-entrypoint.sh"), *args],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 2 and not (tmp_path / "arguments").exists()
    assert "private-invalid" not in result.stdout + result.stderr


def test_local_api_listener_probe_reports_sockets_and_filters_docker_dns(tmp_path: Path) -> None:
    binary = tmp_path / "ss"
    binary.write_text('''#!/usr/bin/env bash
printf '%s\\n' 'LISTEN 0 4096 0.0.0.0:8081 0.0.0.0:*' 'LISTEN 0 4096 127.0.0.11:4567 0.0.0.0:*' 'LISTEN 0 4096 [::]:9090 [::]:*'
''')
    binary.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ["PATH"])
    result = subprocess.run([str(ROOT / "deploy/telegram-bot-api-probe.sh"), "listeners"],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["0.0.0.0|8081", "[::]|9090"]
    assert "http" not in result.stdout
