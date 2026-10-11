"""Public command routing with inert backends and isolated Docker fixtures."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest


ROOT = Path(__file__).resolve().parents[2]


def cli_repository(tmp_path: Path) -> tuple:
    """Copy entrypoints beside record-only backends, outside the real repository."""
    repo = tmp_path / "repo with spaces"
    repo.mkdir()
    (repo / "deploy").mkdir()
    shutil.copy2(ROOT / "kisara.sh", repo / "kisara.sh")
    backend = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ["CALL_LOG"]).write_text(json.dumps({
    "backend": Path(sys.argv[0]).name, "argv": sys.argv[1:],
    "service": os.environ.get("HAKO_SERVICE"), "scope": os.environ.get("HAKO_SCOPE"),
}))
sys.exit(int(os.environ.get("BACKEND_STATUS", "0")))
'''
    for name in ("hako", "deploy/engines.sh"):
        path = repo / name
        path.write_text(backend)
        path.chmod(0o755)
    log = tmp_path / "calls.json"
    env = dict(os.environ, CALL_LOG=str(log), NO_COLOR="1")
    for key in ("KISARA_ENGINE", "COMPOSE_PROFILES", "HAKO_SERVICE", "HAKO_SCOPE", "BACKEND_STATUS"):
        env.pop(key, None)
    return repo, env, log


def execute(repo: Path, env: dict, *args: str,
            cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Capture one public invocation without a live service or runtime credentials."""
    return subprocess.run([str(repo / "kisara.sh"), *args], env=env, cwd=cwd,
                          capture_output=True, text=True, stdin=subprocess.DEVNULL)


@pytest.mark.parametrize("arguments", [(), ("--help",), ("-h",), ("help",)])
def test_help_needs_no_backend_or_dotenv(tmp_path: Path, arguments: tuple) -> None:
    repo, env, log = cli_repository(tmp_path)
    (repo / "hako").unlink()
    (repo / "deploy/engines.sh").unlink()
    (repo / ".env").write_text("invalid dotenv syntax must not be parsed\n")
    result = execute(repo, env, *arguments)
    assert result.returncode == 0 and result.stdout == ""
    assert "Offline commands:" in result.stderr and "up [engine,...]" in result.stderr
    assert "\x1b" not in result.stderr and not log.exists()


@pytest.mark.parametrize("args", [("unknown",), ("console", "extra"), ("--help", "extra"),
                                  ("up", "telegram", "extra"), ("up", "--detach"),
                                  ("up", "telegram,"), ("up", ""),
                                  ("up", "telegram,telegram"), ("up", "onebot,onebot-dev"),
                                  ("down-all", "telegram")])
def test_invalid_public_arguments_do_not_invoke_backends(tmp_path: Path, args: tuple) -> None:
    repo, env, log = cli_repository(tmp_path)
    result = execute(repo, env, *args)
    assert result.returncode == 2 and "Error:" in result.stderr
    assert not log.exists()


@pytest.mark.parametrize("action,backend_action", [("up", "deploy"), ("down", "down"),
                                                  ("stop", "stop"), ("restart", "restart"),
                                                  ("logs", "logs"), ("ps", "ps"),
                                                  ("status", "status"), ("pull", "pull")])
def test_online_routes_keep_targets_and_detached_up(tmp_path: Path, action: str,
                                                   backend_action: str) -> None:
    repo, env, log = cli_repository(tmp_path)
    result = execute(repo, env, action, "telegram,official", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    record = json.loads(log.read_text())
    assert record["backend"] == "engines.sh"
    assert record["argv"] == [backend_action, "telegram,official"]


@pytest.mark.parametrize("action", ["up", "logs", "down-all"])
def test_omitted_target_keeps_backend_configuration_selection(tmp_path: Path, action: str) -> None:
    repo, env, log = cli_repository(tmp_path)
    assert execute(repo, env, action).returncode == 0
    assert json.loads(log.read_text())["argv"] == ["deploy" if action == "up" else action]


@pytest.mark.parametrize("args,expected", [((), ["python", "-m", "pytest"]),
    (("tests/unit/test_settings.py", "-q"), ["python", "-m", "pytest", "tests/unit/test_settings.py", "-q"]),
    (("-k", "literal $(touch /tmp/never-created) and with spaces", "--maxfail=1"),
     ["python", "-m", "pytest", "-k", "literal $(touch /tmp/never-created) and with spaces", "--maxfail=1"])])
def test_tests_forward_literal_arguments_without_prepending_suite(tmp_path: Path, args: tuple,
                                                                 expected: list) -> None:
    repo, env, log = cli_repository(tmp_path)
    env["HAKO_SERVICE"] = "bot"
    (repo / ".env").write_text("not a dotenv file\n")
    result = execute(repo, env, "test", *args, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    record = json.loads(log.read_text())
    assert record["backend"] == "hako" and record["argv"] == expected
    assert record["service"] == "" and record["scope"] == "kisara.sh"


def test_console_is_offline_and_keeps_exit_status(tmp_path: Path) -> None:
    repo, env, log = cli_repository(tmp_path)
    env.update(HAKO_SERVICE="bot", BACKEND_STATUS="37")
    result = execute(repo, env, "console")
    assert result.returncode == 37
    record = json.loads(log.read_text())
    assert record["argv"] == ["python", "-m", "kisara.bot.console"]
    assert record["service"] == ""


@pytest.mark.parametrize("command,backend", [("console", "hako"), ("up", "deploy/engines.sh")])
def test_missing_selected_backend_reports_failure(tmp_path: Path, command: str, backend: str) -> None:
    repo, env, log = cli_repository(tmp_path)
    (repo / backend).unlink()
    result = execute(repo, env, command)
    assert result.returncode == 1 and "executable backend was not found" in result.stderr
    assert not log.exists()


def test_preview_forwards_argv_and_failure_to_owning_parser(tmp_path: Path) -> None:
    repo, env, log = cli_repository(tmp_path)
    env["BACKEND_STATUS"] = "23"
    result = execute(repo, env, "preview", "start", "official,telegram", "--verbose")
    assert result.returncode == 23
    assert json.loads(log.read_text())["argv"] == ["preview", "start", "official,telegram", "--verbose"]


@pytest.mark.parametrize("command", ["console", "test"])
def test_real_hako_offline_mode_excludes_credentials_and_runtime_env_file(tmp_path: Path,
                                                                       command: str) -> None:
    repo, env, log = cli_repository(tmp_path)
    shutil.copy2(ROOT / "hako", repo / "hako")
    (repo / ".env").write_text("TELEGRAM_BOT_TOKEN=fixture-private-token\ninvalid dotenv\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    docker = binary / "docker"
    docker.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ["CALL_LOG"]).write_text(json.dumps(sys.argv[1:]))
''')
    docker.chmod(0o755)
    env.update(PATH=str(binary) + os.pathsep + os.environ["PATH"], HAKO_SERVICE="bot",
               TELEGRAM_BOT_TOKEN="inherited-private-token")
    result = execute(repo, env, command)
    assert result.returncode == 0, result.stderr
    argv = json.loads(log.read_text())
    assert "--env-file" not in argv and "TELEGRAM_BOT_TOKEN" not in " ".join(argv)
    assert "fixture-private-token" not in result.stdout + result.stderr + " ".join(argv)
    assert "inherited-private-token" not in result.stdout + result.stderr + " ".join(argv)
