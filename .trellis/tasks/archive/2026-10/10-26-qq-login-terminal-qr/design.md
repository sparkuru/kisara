# QR presentation in the QQ login-log flow

## Decision and boundary

The user's latest instruction makes the saved PNG part of normal login logs.
Recognize a QQ login requiring a scan, consume the PNG-saved event, and emit
the corresponding PNG as a terminal QR block in the existing log flow.
This replaces the earlier WebUI polling / URL encoding proposal entirely.

The shared behavior belongs in the existing QQ log consumption/presentation
path, used by preview start/status and ordinary `kisara.sh logs onebot` or
`onebot-dev`. There is no additional public QR command, watcher, login API,
authentication session or QR generation dependency. Do not modify upstream
NapCat code or add another service.

## Evidence

- `deploy/preview-runtime.sh:43` deletes QR-symbol rows, and line 44 removes
  ESC characters without consuming entire ANSI sequences. A synthetic probe
  reproduced missing QR rows and residual `[33m`/`[0m` fragments.
- `deploy/preview-runtime.sh:73` prefixes ordinary output, while concurrent
  service readers can interleave writes. QR output needs a whole-block writer.
- `deploy/engines.sh` currently sends ordinary logs through Compose; reuse one
  login-aware consumer for attached QQ views rather than implementing separate
  preview-only and ordinary-log QR features.
- `deploy/compose.yaml:20` retains config and QQ state, but the reported
  `/app/napcat/cache/qrcode.png` remains inside NapCat.
- Prior read-only inspection verified exact repository/source labels before
  checking installed dependencies and static `/app/napcat/napcat.mjs` code.
  NapCat has Python 3 but no Pillow; the selected OneBot application has Pillow.
  No live QR payload, private config or account state was printed or changed.
- Installed `onQRCodeGetPicture` writes the PNG and emits
  `二维码已保存到 /app/napcat/cache/qrcode.png` in its write-completion callback.
  This event is the natural trigger; fetching at the earlier scan prompt could
  race PNG creation. The same PNG path is overwritten on a fresh challenge.

## Log-to-PNG-to-terminal contract

1. The NapCat log consumer recognizes login-required, QR-saved and subsequent
   scanned/expired/login-success events. Match actual NapCat-owned log records,
   not arbitrary message bodies containing similar text. Login text remains
   visible through normal redaction.
2. For a live saved-PNG event in a pending login, read only the fixed
   `/app/napcat/cache/qrcode.png` from that verified NapCat container. Preserve
   the effective Docker context/host and exact ownership checks. Never use an
   arbitrary path extracted from log text as a filesystem capability.
   Preserve the strictly validated Docker timestamp as private transport
   metadata before message redaction; it must not be parsed back from display
   text. Handle nine-digit RFC3339 fractions explicitly on actual NapCat
   Python3.10 rather than depending on Python3.12's fromisoformat behavior.
3. Use bounded one-shot reads and byte/pixel limits. Transfer image bytes by
   private pipe or owner-only scratch to the selected, verified OneBot
   application's existing Python/Pillow runtime. Do not log base64/raw PNG,
   mount the cache publicly, install a host toolchain or launch another service.
4. Convert the existing bitmap to monochrome terminal cells locally. Preserve
   square modules and the white quiet margin; use integer/module-preserving
   reduction only. Reject unreadable/unsupported geometry instead of scaling
   the QR arbitrarily or regenerating a different code from a URL.
5. Emit the complete QR block at the login event's place in the log flow. Do
   not put timestamps/platform labels inside its matrix rows. Follow normal
   log presentation with no user command or separate login lifecycle.
6. When another saved-PNG event arrives, render the replacement once. Repeated
   identical events/images need no duplicate output. Later scanned/expired/
   success events end the pending presentation state. PNG existence alone is
   never evidence of a current login requirement.

## Recent-log replay

Do not blindly render when a historical saved-PNG line is encountered during
the existing tail. Evaluate the bounded recent snapshot as an ordered login
sequence first: a later successful/scanned/expired event invalidates earlier
QR presentation. Only a still-pending latest login sequence may display its
corresponding current PNG. Use event timestamps/file identity to reject an old
event referring to a different overwritten PNG, and avoid a gap between the
recent snapshot and live follow. If no sufficient current-login evidence is
available, keep the existing WebUI recovery hint and wait for the next login
event; do not add an API probe or reconstruct account state from file existence.

## Output, privacy and errors

Interactive terminal output is the deliberate QR surface. Redirected/captured
diagnostics retain sanitized text and do not embed authentication images or
decoded URLs. On an unsuitable or undersized terminal, explain the limitation
and retain the existing WebUI/SSH-tunnel route. Respect NO_COLOR and preserve
monochrome geometry; do not depend on inline PNG protocols.

Use a single invocation-local output serialization mechanism for the whole QR
block, normal log lines, and parent readiness/progress messages. If using the
available `flock`, each process must open its own lock descriptor; sibling
processes sharing an inherited descriptor do not mutually exclude one another.
Do not introduce a second unbounded log buffer or generic event framework.

Strip full ANSI CSI/OSC sequences from ordinary text before sanitization.
Native QR art and authentication URLs remain suppressed in generic diagnostics;
the PNG-derived block is emitted only by the login-aware presentation path.
Preserve ordinary credential redaction, ID visibility and Chinese text.
Recognize configured URL credentials by the actual `_URL` naming contract;
nonsecret settings such as `ONEBOT_EXPORT_MAX_URLS` must never cause blanket
replacement of ordinary numbers. Real token/SESSDATA values still require
redaction even when they collide with private transport timestamp digits.

Missing/corrupt PNG, unsupported geometry, timeout or unavailable Pillow runtime
produces a categorized recovery hint at the event and keeps ordinary logs
flowing. Ownership mismatch and sanitizer/writer failures remain explicit
errors without raw fallback. No periodic read/retry loop is introduced: a new
login event or a newly attached existing log view is the next opportunity.

All image processing/read helpers are bounded one-shot operations owned by
the current command. Preserve readiness deadlines, actual ready summaries,
stream EOF/error propagation and INT/TERM exits 130/143; reap only invocation
helpers and remove only its private scratch. Status/logs do not reconcile,
build, install or restart services. Persistent login/config/device state stays.

## Expected change surface

- `deploy/preview-runtime.sh`: attach the shared login-aware consumer, correct
  ANSI cleanup and preserve reader/lifecycle behavior.
- `deploy/engines.sh`: use the same consumer for existing attached QQ logs,
  preserving selection and ownership; leave other engine routing intact.
- `deploy/preview-console.sh`: atomic output/help where shared presentation
  requires it. A small sourced helper under `deploy/` may own reusable QQ log
  presentation; this is an internal decomposition, not another workflow.
- A small Pillow PNG-rendering helper under `deploy/`, supplied to the existing
  application Python runtime at exec time, with focused behavioral tests.
- Relevant existing log/deployment fixtures, operations docs and CLI/validation/
  logging specs. Preserve all preexisting edits in shared files.

No pyproject, dependency pin, Dockerfile, Compose mount/port or private dotenv
change is needed for this task. Roll back only task-owned changes; no live
deployment, restart, account authorization, commit/archive or push is implied.
