"""Exercise login PNG events through the existing CLI with a private fake daemon."""

import codecs
import datetime
import fcntl
import json
import os
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path

import pytest

from test_preview_lifecycle import calls, child_processes, fixture, run, save_state, state
from test_qq_login_png import png


PROMPT = "10-26 11:22:48 [warn] \u8bf7\u626b\u63cf\u4e0b\u9762\u7684\u4e8c\u7ef4\u7801\uff0c\u7136\u540e\u5728\u624bQ\u4e0a\u6388\u6743\u767b\u5f55\uff1a"
SAVED = "10-26 11:22:48 [warn] \u4e8c\u7ef4\u7801\u5df2\u4fdd\u5b58\u5230 /app/napcat/cache/qrcode.png"
SUCCESS = "10-26 11:22:49 [info] [NapCat] \u5df2\u901a\u77e5\u4e3b\u8fdb\u7a0b\u767b\u5f55\u6210\u529f"
TITLE = "Scan this QR with mobile QQ"
QR_DOCKER = r'''
if os.environ.get("QR_FIXTURE") and "exec" in args:
    import subprocess
    command_index = args.index("exec") + 1
    if args[command_index] == "-i": command_index += 1
    name = container_key(args[command_index])
    if not state["containers"].get(name, {}).get("running", False):
        print("container stopped", file=sys.stderr)
        sys.exit(1)
    code = args[command_index + 3] if len(args) > command_index + 3 else ""
    if "datetime.datetime.now" in code:
        import datetime
        print(datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")); sys.exit(0)
    if "os.O_NOFOLLOW" in code:
        code = code.replace("/app/napcat/cache/qrcode.png", str(root / "qr.png"))
        result = subprocess.run([sys.executable, "-c", code, args[-1]])
        sys.exit(result.returncode)
    if "Render an existing login PNG" in code:
        if os.environ.get("QR_RENDER_MISSING"): sys.exit(127)
        if os.environ.get("QR_RENDER_DELAY"):
            import time
            (root / "qr-render.pid").write_text(str(os.getpid()))
            time.sleep(15)
        result = subprocess.run([sys.executable, "-c", code, *args[-3:]], input=sys.stdin.buffer.read())
        sys.exit(result.returncode)
if os.environ.get("QR_FIXTURE") and "logs" in args and container_key(args[-1]) == "napcat":
    import time
    history = json.loads((root / "qr-history.json").read_text())
    target = sys.stderr if os.environ.get("QR_STDERR") else sys.stdout
    def emit(record):
        stamp, text = record
        print((stamp + " " if "--timestamps" in args else "") + text, file=target, flush=True)
    if "--follow" not in args:
        if args[args.index("--tail") + 1] != "0":
            for record in history: emit(record)
        sys.exit(0)
    (root / "napcat.reader.pid").write_text(str(os.getpid()))
    if "--since" in args:
        cutoff = args[args.index("--since") + 1]
        for record in history:
            if record[0] >= cutoff: emit(record)
    else:
        for record in history: emit(record)
    print("napcat-live-attached", file=target, flush=True)
    offset = 0
    while True:
        queue = json.loads((root / "qr-live.json").read_text())
        for record in queue[offset:]: emit(record)
        offset = len(queue)
        if (root / "qr-eof").exists(): sys.exit(0)
        time.sleep(0.02)
'''


def timestamp(offset: float = 0) -> str:
    """Use one clock for synthetic Docker events and the fixture file metadata."""
    value = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=offset)
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def install_qr_fixture(tmp_path: Path) -> tuple:
    """Prepare ordinary owned containers before attaching the event-driven view."""
    env, log = fixture(tmp_path)
    assert run(tmp_path, env, "start").returncode == 0
    docker = tmp_path / "bin/docker"
    source = docker.read_text()
    docker.write_text(source.replace('if "exec" in args:', QR_DOCKER + '\nif "exec" in args:', 1))
    env.update(QR_FIXTURE="1", FOLLOW_CONTROLLED="1", TERM="xterm", KISARA_PREVIEW_TIMEOUT="15")
    stamp = timestamp()
    write_png(tmp_path, stamp)
    (tmp_path / "qr-history.json").write_text(json.dumps([[stamp, PROMPT], [stamp, SAVED]]))
    (tmp_path / "qr-live.json").write_text("[]")
    log.write_text("")
    return env, log, stamp


