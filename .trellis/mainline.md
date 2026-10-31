# Trellis Mainline

## Completed QQ login QR logs — 2026-10-31

- Task: [qq-login-terminal-qr](tasks/archive/2026-10/10-26-qq-login-terminal-qr/task.json),
  [requirements](tasks/archive/2026-10/10-26-qq-login-terminal-qr/prd.md),
  [design](tasks/archive/2026-10/10-26-qq-login-terminal-qr/design.md).
- Owner accepted the delivered terminal login flow with “通过；可以提交、归档”.
  Human acceptance is recorded by owner report, not an agent-observed phone scan.
- Delivered: existing QQ preview/log commands render the actual saved PNG at
  login events, with bounded ownership-checked reads, whole-block output,
  refresh/deduplication, terminal fallbacks and locale-safe credential redaction.
  No additional QR command, encoder, WebUI session or polling watcher.
- Runtime repair: keep Docker timestamps private from display sanitization,
  exclude public MAX_URLS counts from secret discovery, and parse nanosecond
  fractions using integer arithmetic on actual NapCat Python3.10.
- Verification: final focused62 passed/6 optional locale skips; full1316 passed/
  7 skipped/3 existing warnings. Exact cached Python3.10 reader and synthetic
  PNG byte comparison passed. Historical failures and their narrower evidence
  remain in the [review records](tasks/archive/2026-10/10-26-qq-login-terminal-qr/runtime-check-evidence.md).
- Work commit: `bc74135`; archive commit: `6b03a23`; completed and archived on
  2026-10-31 at `tasks/archive/2026-10/10-26-qq-login-terminal-qr`.
  This was direct work on existing `feat/export-linked-video`, never PR-backed;
  the documented archive branch-validation exception records that fact.
- Unrelated video-export implementation and paused Telegram tasks are retained.
  Video export retains its own acceptance and delivery record.
  This delivery performed no push, merge or service/account operation.

## Completed Bilibili video export — 2026-10-31

- Task: [export-linked-video](tasks/archive/2026-10/10-26-export-linked-video/task.json),
  [requirements](tasks/archive/2026-10/10-26-export-linked-video/prd.md),
  [design](tasks/archive/2026-10/10-26-export-linked-video/design.md),
  [execution plan](tasks/archive/2026-10/10-26-export-linked-video/implement.md).
- Owner decisions: explicitly requested task creation and use of recent
  preview examples, approved Bilibili-only first scope, supplied a temporary
  session file for use, then approved the final planning summary with “开始”.
- Approved scope: OneBot quoted mini-program/short-link/video-URL export,
  session-aware highest available quality, complete MP4/native video return,
  preserved image export/auth boundaries, bounded temporary transport and
  targeted OneBot/NapCat preview verification preserving login/state.
- State: completed and archived on `feat/export-linked-video`; work commit
  `bb228b3`, archive commit `c7a3332`. Initial full Docker
  gate1254 passed/1 missing-Git skip/3 existing SDK warnings.
  The skipped ignore fixture was verified separately. Real extractor/download/
  merge probes produced complete1080p30 audio/video for both supplied source
  videos; final-image source comparison and complete decoding passed.
- Preview follow-up: the user's actual startup exposed non-C collation failure
  in shared ANSI redaction. Scoped byte-locale processing, control normalization
  and strict Bearer separator preservation now pass independent review,
  19 actual-host probes and real read-only CLI follow/cleanup checks. Current
  earlier combined full gate1305 passed/7 dependency-or-locale skips/3 existing
  warnings. Final unchanged-source combined gate1316 passed/7 skips/3 existing
  warnings is reused; delivery-time video/OneBot focus209 passed.
  Host Git/real locale supplements cover absent tooling/locales. No rebuild,
  service/account mutation or private-config change was needed for this fix.
- Acceptance: on 2026-10-31 the user confirmed “qq 回传确认了。通过”,
  closing the prior native return gate, and explicitly authorized commit/archive.
  All ACs are closed; this is user-reported acceptance, without newly collected
  receipt IDs or playback measurements. See
  [evidence](tasks/archive/2026-10/10-26-export-linked-video/validation.md).
