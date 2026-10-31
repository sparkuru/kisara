# Implementation evidence

## Scope and context

Implemented the approved saved-PNG event flow in existing QQ log views, with
Pillow already present in the application runtime. No dependency, WebUI API,
session, status watcher, account operation, live service mutation or commit was
introduced. All preexisting video-export and shared deployment edits remain.

Native injection included the hook marker and a saved full-output notice at
`/tmp/hook_outputs/01a17659-2a57-7ea3-b6f2-2224682bcfad/2d52888a-7c06-4d6c-9b2f-c8fdb240c868.txt`.
The implementer read that output, then separately read the task artifacts and
applicable spec files in smaller reads because combined tool output truncated.
Python and shell skills were loaded. ShellCheck/shfmt are unavailable; no
configured application lint/type checker exists.

## Program evidence

Read-only static `/app/napcat/napcat.mjs` excerpts establish:

- Winston timestamps use `MM-DD HH:mm:ss`; console rows are
  `${timestamp} [${level}] ${optionalNicknamePipe}${message}`.
- `setLogSelfInfo` supplies the account nickname as that optional prefix.
- PNG-saved output follows the `writeFile` callback for `cache/qrcode.png`.
- The scan event logs `[Core] [Login] 二维码已被扫描，等待确认...`.
- Successful initialization logs `[NapCat] 已通知主进程登录成功` after the login
  promise resolves; the parent worker also reports successful worker login.

No runtime QR payload or private config/log history was printed for this work.

## Implementation details

- `qq-login-logs.sh` shares login-aware log consumption and fixed-path image
  reading across preview and ordinary attached QQ logs.
- Interactive replay uses a finite timestamped snapshot, merging stdout and
  stderr. Inclusive follow starts from the last snapshot record; equal-time
  records are skipped by count, allowing newly appended equal-time records.
  An empty/tail-zero snapshot uses a bounded container-clock cutoff obtained
  before the snapshot; there is no `--tail all` without a `--since` cutoff.
- Later scanned/error/success records invalidate earlier historical PNG events.
  The image must be regular, non-symlink, <=1 MiB and stable while read.
  Its mtime may precede the saved event by at most two seconds, and may not be
  later except for one microsecond of timestamp conversion precision. Thus a
  PNG overwritten 0.5 seconds after an old marker is rejected.
- Pillow finds the QR's seven-module finder run and reduces complete uniform
  module cells, adds a four-module quiet border and writes compact half-block
  text. The terminal check reserves heading/cursor rows. Unsupported geometry
  produces recovery guidance instead of arbitrary resampling.
- Output serialization prevents other logs/readiness lines splitting a QR
  block. Inflight image commands are reaped on cancellation. Native QR/URL
  text remains suppressed in generic diagnostics; ANSI sequences are removed
  before secret replacement. Exact UTF-8 byte escapes make event matching
  independent of C/POSIX locale Unicode-escape behavior.
- Ordinary selected auxiliary logs remain included; preview exclusions remain.
  A running application is selected when the logical QQ group contains both
  stopped ordinary and running development app identities.

## Checks actually run

- Initial `./hako python -m pytest tests/unit/test_qq_login_png.py -q`:
  12 failed before the rendering helper existed. After implementation: 12 passed.
- First new CLI/PTY pass after fixture/TTY corrections: 11 passed in 54.72s.
- Expanded focused QR plus existing routing/removal regressions:
  `./hako python -m pytest tests/unit/test_qq_login_png.py tests/unit/test_qq_login_logs.py tests/unit/test_preview_lifecycle.py -k 'qq_login or onebot_forwarder_diagnostics_cover_dev_mode or stop_removed' -q --maxfail=1 --tb=short`:
  38 passed, 180 deselected in 105.94s. This includes inflight-render cleanup,
  exact terminal-height boundary, ordinary auxiliary output and active dev
  runtime selection.
- Added C/POSIX QR event regressions: 2 passed, 17 deselected in 11.51s.
- Added sub-second overwritten-PNG regression (`-k recent`):
  1 passed, 18 deselected in 5.66s.
- Canonical CLI/engine/readiness focused suite:
  `./hako python -m pytest tests/unit/test_kisara_cli.py tests/unit/test_engine_deployment.py tests/unit/test_preview_readiness.py -q --maxfail=1 --tb=short`:
  126 passed, 1 existing skip in 16.40s.
- Earlier whole preview lifecycle run: 178 passed, then one old assertion
  expected Compose log forwarding rather than the new shared consumer.
  Its assertion now checks the same actual owned NapCat/dev IDs, tail and
  no-effects contract; the updated routing cases passed in the focused run.
  This intermediate run is not a final full-regression pass.
- `bash -n` for all four changed shell files and `git diff --check`: passed.

## Independent rendering verification

In a one-off existing hako container, installed `zxing-cpp==2.3.0` with binary
wheels into container-local `/tmp/kisara-qr-decoder-*`. No repository/runtime
dependency or file was added. Reconstructed emitted terminal cells into pixels
and independently decoded each image. All eight cases (integer PNG scales
1/2/5/8, ANSI and plain) decoded to the synthetic fixture's payload.
The fixture matrix was generated once with a temporary Segno 1.6.6 encoder;
production and normal tests require neither encoder nor decoder packages.

## Remaining verification

Independent checker owns final review/fixes and the required complete suite.
Real phone scanning remains human-required/pending and is not established by
the decoded synthetic PNG fixtures. No live login or deployment was attempted.

## Main-session existing PNG format probe

Reverified the running NapCat container's exact Compose project/service,
repository working directory and base configuration labels. A ten-second
bounded fixed-path read of `/app/napcat/cache/qrcode.png` (regular file,
non-symlink, <=1 MiB) was piped privately into one existing `hako` invocation.
That invocation loaded `deploy/qq-login-png.py` and called `render_png` with
ample terminal dimensions, without printing its returned text.

Observed only `Existing NapCat PNG dimensions: (147, 147)` and
`Existing NapCat PNG format: renderable`; pipeline exit 0. No actual bitmap,
payload, URL or hash was printed or saved. This verifies the actual cached QQ
PNG's compatibility with module-preserving rendering, not current login state,
challenge validity or successful phone authorization. No live account/service
state was changed and no login/status API was called.