def write_png(tmp_path: Path, stamp: str, changed: bool = False) -> None:
    """Write an actual PNG with a matching synthetic saved-event timestamp."""
    path = tmp_path / "qr.png"
    path.write_bytes(png(changed=changed))
    seconds = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    os.utime(path, (seconds, seconds))


def attach(tmp_path: Path, env: dict, args: list, columns: int = 100, rows: int = 40) -> tuple:
    """Give the real CLI a terminal without granting it access to a live daemon."""
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
    process = subprocess.Popen([str(tmp_path / "kisara.sh"), *args], env=env, cwd="/tmp",
                               stdin=subprocess.DEVNULL, stdout=slave, stderr=slave, start_new_session=True)
    process.qr_decoder = codecs.getincrementaldecoder("utf-8")()
    os.close(slave)
    return process, master


def read_until(process: subprocess.Popen, master: int, expected: str, count: int = 1, output: str = "") -> str:
    """Require terminal output before EOF while preserving trailing QR spaces."""
    deadline = time.monotonic() + 12
    decoder = process.qr_decoder
    while time.monotonic() < deadline:
        if output.count(expected) >= count:
            return output
        if select.select([master], [], [], 0.1)[0]:
            try:
                output += decoder.decode(os.read(master, 65536))
            except OSError:
                break
        assert process.poll() is None, output
    pytest.fail("Missing terminal output: " + expected + "\n" + output)


def stop(process: subprocess.Popen, master: int, termination: int = signal.SIGTERM) -> None:
    """Stop only the test invocation and close its terminal."""
    if process.poll() is None:
        process.send_signal(termination)
        assert process.wait(timeout=5) == (130 if termination == signal.SIGINT else 143)
    os.close(master)


@pytest.mark.parametrize("args", [["preview", "status", "onebot"], ["logs", "onebot"],
                                 ["preview", "start", "onebot"]])
def test_existing_log_commands_render_refresh_and_keep_qr_blocks_intact(tmp_path: Path, args: list) -> None:
    env, log, stamp = install_qr_fixture(tmp_path)
    env["QR_STDERR"] = "1"
    before = state(tmp_path)["containers"]
    process, master = attach(tmp_path, env, args)
    try:
        output = read_until(process, master, TITLE)
        output = read_until(process, master, "napcat-live-attached", output=output)
        assert output.count(TITLE) == 1
        rows = output.split(TITLE, 1)[1].splitlines()[1:22]
        assert len(rows) == 21 and all(len(row) == 41 and set(row) <= set("█▀▄ ") for row in rows)
        # Same timestamp records in the overlap must not be replayed, while a new
        # record with that exact timestamp still reaches the live stream.
        (tmp_path / "qr-live.json").write_text(json.dumps([[stamp, "same-timestamp-new-record"]]))
        output = read_until(process, master, "same-timestamp-new-record", output=output)
        updated = timestamp()
        write_png(tmp_path, updated, changed=True)
        (tmp_path / "qr-live.json").write_text(json.dumps([[stamp, "same-timestamp-new-record"], [updated, PROMPT], [updated, SAVED]]))
        output = read_until(process, master, TITLE, count=2, output=output)
        assert output.count(SAVED) == 2
        assert not any("/api/" in str(call) for call in calls(log))
        if args[0] == "logs" or args[1] == "status":
            assert state(tmp_path)["containers"] == before
            assert not any(any(op in call for op in ("up", "build", "pull", "stop", "rm")) for call in calls(log))
    finally:
        stop(process, master)


@pytest.mark.parametrize("scenario,expected", [("success", "napcat-live-attached"),
                                              ("stale", "stale-png"), ("missing", "png-unavailable"),
                                              ("recent-overwrite", "stale-png"),
                                              ("corrupt", "png-render-or-terminal-size"),
                                              ("narrow", "png-render-or-terminal-size")])
