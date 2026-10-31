"""Keep terminal-control and secret redaction deterministic across caller locales."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest


ROOT = Path(__file__).resolve().parents[2]
PAYLOAD = ("\u6d88\u606f fi\x1b[31mxture\x1b[0m-secret\n"
           "osc fi\x1b]0;private-title\x07xture-secret\n"
           "st fi\x1b]0;private-title\x1b\\xture-secret\n"
           "control fi\rxture-secret\n"
           "backspace fi\x08xture-secret\n"
           "tab fi\txture-secret\n"
           "delete fi\x7fxture-secret\n"
           "native-art \u2588\n"
           "url https://txz.qq.com/p?k=synthetic-session\n")
EXPECTED = ("\u6d88\u606f [redacted]\nosc [redacted]\nst [redacted]\n"
            "control [redacted]\nbackspace [redacted]\ntab [redacted]\ndelete [redacted]\nurl [login-qr]\n")
BEARER_CASES = [
    ("known-{} Bearer{}fixture-secret".format(label, separator), "known-{} Bearer [redacted]".format(label))
    for label, separator in [("tab", "\t"), ("cr", "\r"), ("vt", "\v"), ("ff", "\f")]
] + [
    ("unknown-{} Bearer{}unconfigured-token".format(label, separator), "unknown-{} Bearer [redacted]".format(label))
    for label, separator in [("tab", "\t"), ("cr", "\r"), ("vt", "\v"), ("ff", "\f")]
] + [
    ("split Bearer\tfi\rxtu\x08re\t-se\x7fcret", "split Bearer [redacted]"),
    ("multiple Bearer\tfirst, Bearer\rsecond; bearer\vthird",
     "multiple Bearer [redacted], Bearer [redacted]; Bearer [redacted]"),
    ("already Bearer\t[redacted]", "already Bearer [redacted]"),
    ("no-token Bearer\t", "no-token Bearer"),
    ("word Bearerword", "word Bearerword"),
    ('quote Bearer\talpha"tail', 'quote Bearer [redacted]"tail'),
    ("apostrophe Bearer\tbeta'tail", "apostrophe Bearer [redacted]'tail"),
    ("comma Bearer\tgamma,tail", "comma Bearer [redacted],tail"),
    ("semicolon Bearer\tdelta;tail", "semicolon Bearer [redacted];tail"),
    ('quoted-token Bearer\t"value"', 'quoted-token Bearer"value"'),
    ("empty-boundary Bearer\t, Bearer\t;", "empty-boundary Bearer, Bearer;"),
]
PAYLOAD += "".join(source + "\n" for source, _ in BEARER_CASES)
EXPECTED += "".join(expected + "\n" for _, expected in BEARER_CASES)
SCRIPT = r'''
set -Eeuo pipefail
source "$1/deploy/preview-runtime.sh"
preview_tmp=$2
before_locale=${LC_ALL+x}:${LC_ALL-}
preview_secrets=(fixture-secret)
preview_filters=()
preview_redact_values show
preview_replace_secrets <"$FIXTURE_LOG" >"$preview_tmp/normalized"
[[ ${LC_ALL+x}:${LC_ALL-} == "$before_locale" ]]
case $3 in
buffered) preview_redact "$FIXTURE_LOG" ;;
snapshot)
    preview_owned() { return 0; }
    preview_docker_command=("$preview_tmp/bin/docker")
    qq_login_snapshot owned-napcat
    cat -- "$qq_snapshot"
    ;;
streaming)
    preview_owned() { return 0; }
    preview_log() { :; }
    preview_platform() { printf '%s' onebot; }
    preview_log_lines() { cat; }
    services=(kisara)
    declare -A preview_ids=([kisara]=owned-app)
    preview_docker_command=("$preview_tmp/bin/docker")
    preview_log_pids=()
    preview_start_log_readers
    printf '%s\n' "${preview_log_pids[2]}" >"$preview_tmp/tracked-sanitizer"
    for pid in "${preview_log_pids[@]}"; do wait "$pid"; done
    ;;
esac
[[ ${LC_ALL+x}:${LC_ALL-} == "$before_locale" ]]
'''


def redaction_probe(tmp_path: Path, mode: str, log_locale: Optional[str], *, broken_sed: bool = False) -> tuple:
    """Exercise real normalization/filter entry points with a recording, non-Docker peer."""
    binary = tmp_path / "bin"
    binary.mkdir()
    sed = binary / "sed"
    sed.write_text('#!/usr/bin/env bash\n'
                   'printf "%s\\n" "${LC_ALL-unset}" >>"$SED_LOCALE_OBSERVATIONS"\n'
                   'printf "%s\\n" "$BASHPID" >>"$SED_PID_OBSERVATIONS"\n'
                   + ('exit 23\n' if broken_sed else 'exec "$REAL_SED" "$@"\n'))
    sed.chmod(0o755)
    docker = binary / "docker"
    docker.write_text('#!/usr/bin/env bash\n'
                      'case $1 in\n'
                      'exec) printf "%s\\n" "2026-10-26T00:00:00.000000Z" ;;\n'
                      'logs) cat -- "$FIXTURE_LOG" ;;\n'
                      '*) exit 2 ;;\nesac\n')
    docker.chmod(0o755)
    source = tmp_path / "input"
    source.write_text(PAYLOAD)
    observations = tmp_path / "sed-locales"
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("KISARA_", "ONEBOT_", "NAPCAT_", "TELEGRAM_", "OFFICIAL_"))}
    env.update(PATH=str(binary) + os.pathsep + os.environ["PATH"], LANG="C.UTF-8",
               ONEBOT_BILIBILI_SESSDATA="fixture-secret", FIXTURE_LOG=str(source),
               SED_LOCALE_OBSERVATIONS=str(observations), SED_PID_OBSERVATIONS=str(tmp_path / "sed-pids"),
               REAL_SED=shutil.which("sed"), TERM="dumb")
    if log_locale is None:
        env.pop("LC_ALL", None)
    else:
        env["LC_ALL"] = log_locale
    result = subprocess.run(["bash", "-c", SCRIPT, "bash", str(ROOT), str(tmp_path), mode],
                            env=env, text=True, capture_output=True, timeout=10)
    return result, observations.read_text().splitlines() if observations.exists() else [], tmp_path / "normalized"


@pytest.mark.parametrize("mode", ["buffered", "streaming", "snapshot"])
@pytest.mark.parametrize("log_locale", ["C", "POSIX", "C.UTF-8", None])
def test_internal_regex_locale_is_scoped_and_unicode_survives(
    tmp_path: Path, mode: str, log_locale: Optional[str],
) -> None:
    result, observations, normalized = redaction_probe(tmp_path, mode, log_locale)
    assert result.returncode == 0, result.stderr
    assert result.stdout + result.stderr == EXPECTED
    assert observations == ["C"] * (2 if mode == "streaming" else 1)
    assert "[redacted]" in normalized.read_text() and "\x1b" not in normalized.read_text()
    assert "fixture-secret" not in result.stdout + result.stderr


@pytest.mark.parametrize("mode", ["buffered", "streaming", "snapshot"])
@pytest.mark.parametrize("log_locale", ["en_US.utf8", "zh_CN.utf8"])
def test_installed_non_c_collation_redacts_ansi_interleaved_secrets(
    tmp_path: Path, mode: str, log_locale: str,
) -> None:
    available = subprocess.run(["locale", "-a"], text=True, capture_output=True, check=True).stdout.splitlines()
    if log_locale not in available:
        pytest.skip("Real locale {} is not installed; unsupported-locale fallback is not evidence".format(log_locale))
    result, observations, normalized = redaction_probe(tmp_path, mode, log_locale)
    assert result.returncode == 0, result.stderr
    assert result.stdout + result.stderr == EXPECTED
    assert observations == ["C"] * (2 if mode == "streaming" else 1)
    assert normalized.read_text().startswith("\u6d88\u606f [redacted]\n")
    assert "\x1b" not in normalized.read_text()


def test_buffered_filter_failure_never_emits_raw_input(tmp_path: Path) -> None:
    result, observations, _ = redaction_probe(tmp_path, "buffered", "C.UTF-8", broken_sed=True)
    assert result.returncode != 0 and result.stdout + result.stderr == ""
    assert observations == ["C"]


def test_stream_cleanup_tracks_the_sanitizer_process_itself(tmp_path: Path) -> None:
    result, _, _ = redaction_probe(tmp_path, "streaming", "C.UTF-8")
    assert result.returncode == 0, result.stderr
    sanitizer = (tmp_path / "sed-pids").read_text().splitlines()[-1]
    assert (tmp_path / "tracked-sanitizer").read_text().strip() == sanitizer
