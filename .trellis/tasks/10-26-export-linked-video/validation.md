# Validation and delivery evidence

## Final user acceptance — 2026-10-31

The user authorized “`10-26-export-linked-video/` task 可以提交、归档”,
then confirmed “qq 回传确认了。通过”. This closes AC1 and the prior
human-required native QQ return acceptance. All PRD acceptance criteria are
now satisfied. The live result is explicitly user-reported; this session did
not collect new native receipt IDs, media measurements or playback logs.

The historical login blockers and pending classifications below describe their
recorded source states; this final confirmation supersedes them. Delivery
includes video export. The shared locale-redaction repair is already committed
with the separate QQ terminal-QR task (`bc74135`), whose own acceptance and
delivery records remain independent. No push or new live service/account
operation is requested.

### Delivery-time verification

Final combined-source focused check on 2026-10-31:

```text
./kisara.sh test tests/unit/test_bilibili.py tests/unit/test_export_video.py tests/unit/test_video_worker.py tests/unit/test_export_settings.py tests/unit/test_export_deployment.py tests/integration/test_video_export_protocol.py tests/unit/test_onebot_adapter.py tests/integration/test_onebot_protocol.py -q -rs
209 passed in 8.99s; exit 0, no skips or warnings
```

The independent checker verified 28 video source/config/test/deployment files
against the initial delivery snapshot; all were byte-identical. The actual
shared preview runtime and locale regression also retained their initial
SHA256. Concurrent QQ work only committed existing source and then archived
its task; it introduced no product changes after the recorded combined-source
full gate: 1316 passed,7 skipped,3 existing PTB warnings in683.25s, exit0.
That gate is reused with its exact source scope, not reported as rerun today.
Bash syntax, whitespace and task context validation passed. The known large
configuration/storage context warning is covered by explicit fallback reads;
no configured application lint/type gate or available ShellCheck/shfmt is
claimed.

Before the concurrent QQ commits were visible, a temporary candidate separated
the two tasks against their old common base. Its focus passed85/4 missing-locale
skips and13 actual-host locale probes. That candidate became obsolete after
the QQ delivery; its full run was interrupted and is not a final gate:
1 failed,582 passed,1 skipped,2 warnings in67.16s, exit2. The failure was the
previously documented unchanged descendant-cleanup timing assertion (the
immediate child state was R rather than Z). No test or product source was
changed to hide it; the final combined-source focus and existing1316-pass
full gate both passed that test. This timing sensitivity remains recorded.

Independent final review found no delivery blocker. Human-required native
acceptance is satisfied by the owner's report above. No new live send, service
mutation, merge or push was performed during closeout.

## Approval and baseline

The user answered “开始” after the final summary, approving implementation and
the described targeted OneBot/NapCat preview validation. Task is in progress on
`feat/export-linked-video`, based on `keiyaku-no-kisu` at21844dc. Before product
work, the only dirty path was this task directory; mainline was then updated
to record the new approval. No commit/archive/push is authorized.

Baseline relevant containers on2026-10-26:

| Service | Container ID | Started |
| --- | --- | --- |
| OneBot app | `573db06cd925a5c8da978b31741682a61a28b565861e1a22aa36fa9513e4d28c` | `2026-10-26T01:54:32.612630542Z` |
| NapCat | `9e75b6f3aaf0558cc450a51c75f90c010866cf61abefe80c1ee02ee1149a532a` | `2026-10-26T01:54:32.304343764Z` |
| Telegram, preserve unchanged | `dff1defad0df13a96fa3e2b7df5dfd925592fb3a2a04384d583edc2d83072570` | `2026-10-22T15:13:06.227062136Z` |

Only selected identity, image IDs, users, mount targets and Compose provenance
were inspected; container environment values were not emitted.

## Independent pinned-extractor metadata probe

Ran `./hako python -c <isolated metadata probe>` with the user-supplied env file
as stdin. The disposable container installed `yt-dlp==2026.10.21` with
`--no-deps --no-cache-dir --target <container /tmp directory>` and removed its
temporary target on exit. Nothing was installed into the running preview or
the project's dependencies. No media download/message send occurred.