- Delivery boundaries: no other providers/engines, playlist expansion, per-user
  credential management, unrelated Telegram work or push. The separate QQ
  terminal-QR task has its own completed delivery above.

## Ready-task delivery and archival — 2026-10-26

The user requested “将可归档/提交归档的，全部归档/提交归档”, authorizing
local delivery of the three checked pending changes and archival of all five
ready tasks. Combined work commit `2e477fb` includes preview streaming,
Telegram startup recovery and configurable scheduled-news retry, with their
plans, review evidence and shared contracts. The task map below records each
archive commit and destination. Earlier commit/archive exclusions in retained
planning and validation history are superseded only for these five tasks.

The two TgSetu parent/child tasks remain paused and active, with their pending
local Bot API/account acceptance unchanged. No new task, deployment, live
service/account operation or push was performed. Existing full-regression
records were reused; this archival session verified Bash syntax, whitespace,
all five archived context manifests, task state, local ancestry and attribution.

## Current initiative

- title: Telegram /tgsetu native archive
- owner decision: 2026-10-11, “嗯，方案合适；继续” approved the latest final
  planning summary for implementation/checking.
- follow-up decision: 2026-10-11, “按照你的建议，处理第 2 点问题” approves
  engine configuration root unification, safe OneBot migration and checks;
  [scope](tasks/10-10-telegram-tgsetu/research/config-root-unification.md).
- source and acceptance: [PRD](tasks/10-10-telegram-tgsetu/prd.md),
  [design](tasks/10-10-telegram-tgsetu/design.md),
  [implementation plan](tasks/10-10-telegram-tgsetu/implement.md).
- scope: authorized private on/off automatic media saving, caption/tag and
  original-attachment naming, flat individual-file atomic publication with
  partial-success retry, local Bot API large-file deployment preparation.
- added scope: explicit config/<engine> loading across Compose/hako/direct
  entrypoints, same-path mounts, private-file ignores and retained old backups.
- entrypoint decisions: user approved kisara.sh/hako/deploy/engines.sh, then
  explicitly removed the four temporary root scripts. Preserve stored preview
  labels and use real canonical fixtures; current guidance uses kisara.sh.
- operational decision: user selected removal of the two stopped QQ deployment
  containers and startup of the effective canonical OneBot preview, preserving
  mounted login/data and leaving Telegram unchanged. The actual QQ preview is
  now ready; this limited authorization supersedes the earlier no-service rule.
- boundaries: preserve OneBot behavior/state, retain current requested QQ
  preview; Telegram deployment/endpoint switch and controlled feature/account
  acceptance remain separate. The combined work commit is complete; the later
  cleanup request authorizes archival only for tasks with completed acceptance,
  local branch integration and removal, without new task creation or push.
- pause decision: on 2026-10-22 the user requested that Telegram-related
  implementation be paused because an application cannot currently be obtained
  from my.telegram.org. Keep the completed offline implementation, tests,
  research and pending live-acceptance records; do not perform the local API
  cutover, cloud `logOut`, service restart or further Telegram implementation
  until the user explicitly resumes it.

## Approved Setu automatic-mode work

- task: [setu-auto-mode](tasks/10-31-setu-auto-mode/task.json).
- source: [PRD](tasks/10-31-setu-auto-mode/prd.md),
  [design](tasks/10-31-setu-auto-mode/design.md),
  [execution plan](tasks/10-31-setu-auto-mode/implement.md).
- owner decisions: on 2026-10-31 the user requested task creation for
  `/setu on` / `/setu off`, selected activation resetting after process restart
  with “重启关闭吧”, and approved the final planning summary with “开始”.
- scope: per-user/instance memory activation for authorized OneBot private
  merged forwards, existing quoted start/result feedback and failed-item retry,
  default-off and restart-off behavior, and preserved manual archive flows.
