# Runtime PNG failure: implementation evidence

## Scope and loading

Continued the existing approved event-driven PNG/log task after the user's real
log showed a recognized saved-PNG event followed by `png-unavailable`.
Read the native full hook output (1,874 lines) from its saved notice in bounded
chunks, including curated specs and task artifacts, then loaded Python/shell
skills and the current mainline. Preserve the separate locale/Bearer repair in
`preview-runtime.sh` and `test_preview_redaction_locale.py` unchanged.

No running/stopped QQ container was available to the main session for reading
historical per-exec stderr. Consequently these results establish two concrete
failure mechanisms and fixes, rather than claiming real phone authorization.
No service/account mutation, login API, dependency, watcher or delivery was added.

## Proven causes

1. `preview_redact_values` matched `*URL*`, treating public
   `ONEBOT_EXPORT_MAX_URLS=3` / `KISARA_EXPORT_MAX_URLS=3` as credentials. Literal
   replacement then damaged ordinary timestamps, durations and hashes.
   A new count/credential regression failed before the fix, showing
   `.12[redacted]456789Z`, `retry=[redacted].5` and `count=[redacted]`.
2. Timestamped Docker records were sanitized as undifferentiated message text.
   A genuine synthetic secret matching a fractional timestamp corrupted private
   event metadata too. Both snapshot and live actual CLI/PTY paths reproduced
   the user's exact `png-unavailable` hint with the real PNG reader source:
   two failed tests in 30.64 seconds. Snapshot boundary corruption also replayed
   historical records. The original reader collapsed invalid-date parsing into
   the same exit category as missing files.
3. The cached NapCat image uses Python3.10, while the existing fake-reader tests
   run Python3.12. Python3.10 rejects Docker's nine-digit fractional timestamp
   in `datetime.fromisoformat`. The exact reader source, before the compatibility
   fix, exited5 (new controlled invalid-timestamp category) in that cached image
   on `2026-10-26T06:05:47.123456789Z` despite an existing matching synthetic PNG.

## Fixes

- Classify configured URL values by the semantic `*_URL` suffix, preserving
  current URL/token/SESSDATA redaction without treating `*_MAX_URLS` counts as
  secrets.
- `preview_replace_secrets [preserve-timestamps]` retains a validated RFC3339
  Docker prefix only in private timestamped NapCat snapshot/follow plumbing.
  Every message still receives the complete existing sanitizer. The consumer
  removes metadata before terminal display; ordinary and captured logs retain
  normal redaction. Timestamp-boundary deduplication now sees the real value.
- Parse the event as a whole-second UTC datetime plus explicitly padded
  nanoseconds. Compare integer `event_ns` / `st_mtime_ns`, retaining the existing
  two-second maximum age and one-microsecond forward precision allowance.
  No version-specific fractional `fromisoformat` parsing remains.
- Distinguish controlled invalid-event, missing, permission, size/type, stale,
  timeout and generic read-failure categories without printing raw exceptions.
- Do not filter bare64-hex log rows speculatively: their upstream source remains
  unproven, and the user's initial pre-feature excerpt already contained them.

## Checks actually run

- Before fixes, two metadata CLI/PTY cases failed and the public-count case
  failed. After timestamp/classifier fixes:
  `./hako python -m pytest tests/unit/test_qq_login_logs.py -k 'timestamp_metadata or public_url_count' -q --tb=short`:
  three passed,25 deselected in8.92s.
- QR/render plus existing locale/redaction suites before the final Python3.10
  compatibility change:
  `./hako python -m pytest tests/unit/test_qq_login_logs.py tests/unit/test_qq_login_png.py tests/unit/test_preview_redaction_locale.py -q --tb=short`:
  58 passed,6 missing-locale skips in117.37s.
- Final-source new regression gate:
  `./hako python -m pytest tests/unit/test_qq_login_logs.py -k 'timestamp_metadata or public_url_count or reader_reports or python310' -q --tb=short`:
  11 passed,25 deselected in9.51s. The compatibility cases model Python3.10's
  documented parser constraint and exercise zero/3/6/9 fractional digits;
  actual-runtime verification below independently covers the nine-digit case.
- `bash -n deploy/qq-login-logs.sh deploy/preview-runtime.sh` and
  `git diff --check`: passed after the final source changes.
- No complete repository suite was started by this implementer; checker owns
  independent review and the appropriate final-source broader verification.

## Exact cached NapCat runtime verification

Used cached image
`sha256:045cb917c7d6f0147447eb272902a153f51e8cbdb1dc0e6df270ebd4253b4337`
with `docker run --rm --pull=never --network none --read-only --cap-drop ALL
--security-opt no-new-privileges --user 1000:1000 --entrypoint python3`.
Only a task-owned synthetic cache directory was bound read-only at
`/app/napcat/cache`; no login/config/account state was mounted. The synthetic
PNG's mtime was `2026-10-26 06:05:47.123456789 UTC`.

The pre-compatibility reader exited5. With the final injected reader source,
the same image/fixture/nine-digit event exited0 and `cmp` confirmed byte-for-byte
PNG transfer. No bitmap, payload or hash was printed. Fixture/source/output
remain in `/tmp/kisara-qq-python310.WwOOd6Lp` for bounded reviewer reuse.

## Handoff

Product/test edits stopped after these checks. No live tool sessions remain.
Changed only `deploy/qq-login-logs.sh`, scoped timestamp/classifier additions to
`deploy/preview-runtime.sh`, and `tests/unit/test_qq_login_logs.py`.
Main owns specs/PRD/mainline updates; checker owns subsequent fixes and checks.
Real phone scanning remains pending, and historical evidence must not be
relabeled as live success.