The probe used the Python API, disabled cache/playlist and raw diagnostics,
and compared no credential versus a `.bilibili.com` scoped SESSDATA cookie.
Public source: `https://www.bilibili.com/video/BV1drnJ6BE86/`.

| Result | Anonymous | Supplied session |
| --- | --- | --- |
| Extraction | success | success |
| Selected height |1080 |1080 |
| Available video heights |360,480,720,1080 |360,480,720,1080 |
| Duration seconds |59.466 |59.466 |
| Selected audio |yes |yes |

This differs from the earlier direct-API anonymous480p/session1080p observation
in [provider research](research/bilibili-provider.md). Those endpoint-specific
metadata observations must not become fixed expected anonymous limits. The
implementation must choose the best formats actually available in its current
extraction. Neither metadata probe establishes playable complete bytes or QQ
video reception; those gates remain pending.

## Implementation, automated checks and live acceptance

The authorized session was copied from the supplied file into the missing
`ONEBOT_BILIBILI_SESSDATA` key of ignored root `.env`. Syntax-aware handling
matches the project's simple data grammar; no shell evaluation or credential
output occurred. Seven scratch cases covered missing destination, custom and
explicit-empty preservation, comments/quoting/CRLF, absent final newline,
duplicate rejection and idempotence. The real append rechecked concurrent
changes, preserved every preexisting byte and verified only the new field's
value privately. Existing running container environments are unchanged until
the later targeted recreation.

The four missing operational keys were subsequently appended with their
reviewed defaults: `ONEBOT_EXPORT_VIDEO_ENABLED=true`,
`ONEBOT_EXPORT_MAX_FILE_BYTES=512M`, `ONEBOT_EXPORT_TIMEOUT_SECONDS=600`,
`ONEBOT_EXPORT_MAX_URLS=3`. Existing assignments/bytes remained intact.

The real card short link was followed with cookies disabled and a bounded
Bilibili-only per-hop host check: `b23.tv/wHhO5iP` returned302, its
`www.bilibili.com` target returned301, and the final public target returned200:
`https://www.bilibili.com/video/BV1rcpL6TEwK/`. It is a different video from
the direct text sample. Both will be validated independently.

Compose source-label inspection confirmed that the OneBot/NapCat baseline
objects belong to this repository's `deploy/compose.yaml` and a historical
temporary preview override. Later operations must use the canonical preview
entrypoint rather than treating their names alone as proof of ownership.

### Isolated image and complete-media checks

`./kisara.sh preview build onebot` succeeded without replacing live services.
A `docker run --rm --network none` against `kisara-preview-kisara:latest`
verified exact yt-dlp2026.10.21, FFmpeg and ffprobe availability, application
UID10001 and spool ownership10001; `preview-deps.py check video` passed.

Ran the actual `BilibiliDownloader`/subprocess worker in a disposable image
container with no application data, OneBot credentials, port publication or
service connection. Only a scratch probe script was mounted read-only; the
supplied Bilibili session arrived on stdin. Three complete downloads passed:

| Case | Native target | Bytes | ffprobe output |
| --- | --- | --- | --- |
| Text, anonymous | `BV1drnJ6BE86`, part1 |6936361 |1920x1080 H264,30fps,1 audio track,59.466625s |
| Text, supplied session | `BV1drnJ6BE86`, part1 |6936361 |1920x1080 H264,30fps,1 audio track,59.466625s |
| Real card short link, supplied session | `BV1rcpL6TEwK`, part1 |7023568 |1920x1080 H264,30fps,1 audio track,54.633313s |

The direct-video SHA256 was identical in both modes:
`20f99bbad0880fc62cb5a9c0ed2ccdb79995ddab742ad775e337817a8e6e92f0`.
The card-video SHA256 was
`1125a6f6684d4dc7d2cdf564d3b1bce557b49357a1e4957209902d791c6c4d9c`.
Independent ffprobe verified the worker's height and complete audio/video
duration; the spool was empty after all releases. These prove actual downloads
and merging for these samples, not QQ reception or universal site entitlement.

### Fresh shared-volume permission check