- state: implementation, independent review and owner acceptance complete;
  user reported “验收通过；可以提交” on 2026-10-31 and authorized local delivery.
  Focused Setu/protocol gate: 276 passed. Full run:
  1342 passed, 7 skipped, one unrelated preview process-cleanup assertion failed;
  exact isolated retry passed (1 passed). Full run is not wholly green; no
  deployment code was changed. [Evidence](tasks/10-31-setu-auto-mode/validation.md).
- boundaries: local work commit and normal archive/session record are now
  authorized. No Telegram/group/standalone-media expansion, schema changes,
  live service operations, deployment or push. This task does not resume the
  paused TgSetu account/deployment work.

## Approved scoped work

- title: Per-engine public command features and Telegram /tguid
- task: [telegram-tguid](tasks/archive/2026-10/10-12-telegram-tguid/task.json)
- source: [PRD](tasks/archive/2026-10/10-12-telegram-tguid/prd.md),
  [design](tasks/archive/2026-10/10-12-telegram-tguid/design.md),
  [implementation plan](tasks/archive/2026-10/10-12-telegram-tguid/implement.md).
- decisions: on 2026-10-12 the user requested public-feature lists across bot
  engines, chose `.env`, retained the group master switch, then approved the
  final planning summary with “开始”. Implementation/checking is authorized.
- scope: independent TELEGRAM/ONEBOT/OFFICIAL_PUBLIC_FEATURE inputs, Telegram
  default tguid and otherwise empty defaults, explicit-empty clearing, public
  ordinary command routing and source-UID reply. Existing native permissions,
  live services, private values and unrelated task acceptance stay intact.
- state: completed and archived as 6214a28 on 2026-10-26; work commit 7da12cd
  is on keiyaku-no-kisu. The user authorized archival of all ready tasks. Original public-feature
  offline Docker gate: 997 passed, 1 missing-Git skip, 3 existing PTB warnings;
  [validation](tasks/archive/2026-10/10-12-telegram-tguid/validation.md). Only missing dotenv keys
  were appended after seven scratch preservation/refusal cases passed.
- follow-up: the user requested current-source/settings preview rebuild,
  no-target startup for the COMPOSE_PROFILES list, and platform log labels.
  They chose the same task and explicitly chose profile-list selection rather
  than credential detection, then approved the final summary with “可用”.
  Preview implementation, independent review and spec synchronization are
  complete. Fresh combined full Docker gate: 1024 passed, 1 missing-Git skip,
  3 existing PTB warnings; preview focused 237 and independent combined 140 passed.
  Earlier 997-pass evidence covers only the public-feature scope.
- boundaries: local delivery and archival are authorized; no automatic enrollment,
  account operation, deployment or push. The existing native-archive initiative and its
  separate account acceptance above remain unchanged.
- proposed follow-up: after an ownership refusal on the stopped ordinary
  Telegram container, the user highlighted redundant lifecycle guards.
  The user requested a new fix task, now tracked as
  [container-lifecycle](tasks/archive/2026-10/10-13-container-lifecycle/prd.md). No service
  conversion was performed.

## Approved lifecycle fix

- task: [container-lifecycle](tasks/archive/2026-10/10-13-container-lifecycle/task.json)
- source: [PRD](tasks/archive/2026-10/10-13-container-lifecycle/prd.md),
  [design](tasks/archive/2026-10/10-13-container-lifecycle/design.md),
  [implementation plan](tasks/archive/2026-10/10-13-container-lifecycle/implement.md),
  [research](tasks/archive/2026-10/10-13-container-lifecycle/research/lifecycle.md).
- owner decisions: on 2026-10-13 the user requested task creation and a fix for
  the redundant deployment/preview guards, then explicitly chose to merge
  stop/down and retain down only (stop and remove objects, persistent data kept).
- delivered scope: common exact repository identity/preflight and removal;
  ordinary/preview switching through Compose; remove custom fingerprint/reuse/
  partial/build-existing refusals and attempt labels; scoped OneBot forwarding;
  application-only startup recreation and normal auxiliary reconciliation.
