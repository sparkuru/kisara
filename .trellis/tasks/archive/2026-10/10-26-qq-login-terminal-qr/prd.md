# QQ login QR codes in the terminal

## Goal

Let users scan a QQ login QR code directly from the terminal during first
login and subsequent authentication, without opening a QR generation website.

## Background and evidence

- The user explicitly requested task creation and supplied redacted NapCat
  login output showing a decoded URL and `/app/napcat/cache/qrcode.png`.
  Do not retain actual authentication URLs or QR images in task artifacts.
- Before implementation, `deploy/preview-runtime.sh:43` deleted every line
  containing QR block symbols. The same filters served attached viewing and
  captured diagnostics. Baseline fixtures asserted QR suppression in
  `tests/unit/test_preview_lifecycle.py:199` and
  `tests/unit/test_preview_lifecycle.py:1298`.
- Baseline `deploy/preview-runtime.sh:44` removed control characters without consuming
  entire ANSI sequences. An environment-isolated synthetic filter probe
  preserved a Chinese sentinel, dropped a QR-symbol row, and left `[33m` and
  `[0m` fragments around colored text. This proves filter behavior only;
  that initial probe inspected neither a live login nor a QR image.
- `deploy/compose.yaml:20` mounts configuration and QQ state, but not
  `/app/napcat/cache`. The reported PNG path belongs to the container.
- Baseline `deploy/preview-runtime.sh:73` prefixed each displayed log line, and
  independent readers printed concurrently. A QR block requires intact geometry
  and uninterrupted output.
- `docs/operations.md:316` documents manual login and persistent QQ state.
  Preserve that state and the existing loopback WebUI/SSH-tunnel route.
- A later bounded, read-only format probe privately processed the owned
  NapCat's existing 147-by-147 PNG and confirmed it is renderable. It printed
  only dimensions/result, not image content; current challenge validity and
  phone authorization remain unverified. See `implementation-evidence.md`.

## Requirements

- R1: Show an intact, directly scannable terminal QR block when QQ requires
  first login or reauthentication. Recognize NapCat's login/PNG-saved events
  in the existing QQ log flow and render the corresponding PNG directly.
- R2: Display a replacement when NapCat supplies a new challenge; avoid
  repeatedly printing unchanged content or replaying obsolete login codes.
- R3: Preserve QR contrast, quiet space and row alignment without per-row
  prefixes or interleaved logs. Remove complete ANSI sequences from ordinary
  log text so no escape-code fragments remain.
- R4: Preserve credential redaction and Chinese logs. Interactive QR display
  is a deliberate authentication surface, not a blanket diagnostic exemption.
  Keep authentication artifacts out of tracked files and captured diagnostics.
- R5: Explain unavailable QR content or unsupported terminal presentation and
  provide the existing WebUI recovery route.
- R6: Preserve login/configuration directories, account/device settings,
  service ownership checks and Ctrl+C viewing semantics.
- R7: Treat QR presentation as part of the existing login-log flow. Reuse
  existing Pillow for PNG rendering; do not add a QR encoder, WebUI API client,
  authentication session, periodic status watcher or separate QR command.

## Scope and owner decision

- On 2026-10-26 the user responded “开始实现” to the recommended automatic
  preview integration. Use that entry point; no separate QR-view command.
- The user then corrected the design: “识别到需要登录时，根据所需的 png
  直接输出在 log 里就行，做成登录流程的一等公民”. This supersedes the
  proposed API polling and URL re-encoding design. Login events and the saved
  PNG own the behavior, and existing attached QQ log views share it.
- Automatically display in the existing QQ log flow, including
  `./kisara.sh preview start onebot` / `onebot-dev` and corresponding
  `preview status` views while the bot is not ready, and the canonical
  `./kisara.sh logs onebot` / `onebot-dev` view.
- Terminal QR presentation and relevant help, tests and specs.
- Noninteractive diagnostics retain sanitized textual output.

## Acceptance criteria

- [x] AC1 / R1: Controlled first-login and reauthentication PNG-saved events
  produce terminal QR blocks decoding to the corresponding PNG payloads,
  through the actual existing attached log commands.
- [x] AC2 / R2: A changed challenge produces a replacement; unchanged content
  is not repeatedly displayed. Missing/stale content has explicit behavior.