Created an isolated task-labeled Docker volume. With the actual NapCat image,
mounted it first as UID1000 with `readonly,volume-nocopy`, then mounted it in
the new application image as default UID10001. Application copy-up retained
owner10001 and `ExportSpool.create()` successfully wrote media. A later
NapCat-image UID1000 container read the media through the read-only mount.
The real configured NapCat UID/GID were checked as1000:1000. All test containers
were disposable, disconnected and had no existing data mounts. This verifies
the planned first-start mount order without touching the live spool.

### Remaining validation

Implementation clarified an internal lifecycle detail: pruning is lazy before
authorized video admission, rather than an unconditional adapter-startup sweep.
Expired unknown-send jobs are eligible for removal after1h and count against
the aggregate2 GiB budget until pruning. There is no background deletion timer.
Design/operations now state this precisely; successful export behavior, native
permissions, user scope and existing data lifetime are otherwise unchanged.

Independent check/full regression and actual preview update/native return are
pending. Agents must report exact commands/results and context fallback reads;
main session will append deployment/native evidence and residual human review.

### Implementer gates and loading

The implementer reported native injection was truncated, then explicitly read
the saved output, task artifacts, all applicable spec fallbacks including the
complete configuration/storage file in chunks, plus Python/shell coding skills.
Source changes remained inside the approved product/deployment scope; task,
mainline, private setup and external operations stayed with the main session.

```text
./kisara.sh test tests/unit/test_bilibili.py tests/unit/test_export_video.py tests/unit/test_export_settings.py tests/unit/test_video_worker.py tests/unit/test_export_deployment.py tests/integration/test_video_export_protocol.py tests/unit/test_setu_config.py tests/unit/test_dispatcher.py tests/unit/test_offline_commands.py tests/unit/test_settings.py tests/unit/test_onebot_adapter.py tests/integration/test_onebot_protocol.py -q
373 passed in 8.34s

./kisara.sh test tests/unit/test_bilibili.py tests/unit/test_export_video.py tests/unit/test_export_deployment.py tests/integration/test_video_export_protocol.py -q
51 passed in 1.95s

./kisara.sh test tests/unit/test_engine_deployment.py tests/unit/test_preview_lifecycle.py tests/unit/test_preview_readiness.py tests/unit/test_hako_deployment.py -q
284 passed, 1 skipped in 538.02s
```

The deployment invocation did not print its skip reason (`-q`, without`-rs`);
do not assume the reason from older tasks. Independent full regression will
report the actual skip evidence. Implementer Bash syntax and whitespace checks
passed; ShellCheck/shfmt were unavailable and no application lint/type-check
command is configured. Later checker fixes and final image evidence supersede
these gates only where their executed scope actually overlaps.

### Independent local regressions

The checker verified and fixed two bounded-lifetime defects before its full
gate: stdout EOF collection originally occurred outside the worker deadline,
so an exited worker's descendant retaining the pipe could hang the request;
and an async native acceptance with retcode0 plus an optimistic message ID
was still treated as confirmed. Real subprocess/correlated protocol regressions
failed before the fixes. Current code bounds EOF collection by the same worker
deadline and requires native `status=ok` for confirmation; async outcomes retain
their files as uncertain.

Checker focused gates passed74 feature cases and then161 combined export/
existing OneBot cases. Its full gate passed:

```text
./kisara.sh test -q -rs
1254 passed, 1 skipped, 3 warnings in 563.61s
```

Exact skip: `tests/unit/test_engine_deployment.py:199`, Git CLI is not installed.
Main separately reproduced that test's actual Git ignore-matching fixture in
a temporary host repository, adding synthetic export private/example paths:
10 private paths ignored, 7 examples visible, passed. No host application
imports/toolchain or real private-file contents were involved. The3 warnings
were PTBDeprecationWarning for the SDK's `telegram.error.retry_after` timedelta
transition, not new video warnings.

