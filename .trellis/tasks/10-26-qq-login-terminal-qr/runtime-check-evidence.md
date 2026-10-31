# Independent runtime-acceptance repair check

## Scope and context

Reopened the same task after real saved-PNG output was followed by
`png-unavailable`. Refreshed the latest PRD/design/execution repair sections,
current QR reader and log pipeline, implementation/retrospective evidence, and
the updated CLI contract. The prior complete curated context remains loaded;
this repair also explicitly preserves the separate locale/Bearer sanitizer
changes and `tests/unit/test_preview_redaction_locale.py`.

Initial review remained read-only until main confirmed implementation had
stopped editing and had no running tools. No additional task-owned defect has
been found in the repaired source, and this reviewer has made no product
or test changes. No live service/account operation, dependency, commit, archive,
image pull or automatic second full run is authorized or performed.

## Source-path verification

- URL credential discovery now uses the actual `*_URL` suffix, preserving URL,
  token and SESSDATA redaction without treating `*_MAX_URLS=3` as a secret.
- Valid Docker RFC3339 prefixes survive only the private timestamped NapCat
  snapshot/follow channel. Messages still receive the existing credential,
  ANSI/control, Bearer and URL filtering; the consumer strips the transport
  prefix before presentation. Snapshot deduplication and PNG freshness use the
  preserved value instead of reparsing sanitized display text.
- The reader parses the whole-second UTC date separately and pads fractional
  digits into integer nanoseconds. It compares against `st_mtime_ns`, retaining
  the two-second age limit and one-microsecond forward precision allowance.
  Normal nine-digit Docker fractions no longer reach Python3.10's unsupported
  fractional `fromisoformat` parser.
- Invalid metadata, missing file, permission, type/size, stale image, timeout
  and other I/O failures retain controlled categories without raw exceptions.
- No bare-hex suppression, login/status API or periodic watcher was added.

## Independent actual-runtime execution

Extracted the current `qq_login_png_reader_source` into the task's existing
synthetic scratch fixture at `/tmp/kisara-qq-python310.WwOOd6Lp/review-reader.py`.
Ran that exact source with an added assertion that the runtime is Python3.10
in cached image
`sha256:045cb917c7d6f0147447eb272902a153f51e8cbdb1dc0e6df270ebd4253b4337`.
The disposable command used `--pull=never --network none --read-only
--cap-drop ALL --security-opt no-new-privileges --user 1000:1000`, Python as
the entrypoint, and only the synthetic fixture directory bound read-only at
`/app/napcat/cache`. It mounted no login/config/account state.

For `2026-10-26T06:05:47.123456789Z`, the current reader exited 0.
An independent private `cmp -s` against the synthetic input PNG also exited 0.
No bitmap, challenge, URL, credential or hash was printed. This independently
confirms the deployed-runtime reader path, not real challenge currency or
phone authorization. Implementer's separate before/after run is retained in
`runtime-implementation-evidence.md`.

## Checks actually run

- Final-source focused gate:
  `./hako python -m pytest tests/unit/test_qq_login_logs.py tests/unit/test_qq_login_png.py tests/unit/test_preview_redaction_locale.py -q --tb=short`:
  **62 passed, 6 skipped in 118.52s**. The skips are the explicitly optional
  en_US/zh_CN locale cases because those locales are absent in the image.
  Required C, POSIX, C.UTF-8 and inherited-locale cases ran.
- The focused gate covers snapshot/live timestamp collisions with real
  credential redaction, URL-count semantics, controlled reader categories,
  zero/3/6/9 fractional digits, existing PNG/render/CLI behavior, locale/Bearer
  preservation and sanitizer process cleanup.
- `bash -n deploy/qq-login-logs.sh deploy/preview-runtime.sh deploy/preview-console.sh deploy/engines.sh`: passed.
- `git diff --check`: passed.
- Both eight-entry task context manifests validate. Package discovery confirms
  one repository with backend and trellis-plus layers. No application lint/type
  checker is configured; ShellCheck/shfmt are unavailable, so no such pass is
  claimed.

## Full regression

The single required final-source `./kisara.sh test -q --tb=short` completed
successfully: **1316 passed, 7 skipped, 3 warnings in 683.25s**, exit 0.
The skips comprise the six optional unavailable-locale cases and one existing
skip; warnings are the existing PTB deprecations. The previously timing-sensitive
video cleanup test passed in this run. No video source/test was changed and no
second full run was performed. Source remained unchanged throughout this check.

## Remaining acceptance

Real phone scanning remains human-required/pending. Current host availability
does not authorize starting QQ services or mounting accounts to obtain it.

After verification, main inspected the task-owned scratch directory (UID1000,
mode700) and removed only its six synthetic fixture/source/output files, then
the empty directory. No real QR image or account data was retained or removed.

## Owner acceptance — 2026-10-31

The user reported “通过；可以提交、归档”. Human acceptance is complete by
owner report, and local commit/archive is authorized. This supersedes the
pending mobile-acceptance/delivery status above; no additional agent-run live
login or phone scan is claimed. The existing final automated gate remains
1316 passed, seven skipped, three existing warnings; no product code changed
after that gate.
