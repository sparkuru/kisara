"""Preview behavior in temporary repositories with a recording Docker fixture.

No test talks to a daemon, loads repository credentials or installs dependencies.
"""

import importlib.util
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional

import pytest


ROOT = Path(__file__).resolve().parents[2]
FAKE_DOCKER = r'''#!/usr/bin/env python3
import hashlib, json, os, pathlib, re, sys
args = sys.argv[1:]
root = pathlib.Path(os.environ["FIXTURE_ROOT"])
with (root / "calls.jsonl").open("a") as stream:
    stream.write(json.dumps(args) + "\n")
state_path = root / "state.json"
state = json.loads(state_path.read_text())
def save(): state_path.write_text(json.dumps(state))
def value(flag): return args[args.index(flag)+1]
def services_after(operation):
    return [x for x in args[args.index(operation)+1:] if not x.startswith("-")]
if "context" in args:
    if os.environ.get("NO_CONTEXT"): sys.exit(125)
    print(os.environ.get("ENDPOINT", "unix:///var/run/docker.sock")); sys.exit(0)
if "info" in args: print("fixture"); sys.exit(0)
if "compose" in args or pathlib.Path(sys.argv[0]).name == "docker-compose":
    if "version" in args: sys.exit(1 if os.environ.get("OLD_COMPOSE") else 0)
    if "config" in args: sys.exit(int(os.environ.get("INVALID_COMPOSE", "0")))
    if "build" in args:
        if os.environ.get("BUILD_FAIL"):
            print("build secret=" + os.environ.get("ONEBOT_ACCESS_TOKEN", "fixture")); sys.exit(7)
        for name in services_after("build"):
            state["images"].append(name)
            if not os.environ.get("POSTINSTALL_FAIL"): state["dependencies"].append(name)
            state.setdefault("built_inputs", {})[name] = {
                "source": (root / "src" / "example.py").read_text(),
                "manifest": hashlib.sha256((root / "pyproject.toml").read_bytes()).hexdigest(),
            }
        save(); sys.exit(0)
    if "up" in args:
        override = pathlib.Path(args[args.index("--file", args.index("--file")+1)+1]).read_text()
        for name in services_after("up"):
            block = re.search(r"^  " + name + r":\n((?:    .*\n)*)", override, re.MULTILINE).group(1)
            labels = {key: val.strip('"') for key, val in re.findall(r"      (hako\.[a-z]+): (.+)", block)}
            engine = "onebot" if name in ("kisara", "kisara-dev") else name
            state["containers"][name] = {"labels": labels, "ready": not bool(os.environ.get("UNREADY")), "running": True,
                "image_inputs": state.get("built_inputs", {}).get(name),
                "settings": {"allowed": os.environ.get(engine.upper() + "_ALLOWED_USERS", ""),
                             "public": os.environ.get(engine.upper() + "_PUBLIC_FEATURE", "tguid" if engine == "telegram" else "")}}
        save(); sys.exit(int(os.environ.get("UP_FAIL", "0")))
    sys.exit(0)
if "ps" in args:
    filters = [args[i+1].removeprefix("label=") for i, x in enumerate(args) if x == "--filter"]
    for name, facts in state["containers"].items():
        selected = True
        for item in filters:
            key, val = item.split("=",1)
            actual = {"com.docker.compose.project": "kisara", "com.docker.compose.service": name}.get(key, facts["labels"].get(key))
            if actual != val: selected = False
        if selected: print(name)
    sys.exit(0)
if "inspect" in args:
    if "image" in args:
        image = args[-1]
        match = re.search(r"-(telegram-bot-api|kisara-dev|kisara|telegram|official):", image)
        name = match.group(1) if match else "napcat" if "napcat" in image else "music" if "ncm" in image else None
        if image == "python:3.12-slim": name = "hako"
        sys.exit(0 if name in state["images"] else 1)
    name = args[-1]
    if name not in state["containers"]: sys.exit(1)
    facts = state["containers"][name]
    fmt = value("--format")
    if ".Config.Env" in fmt: print("official" if facts.get("engine") == "official" else "")
    elif ".State.Running" in fmt: print("true" if facts["running"] else "false")
    elif ".State.Status" in fmt: print("running" if facts["running"] else "exited")
    else:
        keys = re.findall(r'\.Config.Labels "([^"]+)"', fmt)
        if len(keys) == 3 and os.environ.get("FOLLOW_FOREIGN") == name:
            counter = root / (name + ".ownership-checks")
            checks = int(counter.read_text()) + 1 if counter.exists() else 1
            counter.write_text(str(checks))
            if checks > 1:
                print("foreign|preview.sh|" + name); sys.exit(0)
        print("|".join(facts["labels"].get(key, "") for key in keys))
    sys.exit(0)
if "pull" in args:
    if os.environ.get("PULL_FAIL"): sys.exit(6)
    name = "napcat" if "napcat" in args[-1] else "music" if "ncm" in args[-1] else "hako"
    state["images"].append(name); save(); sys.exit(0)
if "run" in args:
    if "install" in args:
        if os.environ.get("INSTALL_FAIL"): print("install failed"); sys.exit(8)
        if not os.environ.get("POSTINSTALL_FAIL"): state["dependencies"].append("hako")
        save(); sys.exit(0)
    if "check" in args:
        image = next((x for x in args if x.endswith(":latest") or x == "python:3.12-slim"), "")
        match = re.search(r"-(telegram-bot-api|kisara-dev|kisara|telegram|official):", image)
        name = match.group(1) if match else "hako"
        sys.exit(0 if name in state["dependencies"] else 1)
    if "--detach" in args:
        labels = dict(args[i+1].split("=",1) for i,x in enumerate(args) if x == "--label")
        state["containers"]["bot"] = {"labels": labels,"ready": not bool(os.environ.get("UNREADY")),"running": True}
        save(); print("bot"); sys.exit(0)
    sys.exit(0)
if "exec" in args:
    if os.environ.get("API_UNREADY") and "telegram-bot-api" in args: sys.exit(1)
    name = args[args.index("exec")+1]
    if name == "napcat":
        command_index = args.index("exec") + 2
        if args[command_index:command_index+2] != ["python3", "-c"]: sys.exit(127)
        if args[-1] == "listeners":
            if os.environ.get("LISTENERS_FAIL"): sys.exit(5)
            for port in (3001, 6099):
                print(os.environ.get("LISTENER_BIND", "0.0.0.0") + "|" + str(port))
            if os.environ.get("EXTRA_LISTENER"): print(os.environ["EXTRA_LISTENER"])
    elif "const requested" in " ".join(args):
        if os.environ.get("LISTENERS_FAIL"): sys.exit(5)
        for port in ([3001, 6099] if name == "napcat" else [3000]):
            print(os.environ.get("LISTENER_BIND", "0.0.0.0") + "|" + str(port))
        if os.environ.get("EXTRA_LISTENER"): print(os.environ["EXTRA_LISTENER"])
    elif "listeners" in args and name == "telegram-bot-api":
        if os.environ.get("LISTENERS_FAIL"): sys.exit(5)
        print("0.0.0.0|8081")
    elif "listeners" in args:
        if os.environ.get("BOT_LISTENER"): print(os.environ["BOT_LISTENER"])
    sys.exit(0 if state["containers"].get(name, {}).get("ready", False) else 1)
if "port" in args:
    if args[-1] == "napcat": print("6099/tcp -> " + os.environ.get("PORT_MAPPING", "127.0.0.1:6099"))
    sys.exit(0)
if "logs" in args:
    name = args[-1]
    if "--follow" in args and os.environ.get("FOLLOW_CONTROLLED"):
        import time
        (root / (name + ".reader.pid")).write_text(str(os.getpid()))
        print("recent " + name + " token=fixture-token account=" + os.environ.get("NAPCAT_ACCOUNT", "123456789"), flush=True)
        print("https://name:pass@example.invalid/resource Bearer private-credential", flush=True)
        print("https://api.telegram.org/botunknown-token/getMe?access_token=unknown-query", flush=True)
        print("Official bot is ready: private-display-name", flush=True)
        print("Received private message user=111 chat=222 text=private-message", flush=True)
        print("Replying private message user=111 chat=222: pong", flush=True)
        print("No reply for private message user=111 chat=222", flush=True)
        print("Sent private text chat=222 message=333 part=1/1: pong", flush=True)
        print("QR █ secret", flush=True)
        print("user_id=hidden-user chat=hidden-chat app_id=hidden-app", flush=True)
        print("group user=987654321 chat=-1009876543210 message=87654321: order 246810 at 2026-10-11", flush=True)
        print("api_hash=" + "a" * 32 + " api_id=12345", flush=True)
        print("history-end " + name, flush=True)
        while not (root / (name + ".release")).exists(): time.sleep(0.02)
        if os.environ.get("FOLLOW_ERROR") == name:
            print("stream error fixture-token", file=sys.stderr, flush=True)
            sys.exit(6)
        print("fresh " + name + " token=fixture-token", flush=True)
        print("Received private message user=111 chat=222: /ping", flush=True)
        print("Sent private text chat=222 message=444 part=1/1: pong", flush=True)
        while True: time.sleep(0.02)
    if os.environ.get("LOG_FAIL"): print("raw must never be emitted"); sys.exit(4)
    if os.environ.get("LOG_TIMEOUT"): import time; time.sleep(10)
    print("watcher alive; application import failed")
    print("token=" + os.environ.get("ONEBOT_ACCESS_TOKEN", "secret-fixture"))
    print("account=" + os.environ.get("NAPCAT_ACCOUNT", "123456789"))
    print("api_hash=" + "a" * 32)
    print("api_id=12345")
    print("https://name:pass@example.invalid/resource Bearer private-credential")
    print("Received private message user=111 chat=222: diagnostic-message")
    print("Replying private message user=111 chat=222: diagnostic-reply")
    print("No reply for private message user=111 chat=222")
    sys.exit(0)
if "stop" in args:
    name = args[-1]
    if name in state["containers"]: state["containers"][name]["running"] = False
    save(); sys.exit(0)
if "rm" in args:
    state["containers"].pop(args[-1], None); save(); sys.exit(0)
sys.exit(0)
'''