Final `./kisara.sh preview build onebot` passed after both source fixes. A
disconnected disposable container compared SHA256 for all63 Python source
files against the current workspace: zero mismatches. The actual final
downloader/worker then re-exported the real mini-program short link with the
supplied session; its output matched the earlier digest/size/1080p30 metadata,
and FFmpeg decoded every audio/video stream successfully with `-xerror`.
Spool cleanup passed. New shared spec source claims and manifests were checked;
the known per-file configuration/storage injection warning was covered by
explicit full chunked fallback reads in both agents.

### Live preview rollout and current account gate

After the full gate and exact source/image comparison passed,
`./kisara.sh preview start onebot` performed the approved targeted update.
Before execution, both QQ container IDs/start times still matched baseline,
and the dedicated production export volume did not yet exist. Canonical
ownership preflight accepted the repository objects.

NapCat then reported that its retained QQ quick-login identity had expired and
required QR re-login. The OneBot endpoint was not listening, so no native test
send was attempted. The preview log viewer was interrupted with Ctrl+C (exit130)
to stop viewing only; application/gateway containers and all mounted data were
retained. The user was asked asynchronously to re-login through their existing
NapCat WebUI. Account recovery is an external acceptance prerequisite, not
evidence of a failed provider download or a successful native video return.

Avoid further raw startup-log output while waiting for account recovery:
upstream login diagnostics include dynamically generated QR/token material
that existing configured-value replacement does not fully suppress. No such
values are retained in these task artifacts. Continue with bounded readiness
and selected metadata probes; do not reset QQ state or switch accounts.

Task stays in progress. Native return/client playback remain pending until
login recovery; no commit/archive/push has occurred.

Post-update selected metadata:

| Service | Container ID | Started | Status |
| --- | --- | --- | --- |
| OneBot app | `d75f664f4e64099196f7b4595ac7fee9bc8f1a716a783f840ee24c4fd8135b4f` | `2026-10-26T03:18:41.646742359Z` | running, not ready while QQ endpoint unavailable |
| NapCat | `bd8ddb0f474ad65aa4423599b3eccc7090ff946ecc4b2fd7cf1f1678bbf2191a` | `2026-10-26T03:18:31.132364048Z` | running, awaiting QQ login |
| Telegram | `dff1defad0df13a96fa3e2b7df5dfd925592fb3a2a04384d583edc2d83072570` | `2026-10-22T15:13:06.227062136Z` | unchanged, running |

Application image is
`sha256:2f75691637428e236bec348786e77519592ed53f53b6c88689c8b2b03b8580f1`;
NapCat retains its prior image ID. The live spool is mounted application-RW /
NapCat-RO, owner10001 matches the app, and currently contains zero entries.
No test send occurred before OneBot readiness.

Residual human review classification: `human-required` for account re-login,
native receipt validation and client playback. Implementation, automated checks,
provider bytes/decoding, private setup and runnable verification preparation
are complete. Task remains in progress, uncommitted and unarchived.

## Follow-up: preview locale blocker

The user's later real preview startup failed with `sed` expression2/char25
`Invalid range end` after separate terminal-QR changes. Main reproduced the
exact error under real installed en_US.utf8 and zh_CN.utf8 with synthetic
input; C/C.UTF-8 passed. See
[diagnosis and prevention](research/preview-redaction-locale.md).

The narrow repair scopes byte semantics to internal processing. Bash ANSI/OSC
normalization uses function-local C before literal secret replacement;
foreground filters use `preview_filter_logs`, and background streaming starts
byte-locale sed directly to preserve its real tracked PID. Existing QR,
source/provider code, private configuration and service state are preserved.

Implementer exact final-source gates:

```text
./kisara.sh test tests/unit/test_preview_redaction_locale.py tests/unit/test_qq_login_logs.py tests/unit/test_export_deployment.py -q -rs
43 passed, 6 skipped in 113.01s

./kisara.sh test tests/unit/test_preview_lifecycle.py -q -k 'redaction or keeps_delayed_unicode or status_follows_selected_bot_logs or start_streams_during_readiness or stream_failure or timeout_retains_auxiliary'
30 passed, 160 deselected in 137.66s
```

