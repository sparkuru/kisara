# Independent check evidence

## Context and scope

The native check hook supplied a saved full-output notice at
`/tmp/hook_outputs/01a1766a-1303-78d0-aa6c-8695396b741a/176544e9-7448-4a68-ae49-9efc2333eaf7.txt`.
The reviewer read all 1,770 lines in four bounded chunks, including the complete
eight-entry curated context and PRD/design/execution artifacts. Python/shell
skills and the relevant backend/guide indexes were also read. Package discovery
confirms one repository with backend and trellis-plus layers.

The implementer retained code ownership during initial read-only review. Main
then confirmed exclusive review/fix ownership after implementation stopped.
Only the QQ log/presentation helpers and their tests were fixed. Preexisting
video-export source, dependencies, deployment files and paused work were left
intact. No live service/account operation, commit, archive or push was performed.

## Findings fixed

1. `deploy/preview-console.sh`: locked output returned the successful descriptor
   close status after a failed `printf`; failed lock acquisition also leaked
   the descriptor. A `/dev/full` probe reproduced false success. Preserve the
   actual write/lock status while closing the lock in both cases.
2. `deploy/qq-login-logs.sh`: an invalid `KISARA_LOG_TAIL` was validated after
   creating scratch and before installing cleanup. Validate before any scratch
   creation; the regression wraps mktemp and checks it is never called.
3. `deploy/preview-runtime.sh`: TTY log setup always executed a clock helper
   inside NapCat, preventing available stopped-container history from being
   displayed. Only use the QR snapshot path for a running gateway; stopped
   gateway diagnostics retain the existing bounded normal log flow.
4. `deploy/preview-console.sh`: serializing a section via the styled message
   helper colored its body/URLs as well as the heading, changing the existing
   plain-URL contract. A direct PTY regression failed before the fix. Style
   only the heading, retaining one atomic write for the complete section.
5. The corrupt-PNG fixture rewrote its bytes after the synthetic saved timestamp,
   so the stricter intended freshness rule correctly rejected it as overwritten
   before decoding. Align the fixture's mtime with its simulated save event.

## Checks completed

- New reviewer regressions before fixes:
  `./hako python -m pytest tests/unit/test_qq_login_logs.py -k 'serialized_output or invalid_log_tail or stopped_napcat' -q --tb=short`:
  five failures in 10.92s. After fixes: five passed in 10.91s.
- Full QR-focused renderer/CLI suite:
  `./hako python -m pytest tests/unit/test_qq_login_png.py tests/unit/test_qq_login_logs.py -q --tb=short`:
  35 passed and one corrupt-fixture timestamp failure in 117.86s.
- After correcting only that fixture, `-k 'corrupt or cancellation'`:
  two passed in 11.49s. Inflight-render cancellation therefore passed both the
  complete focused run and its repeat. Handoff source already provides a
  bounded 200ms TERM grace before forced reader cleanup.
- Final-source focused gate after the heading-only style fix:
  `./hako python -m pytest tests/unit/test_qq_login_png.py tests/unit/test_qq_login_logs.py tests/unit/test_preview_lifecycle.py -k 'qq_login or onebot_forwarder_diagnostics_cover_dev_mode or stop_removed' -q --maxfail=1 --tb=short`:
  47 passed, 180 deselected in 137.97s. This includes all new renderer/CLI
  regressions, source-locale checks, writer/lock failure, stopped-container
  history, terminal styling and cancellation, plus existing routing cases.
- `bash -n deploy/engines.sh deploy/preview-console.sh deploy/preview-runtime.sh deploy/qq-login-logs.sh`: passed.
- `git diff --check`: passed. Explicit trailing-whitespace search in all four
  new helper/test files returned no matches.
- `task.py validate` passed both eight-entry manifests. No configured application
  lint/type checker exists; ShellCheck/shfmt are unavailable, so no such pass
  is claimed.
- Implementation's separate independent zxing-cpp check decoded all eight
  PNG-scale/ANSI/plain combinations; see implementation-evidence.md.
- Main also reports a read-only, private actual-PNG format probe: bounded owned
  NapCat PNG bytes were piped into the existing renderer, printing only image
  dimensions 147x147 and the renderable category. No QR payload/hash/image was
  printed or saved. This establishes format support, not challenge currency or
  successful QQ authorization.

## Full regression

`./kisara.sh test -q --tb=short` completed in 683.16s: 1 failed, 1289 passed,
1 skipped and 3 existing PTB deprecation warnings. The only failure was at
collection position 444, the preexisting video-export timeout test
`test_exited_worker_with_stdout_held_by_descendant_still_times_out`, before the
QR tests. Its immediate descendant cleanup assertion observed process state
`R` where it required absence or `Z` (`tests/unit/test_export_video.py:319`).
An isolated rerun of that unchanged existing test passed in 1.14s. No video
source/test changes were made by this task and no green full-suite gate is
claimed. Do not infer a QR regression from this unrelated timing-sensitive
failure or silently weaken the video cleanup assertion.

This full run began before the final heading-only styling preservation fix and
its additional direct PTY test. The complete final-source 47-test focused gate
above passed afterward. Main explicitly chose to retain the full-run result
and targeted isolation evidence rather than rerun the entire suite or expand
this task into unrelated video cleanup work.

## Human review boundary

Real phone scanning is human-required/pending. No synthetic PNG decode or
format-only probe establishes that a real QQ account authorized login.