- approved failure policy: retain failed-start containers for diagnostic
  inspection and direct startup retry, rather than bespoke container rollback.
  Keep redacted logs, readiness and readers/temp cleanup.
- state: final summary approved with “开始”; implementation, independent review
  and spec synchronization complete on feat/container-lifecycle. The user's
  2026-10-14 “提交” instruction authorized local delivery; work commit is 6af84c6.
  Completed and archived as 671f6e1 on 2026-10-26 under the ready-task cleanup request.
  Independent gate 70 passed; final full Docker gate 1067 passed, 1 existing
  missing-Git skip, 3 existing PTB warnings. Bash/whitespace checks and both
  context manifests pass; [validation](tasks/archive/2026-10/10-13-container-lifecycle/validation.md)
  records intermediate fixes, exact checks and offline evidence limits.
- boundaries: preserve prior work, all stored data, bot/native/public permissions
  and foreign project isolation. Local delivery commits are authorized. No
  private dotenv changes, live operation, push or generic repository lock audit.
  The 2026-10-26 request authorized local archival.

## Approved preview status fix

- task: [preview-status-streaming](tasks/archive/2026-10/10-22-preview-status-streaming/task.json)
- source and acceptance: [PRD](tasks/archive/2026-10/10-22-preview-status-streaming/prd.md).
- owner decisions: on 2026-10-22 the user requested a new task to restore
  continuous `./kisara.sh preview status` output, then approved the final
  planning summary with “同意”. Implementation/checking is authorized.
- scope: reproduce and minimally repair the existing log stream; retain
  credential redaction, platform labels, bounded storage and signal cleanup.
- state: the user reopened acceptance after bare preview waited until Ctrl+C
  and status printed logs then exited. The diagnostic marker and actual-CLI
  fixtures established readiness-gated diagnostics; earlier locale-only checks
  did not cover those paths. The user approved the revised final summary with
  “确认”. Startup now streams during readiness and remains attached afterward;
  unready status warns and follows. Viewing interruption skips duplicate
  diagnostics while genuine startup failures retain bounded diagnostics.
  New regressions: 8 failed before / 8 passed after; focused gate: 289 passed,
  1 existing skip; strengthened post-ready output: 4 passed. Independent full
  regression: 1115 passed, 1 existing skip, 3 existing PTB warnings. Independent
  review found no actionable production defect. Work committed as 2e477fb and
  task completed/archived as 44dcd31 on 2026-10-26.
  Controlled read-only unready status held for 12 seconds
  with unchanged three-container identities/state. QR filtering also preserves
  Chinese logs in C/POSIX and UTF-8 locales. See
  [validation](tasks/archive/2026-10/10-22-preview-status-streaming/validation.md) for current
  readiness-path evidence and separately scoped historical locale results.
- boundaries: no private dotenv value inspection, live service changes, account
  messages or push. Local delivery and archival were authorized on 2026-10-26;
  Telegram deployment/account work stays paused.

## Approved Telegram startup recovery

- task: [telegram-startup-recovery](tasks/archive/2026-10/10-22-telegram-startup-recovery/task.json)
- source: [PRD](tasks/archive/2026-10/10-22-telegram-startup-recovery/prd.md),
  [design](tasks/archive/2026-10/10-22-telegram-startup-recovery/design.md),
  [execution plan](tasks/archive/2026-10/10-22-telegram-startup-recovery/implement.md).
- user request: on 2026-10-22 the user supplied one failed Telegram startup
  followed by polling-ready logs and requested a fix. This narrowly resumes
  startup diagnosis/repair; TgSetu deployment/account work stays paused. The
  user approved the final planning summary with “可以”.
- evidence: startup has no network retry and the process boundary discards safe
  exception classification. The supplied logs cannot recover the actual prior
  exception; no private runtime or live account operation was inspected.
- approved scope: three total startup attempts for transient network failures,
  interruptible 1/2-second backoff, safe phase/category diagnostics, cleanup
  before retry, and no retry for credential/ownership/bad-request failures.