- [x] AC3 / R3: Concurrent logs do not split QR rows; presentation preserves
  scan margins and contrast. ANSI fixtures contain no residual color codes.
- [x] AC4 / R4: Ordinary secrets remain redacted, Chinese text survives C and
  UTF-8 locales, and captured diagnostics contain no QR authentication data.
- [x] AC5 / R5: Unusable content or terminal constraints yield useful recovery
  information rather than a claimed usable code.
- [x] AC6 / R6: Cancelling viewing only cleans up this invocation's helpers;
  service identities and persistent login state remain intact.
- [x] AC7 / R1: Record a real phone scan if explicitly authorized for acceptance,
  or mark it pending. Fixture decoding alone does not prove QQ login success.
- [x] AC8 / R7: No QR-specific command, background status polling, WebUI API
  authentication or new production encoder dependency is introduced. A new
  QR display follows a saved-PNG login event rather than a polling timer.

## Out of scope

- Resetting/deleting QQ login state or automatic logout/account switching.
- Guaranteeing QQ sessions never expire or automating mobile authorization.
- QR generation from decoded URLs, periodic login-status monitoring, WebUI
  login/session management, or modifications to upstream NapCat internals.
- Telegram work, public WebUI exposure, unrelated pending video-export changes,
  commit/archive/push, or live service recreation.

## Planning status

On 2026-10-26 the user approved the revised PNG/event/log final summary with
“可以”. Product decisions and the planning gate are resolved. Task status is
in_progress with implementation and independent checking complete. Final-source
focused gate: 47 passed; independent decoding: eight passed; actual cached PNG
format probe: passed. Full regression: 1289 passed, one skipped and one unrelated
existing video cleanup timing failure that passed in isolation. No green full
gate is claimed. See `implementation-evidence.md` and `check-evidence.md`.
Real phone scanning remains human-required/pending; no live authorization,
service deployment, code commit or task archival was performed.

## Reopened runtime acceptance

The user then supplied actual login output where the PNG-saved event was
recognized but followed by `png-unavailable`. Reopen implementation/checking
under the same approved outcome; earlier focused/decoder results do not prove
the failing reader path works on the deployed runtime.

Confirmed independent causes:

- `preview_redact_values` matched `ONEBOT_EXPORT_MAX_URLS` using `*URL*`.
  The documented nonsecret count3 was treated as a credential, corrupting
  ordinary log numbers and private Docker timestamp fractions. The sanitized
  timestamp was then reused as reader input and snapshot/follow metadata.
- The cached actual NapCat image uses Python3.10. A read-only, offline image
  probe accepted six-digit fractions but rejected nine-digit Docker timestamps
  in `datetime.fromisoformat`. Prior reader fixtures used Python3.12; the real
  image format probe verified PNG rendering but bypassed timestamp parsing.

Add regression coverage for both causes separately and together, executing
the exact reader source in the actual cached Python3.10 runtime. Keep validated
Docker transport metadata separate from redacted display text, preserve genuine
credential redaction, avoid classifying public URL counts as secrets, and report
controlled read failure categories. No service/account changes are authorized.

Repair implementation and independent review are complete. The exact final
reader passed in the actual cached NapCat Python3.10 image and transferred
the synthetic PNG byte-for-byte with a nine-digit timestamp. Final focused
QR/locale/Bearer gate: 62 passed, six optional locale skips. Final full gate:
1316 passed, seven skipped, three existing warnings, exit0. See
`runtime-implementation-evidence.md`, `runtime-check-evidence.md` and
`runtime-regression.md`. Real mobile QQ scan/authorization remains pending.

## Final owner acceptance and delivery — 2026-10-31

The user reported “通过；可以提交、归档”, accepting the delivered terminal
login flow and authorizing its local commits and task archival. AC7 is closed
on that owner acceptance; no independent agent observation of phone scanning
or QQ account authorization is claimed. This supersedes earlier pending-review
and no-commit/no-archive boundaries for this task only. No push or additional
service/account operation is authorized.

Delivery includes the shared locale/control/Bearer sanitizer fixes and their
regressions, which protect the same attached QR log path. Unrelated video-export
implementation/configuration remains uncommitted. This task was implemented
directly on the existing feat/export-linked-video branch and was never
PR-backed or assigned a separate feature branch; archival uses the documented
skip-branch-validation option for that exact case, without claiming a merge.
