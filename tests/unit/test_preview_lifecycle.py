"""Preview behavior in temporary repositories with a recording Docker fixture.

No test talks to a daemon, loads repository credentials or installs dependencies.
"""

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
FAKE_DOCKER = r'''#!/usr/bin/env python3
import json, os, pathlib, re, sys
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
        save(); sys.exit(0)
    if "up" in args:
        override = pathlib.Path(args[args.index("--file", args.index("--file")+1)+1]).read_text()
        for name in services_after("up"):
            block = re.search(r"^  " + name + r":\n((?:    .*\n)*)", override, re.MULTILINE).group(1)
            labels = {key: val.strip('"') for key, val in re.findall(r"      (hako\.[a-z]+): (.+)", block)}
            state["containers"][name] = {"labels": labels, "ready": not bool(os.environ.get("UNREADY")), "running": True}
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
        match = re.search(r"-(kisara-dev|kisara|telegram|official):", image)
        name = match.group(1) if match else "napcat" if "napcat" in image else "music" if "ncm" in image else None
        if image == "python:3.12-slim": name = "hako"
        sys.exit(0 if name in state["images"] else 1)
    name = args[-1]
    if name not in state["containers"]: sys.exit(1)
    facts = state["containers"][name]
    fmt = value("--format")
    if ".State.Running" in fmt: print("true" if facts["running"] else "false")
    elif ".State.Status" in fmt: print("running" if facts["running"] else "exited")
    else:
        keys = re.findall(r'\.Config.Labels "([^"]+)"', fmt)
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
        match = re.search(r"-(kisara-dev|kisara|telegram|official):", image)
        name = match.group(1) if match else "hako"
        sys.exit(0 if name in state["dependencies"] else 1)
    if "--detach" in args:
        labels = dict(args[i+1].split("=",1) for i,x in enumerate(args) if x == "--label")
        state["containers"]["bot"] = {"labels": labels,"ready": not bool(os.environ.get("UNREADY")),"running": True}
        save(); print("bot"); sys.exit(0)
    sys.exit(0)
if "exec" in args:
    name = args[args.index("exec")+1]
    if "const requested" in " ".join(args):
        if os.environ.get("LISTENERS_FAIL"): sys.exit(5)
        for port in ([3001, 6099] if name == "napcat" else [3000]):
            print(os.environ.get("LISTENER_BIND", "0.0.0.0") + "|" + str(port))
        if os.environ.get("EXTRA_LISTENER"): print(os.environ["EXTRA_LISTENER"])
    elif "listeners" in args:
        if os.environ.get("BOT_LISTENER"): print(os.environ["BOT_LISTENER"])
    sys.exit(0 if state["containers"].get(name, {}).get("ready", False) else 1)
if "port" in args:
    if args[-1] == "napcat": print("6099/tcp -> " + os.environ.get("PORT_MAPPING", "127.0.0.1:6099"))
    sys.exit(0)
if "logs" in args:
    name = args[-1]
    if os.environ.get("LOG_FAIL"): print("raw must never be emitted"); sys.exit(4)
    if os.environ.get("LOG_TIMEOUT"): import time; time.sleep(10)
    print("watcher alive; application import failed")
    print("token=" + os.environ.get("ONEBOT_ACCESS_TOKEN", "secret-fixture"))
    print("account=" + os.environ.get("NAPCAT_ACCOUNT", "123456789"))
    print("https://name:pass@example.invalid/resource Bearer private-credential")
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
                 "preview-console.sh", "preview-deps.py", "preview-probe.py", "preview-listeners.js", "preview-constraints-py312.txt"):
        shutil.copy2(ROOT / "deploy" / name, tmp_path / "deploy" / name)
    for name in ("preview.sh", "hako", "start.sh", "pyproject.toml"):
        shutil.copy2(ROOT / name, tmp_path / name)
    (tmp_path / "config").mkdir()
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
    """Execute the thin entry from an unrelated directory."""
    return subprocess.run([str(tmp_path / "preview.sh"), *args], cwd="/tmp", env=env, capture_output=True, text=True)


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
    assert not any(word in result.stderr for word in ("secret-fixture", "123456789", "name:pass", "private-credential", "raw must never"))
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


def test_official_uses_credential_free_pinned_preparation_and_hako(tmp_path: Path) -> None:
    env, log = fixture(tmp_path, "official")
    env["KISARA_ENGINE"] = "official"
    result = run(tmp_path, env)
    assert result.returncode == 0, result.stderr
    installation = next(call for call in calls(log) if "install" in call)
    assert "--env-file" not in installation and "-p" not in installation
    assert not any("SECRET" in arg or "TOKEN" in arg for arg in installation)
    startup = next(call for call in calls(log) if "run" in call and "--detach" in call)
    assert "KISARA_PREVIEW_READINESS" in startup and "--label" in startup
    assert "bot: outbound" in result.stdout and "Listeners:" not in result.stdout
    log.write_text("")
    assert run(tmp_path, env).returncode == 0
    assert not any("run" in call for call in calls(log))


@pytest.mark.parametrize("flag,code", [("INSTALL_FAIL", 8), ("POSTINSTALL_FAIL", 1)])
def test_official_install_failure_never_starts(tmp_path: Path, flag: str, code: int) -> None:
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