- state: PRD/design/execution plan and both context manifests prepared and
  validated; implementation and independent review passed. The original getMe
  and deleteWebhook transport-failure fixtures failed before the correction;
  focused gate passed 173 tests and independent full regression passed 1107
  tests, with 1 existing skip and 3 existing PTB warnings. See
  [validation](tasks/archive/2026-10/10-22-telegram-startup-recovery/validation.md). Commit approval
  was granted on 2026-10-26: work committed as 2e477fb and task completed/archived
  as a2b17f3. This task did not rebuild or change live images/containers, and
  deployment of the Telegram application changes is unverified.
- boundaries: preserve preview streaming work and prior commit boundaries;
  no live restart, endpoint/proxy change, cloud logOut or local API cutover.

## Scheduled news retry configuration

- task: [news-push-retry](tasks/archive/2026-10/10-26-news-push-retry/task.json)
- source: [PRD](tasks/archive/2026-10/10-26-news-push-retry/prd.md),
  [design](tasks/archive/2026-10/10-26-news-push-retry/design.md),
  [execution plan](tasks/archive/2026-10/10-26-news-push-retry/implement.md).
- user request: on 2026-10-26 the user requested automatic scheduled-news retry
  after about60 seconds and then required a configurable seconds value.
- scope: replace the existing15-minute retry interval with a positive integer
  setting, default60, for OneBot and Telegram scheduled news. Reuse per-engine
  TOML/environment precedence, delivery checkpoints and Telegram longer
  retry-after/permanent/uncertain guards. Manual news and HTTP retry are unchanged.
- state: implementation and focused regression passed386 tests with one existing
  skip in20.97 seconds. Selected new regressions failed23/passed8 before the
  implementation and passed31 afterward. Independent source review found no
  actionable production defect; full offline regression passed1179 tests with
  one existing skip and three existing PTB warnings in560.36 seconds, exit0.
  Both eight-entry task context manifests validated (large spec explicitly read
  after native truncation); examples/docs/specs updated. All acceptance criteria
  met; work committed as 2e477fb and task completed/archived as 6cd1c1e on
  2026-10-26. Live deployment remains unperformed. See
  [independent check](tasks/archive/2026-10/10-26-news-push-retry/check-evidence.md).
- boundaries: preview and Telegram startup work were delivered together in the
  authorized 2e477fb commit. No live service mutation, account/provider operation,
  private configuration rewrite, schema/dependency change or push.

## Previous initiative

- title: Approved Trellis Plus audit-gap remediation
- parent task: none
- objective: repair the approved repository policy/loading/notices/continuity and
  preview gaps while preserving live services and protected Trellis material
- owner decision: 2026-10-09, user approved the full audit plan and then task
  creation plus planning/implementation; after the final report, "可以归档"
  authorized work commit, this task's archive and session/mainline records.
  No deployment, push, live-service operation or other-task archive is authorized.

## Requirements and sources

- Current remediation scope/acceptance:
  [PRD](tasks/archive/2026-10/10-09-trellis-plus-gaps/prd.md),
  [design](tasks/archive/2026-10/10-09-trellis-plus-gaps/design.md),
  [implementation plan](tasks/archive/2026-10/10-09-trellis-plus-gaps/implement.md).
- Separately approved product work:
  [setu PRD Goal/Requirements/Acceptance](tasks/archive/2026-10/10-09-setu-archive-files/prd.md).
  Its 2026-10-09 plan approval covers archive naming, canonical IDs, bounded
  native transfer/retry and save-start notices; it is not deployment authority.
- Historical architecture direction:
  [design.md sections 1-4](../design.md). Preserve its useful single-engine,
  protocol-neutral and allowlist boundaries. Its opening correction supersedes
  first-version database/external-service bans and group-only-mention restriction.
- Current feature/storage evidence: [Plus index](spec/trellis-plus/index.md),
  [architecture](spec/trellis-plus/architecture.md),
  [configuration/storage](spec/trellis-plus/configuration-storage.md),
  [legacy migration](../docs/legacy-migration.md).