def fixture(tmp_path: Path, profile: str = "onebot") -> tuple[dict, Path]:
    """Copy only preview inputs and use private recording fixtures."""
    (tmp_path / "deploy").mkdir()
    for name in ("engines.sh", "onebot.sh", "compose.yaml", "Dockerfile", "dotenv.sh", "preview-runtime.sh",
                 "telegram-bot-api.Dockerfile", "telegram-bot-api-entrypoint.sh", "telegram-bot-api-probe.sh",
                 "preview-console.sh", "preview-deps.py", "preview-probe.py", "preview-listeners.js", "preview-constraints-py312.txt"):
        shutil.copy2(ROOT / "deploy" / name, tmp_path / "deploy" / name)
    for name in ("kisara.sh", "hako", "pyproject.toml"):
        shutil.copy2(ROOT / name, tmp_path / name)
    (tmp_path / "config").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src/example.py").write_text("# synthetic source version 1\n")
    (tmp_path / ".env").write_text("COMPOSE_PROFILES={}\nONEBOT_ACCESS_TOKEN=secret-fixture\nNAPCAT_ACCOUNT=123456789\nTELEGRAM_BOT_TOKEN=fixture-token\nOFFICIAL_APP_ID=fixture-id\nOFFICIAL_APP_SECRET=fixture-secret\n".format(profile))
    (tmp_path / "state.json").write_text(json.dumps({"images": [], "dependencies": [], "containers": {}}))
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "docker").write_text(FAKE_DOCKER)
    (binary / "docker").chmod(0o755)
    (binary / "ip").write_text("#!/bin/sh\nprintf '%s\\n' 'lo UNKNOWN 127.0.0.1/8 ::1/128' 'eth0 UP 192.0.2.10/24 192.0.2.11/24' 'vpn UNKNOWN 198.51.100.2/32 192.0.2.10/24' 'bad DOWN 203.0.113.1/24'\n")
    (binary / "ip").chmod(0o755)
    env = {key: value for key, value in os.environ.items() if not key.startswith(("KISARA_", "HAKO_", "DOCKER_", "COMPOSE_", "ONEBOT_", "NAPCAT_", "TELEGRAM_", "OFFICIAL_"))}
    env.update(PATH=str(binary) + os.pathsep + os.environ["PATH"], FIXTURE_ROOT=str(tmp_path), KISARA_PREVIEW_TIMEOUT="1", NO_COLOR="")
    return env, tmp_path / "calls.jsonl"


def run(tmp_path: Path, env: dict, *args: str) -> subprocess.CompletedProcess:
    """Execute the public preview command from an unrelated directory."""
    return subprocess.run([str(tmp_path / "kisara.sh"), "preview", *args], cwd="/tmp", env=env, capture_output=True, text=True)


def calls(log: Path) -> list:
    """Read recorded operations without depending on human console formatting."""
    return [json.loads(row) for row in log.read_text().splitlines()] if log.exists() else []


def state(tmp_path: Path) -> dict:
    """Read isolated fake daemon state."""
    return json.loads((tmp_path / "state.json").read_text())


def save_state(tmp_path: Path, value: dict) -> None:
    """Update only the temporary fake daemon."""
    (tmp_path / "state.json").write_text(json.dumps(value))


@pytest.mark.parametrize("command", ["--help", "status", "stop", "down"])
def test_readonly_commands_never_prepare(tmp_path: Path, command: str) -> None:
    env, log = fixture(tmp_path)
    result = run(tmp_path, env, command)
    assert result.returncode == (1 if command == "status" else 0)
    assert not any(any(op in call for op in ("build", "pull", "run", "up")) for call in calls(log))
    if command == "--help":
        assert calls(log) == [] and result.stdout == ""


def test_first_start_reuses_and_stop_preserves_data(tmp_path: Path) -> None:
    env, log = fixture(tmp_path)
    original = (tmp_path / ".env").read_bytes()
    result = run(tmp_path, env, "start")
    assert result.returncode == 0, result.stderr
    assert "System is ready." in result.stdout and "Local only (preview host):" in result.stdout
    assert "http://127.0.0.1:6099/" in result.stdout and "Open:" not in result.stdout
    assert "secret-fixture" not in result.stdout + result.stderr
    assert "--no-build" in next(call for call in calls(log) if "up" in call)
    log.write_text("")
    assert run(tmp_path, env, "start").returncode == 0
    assert not any(any(op in call for op in ("build", "pull", "run", "up")) for call in calls(log))
    assert run(tmp_path, env, "status").stdout.startswith("System is ready.")
    sentinel = tmp_path / "data/kisara/setu/retained.bin"
    sentinel.write_bytes(b"retain")
    assert run(tmp_path, env, "down").returncode == 0
    assert state(tmp_path)["containers"] == {}
    assert sentinel.read_bytes() == b"retain" and (tmp_path / ".env").read_bytes() == original
    assert run(tmp_path, env, "stop").returncode == 0


