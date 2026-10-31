# Execution plan

## Planning gate

- [x] Record the user's event-driven PNG/log integration correction in PRD.
- [x] Replace API polling / URL encoding design and remove dependency work.
- [x] Curate both context manifests with actual shared specs and design.
- [x] Validate final artifacts and present the revised planning summary.
- [x] Receive approval (“可以”), then run `task.py start`.

## Implementation

1. Recheck task/worktree state and load shell/Python skills and applicable
   specs. Preserve pending video-export changes and all login/config state.
2. Dispatch `trellis-implement` with the active task and ownership of shared
   QQ log consumption, PNG rendering, existing attached command integration,
   focused tests and operations/help. Main session owns specs/task records.
   Verify native injection or child-reported fallback reads.
3. Reproduce missing QR rows and ANSI fragments; add failing real CLI/PTY
   fixtures for PNG-saved login events, recent-log replay and refresh.
4. Implement the common event-driven consumer and bounded fixed-path image
   read, PNG renderer using existing Pillow, and uninterrupted block output.
   Share it across existing QQ preview and ordinary attached log views.
5. Handle missing/corrupt/oversized PNG, narrow/non-TTY/dumb terminals,
   unavailable runtime, duplicate events, later login completion, ownership
   failure and cancellation without inventing polling or account operations.
6. Main session updates existing CLI/validation/logging contracts; document
   the normal login-log behavior and retained WebUI recovery path.

## Validation

- Bash syntax and available ShellCheck/shfmt checks for changed scripts.
- Focused renderer/event tests through `./hako python -m pytest` using actual
  PNG fixtures, not a mocked renderer output.
- Reconstruct terminal cells into pixels and independently decode a synthetic
  fixture challenge, verifying the original PNG payload survives rendering.
  Any decoder is a scratch validation dependency, not production infrastructure.
- Real existing CLI plus PTY tests: first login/relogin, PNG-ready ordering,
  changed QR once, duplicate suppression, historical successful login with
  residual PNG, overwritten PNG mismatch, no snapshot/follow gap, mixed logs
  without split QR rows, missing/corrupt image, terminal constraints, ordinary
  QQ logs and preview start/status while unready.
- Assert no periodic status/QR fetch, no WebUI authentication, no new encoder
  dependency, no container mutation and no image output into captured logs.
- Preserve Chinese/credential tests in C/POSIX/UTF-8 and verify full ANSI
  cleanup. Assert INT/TERM cleanup retains service IDs and persisted data.
- Run focused existing deployment suites:
  `./kisara.sh test tests/unit/test_kisara_cli.py tests/unit/test_engine_deployment.py tests/unit/test_preview_lifecycle.py tests/unit/test_preview_readiness.py -q`.
- Dispatch `trellis-check` for independent review/fixes, run required full
  `./kisara.sh test`, inspect final diff and `git diff --check`, and validate
  context manifests. Record commands/results and actual coverage limits.

## Review boundary

Prepare runnable automation before asking for real phone scanning. Record
that scan as human-required/pending unless explicitly authorized and observed;
PNG/terminal decoding is evidence of rendering, not QQ account login success.

Do not deploy/restart containers, reset state, scan/approve the login, commit,
archive or push as part of implementation. All production dependencies already
exist; the earlier Segno/API/session proposal is superseded and must not ship.

## Result

Implementation and independent review are complete; all task-owned findings
were fixed. Final-source focused gate: 47 passed. Eight independent decoding
cases and the private existing-PNG format probe passed. Full suite: 1289 passed,
one skipped and one unrelated preexisting video cleanup timing failure; that
unchanged test passed in isolation. Retain that exact full-suite limitation.
Real phone scanning and delivery remain pending. Detailed commands and review
boundaries are in `implementation-evidence.md` and `check-evidence.md`.

## Runtime acceptance repair

User-reported `png-unavailable` reopens implementation/checking. Preserve raw
validated Docker timestamp metadata separately from sanitized message text,
stop treating public URL-count settings as credentials, parse nanosecond RFC3339
fractions on actual NapCat Python3.10, and keep read-failure categories useful.
Run failing-before/passing-after snapshot and live CLI cases with synthetic
timestamp-colliding secrets; independently execute the actual reader source
inside the cached NapCat image with synthetic PNG only and no account mounts.
Preserve current locale-redaction changes from other work. Recheck focused
QR/redaction/deployment suites and independently review the final repair.

Repair complete: actual cached Python3.10 reader/source and private PNG byte
comparison passed. Independent final focused gate62 passed/6 optional locale
skips; full final-source gate1316 passed/7 skips/3 existing warnings, exit0.
No reviewer code edits or live service/account operations were needed. Prior
initial-check results remain historical; actual phone acceptance is pending.

## Owner acceptance — 2026-10-31

The user reported “通过；可以提交、归档”. Human acceptance is complete by
owner report, and local commit/archive is authorized. This supersedes the
pending mobile-acceptance/delivery status above; no additional agent-run live
login or phone scan is claimed. The existing final automated gate remains
1316 passed, seven skipped, three existing warnings; no product code changed
after that gate.