- Previous remediation constraints/non-goals: no new product feature, reinitialization/tool upgrade,
  historical commit rewrite, unrelated cleanup or live data reset. Keep loopback,
  SSH-tunnel and internal-only services. Sources stay in place.
- Proposed/conflicting requirements: remaining old design milestones have no
  current approval/priority evidence and are proposed/reference only. Older
  rollout status does not reopen later approved task acceptance. No serial
  initiative or subsequent product backlog is inferred from implementation.

## Continuation

- mode: guided
- serial authorization: none
- next pulse: relevant no-task request, after archive, or user-requested

## Work and dependencies

Rows list existing approved work, not a new product-priority decision. No
parent/child relationship or serial execution is inferred.

| Order | Task | State | Readiness/dependency evidence |
| --- | --- | --- | --- |
| 1 | [Trellis Plus remediation](tasks/archive/2026-10/10-09-trellis-plus-gaps/task.json) | completed, archived | Work 6f8f043; archive fc0d64f; final full suite 643 passed; real preview acceptance remains unrun |
| 2 | [Setu archive attachments](tasks/archive/2026-10/10-09-setu-archive-files/task.json) | completed, archived | Work c3e2f32 on keiyaku-no-kisu; user confirmed task acceptance passed on 2026-10-11; archive 10feef1; existing 308 focused/580 full passes and isolated native-byte/digest evidence retained |
| 3 | [Telegram /tgsetu, configuration roots and command entry](tasks/10-10-telegram-tgsetu/task.json) | paused at user request; implemented and merged | Work 2782454 on keiyaku-no-kisu; final combined Docker suite 913 passed/1 host-verified Git skip; official image/RO-cache smoke passed; scoped OneBot preview ready with data retained; Telegram account/deployment acceptance remains pending and is not archived |
| 4 | [Preview status bot logs](tasks/archive/2026-10/10-11-preview-status-logs/task.json) | completed, archived | Work 2782454; archive 47ea1cc on keiyaku-no-kisu; all acceptance met; fresh 20-case focused gate passed; existing full913 passed/1 skipped and real read-only follow/interrupt smoke preserved bot/NapCat |
| 5 | [Public features, /tguid and preview](tasks/archive/2026-10/10-12-telegram-tguid/task.json) | completed, archived | Work 7da12cd; archive 6214a28; independent combined 140 and full 1024 passed/1 existing skip/3 existing warnings; no deployment/push |
| 6 | [Unified container lifecycle](tasks/archive/2026-10/10-13-container-lifecycle/task.json) | completed, archived | Work 6af84c6; archive 671f6e1; independent 70 and full 1067 passed/1 existing skip/3 existing warnings; no live operation/push |
| 7 | [Preview status continuous output](tasks/archive/2026-10/10-22-preview-status-streaming/task.json) | completed, archived | Work 2e477fb; archive 44dcd31; actual readiness regressions 8 failed before/8 passed after; 289 focused and 1115 full passes/1 existing skip/3 existing warnings; strengthened post-ready cases 4 passed |
| 8 | [Telegram startup recovery](tasks/archive/2026-10/10-22-telegram-startup-recovery/task.json) | completed, archived | Work 2e477fb; archive a2b17f3; bounded startup recovery and safe categories verified; 173 focused and 1107 full passes/1 existing skip/3 existing warnings; no live operation |
| 9 | [Configurable scheduled news retry](tasks/archive/2026-10/10-26-news-push-retry/task.json) | completed, archived | Work 2e477fb; archive 6cd1c1e; 386 focused and 1179 independent full passes/1 existing skip/3 existing warnings; default/configurable retry and delivery-state protections verified; no live deployment |
| 10 | [Quoted Bilibili video export](tasks/archive/2026-10/10-26-export-linked-video/task.json) | completed, archived | Work bb228b3; archive c7a3332; final video/OneBot focus209 passed; unchanged-source full1316 passed/7 skips/3 existing warnings; real MP4/decoding/shared-volume checks and owner QQ native-return acceptance complete; no push |