def test_napcat_python_probes_preserve_compressed_ipv6_and_music_node(tmp_path: Path) -> None:
    """A Node-free NapCat uses the real helper source and keeps socket scope facts."""
    env, log = fixture(tmp_path, "onebot,music")
    env["LISTENER_BIND"] = "[::]"
    result = run(tmp_path, env, "start")
    assert result.returncode == 0, result.stderr
    assert "napcat: ws://napcat:3001" in result.stdout
    source = (ROOT / "deploy/preview-probe.py").read_text().rstrip("\n")
    napcat_commands = [call for call in calls(log) if call[:2] == ["exec", "napcat"]]
    assert any(call[2:] == ["python3", "-c", source, "napcat"] for call in napcat_commands)
    assert any(call[2:] == ["python3", "-c", source, "listeners"] for call in napcat_commands)
    assert all(call[2] not in ("node", "nodejs") for call in napcat_commands)
    assert any(call[:4] == ["exec", "music", "node", "-e"] for call in calls(log))


@pytest.mark.parametrize("missing", ["image", "dependencies", "both", "neither"])
def test_prepares_only_missing_resources(tmp_path: Path, missing: str) -> None:
    env, log = fixture(tmp_path, "telegram")
    value = state(tmp_path)
    if missing not in {"image", "both"}: value["images"] = ["telegram"]
    if missing not in {"dependencies", "both"}: value["dependencies"] = ["telegram"]
    save_state(tmp_path, value)
    result = run(tmp_path, env)
    assert result.returncode == 0, result.stderr
    builds = [call for call in calls(log) if "build" in call]
    assert len(builds) == (0 if missing == "neither" else 1)
    probes = [call for call in calls(log) if "run" in call]
    assert all("--network" in call and "none" in call and "-e" not in call and "-p" not in call for call in probes)
    assert "Listeners:" not in result.stdout and "outbound bot" in result.stdout


@pytest.mark.parametrize("kind", ["unhealthy", "incomplete", "changed", "foreign"])
def test_abnormal_existing_group_is_never_repaired(tmp_path: Path, kind: str) -> None:
    env, log = fixture(tmp_path)
    assert run(tmp_path, env).returncode == 0
    value = state(tmp_path)
    if kind == "unhealthy": value["containers"]["kisara"]["ready"] = False
    elif kind == "incomplete": value["containers"].pop("kisara")
    elif kind == "foreign": value["containers"]["napcat"]["labels"]["hako.repo"] = "/unrelated"
    else:
        with (tmp_path / ".env").open("a") as stream: stream.write("NAPCAT_WEBUI_PORT=6100\n")
    save_state(tmp_path, value)
    log.write_text("")
    result = run(tmp_path, env)
    assert result.returncode != 0 and "System is ready." not in result.stdout
    assert not any(any(op in call for op in ("up", "build", "pull", "stop", "rm")) for call in calls(log))
    assert state(tmp_path)["containers"] == value["containers"]


@pytest.mark.parametrize("flag,code", [("BUILD_FAIL", 7), ("POSTINSTALL_FAIL", 1), ("PULL_FAIL", 6)])
def test_preparation_failure_creates_no_group(tmp_path: Path, flag: str, code: int) -> None:
    env, log = fixture(tmp_path)
    env[flag] = "1"
    result = run(tmp_path, env, "--verbose")
    assert result.returncode == code and "System is ready." not in result.stdout
    assert not any("up" in call for call in calls(log)) and state(tmp_path)["containers"] == {}
    assert "secret-fixture" not in result.stdout + result.stderr


@pytest.mark.parametrize("flag", ["UNREADY", "UP_FAIL", "LOG_FAIL", "LOG_TIMEOUT"])
def test_failed_start_diagnoses_before_owned_cleanup(tmp_path: Path, flag: str) -> None:
    env, log = fixture(tmp_path)
    env[flag] = "9" if flag == "UP_FAIL" else "1"
    env["UNREADY"] = "1"
    result = run(tmp_path, env)
    assert result.returncode == (9 if flag == "UP_FAIL" else 1)
    assert "System is ready." not in result.stdout and state(tmp_path)["containers"] == {}
    recorded = calls(log)
    assert max(i for i, call in enumerate(recorded) if "logs" in call) < min(i for i, call in enumerate(recorded) if "rm" in call)
    assert not any(word in result.stderr for word in ("secret-fixture", "123456789", "name:pass", "private-credential", "raw must never",
                                                     "diagnostic-message", "diagnostic-reply", "No reply for"))
    if flag not in {"LOG_FAIL", "LOG_TIMEOUT"}: assert "application import failed" in result.stderr
    assert (tmp_path / "data/kisara/setu").exists()


def test_wildcard_candidates_are_complete_and_grouped(tmp_path: Path) -> None:
    env, log = fixture(tmp_path)
    env.update(NAPCAT_WEBUI_BIND="0.0.0.0", PORT_MAPPING="0.0.0.0:7081")
    result = run(tmp_path, env)
    assert result.returncode == 0, result.stderr
    for address in ("192.0.2.10", "192.0.2.11", "198.51.100.2"):
        assert result.stdout.count("http://{}:7081/".format(address)) == 1
    assert "203.0.113.1" not in result.stdout and "http://0.0.0.0" not in result.stdout
    assert result.stdout.index("Open:") < result.stdout.index("Local only") < result.stdout.index("Listeners:") < result.stdout.index("Published:")
    assert result.stdout.count("NapCat WebUI (napcat):") == 2
    assert "candidates" in result.stdout


@pytest.mark.parametrize("overrides,expected", [({"DOCKER_CONTEXT": "explicit", "DOCKER_HOST": "tcp://ignored:2375"}, "--context"),
                                                ({"DOCKER_HOST": "unix:///tmp/fake.sock"}, "--host"), ({}, "context")])
def test_effective_endpoint_precedence_and_old_current_inspect(tmp_path: Path, overrides: dict, expected: str) -> None:
    env, log = fixture(tmp_path, "telegram")
    env.update(overrides)
    assert run(tmp_path, env).returncode == 0
    assert expected in calls(log)[0]
    assert not any("show" in call for call in calls(log))
    if "DOCKER_CONTEXT" in overrides: assert all("--host" not in call for call in calls(log))


def test_remote_wildcard_does_not_discover_caller(tmp_path: Path) -> None:
    env, log = fixture(tmp_path)
    env.update(DOCKER_HOST="ssh://remote", NAPCAT_WEBUI_BIND="0.0.0.0", PORT_MAPPING="0.0.0.0:7081")
    result = run(tmp_path, env)
    assert result.returncode == 2 and "daemon host" in result.stderr
    assert not any("up" in call or "build" in call for call in calls(log))
    env["KISARA_PREVIEW_HOST_ADDRESSES"] = "203.0.113.8,203.0.113.9"
    result = run(tmp_path, env)
    assert result.returncode == 0
    assert "http://203.0.113.8:7081/" in result.stdout and "192.0.2.10" not in result.stdout
    assert "remote" in result.stdout


@pytest.mark.parametrize("config", ["COMPOSE_PROFILES=onebot,onebot-dev\n", "COMPOSE_PROFILES=\n", "ONEBOT_ACCESS_TOKEN='unclosed\n", "PATH=/malicious\n", "COMPOSE_PROFILES=onebot\nCOMPOSE_PROFILES=telegram\n"])
def test_invalid_dotenv_blocks_before_docker(tmp_path: Path, config: str) -> None:
    env, log = fixture(tmp_path)
    (tmp_path / ".env").write_text(config)
    result = run(tmp_path, env)
    assert result.returncode == 2 and calls(log) == []


