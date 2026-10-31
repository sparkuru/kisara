# Execution and validation plan

## Phase transition

- [x] Task created with explicit user consent.
- [x] User approved Bilibili-only initial provider scope and supplied an
  authorized credential file; structural/login/API probes are recorded safely.
- [x] PRD convergence pass completed; design and execution plan recorded.
- [x] Present the final planning summary and obtain a subsequent explicit
  approval before `task.py start` or any product implementation.
- [x] Re-read the latest task/specs and inspect current Git/runtime status.
  Preserve unrelated work and the paused Telegram task boundaries.

## Implementation ownership

After approval, use the available Trellis implement/check roles as required by
the active Codex dispatch instructions. Main session owns task/mainline/specs,
secret setup, external operations and final acceptance. Every dispatch starts
with the actual active task path, names owned files/responsibility, and tells
workers they are not alone and must preserve others' edits. Prefer native
context injection; require reported child-side reads for missing/truncated
files. `configuration-storage.md` exceeds the per-file injection budget: read
the complete file in bounded pieces before relying on its contracts.

Use one implementer for the coherent cross-layer path, then an independent
checker; avoid concurrent edits to the adapter/settings/deployment wiring.
Load `trellis-before-dev`, Python/shell coding skills for their target files,
and the relevant backend and shared policies.

1. Implement source parsing/normalization, safe Bilibili short-link resolution,
   typed provider results and the pinned-extractor worker. Cover observed card
   schema, BV/av/mobile URLs, `p`, deduplication and rejected redirect targets.
2. Implement scoped-cookie extraction, best-format selection, complete
   audio/video MP4 merging, size/workspace limits, bounded worker diagnostics,
   timeouts/cancellation and subprocess-group cleanup. Credentials use stdin;
   no values in subprocess arguments, repr, logs or shared spool.
3. Wire configuration/startup injection, native export routing and gateway video
   sends. Fetch the quote once after authorization; preserve explicit image
   commands and select source correctly for generic export. Cover command
   duplicate suppression, progress, partial multi-target failures and busy limits.
4. Prepare the dedicated shared spool, permissions/retention, OneBot video
   dependency extra, exact preview pins, FFmpeg image installation and preview
   tooling checks. Update only relevant Compose services/helper behavior and
   existing operations/help/module docs; do not edit README.
5. Run focused checks and inspect the diff. Independent check follows the
   full approved scope, fixes verified defects and runs the full offline gate
   once after final changes. Main session reconciles requirements/specs.
6. Finish runnable isolated provider/merger checks, then prepare targeted live
   preview validation. Use only the authorized supplied credential and existing
   sample conversation; do not print raw history, credentials or signed URLs.
   Confirm the exact runtime update scope before executing any broader service
   operation. Record metadata, downloads and native sends as separate evidence.

## Automated validation

Use existing Docker entrypoints, starting with new focused feature suites:

```text
./kisara.sh test tests/unit/test_export_video.py tests/unit/test_bilibili.py -q
./kisara.sh test tests/unit/test_settings.py tests/unit/test_onebot_adapter.py tests/integration/test_onebot_protocol.py -q
./kisara.sh test tests/unit/test_engine_deployment.py tests/unit/test_preview_lifecycle.py tests/unit/test_preview_readiness.py tests/unit/test_hako_deployment.py -q
./kisara.sh test -q
git diff --check
```

The first two new suite names are planned; choose final focused files by actual
ownership rather than manufacturing a matching empty suite. Run relevant Bash
syntax/ShellCheck/shfmt checks for changed shell files if applicable/available.
No application lint/type-check tool is configured; do not invent a passed gate.

Required behavioral cases: native auth/quote isolation before I/O; source-shape
routing; explicit image compatibility; anonymous/session best-quality selection
including >1080p; no-audio source distinction; invalid/restricted sessions;
safe redirects and cookie isolation; unknown-length/oversize transfer; merge
failure; timeout/cancel with no leaked worker; spool access/cleanup/grace and
symlink rejection; duplicate/busy limits; native receipt/failure/unknown outcome;
selected-engine config/empty precedence; preview pins/tooling and unrelated
engine isolation. Use synthetic credentials in automated tests only.

## Isolated and live acceptance

- Build the OneBot image and verify exact downloader version plus FFmpeg/
  ffprobe without starting or replacing live services.
- In a temporary isolated job, extract the public sample with and without the
  supplied credential. Inspect actual selected formats and complete merged
  streams/duration using ffprobe. Do not assume the observed480p/1080p API
  result is immutable or that yt-dlp necessarily returns the same formats.
- Verify actual shared media read access for configured application/NapCat
  users, then use the two user-supplied preview sources to validate native
  video replies. Record OneBot message receipt IDs without storing unrelated
  conversation content. Confirm real reception/playback separately.
- Classify residual human review with the existing validation policy. Native
  reception/playback remains `human-required` unless directly established;
  finish runnable preparation before asking for that narrow remaining check.

## Rollback and delivery boundaries

Follow-up execution: the user reported `sed` expression2/char25 `Invalid range
end` from real preview startup. Returned to Phase2 for a bounded shared redaction
fix and independent check. Main reproduced the failure with real installed
en_US.utf8 and zh_CN.utf8 locales while C/C.UTF-8 pass. Preserve the other
terminal-QR task's existing changes and add direct boundary/locale regressions.
See `research/preview-redaction-locale.md`. No new task, feature approval,
private configuration edit or account/service mutation is required for this
host-side CLI correction.
The fix and independent check are now complete: final full gate1305 passed,
7 dependency/locale skips,3 existing warnings;19 real-host locale probes and
actual read-only CLI follow/interrupt/process-group cleanup passed. No rebuild
or account operation was needed. R9/AC8 is closed; original native-video
acceptance still waits for QQ login.

Video-export baseline before this follow-up: implementation and its independent
full gate completed; the image matched all63 Python source files and real MP4 download,
merge, full audio/video decoding and shared-volume permission checks passed.
Targeted preview recreation applied the feature, but retained QQ quick-login
identity was reported expired. Wait for the user's WebUI login and OneBot
readiness; do not reset account data or claim native send acceptance.

Prepared native verification driver: `/tmp/kisara-video-live-probe.py`. It reads
credentials from the running app's existing selected environment, retrieves the
two real source messages, validates their allowed private owner, and constructs
explicit test quote commands through the production adapter/service path. It
prints only controlled status/native receipt metadata and ignores unrelated
events. Once ready, run `docker exec -i kisara-kisara-1 python -` with that
script as stdin, then verify both returned messages have native video segments
and ask only for remaining client playback confirmation. Inspect the scratch
script before reuse in another session; actual user source messages remain
the authoritative inputs. User's existing test authorization still applies.

Risky files are OneBot routing, settings/config loaders and deployment/preview
dependency/spool wiring. Restore reviewed prior source/image/config mappings
if needed; preserve QQ login, all existing app/archive volumes, other engines
and the supplied credential source. Never use broad cleanup as rollback.

Record exact commands/results and limitations in this task. The original
implementation approval did not authorize Git delivery or unrelated Telegram
work. On 2026-10-31 the user explicitly authorized committing/archiving and
confirmed QQ native return acceptance (“qq 回传确认了。通过”). Feature
acceptance is complete; proceed with task-scoped delivery and preserve the
separate QQ terminal-QR task's concurrent commits and archive. No push is
authorized.