## Evidence and decisions

- Setu acceptance closure 2026-10-11: the user confirmed
  “setu-archive-files 已通过；可以验收；”. This user-reported live pass
  satisfies the prior human acceptance gate and authorizes completion under
  the existing archive request. Task archived as `10feef1`, with one Codex
  trailer. [Acceptance record](tasks/archive/2026-10/10-09-setu-archive-files/validation.md)
  distinguishes the user report from earlier automated/isolated evidence;
  no new per-case logs, digests or independent native-forward repair claims
  were invented. No new application tests, account/service operation or push
  occurred. Only Telegram remains active and pending its separate acceptance.
- Existing-task cleanup 2026-10-11: the user explicitly requested no new task,
  review/completion/archival of existing tasks where ready, merge of all local
  branches into the main branch and deletion of the remaining local branches.
  All three active tasks were reviewed. Preview status logs met every criterion
  and were archived as `47ea1cc`, with the required single Codex trailer and
  corrected target branch metadata. Fresh focused gate: 20 passed, 89 deselected
  in78.03s; Bash syntax and merge-range whitespace checks passed. Setu and
  Telegram retain in-progress status for their recorded account acceptance.
  `chore/trellis-plus-gaps` was already included; `feat/telegram-tgsetu` was
  fast-forwarded into `keiyaku-no-kisu`. Both source branches were verified as
  ancestors of main and deleted with non-forced `git branch -d`; their recorded
  task branch fields remain historical provenance. No push, account message or
  live service mutation occurred. This supersedes the earlier archive exclusion
  for completed tasks only; historical decisions below describe their own stage.
- Delivery decision: after reviewing the preview-status commit dependency scope,
  the user approved the combined 105-path work commit covering implemented Telegram
  archiving/configuration/canonical-command/probe work and continuous status logs.
  Workspace journals, push and archive are excluded. This supersedes prior
  no-commit boundaries for those reviewed paths only; Telegram account/deployment
  acceptance and existing task in-progress states remain unchanged.
- Preview status logs 2026-10-11: user corrected the finite snapshot to continuous
  following and approved the revised plan. Owned bot IDs now emit the last80
  lines and new sanitized labeled logs through bounded FIFO stages. Parent-only
  INT/TERM reaps all invocation readers/helpers without container/data changes;
  failures remain explicit with no raw fallback. Independent20-case review gate,
  real12-second status/interrupt smoke and final Docker regression913 passed,
  1 skipped, 3 existing PTB warnings passed. No service recreation, deployment,
  commit or archive. [Evidence](tasks/archive/2026-10/10-11-preview-status-logs/validation.md).
- Script retirement and scoped runtime follow-up 2026-10-11: user deleted the
  four old root scripts and approved replacing stopped QQ deployment containers
  with canonical OneBot preview, keeping mounted data and Telegram unchanged.
  Real startup exposed NapCat's missing Node and root301 WebUI redirect; bounded
  Python stdlib HTTP/TCP at /webui/ plus existing listener decoder fixes both,
  with real helper/no-Node/remote-host regression coverage. Final fullgate:
  893 passed, 1 host-verified Git skip, 3 existing PTB warnings. Real start and
  separate status returned ready; both QQ objects own stored preview labels,
  retain original login/config/state storage and use config/onebot/fonts roots.
  Telegram retains its original stopped container. No controlled feature
  acceptance, Telegram migration, commit or archive. [Evidence](tasks/10-10-telegram-tgsetu/validation.md).
- Command-entry follow-up 2026-10-11: user approved kisara.sh as public command,
  hako as development executor and deploy/engines.sh as lifecycle owner. Pure
  help, offline console/tests, detached up, explicit preview targets and
  temporary compatibility forwarding are implemented and independently
  reviewed. Existing preview ownership/readiness/cleanup/local API staging
  remains. Latest canonical full gate: `./kisara.sh test -q`, 907 passed,
  1 existing host-verified Git skip, 3 existing PTB warnings; real offline
  console /quit smoke passed. No live service/account operation, commit or
  archive. [Validation](tasks/10-10-telegram-tgsetu/validation.md) records scope.