def test_official_uses_compose_image_and_credential_free_pinned_probe(tmp_path: Path) -> None:
    env, log = fixture(tmp_path, "official")
    env["KISARA_ENGINE"] = "official"
    result = run(tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert any("build" in call and call[-1] == "official" for call in calls(log))
    probes = [call for call in calls(log) if "run" in call]
    assert len(probes) == 1
    assert probes[0][-2:] == ["check", "official"]
    assert "--env-file" not in probes[0] and "-p" not in probes[0] and "-e" not in probes[0]
    startup = next(call for call in calls(log) if "up" in call)
    assert "--detach" in startup and "--no-build" in startup and startup[-1] == "official"
    assert not any("install" in call or ("run" in call and "--detach" in call) for call in calls(log))
    assert "official: outbound" in result.stdout and "Listeners:" not in result.stdout
    log.write_text("")
    assert run(tmp_path, env).returncode == 0
    assert not any("run" in call for call in calls(log))


@pytest.mark.parametrize("flag,code", [("BUILD_FAIL", 7), ("POSTINSTALL_FAIL", 1)])
def test_official_image_preparation_failure_never_starts(tmp_path: Path, flag: str, code: int) -> None:
    env, log = fixture(tmp_path, "official")
    env.update(KISARA_ENGINE="official")
    env[flag] = "1"
    result = run(tmp_path, env)
    assert result.returncode == code and state(tmp_path)["containers"] == {}
    assert not any("--detach" in call for call in calls(log))


def test_dotenv_literal_quotes_presence_empty_and_no_execution(tmp_path: Path) -> None:
    env, log = fixture(tmp_path, "telegram")
    sentinel = tmp_path / "must-not-exist"
    config = "COMPOSE_PROFILES='telegram' # comment\nNAPCAT_UID=2345\nNAPCAT_GID=3456\nONEBOT_ACCESS_TOKEN=\"$(touch {})\"\n".format(sentinel)
    (tmp_path / ".env").write_text(config)
    result = subprocess.run(["bash", "-c", 'set -eu; DOTENV_KEYS=(); source "$1/deploy/dotenv.sh"; dotenv_load "$1/.env"; printf "%s|%s|%s|%s" "$COMPOSE_PROFILES" "$NAPCAT_UID" "$NAPCAT_GID" "$ONEBOT_ACCESS_TOKEN"', "bash", str(tmp_path)], env=dict(env, NAPCAT_UID="", NAPCAT_GID="4567"), capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.startswith("telegram||4567|$(touch") and not sentinel.exists()
    assert calls(log) == [] and (tmp_path / ".env").read_text() == config


def test_readiness_probe_rejects_watcher_stale_and_wrong_engine(tmp_path: Path) -> None:
    path = ROOT / "deploy/preview-probe.py"
    spec = importlib.util.spec_from_file_location("preview_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    marker = tmp_path / "ready.json"
    for value in ({"pid": os.getpid(), "start": "wrong", "engine": "onebot", "ready": True},
                  {"pid": 99999999, "start": "1", "engine": "onebot", "ready": True},
                  {"pid": os.getpid(), "start": "wrong", "engine": "telegram", "ready": True}):
        marker.write_text(json.dumps(value))
        assert module.ready("onebot", marker) is False


def test_build_prepares_without_start_and_refuses_live_group(tmp_path: Path) -> None:
    env, log = fixture(tmp_path, "telegram")
    assert run(tmp_path, env, "build").returncode == 0
    assert state(tmp_path)["containers"] == {} and not any("up" in call for call in calls(log))
    assert run(tmp_path, env).returncode == 0
    log.write_text("")
    assert run(tmp_path, env, "build").returncode == 2
    assert not any("build" in call for call in calls(log))


def test_offline_missing_resource_is_actionable(tmp_path: Path) -> None:
    env, log = fixture(tmp_path)
    env["KISARA_PREVIEW_OFFLINE"] = "true"
    result = run(tmp_path, env)
    assert result.returncode == 1 and "offline" in result.stderr
    assert not any("pull" in call or "build" in call or "up" in call for call in calls(log))


def test_old_compose_fallback_and_missing_context_capability(tmp_path: Path) -> None:
    env, log = fixture(tmp_path, "telegram")
    env["OLD_COMPOSE"] = "1"
    shutil.copy2(tmp_path / "bin/docker", tmp_path / "bin/docker-compose")
    result = run(tmp_path, env)
    assert result.returncode == 0, result.stderr
    env["NO_CONTEXT"] = "1"
    result = run(tmp_path, env, "status")
    assert result.returncode == 127 and "capability" in result.stderr


def test_remote_malformed_ipv6_rejected_before_prepare(tmp_path: Path) -> None:
    env, log = fixture(tmp_path)
    env.update(DOCKER_HOST="ssh://remote", NAPCAT_WEBUI_BIND="0.0.0.0", KISARA_PREVIEW_HOST_ADDRESSES="abcd:,:::1")
    result = run(tmp_path, env)
    assert result.returncode == 2 and "Invalid explicit" in result.stderr
    assert not any("build" in call or "up" in call for call in calls(log))


def test_mapping_specific_and_ipv6_scopes(tmp_path: Path) -> None:
    env, log = fixture(tmp_path)
    env["PORT_MAPPING"] = "192.0.2.42:7182"
    result = run(tmp_path, env)
    assert result.returncode == 0 and "http://192.0.2.42:7182/" in result.stdout
    assert "Local only" not in result.stdout
    env["PORT_MAPPING"] = "[::1]:7182"
    result = run(tmp_path, env, "status")
    assert result.returncode == 0 and "http://[::1]:7182/" in result.stdout and "Open:" not in result.stdout
    env["PORT_MAPPING"] = "[::]:7182"
    with (tmp_path / "bin/ip").open("w") as stream:
        stream.write("#!/bin/sh\nprintf '%s\\n' 'eth0 UP 2001:db8::10/64 2001:db8::11/64 fe80::1/64'\n")
    result = run(tmp_path, env, "status")
    assert result.returncode == 0 and "http://[2001:db8::10]:7182/" in result.stdout
    assert "http://[2001:db8::11]:7182/" in result.stdout and "http://[fe80" not in result.stdout
    assert "Link-local" in result.stdout and "http://192." not in result.stdout


def test_failed_address_discovery_has_no_success(tmp_path: Path) -> None:
    env, log = fixture(tmp_path)
    (tmp_path / "bin/ip").write_text("#!/bin/sh\nexit 4\n")
    env["NAPCAT_WEBUI_BIND"] = "0.0.0.0"
    result = run(tmp_path, env)
    assert result.returncode == 1 and "discovery failed" in result.stderr
    assert not any("up" in call or "build" in call for call in calls(log))


def test_sourced_helpers_preserve_options_traps_and_output(tmp_path: Path) -> None:
    env, log = fixture(tmp_path)
    result = subprocess.run(["bash", "-c", 'set -eu; before=$(set +o); trap "true" EXIT; old=$(trap -p); source "$1/deploy/dotenv.sh"; source "$1/deploy/preview-console.sh"; source "$1/deploy/preview-runtime.sh"; [[ "$before" == "$(set +o)" && "$old" == "$(trap -p)" ]]', "bash", str(tmp_path)], env=env, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout == "" and result.stderr == "" and calls(log) == []


def test_loopback_container_listener_omits_host_urls_and_extra_tcp_is_visible(tmp_path: Path) -> None:
    env, log = fixture(tmp_path)
    env.update(LISTENER_BIND="127.0.0.1", EXTRA_LISTENER="0.0.0.0|7788")
    result = run(tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert "Listening napcat: 127.0.0.1:6099" in result.stdout
    assert "127.0.0.1:6099 (container loopback only; WebUI HTTP)" in result.stdout
    assert "7788" in result.stdout and "protocol unknown" in result.stdout
    assert "http://127.0.0.1:6099" not in result.stdout and "inactive/unverified" in result.stdout


@pytest.mark.parametrize("profile,key,value", [("telegram", "TELEGRAM_BOT_TOKEN", ""),
                                               ("onebot", "ONEBOT_ACCESS_TOKEN", ""),
                                               ("onebot", "ONEBOT_ACCESS_TOKEN", "replace-with-a-secret"),
                                               ("onebot", "ONEBOT_ACCESS_TOKEN", "invalid+token")])
def test_missing_required_credentials_never_prepare(tmp_path: Path, profile: str, key: str, value: str) -> None:
    env, log = fixture(tmp_path, profile)
    env[key] = value
    result = run(tmp_path, env)
    assert result.returncode == 2 and key in result.stderr and calls(log) == []


def test_onebot_valid_token_with_example_like_prefix_is_preserved(tmp_path: Path) -> None:
    """Reject the exact example value without introducing a token prefix restriction."""
    env, log = fixture(tmp_path)
    env["ONEBOT_ACCESS_TOKEN"] = "replace-with-valid-user-token"
    result = run(tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert "System is ready." in result.stdout


def test_missing_fingerprint_input_blocks_preparation(tmp_path: Path) -> None:
    """A missing manifest cannot be silently hashed as empty and start stale resources."""
    env, log = fixture(tmp_path, "telegram")
    (tmp_path / "pyproject.toml").unlink()
    result = run(tmp_path, env)
    assert result.returncode != 0 and "pyproject.toml" in result.stderr
    assert "System is ready." not in result.stdout and state(tmp_path)["containers"] == {}
    assert not any(any(op in call for op in ("build", "pull", "run", "up")) for call in calls(log))


@pytest.mark.parametrize("remote", [False, True])
def test_stop_does_not_require_host_address_discovery(tmp_path: Path, remote: bool) -> None:
    """Teardown remains usable when discovery is unavailable after successful startup."""
    env, log = fixture(tmp_path)
    env.update(NAPCAT_WEBUI_BIND="0.0.0.0", PORT_MAPPING="0.0.0.0:7081")
    assert run(tmp_path, env).returncode == 0
    sentinel = tmp_path / "data/kisara/setu/retained.bin"
    sentinel.write_bytes(b"retain")
    if remote:
        env["DOCKER_HOST"] = "ssh://remote"
        env.pop("KISARA_PREVIEW_HOST_ADDRESSES", None)
    else:
        (tmp_path / "bin/ip").write_text("#!/bin/sh\nexit 4\n")
    log.write_text("")
    result = run(tmp_path, env, "down")
    assert result.returncode == 0, result.stderr
    assert state(tmp_path)["containers"] == {} and sentinel.read_bytes() == b"retain"
    assert not any(any(op in call for op in ("build", "pull", "run", "up")) for call in calls(log))


def test_new_outbound_bot_tcp_socket_is_reported_without_invented_url(tmp_path: Path) -> None:
    env, log = fixture(tmp_path, "telegram")
    env["BOT_LISTENER"] = "127.0.0.1|8765"
    result = run(tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert "Listening telegram: 127.0.0.1:8765" in result.stdout
    assert "http://127.0.0.1:8765" not in result.stdout
    assert "no inbound application listener" not in result.stdout


@pytest.mark.parametrize("failure", ["listeners", "redaction"])
def test_inspection_or_redaction_failure_is_closed(tmp_path: Path, failure: str) -> None:
    """Unavailable facts never claim success; redaction failure never falls back to raw logs."""
    env, log = fixture(tmp_path)
    if failure == "listeners":
        env["LISTENERS_FAIL"] = "1"
    else:
        env["UNREADY"] = "1"
        binary = tmp_path / "bin/sed"
        binary.write_text("#!/bin/sh\nexit 5\n")
        binary.chmod(0o755)
    result = run(tmp_path, env)
    assert result.returncode == 1 and "System is ready." not in result.stdout
    assert state(tmp_path)["containers"] == {}
    assert "secret-fixture" not in result.stdout + result.stderr
    if failure == "redaction":
        assert "Diagnostics suppressed" in result.stderr
        assert "application import failed" not in result.stderr


def local_api_environment(env: dict) -> None:
    """Use isolated fake API credentials, not a Telegram account."""
    env.update(TELEGRAM_LOCAL_MODE="true", TELEGRAM_API_BASE_URL="http://telegram-bot-api:8081",
               TELEGRAM_API_ID="12345", TELEGRAM_API_HASH="a" * 32)


def test_local_api_preview_is_internal_and_owned(tmp_path: Path) -> None:
    env, log = fixture(tmp_path, "telegram")
    local_api_environment(env)
    result = run(tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert "http://telegram-bot-api:8081/" in result.stdout and "Open:" not in result.stdout
    assert set(state(tmp_path)["containers"]) == {"telegram", "telegram-bot-api"}
    operations = calls(log)
    api_start = next(index for index, call in enumerate(operations) if "up" in call and call[-1] == "telegram-bot-api")
    api_ready = next(index for index, call in enumerate(operations) if "exec" in call and "ready" in call)
    bot_start = next(index for index, call in enumerate(operations) if "up" in call and call[-1] == "telegram")
    assert api_start < api_ready < bot_start
    assert any("run" in call and "--version" in call and "--network" in call for call in operations)
    assert not any("telegram-bot-api" in call and "python" in call for call in operations)
    log.write_text("")
    assert run(tmp_path, env).returncode == 0
    assert not any(any(operation in call for operation in ("build", "pull", "run", "up")) for call in calls(log))
    sentinel = tmp_path / "data/kisara/tgsetu/retained.mp4"
    sentinel.write_bytes(b"retained")
    assert run(tmp_path, env, "stop").returncode == 0
    assert state(tmp_path)["containers"] == {} and sentinel.read_bytes() == b"retained"


def test_local_api_unready_rolls_back_owned_attempt_before_bot(tmp_path: Path) -> None:
    env, log = fixture(tmp_path, "telegram")
    local_api_environment(env)
    env["API_UNREADY"] = "1"
    result = run(tmp_path, env)
    assert result.returncode == 1 and "System is ready." not in result.stdout
    assert not any("up" in call and call[-1] == "telegram" for call in calls(log))
    assert state(tmp_path)["containers"] == {}
    assert env["TELEGRAM_API_HASH"] not in result.stdout + result.stderr


def test_local_api_source_change_requires_explicit_stop(tmp_path: Path) -> None:
    env, log = fixture(tmp_path, "telegram")
    local_api_environment(env)
    assert run(tmp_path, env).returncode == 0
    with (tmp_path / "deploy/telegram-bot-api.Dockerfile").open("a") as stream:
        stream.write("\n# changed source\n")
    log.write_text("")
    result = run(tmp_path, env)
    assert result.returncode == 2 and "Configuration changed" in result.stderr
    assert not any(any(operation in call for operation in ("build", "pull", "run", "up")) for call in calls(log))


@pytest.mark.parametrize("command", ["status", "stop"])
def test_local_api_readonly_commands_need_no_credentials(tmp_path: Path, command: str) -> None:
    env, log = fixture(tmp_path, "telegram")
    env["TELEGRAM_LOCAL_MODE"] = "true"
    result = run(tmp_path, env, command)
    assert result.returncode == (1 if command == "status" else 0)
    assert not any(any(operation in call for operation in ("build", "pull", "run", "up")) for call in calls(log))


@pytest.mark.parametrize("target,expected", [
    ("onebot", {"napcat", "kisara"}),
    ("onebot-dev", {"napcat", "kisara-dev"}),
    ("telegram", {"telegram"}),
    ("official", {"official"}),
    ("music", {"music"}),
    ("telegram,official", {"telegram", "official"}),
])
def test_explicit_target_overrides_environment_and_dotenv(
    tmp_path: Path, target: str, expected: set
) -> None:
    """A target selects only its group without rewriting inherited/private inputs."""
    env, log = fixture(tmp_path, "invalid-dotenv-profile")
    env.update(KISARA_ENGINE="invalid-env-engine", COMPOSE_PROFILES="invalid-env-profile")
    original = (tmp_path / ".env").read_bytes()
    result = run(tmp_path, env, "start", target)
    assert result.returncode == 0, result.stderr
    assert set(state(tmp_path)["containers"]) == expected
    assert (tmp_path / ".env").read_bytes() == original
    if target == "official":
        assert not any("run" in call and "--detach" in call for call in calls(log))
        assert any("up" in call and call[-1] == "official" for call in calls(log))
    if target == "telegram,official":
        assert not any("--detach" in call and "run" in call for call in calls(log))
        assert any("up" in call and call[-2:] == ["telegram", "official"] for call in calls(log))


@pytest.mark.parametrize("args", [
    ("start", "unknown"), ("start", "telegram", "official"),
    ("start", "start", "telegram"), ("telegram", "status"),
    ("start", "telegram,telegram"), ("start", "telegram,"),
    ("start", ",telegram"), ("start", "telegram,,official"),
    ("start", "onebot,onebot-dev"), ("start", ""),
    ("start", "selected"), ("start", "--unknown"),
    ("--verbose", "--verbose"),
])
def test_invalid_preview_arguments_fail_before_configuration_or_docker(
    tmp_path: Path, args: tuple
) -> None:
    """Invalid public argv cannot load configuration or perform backend operations."""
    env, log = fixture(tmp_path)
    (tmp_path / ".env").unlink()
    result = run(tmp_path, env, *args)
    assert result.returncode == 2 and calls(log) == []
    assert "Missing .env" not in result.stderr


def test_optional_action_and_targeted_status_stop_preserve_other_group(tmp_path: Path) -> None:
    """Omitting start is supported, while inspection/teardown cannot grow groups."""
    env, log = fixture(tmp_path)
    assert run(tmp_path, env, "telegram").returncode == 0
    assert run(tmp_path, env, "official").returncode == 0
    assert set(state(tmp_path)["containers"]) == {"telegram", "official"}
    log.write_text("")
    assert run(tmp_path, env, "status", "telegram").returncode == 0
    assert run(tmp_path, env, "down", "telegram").returncode == 0
    assert set(state(tmp_path)["containers"]) == {"official"}
    assert not any(any(operation in call for operation in ("build", "pull", "run", "up")) for call in calls(log))


def test_canonical_status_recognizes_stored_ownership_in_space_path(tmp_path: Path) -> None:
    """Canonical status recognizes stable preview ownership without retired scripts."""
    root = tmp_path / "repository with spaces"
    root.mkdir()
    env, log = fixture(root, "telegram")
    assert run(root, env, "start", "telegram").returncode == 0
    log.write_text("")
    result = run(root, env, "status", "telegram")
    assert result.returncode == 0, result.stderr
    assert "System is ready." in result.stdout
    assert not any(any(operation in call for operation in ("build", "pull", "run", "up")) for call in calls(log))
    assert all(value["labels"]["hako.scope"] == "preview.sh" for value in state(root)["containers"].values())


@pytest.mark.parametrize("engine,environment_profiles,dotenv_profiles,expected", [
    ("official", "telegram", "onebot", {"telegram"}),
    ("telegram", "onebot", "official", {"napcat", "kisara"}),
    ("onebot", None, "onebot,telegram,official", {"napcat", "kisara", "telegram", "official"}),
    ("invalid-engine", None, "telegram", {"telegram"}),
    (None, "telegram", "onebot", {"telegram"}),
    (None, None, "telegram", {"telegram"}),
    (None, None, None, {"napcat", "kisara"}),
])
def test_preview_without_target_uses_profiles_and_ignores_runtime_engine(
    tmp_path: Path, engine: Optional[str], environment_profiles: Optional[str],
    dotenv_profiles: Optional[str], expected: set
) -> None:
    """The owning parser selects env, dotenv or default without a wrapper menu."""
    env, log = fixture(tmp_path)
    dotenv = tmp_path / ".env"
    lines = dotenv.read_text().splitlines()
    if dotenv_profiles is None:
        lines = [line for line in lines if not line.startswith("COMPOSE_PROFILES=")]
    else:
        lines[0] = "COMPOSE_PROFILES=" + dotenv_profiles
    dotenv.write_text("\n".join(lines) + "\n")
    if engine is not None:
        env["KISARA_ENGINE"] = engine
    if environment_profiles is not None:
        env["COMPOSE_PROFILES"] = environment_profiles
    original = dotenv.read_bytes()
    result = run(tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert set(state(tmp_path)["containers"]) == expected
    assert dotenv.read_bytes() == original
    assert any("--detach" in call for call in calls(log))


@pytest.mark.parametrize("profile,bots", [
    ("onebot,telegram,official", {"kisara", "telegram", "official"}),
    ("onebot-dev,telegram,official", {"kisara-dev", "telegram", "official"}),
    ("official", {"official"}),
])
def test_default_down_build_start_refreshes_all_selected_images_and_settings(
        tmp_path: Path, profile: str, bots: set[str]) -> None:
    """Existing tags rebuild current source; new creation gets current dotenv."""
    env, log = fixture(tmp_path, profile)
    env["KISARA_ENGINE"] = "onebot"
    assert run(tmp_path, env).returncode == 0
    previous = state(tmp_path)
    expected = bots | ({"napcat"} if "onebot" in profile else set())
    assert set(previous["containers"]) == expected
    retained = []
    for directory in ("data/napcat/QQ", "data/kisara/setu", "data/kisara/tgsetu", "data/official-state"):
        target = tmp_path / directory / "retained.bin"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"preserved")
        retained.append(target)
    log.write_text("")
    assert run(tmp_path, env, "down").returncode == 0
    assert state(tmp_path)["containers"] == {}
    assert {call[-1] for call in calls(log) if "rm" in call} == expected
    assert not any("--volumes" in call or "volume" in call for call in calls(log))
    source = tmp_path / "src/example.py"
    source.write_text("# synthetic source version 2\n")
    with (tmp_path / "pyproject.toml").open("a") as stream:
        stream.write("\n# changed synthetic manifest input\n")
    with (tmp_path / ".env").open("a") as stream:
        stream.write("ONEBOT_ALLOWED_USERS=101\nTELEGRAM_ALLOWED_USERS=202\nOFFICIAL_ALLOWED_USERS=303\n"
                     "ONEBOT_PUBLIC_FEATURE=ping\nTELEGRAM_PUBLIC_FEATURE=\nOFFICIAL_PUBLIC_FEATURE=help\n")
    for engine in ("onebot", "telegram", "official"):
        config = tmp_path / "config" / engine / "features/ping/config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text("enabled = false\n")
    configured = (tmp_path / ".env").read_bytes()
    log.write_text("")
    result = run(tmp_path, env, "build")
    assert result.returncode == 0, result.stderr
    operations = calls(log)
    assert {call[-1] for call in operations if "build" in call} == bots
    assert sum("build" in call for call in operations) == len(bots)
    assert not any("up" in call or "pull" in call or "--detach" in call for call in operations)
    assert state(tmp_path)["containers"] == {}
    built = state(tmp_path)["built_inputs"]
    for bot in bots:
        assert built[bot]["source"] == source.read_text()
        assert built[bot]["manifest"] != previous["built_inputs"][bot]["manifest"]
    log.write_text("")
    result = run(tmp_path, env)
    assert result.returncode == 0, result.stderr
    current = state(tmp_path)
    assert set(current["containers"]) == expected
    assert not any("build" in call or "pull" in call for call in calls(log))
    assert any("up" in call and "--no-build" in call for call in calls(log))
    for bot in bots:
        facts = current["containers"][bot]
        assert facts["image_inputs"] == built[bot]
        assert facts["labels"]["hako.config"] != previous["containers"][bot]["labels"]["hako.config"]
        assert facts["labels"]["hako.repo"] == str(tmp_path)
        assert facts["labels"]["hako.scope"] == "preview.sh" and facts["labels"]["hako.service"] == bot
        engine = "onebot" if bot.startswith("kisara") else bot
        assert facts["settings"] == {"allowed": {"onebot": "101", "telegram": "202", "official": "303"}[engine],
                                     "public": {"onebot": "ping", "telegram": "", "official": "help"}[engine]}
    assert (tmp_path / ".env").read_bytes() == configured
    assert all(target.read_bytes() == b"preserved" for target in retained)
    assert "fixture-secret" not in result.stdout + result.stderr


@pytest.mark.parametrize("action", ["down", "build", "start", "status"])
@pytest.mark.parametrize("profiles", ["", "unknown", "telegram,telegram", "onebot,onebot-dev"])
def test_default_invalid_profiles_cannot_be_hidden_by_runtime_engine(
        tmp_path: Path, action: str, profiles: str) -> None:
    env, log = fixture(tmp_path, "telegram")
    env.update(KISARA_ENGINE="onebot", COMPOSE_PROFILES=profiles)
    assert run(tmp_path, env, action).returncode == 2
    assert calls(log) == []


def legacy_official(tmp_path: Path, *, owner: bool = True, engine: str = "official") -> dict:
    """Construct the persisted old hako identity without starting any runtime."""
    return {"labels": {"hako.repo": str(tmp_path) if owner else "/unrelated", "hako.scope": "preview.sh",
                       "hako.service": "bot", "hako.config": "old-hako-fingerprint"},
            "engine": engine, "ready": True, "running": True}


@pytest.mark.parametrize("action", ["build", "start", "status"])
def test_selected_official_refuses_legacy_hako_conflict(tmp_path: Path, action: str) -> None:
    env, log = fixture(tmp_path, "official")
    value = state(tmp_path)
    value["containers"]["bot"] = legacy_official(tmp_path)
    save_state(tmp_path, value)
    result = run(tmp_path, env, action)
    assert result.returncode == 2 and "preview down official" in result.stderr
    assert state(tmp_path) == value
    assert not any(any(op in call for op in ("build", "pull", "run", "up", "stop", "rm")) for call in calls(log))


def test_selected_official_down_removes_only_verified_legacy_runtime(tmp_path: Path) -> None:
    env, log = fixture(tmp_path, "telegram")
    assert run(tmp_path, env).returncode == 0
    value = state(tmp_path)
    value["containers"]["bot"] = legacy_official(tmp_path)
    save_state(tmp_path, value)
    retained = tmp_path / "data/legacy-state/retained.bin"
    retained.parent.mkdir(parents=True)
    retained.write_bytes(b"preserved")
    log.write_text("")
    result = run(tmp_path, env, "down", "official")
    assert result.returncode == 0, result.stderr
    assert state(tmp_path)["containers"] == {"telegram": value["containers"]["telegram"]}
    assert [call[-1] for call in calls(log) if "stop" in call or "rm" in call] == ["bot", "bot"]
    assert retained.read_bytes() == b"preserved"
    assert not any("--volumes" in call or "volume" in call for call in calls(log))
    log.write_text("")
    assert run(tmp_path, env, "build", "official").returncode == 0
    assert run(tmp_path, env, "start", "official").returncode == 0
    assert set(state(tmp_path)["containers"]) == {"official", "telegram"}


def test_selected_official_preserves_foreign_and_unverified_legacy_bot(tmp_path: Path) -> None:
    env, log = fixture(tmp_path, "official")
    value = state(tmp_path)
    value["containers"]["bot"] = legacy_official(tmp_path, owner=False)
    save_state(tmp_path, value)
    assert run(tmp_path, env, "down").returncode == 0
    assert state(tmp_path) == value
    assert not any("stop" in call or "rm" in call for call in calls(log))
    value["containers"]["bot"] = legacy_official(tmp_path, engine="telegram")
    save_state(tmp_path, value)
    log.write_text("")
    result = run(tmp_path, env, "down")
    assert result.returncode == 2 and "verified unique Official" in result.stderr
    assert state(tmp_path) == value and not any("stop" in call or "rm" in call for call in calls(log))


def test_platform_names_are_presentation_only_for_legacy_and_onebot_streams(tmp_path: Path) -> None:
    env, log = fixture(tmp_path)
    result = subprocess.run(["bash", "-c", 'source "$1/deploy/preview-console.sh"; source "$1/deploy/preview-runtime.sh"; '
                             'for service in napcat kisara kisara-dev telegram official bot; do '
                             'printf "%s\\n" "$service" | preview_log_lines "$service"; done', "bash", str(tmp_path)],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout.splitlines() == [
        "onebot | napcat", "onebot | kisara", "onebot | kisara-dev", "telegram | telegram", "official | official", "official | bot"]
    assert calls(log) == []


def test_selected_failure_recovery_guidance_names_canonical_target(tmp_path: Path) -> None:
    """Failure advice can recover the explicitly selected group despite other defaults."""
    env, log = fixture(tmp_path)
    env["UNREADY"] = "1"
    result = run(tmp_path, env, "start", "telegram")
    assert result.returncode == 1
    assert "./kisara.sh preview stop telegram" in result.stderr
    assert "./kisara.sh preview start telegram" in result.stderr
    assert state(tmp_path)["containers"] == {}


def test_preview_up_alias_reuses_matching_explicit_target(tmp_path: Path) -> None:
    """The historical up alias retains start's reuse and owned-lifecycle behavior."""
    env, log = fixture(tmp_path)
    assert run(tmp_path, env, "up", "telegram").returncode == 0
    log.write_text("")
    assert run(tmp_path, env, "up", "telegram").returncode == 0
    assert not any(any(operation in call for operation in ("build", "pull", "run", "up")) for call in calls(log))


def test_explicit_foreign_group_failure_preserves_unselected_preview(tmp_path: Path) -> None:
    """Choosing a target cannot repair foreign resources or tear down another group."""
    env, log = fixture(tmp_path)
    assert run(tmp_path, env, "start", "onebot").returncode == 0
    assert run(tmp_path, env, "start", "telegram").returncode == 0
    value = state(tmp_path)
    value["containers"]["telegram"]["labels"]["hako.repo"] = "/unrelated"
    save_state(tmp_path, value)
    log.write_text("")
    result = run(tmp_path, env, "start", "telegram")
    assert result.returncode == 2 and "not owned by preview" in result.stderr
    assert state(tmp_path)["containers"] == value["containers"]
    assert not any(any(operation in call for operation in ("build", "pull", "run", "up", "stop", "rm")) for call in calls(log))


def wait_output(path: Path, expected: str, process: subprocess.Popen) -> str:
    """Require prompt line delivery while the producer still owns its stream."""
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        output = path.read_text() if path.exists() else ""
        if expected in output:
            return output
        assert process.poll() is None, output
        time.sleep(0.02)
    pytest.fail("Timed out waiting for sanitized output: " + expected)


def reader_pids(tmp_path: Path) -> list[int]:
    """Read only process identities explicitly recorded by this fixture."""
    return [int(path.read_text()) for path in tmp_path.glob("*.reader.pid")]


def assert_readers_reaped(tmp_path: Path) -> None:
    """The reader must disappear, rather than survive or remain a zombie."""
    assert reader_pids(tmp_path)
    assert all(not Path("/proc", str(pid)).exists() for pid in reader_pids(tmp_path))


def child_processes(pid: int) -> set[int]:
    """Collect this invocation's descendants through kernel-owned child lists."""
    path = Path("/proc", str(pid), "task", str(pid), "children")
    children = {int(item) for item in path.read_text().split()} if path.exists() else set()
    return children | {descendant for child in children for descendant in child_processes(child)}


@pytest.mark.parametrize("target,expected", [
    (None, ["napcat", "kisara"]), ("onebot-dev", ["napcat", "kisara-dev"]),
    ("telegram", ["telegram"]), ("official", ["official"]),
    ("telegram,official", ["telegram", "official"]),
])
@pytest.mark.parametrize("termination,group", [(signal.SIGINT, False), (signal.SIGINT, True), (signal.SIGTERM, False)])
def test_status_follows_selected_bot_logs_and_reaps_readers(
    tmp_path: Path, target: Optional[str], expected: list[str], termination: int, group: bool
) -> None:
    """Status preserves identities while protecting credentials and service lifecycle."""
    env, log = fixture(tmp_path)
    local_api_environment(env)
    env.update(NAPCAT_ACCOUNT="246897531", ONEBOT_ALLOWED_USERS="111,987654321", TELEGRAM_ALLOWED_USERS="111,987654321",
               TELEGRAM_ALLOWED_GROUPS="-1009876543210")
    args = [target] if target is not None else []
    assert run(tmp_path, env, "start", *args).returncode == 0
    sentinel = tmp_path / "retained.bin"
    sentinel.write_bytes(b"retain")
    original = state(tmp_path)
    log.write_text("")
    env["FOLLOW_CONTROLLED"] = "1"
    stdout = tmp_path / "follow.stdout"
    stderr = tmp_path / "follow.stderr"
    with stdout.open("w") as out, stderr.open("w") as err:
        process = subprocess.Popen(
            [str(tmp_path / "kisara.sh"), "preview", "status", *args],
            env=env, cwd="/tmp", stdout=out, stderr=err, start_new_session=True,
        )
    try:
        for name in expected:
            display = "onebot" if name in {"napcat", "kisara", "kisara-dev"} else name
            output = wait_output(stdout, display + " | history-end " + name, process)
            assert "System is ready." in output
            assert display + " | Received private message user=111 chat=222 text=private-message" in output
            assert display + " | Replying private message user=111 chat=222: pong" in output
            assert display + " | No reply for private message user=111 chat=222" in output
            assert display + " | Sent private text chat=222 message=333 part=1/1: pong" in output
            assert display + " | recent " + name + " token=[redacted] account=246897531" in output
            assert display + " | Official bot is ready: private-display-name" in output
            assert display + " | user_id=hidden-user chat=hidden-chat app_id=hidden-app" in output
            assert display + " | group user=987654321 chat=-1009876543210 message=87654321: order 246810 at 2026-10-11" in output
            assert display + " | api_hash=[redacted] api_id=[redacted]" in output
            assert "[private-id]" not in output and "[private-name]" not in output
        assert process.poll() is None
        for name in expected:
            (tmp_path / (name + ".release")).touch()
        for name in expected:
            display = "onebot" if name in {"napcat", "kisara", "kisara-dev"} else name
            wait_output(stdout, display + " | fresh " + name + " token=[redacted]", process)
            wait_output(stdout, display + " | Received private message user=111 chat=222: /ping", process)
            wait_output(stdout, display + " | Sent private text chat=222 message=444 part=1/1: pong", process)
        for pid in reader_pids(tmp_path):
            workspace = Path(os.readlink(Path("/proc", str(pid), "fd/1"))).parent
            pipes = [path for suffix in ("raw", "replaced", "safe") for path in workspace.glob("*." + suffix)]
            assert len(pipes) == len(expected) * 3
            assert all(path.is_fifo() and path.stat().st_size == 0 for path in pipes)
            assert not (workspace / "safe.log").exists() and not (workspace / "logs.log").exists()
        descendants = child_processes(process.pid)
        assert set(reader_pids(tmp_path)).issubset(descendants)
        assert len(descendants) >= len(expected) * 4
        if group:
            os.killpg(process.pid, termination)
        else:
            process.send_signal(termination)
        assert process.wait(timeout=5) == (130 if termination == signal.SIGINT else 143)
        assert_readers_reaped(tmp_path)
        assert all(not Path("/proc", str(pid)).exists() for pid in descendants)
        assert state(tmp_path) == original and sentinel.read_bytes() == b"retain"
        operations = calls(log)
        follow = [call for call in operations if "logs" in call]
        assert {call[-1] for call in follow} == set(expected)
        assert all(call[-5:-1] == ["logs", "--follow", "--tail", "80"] for call in follow)
        assert not any(any(op in call for op in ("build", "pull", "run", "up", "stop", "rm")) for call in operations)
        combined = stdout.read_text() + stderr.read_text()
        assert not any(line.startswith(("napcat |", "kisara |", "kisara-dev |", "bot |")) for line in combined.splitlines())
        assert not any(hint in combined for hint in ("Following napcat", "Following kisara", "Following bot"))
        for name in expected:
            display = "onebot" if name in {"napcat", "kisara", "kisara-dev"} else name
            assert "Following " + display + " logs" in combined
        for private in ("fixture-token", "name:pass", "private-credential", "unknown-token",
                        "unknown-query", "QR █", "a" * 32, "12345"):
            assert private not in combined
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)


def test_ready_auxiliary_status_does_not_request_bot_logs(tmp_path: Path) -> None:
    """Auxiliary-only selection keeps finite readiness without an invented bot."""
    env, log = fixture(tmp_path, "music")
    assert run(tmp_path, env, "start").returncode == 0
    log.write_text("")
    result = run(tmp_path, env, "status")
    assert result.returncode == 0 and "System is ready." in result.stdout
    assert not any("logs" in call for call in calls(log))


def test_status_rechecks_ownership_before_log_reader(tmp_path: Path) -> None:
    """Readiness cannot authorize logs after the container's ownership changes."""
    env, log = fixture(tmp_path, "telegram")
    assert run(tmp_path, env, "start").returncode == 0
    original = state(tmp_path)
    env["FOLLOW_FOREIGN"] = "telegram"
    log.write_text("")
    result = run(tmp_path, env, "status")
    assert result.returncode == 1 and "ownership mismatch/unavailable" in result.stderr
    assert not any("logs" in call for call in calls(log))
    assert state(tmp_path) == original


@pytest.mark.parametrize("failure", ["reader", "sanitizer", "preflight"])
def test_status_stream_failure_is_closed_and_reaps_other_bot(
    tmp_path: Path, failure: str
) -> None:
    """A failed stream stage cannot leak raw output or leave another stream attached."""
    env, log = fixture(tmp_path, "telegram,official")
    assert run(tmp_path, env, "start").returncode == 0
    original = state(tmp_path)
    log.write_text("")
    env["FOLLOW_CONTROLLED"] = "1"
    if failure == "reader":
        env["FOLLOW_ERROR"] = "telegram"
    else:
        binary = tmp_path / "bin/sed"
        command = "exit 9" if failure == "preflight" else "IFS= read -r line && exit 9; exit 0"
        binary.write_text('#!/bin/bash\nif [[ $1 != -u ]]; then exec /usr/bin/sed "$@"; fi\n' + command + "\n")
        binary.chmod(0o755)
    stdout = tmp_path / "follow.stdout"
    stderr = tmp_path / "follow.stderr"
    with stdout.open("w") as out, stderr.open("w") as err:
        process = subprocess.Popen(
            [str(tmp_path / "kisara.sh"), "preview", "status"], env=env,
            stdout=out, stderr=err, start_new_session=True,
        )
    try:
        if failure == "reader":
            for name in ("telegram", "official"):
                wait_output(stdout, "history-end " + name, process)
            (tmp_path / "telegram.release").touch()
        assert process.wait(timeout=10) == 1
        if failure != "preflight":
            assert_readers_reaped(tmp_path)
        else:
            assert not any("logs" in call for call in calls(log))
        combined = stdout.read_text() + stderr.read_text()
        assert "fixture-token" not in combined and "private-credential" not in combined
        assert "redaction" in stderr.read_text()
        assert state(tmp_path) == original
        assert not any(any(op in call for op in ("build", "pull", "run", "up", "stop", "rm")) for call in calls(log))
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