The6 skips are explicitly unavailable real en_US/zh_CN locales in the test
container. Main independently passed19 host shell probes across six locale
states and three production boundaries plus fail-closed behavior. Both actual
non-C locales are installed; no unsupported-locale fallback is counted as a
pass. Unicode, hidden synthetic secrets and caller locale preservation passed.
The real read-only en_US preview-status smoke restored following, showed no
range/redaction failure, exited130 on interruption and retained all three bot
container IDs/start times. These main probes preceded a later PID-tracking-only
adjustment; the final-source verification is recorded below.

New tests failed before the repair (10failed/3passed/6skipped); an additional
sanitizer-PID regression also failed before correcting the helper-in-background
variant. Bash syntax and whitespace checks pass; ShellCheck/shfmt are absent.
At that stage independent check was active. Earlier full-suite records remain scoped to their
actual source states, including the QQ task's retained video-cleanup timing
failure; no current green full-gate claim is inferred from those records.

Independent review reproduced another same-boundary ordering gap: CR could
split a configured synthetic secret, then final sed control removal could
reconstruct it after literal replacement. The focused regression failed first;
the normalizer now removes remaining ASCII controls before secret replacement,
with CR/backspace/tab/DEL payloads added to all three boundary tests.

Reviewer final-source focused command is the same combined locale/QQ/export
command above:43 passed,6 absent-locale skips in109.12s. Main repeated the
complete19-case HOST matrix on this final source, including real en_US/zh_CN,
expanded hidden-control payloads and sanitizer PID identity, all passed.
Final actual en_US read-only preview-status smoke again followed logs without
range/redaction errors, exited130, reaped its complete viewer process group,
and preserved all related container IDs/start times. QQ remains unready pending
login; these are CLI-fix checks, not native-video or account acceptance.

That full regression was intentionally cancelled after806 passes/7 skips/2
existing warnings in636.65s when review demonstrated that early control removal
collapsed a tab-separated generic Bearer separator. It is incomplete
intermediate evidence, not a completed final gate or a hidden test failure.

The final correction canonicalizes only a strict valid Bearer prefix/separator,
preserving token bytes until control normalization and configured-literal
redaction complete. A partial token is never consumed before a split known
credential can be recognized.19 cross-cases cover known/unknown values and
tab/CR/VT/FF, split tokens, repeated/already-redacted/no-token/Bearerword and
quote/apostrophe/comma/semicolon boundaries in all three fixture paths.

Final frozen-source reviewer focus again passed43/6 unavailable-locale skips
in108.92s. Main reran19 actual HOST probes with every expanded Bearer case per
boundary, direct PID assertions, Unicode and caller-state checks, all passed.
Only after completing the bounded review did the final full gate start.

### Completed final follow-up verification

```text
./kisara.sh test -q -rs
1305 passed, 7 skipped, 3 warnings in 677.45s
exit 0
```

Skips: one absent Git CLI (`test_engine_deployment.py:199`) and three cases
each for genuinely absent en_US.utf8/zh_CN.utf8 in the slim test container
(`test_preview_redaction_locale.py:137`). Host Git ignore matching had already
been verified with synthetic private/example files; current-source real-host
locale probes passed rather than counting fallback-to-C as those skipped tests.
The3 warnings are the existing PTB retry-after timedelta deprecations. The
historical video descendant cleanup timing failure did not recur; its source/
assertion was not changed or claimed repaired by this locale fix.

Final-source host matrix included all19 Bearer cross-cases per payload across
buffered/streaming/snapshot under six locale states, plus failed-filter closure:
19 host probes passed with exact expected output, caller-state preservation and
real sanitizer PID checks. Final real en_US status viewing again followed actual
logs without the user's range/redaction failure, exited130 on SIGINT, left no
viewer process-group members and preserved all three container IDs/start times.
Only verification metadata was printed; captured logs were private and removed.

Independent final source/spec review, Bash syntax and whitespace checks passed.
The locale blocker is `human-not-needed` for its proven behavior; no extra user
confirmation is required for R9/AC8. Overall task still has `human-required`
QQ re-login/native return/playback, with readiness false on the final read-only
check. No native messages have been sent in this follow-up. Host scripts are
already effective, so retrying the existing preview command needs no image
build. No commit/archive/push has occurred.