- Configuration follow-up 2026-10-11: selected config/<engine> roots now match
  across Compose/hako/direct execution; engine-only same-path mounts, moved
  OneBot examples, private ignores and no-overwrite byte/mode migration are
  independently reviewed. Final full Docker gate: 825 passed, 1 Git-dependent
  skip verified separately in a host temporary repository, 3 existing PTB
  warnings. Existing broad preview fingerprint is documented; runtime roots
  remain isolated. Activation needs targeted recreation, not just restart;
  no live service operation or commit/archive was performed.
- TgSetu 2026-10-11: native activation/media handling, durable per-file flat
  archive/retry/recovery, caption/album naming and internal local API deployment
  preparation implemented. Independent review addressed cache symlink aliasing,
  count wording, saturated-worker naming deadlines and readiness fixtures.
  Final full Docker suite: 786 passed,
  3 existing PTB warnings; [validation](tasks/10-10-telegram-tgsetu/validation.md)
  records scoped checks, successful official image/RO-cache smoke and remaining
  account acceptance. No live switch,
  deployment, commit or archive performed.
- Setu work commit: `c3e2f324e3a4a780702cc5c84b3deb670f48d807`.
  [2026-10-09 validation](tasks/archive/2026-10/10-09-setu-archive-files/validation.md) records
  308 focused/580 full Docker tests and one 109092709-byte native transfer with
  independent hash match. These are historical scoped results, not this task's
  revalidation or proof of deployed quoted-command acceptance.
- Setu acceptance: the formerly pending deployed-command human gate is closed
  by the user's 2026-10-11 pass confirmation; task completed and archived.
  See [live acceptance record](tasks/archive/2026-10/10-09-setu-archive-files/live-validation.md).
  Earlier private-forward diagnostics remain historical, without a new
  independently verified repair claim.
- Earlier engine configuration archive:
  [task](tasks/archive/2026-10/10-04-engine-env-config/task.json), work `d89fdbe`,
  archive `45cc86a`; [validation](tasks/archive/2026-10/10-04-engine-env-config/validation.md)
  records engine isolation and scoped Telegram readiness on 2026-10-04.
- Remediation start: normal task created/started after explicit user consent;
  PRD/design/plan and curated context recorded. Implementation and behavioral
  regression checks are recorded in [validation](tasks/archive/2026-10/10-09-trellis-plus-gaps/validation.md);
  independent final gate passed 643 tests (3 existing PTB warnings), shell syntax
  and diff checks. After verified archive execution, self-check is 45 PASS /
  1 historical GAP / 6 UNKNOWN / 5 N/A; the 22 prospectively repairable GAPs
  are addressed. Real preview cold-start/image/account/device acceptance is unrun.
- Remediation closure: user approved archival after reviewing the final report.
  Work `6f8f043910e444cf1f2e18a0d5c26ef0668044f7`; archive
  `fc0d64f15f381fae3a4faab57ddcc84e9ddfdeb6`, exact single-task scope and
  one Codex trailer. Status completed; active pointer cleared. Preserve the
  Setu task and all prior approvals; no merge or push was performed.
- Next permitted action: retain the requested running QQ preview; Telegram's
  separately scoped deployment/account acceptance is paused. Its
  [prepared acceptance](tasks/10-10-telegram-tgsetu/live-validation.md) remains
  ready for a future explicit resume.
  Setu is accepted and archived; no further work or new task is inferred.

## Lifecycle maintenance

Read this record at task start/resume, before commit/archive and next-work
selection. Approved requirement changes update sources/scope/acceptance/work
mapping together. Checks add verified results and remaining limitations; archives
update locations/work and archive commits/remaining scope. Preserve approvals
and source distinctions on rerun; do not create duplicate tasks or work rows.
Use the read-only Pulse and guided/serial/paused boundaries in
[workflow.md](spec/trellis-plus/workflow.md#mainline-continuity).