def test_historical_login_outcome_and_png_failure_paths(tmp_path: Path, scenario: str, expected: str) -> None:
    env, log, stamp = install_qr_fixture(tmp_path)
    if scenario == "success":
        (tmp_path / "qr-history.json").write_text(json.dumps([[stamp, PROMPT], [stamp, SAVED], [stamp, SUCCESS]]))
    elif scenario == "stale":
        write_png(tmp_path, timestamp(10))
    elif scenario == "recent-overwrite":
        newer = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00")) + datetime.timedelta(seconds=0.5)
        write_png(tmp_path, newer.isoformat().replace("+00:00", "Z"))
    elif scenario == "missing":
        (tmp_path / "qr.png").unlink()
    elif scenario == "corrupt":
        (tmp_path / "qr.png").write_bytes(b"not a PNG")
        seconds = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
        os.utime(tmp_path / "qr.png", (seconds, seconds))
    process, master = attach(tmp_path, env, ["preview", "status"], columns=30 if scenario == "narrow" else 100)
    try:
        output = read_until(process, master, expected)
        assert TITLE not in output
        if scenario == "success":
            assert not any("os.O_NOFOLLOW" in str(call) for call in calls(log))
    finally:
        stop(process, master)


def test_non_tty_login_event_has_a_safe_recovery_hint_without_png_read(tmp_path: Path) -> None:
    env, log, stamp = install_qr_fixture(tmp_path)
    out = tmp_path / "stdout"
    with out.open("w") as stream:
        process = subprocess.Popen([str(tmp_path / "kisara.sh"), "preview", "status"], env=env,
                                   stdout=stream, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and "terminal-output-required" not in out.read_text():
            assert process.poll() is None
            time.sleep(0.02)
        assert "terminal-output-required" in out.read_text()
        assert TITLE not in out.read_text() and not any("os.O_NOFOLLOW" in str(call) for call in calls(log))
    finally:
        process.send_signal(signal.SIGTERM)
        assert process.wait(timeout=5) == 143


def test_empty_zero_tail_uses_a_bounded_live_cutoff(tmp_path: Path) -> None:
    env, log, stamp = install_qr_fixture(tmp_path)
    env["KISARA_LOG_TAIL"] = "0"
    process, master = attach(tmp_path, env, ["logs", "onebot"])
    try:
        output = read_until(process, master, "napcat-live-attached")
        assert TITLE not in output
        follows = [call for call in calls(log) if "logs" in call and "--follow" in call and call[-1] == "napcat"]
        assert follows and all("--since" in call for call in follows)
        updated = timestamp()
        write_png(tmp_path, updated)
        (tmp_path / "qr-live.json").write_text(json.dumps([[updated, PROMPT], [updated, SAVED]]))
        read_until(process, master, TITLE, output=output)
    finally:
        stop(process, master)


@pytest.mark.parametrize("locale", ["C", "POSIX"])
def test_qr_events_are_recognized_in_byte_oriented_locales(tmp_path: Path, locale: str) -> None:
    env, log, stamp = install_qr_fixture(tmp_path)
    env["LC_ALL"] = locale
    process, master = attach(tmp_path, env, ["preview", "status"])
    try:
        read_until(process, master, TITLE)
    finally:
        stop(process, master)


@pytest.mark.parametrize("source", ["snapshot", "live"])
def test_qr_timestamp_metadata_survives_colliding_secret_redaction(tmp_path: Path, source: str) -> None:
    """Redact message secrets without corrupting the PNG event's private timestamp."""
    env, log, _ = install_qr_fixture(tmp_path)
    env["NAPCAT_WEBUI_TOKEN"] = "314159"
    stamp = timestamp().split(".", 1)[0] + ".314159Z"
    write_png(tmp_path, stamp)
    records = [[stamp, PROMPT], [stamp, SAVED], [stamp, "private-value=314159 metadata-test-end"]]
    (tmp_path / "qr-history.json").write_text(json.dumps(records if source == "snapshot" else []))
    process, master = attach(tmp_path, env, ["logs", "onebot"])
    try:
        output = ""
        if source == "live":
            output = read_until(process, master, "napcat-live-attached")
            (tmp_path / "qr-live.json").write_text(json.dumps(records))
        output = read_until(process, master, TITLE, output=output)
        output = read_until(process, master, "metadata-test-end", output=output)
        if source == "snapshot":
            output = read_until(process, master, "napcat-live-attached", output=output)
            assert output.count(TITLE) == 1 and output.count(SAVED) == 1
        assert "private-value=[redacted]" in output
        assert "314159" not in output and "png-unavailable" not in output
        image_reads = [call for call in calls(log) if "os.O_NOFOLLOW" in str(call)]
        assert image_reads and all(call[-1] == stamp for call in image_reads)
    finally:
        stop(process, master)


def test_public_url_count_keeps_numbers_while_actual_credentials_are_redacted(tmp_path: Path) -> None:
    """URL count limits are ordinary configuration, not URL credentials."""
    env, _ = fixture(tmp_path)
    env.update(ONEBOT_EXPORT_MAX_URLS="3", KISARA_EXPORT_MAX_URLS="3",
               ONEBOT_MUSIC_API_URL="https://provider.invalid/private", ONEBOT_BILIBILI_SESSDATA="session-private",
               ONEBOT_ACCESS_TOKEN="token-private")
    script = ('source "$1/deploy/preview-runtime.sh"; preview_secrets=(); preview_filters=(); '
              'preview_redact_values show; '
              'printf "%s\\n" "2026-10-26T06:05:47.123456789Z retry=3.5 count=3 '
              'https://provider.invalid/private session-private token-private" '
              '| preview_replace_secrets | preview_filter_logs')
    result = subprocess.run(["bash", "-c", script, "bash", str(tmp_path)], env=env,
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "2026-10-26T06:05:47.123456789Z retry=3.5 count=3 [redacted] [redacted] [redacted]\n"


@pytest.mark.parametrize("scenario,expected", [("invalid-event", 5), ("missing", 2),
                                              ("permission", 6), ("oversized", 3)])
def test_png_reader_reports_controlled_failure_categories(tmp_path: Path, scenario: str, expected: int) -> None:
    """Keep invalid metadata distinguishable from filesystem failures without raw errors."""
    env, _ = fixture(tmp_path)
    source = subprocess.run(["bash", "-c", 'source "$1/deploy/qq-login-logs.sh"; qq_login_png_reader_source',
                             "bash", str(tmp_path)], env=env, text=True, capture_output=True, check=True).stdout
    path = tmp_path / "reader.png"
    source = source.replace("/app/napcat/cache/qrcode.png", str(path))
    if scenario == "permission":
        path.write_bytes(png())
        path.chmod(0)
    elif scenario == "oversized":
        path.write_bytes(b"x" * (1024 * 1024 + 1))
    stamp = "invalid" if scenario == "invalid-event" else timestamp()
    try:
        result = subprocess.run([sys.executable, "-c", source, stamp], capture_output=True)
        assert result.returncode == expected
        assert result.stdout == result.stderr == b""
    finally:
        if path.exists():
            path.chmod(0o600)


@pytest.mark.parametrize("fraction", ["", ".123", ".123456", ".123456789"])
def test_png_reader_uses_python310_compatible_nanosecond_metadata(tmp_path: Path, fraction: str) -> None:
    """Exercise the reader against Python3.10's fractional-parser constraint."""
    env, _ = fixture(tmp_path)
    source = subprocess.run(["bash", "-c", 'source "$1/deploy/qq-login-logs.sh"; qq_login_png_reader_source',
                             "bash", str(tmp_path)], env=env, text=True, capture_output=True, check=True).stdout
    path = tmp_path / "reader.png"
    data = png()
    path.write_bytes(data)
    stamp = "2026-10-26T06:05:47" + fraction + "Z"
    seconds = int(datetime.datetime(2026, 10, 26, 6, 5, 47, tzinfo=datetime.timezone.utc).timestamp())
    event_ns = seconds * 1000000000 + int((fraction.lstrip(".") or "0").ljust(9, "0"))
    os.utime(path, ns=(event_ns, event_ns))
    source = source.replace("/app/napcat/cache/qrcode.png", str(path))
    compatibility_guard = '''import datetime, re
class Python310Datetime(datetime.datetime):
    @classmethod
    def fromisoformat(cls, value):
        fraction = re.search(r"\\.([0-9]+)", value)
        if fraction and len(fraction[1]) > 6:
            raise ValueError("Python3.10 rejects nanosecond fractions")
        return super().fromisoformat(value)
datetime.datetime = Python310Datetime
'''
    result = subprocess.run([sys.executable, "-c", compatibility_guard + source, stamp], capture_output=True)
    assert result.returncode == 0 and result.stderr == b""
    assert result.stdout == data


def test_complete_ansi_sequences_are_removed_before_short_secret_replacement(tmp_path: Path) -> None:
    env, log = fixture(tmp_path)
    result = subprocess.run(["bash", "-c", 'source "$1/deploy/preview-runtime.sh"; preview_secrets=(3); '
                             'printf "\\033[33mhello\\033[0m \\033]8;;https://example.invalid\\007label\\033]8;;\\007 value=3\\n" | preview_replace_secrets',
                             "bash", str(tmp_path)], env=env, text=True, capture_output=True)
    assert result.returncode == 0 and result.stdout == "hello label value=[redacted]\n"


def test_account_prefixed_relogin_and_ordinary_auxiliary_logs(tmp_path: Path) -> None:
    env, log, stamp = install_qr_fixture(tmp_path)
    (tmp_path / "qr-history.json").write_text(json.dumps([
        [stamp, PROMPT.replace("[warn] ", "[warn] Fixture Bot | ")],
        [stamp, SAVED.replace("[warn] ", "[warn] Fixture Bot | ")],
    ]))
    assert run(tmp_path, {key: value for key, value in env.items() if key not in {"QR_FIXTURE", "FOLLOW_CONTROLLED"}}, "start", "music").returncode == 0
    before = state(tmp_path)
    process, master = attach(tmp_path, env, ["logs", "onebot,music"])
    try:
        output = read_until(process, master, TITLE)
        output = read_until(process, master, "music | history-end music", output=output)
        assert state(tmp_path) == before
    finally:
        stop(process, master)


def test_render_uses_running_dev_runtime_in_the_logical_qq_group(tmp_path: Path) -> None:
    env, log, stamp = install_qr_fixture(tmp_path)
    value = state(tmp_path)
    active = json.loads(json.dumps(value["containers"]["kisara"]))
    active["id"] = "kisara-dev"
    active["labels"]["com.docker.compose.service"] = "kisara-dev"
    value["containers"]["kisara-dev"] = active
    value["containers"]["kisara"]["running"] = False
    save_state(tmp_path, value)
    process, master = attach(tmp_path, env, ["logs", "onebot"])
    try:
        read_until(process, master, TITLE)
        render_calls = [call for call in calls(log) if "Render an existing login PNG" in str(call)]
        assert render_calls and all(call[call.index("-i") + 1] == "kisara-dev" for call in render_calls)
    finally:
        stop(process, master)


@pytest.mark.parametrize("rows,shown", [(22, False), (23, True)])
def test_terminal_height_reserves_heading_and_cursor_rows(tmp_path: Path, rows: int, shown: bool) -> None:
    env, log, stamp = install_qr_fixture(tmp_path)
    process, master = attach(tmp_path, env, ["preview", "status"], rows=rows)
    try:
        output = read_until(process, master, TITLE if shown else "png-render-or-terminal-size")
        assert (TITLE in output) == shown
    finally:
        stop(process, master)


def test_cancellation_reaps_an_inflight_png_render_command(tmp_path: Path) -> None:
    env, log, stamp = install_qr_fixture(tmp_path)
    env["QR_RENDER_DELAY"] = "1"
    process, master = attach(tmp_path, env, ["preview", "status"])
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path / "qr-render.pid").exists() and time.monotonic() < deadline:
            assert process.poll() is None
            time.sleep(0.02)
        assert (tmp_path / "qr-render.pid").exists()
        descendants = child_processes(process.pid)
        process.send_signal(signal.SIGTERM)
        assert process.wait(timeout=5) == 143
        assert all(not Path("/proc", str(pid)).exists() for pid in descendants)
    finally:
        stop(process, master)


@pytest.mark.parametrize("failure", ["write", "lock"])
def test_serialized_output_propagates_errors_and_closes_lock(tmp_path: Path, failure: str) -> None:
    """Failed output cannot look successful or leave an acquired descriptor open."""
    env, _ = fixture(tmp_path)
    script = ('source "$1/deploy/preview-console.sh"; preview_output_lock="$2/output.lock"; '
              'if [[ $3 == lock ]]; then flock() { return 74; }; fi; '
              'before=(/proc/$$/fd/*); '
              'preview_write 1 synthetic >/dev/full 2>/dev/null; write_status=$?; '
              'after=(/proc/$$/fd/*); '
              '[[ $write_status -ne 0 && ${#before[@]} -eq ${#after[@]} ]]')
    result = subprocess.run(["bash", "-c", script, "bash", str(tmp_path), str(tmp_path), failure],
                            env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_atomic_sections_keep_plain_url_rows(tmp_path: Path) -> None:
    """Serialization must retain heading-only color and plain URL/body text."""
    env, _ = fixture(tmp_path)
    env.pop("NO_COLOR", None)
    env["TERM"] = "xterm"
    master, slave = pty.openpty()
    try:
        script = ('source "$1/deploy/preview-console.sh"; '
                  'preview_output_lock="$1/output.lock"; '
                  'preview_section Endpoints http://example.invalid/')
        result = subprocess.run(["bash", "-c", script, "bash", str(tmp_path)], env=env,
                                stdout=slave, stderr=subprocess.PIPE, text=True)
        output = os.read(master, 4096).decode("utf-8").replace("\r\n", "\n")
        assert result.returncode == 0, result.stderr
        assert output == "\n\x1b[1;32mEndpoints:\x1b[0m\nhttp://example.invalid/\n"
    finally:
        os.close(slave)
        os.close(master)


def test_invalid_log_tail_is_rejected_before_scratch_creation(tmp_path: Path) -> None:
    """Invalid input must not create an unowned preview temporary directory."""
    env, log, _ = install_qr_fixture(tmp_path)
    before = state(tmp_path)
    env.update(KISARA_LOG_TAIL="invalid", QR_MKTEMP_CALLS=str(tmp_path / "mktemp.called"),
               QR_REAL_MKTEMP=shutil.which("mktemp", path=env["PATH"]))
    wrapper = tmp_path / "bin/mktemp"
    wrapper.write_text('#!/usr/bin/env bash\nprintf "called\\n" >"$QR_MKTEMP_CALLS"\n'
                       'exec "$QR_REAL_MKTEMP" "$@"\n')
    wrapper.chmod(0o755)
    result = subprocess.run([str(tmp_path / "kisara.sh"), "logs", "onebot"], env=env,
                            text=True, capture_output=True)
    assert result.returncode == 2
    assert not (tmp_path / "mktemp.called").exists()
    assert state(tmp_path) == before
    assert not any("logs" in call for call in calls(log))


@pytest.mark.parametrize("args", [["logs", "onebot"], ["preview", "status", "onebot"]])
def test_stopped_napcat_retains_available_diagnostic_logs(tmp_path: Path, args: list) -> None:
    """A stopped gateway's history must not require a running QR clock helper."""
    env, log, _ = install_qr_fixture(tmp_path)
    value = state(tmp_path)
    value["containers"]["napcat"]["running"] = False
    save_state(tmp_path, value)
    before = state(tmp_path)
    process, master = attach(tmp_path, env, args)
    try:
        output = read_until(process, master, "napcat-live-attached")
        assert TITLE not in output
        assert not any("datetime.datetime.now" in str(call) for call in calls(log))
        assert state(tmp_path) == before
    finally:
        stop(process, master)
