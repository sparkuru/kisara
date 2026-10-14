# Trellis Mainline

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

## Approved scoped work

- title: Per-engine public command features and Telegram /tguid
- task: [telegram-tguid](tasks/10-12-telegram-tguid/task.json)
- source: [PRD](tasks/10-12-telegram-tguid/prd.md),
  [design](tasks/10-12-telegram-tguid/design.md),
  [implementation plan](tasks/10-12-telegram-tguid/implement.md).
- decisions: on 2026-10-12 the user requested public-feature lists across bot
  engines, chose `.env`, retained the group master switch, then approved the
  final planning summary with “开始”. Implementation/checking is authorized.
- scope: independent TELEGRAM/ONEBOT/OFFICIAL_PUBLIC_FEATURE inputs, Telegram
  default tguid and otherwise empty defaults, explicit-empty clearing, public
  ordinary command routing and source-UID reply. Existing native permissions,
  live services, private values and unrelated task acceptance stay intact.
- state: implementation and independent check complete, committed as 7da12cd
  after the user's “提交” instruction. Original public-feature
  offline Docker gate: 997 passed, 1 missing-Git skip, 3 existing PTB warnings;
  [validation](tasks/10-12-telegram-tguid/validation.md). Only missing dotenv keys
  were appended after seven scratch preservation/refusal cases passed.
- follow-up: the user requested current-source/settings preview rebuild,
  no-target startup for the COMPOSE_PROFILES list, and platform log labels.
  They chose the same task and explicitly chose profile-list selection rather
  than credential detection, then approved the final summary with “可用”.
  Preview implementation, independent review and spec synchronization are
  complete. Fresh combined full Docker gate: 1024 passed, 1 missing-Git skip,
  3 existing PTB warnings; preview focused 237 and independent combined 140 passed.
  Earlier 997-pass evidence covers only the public-feature scope.
- boundaries: local delivery commits are authorized; no automatic enrollment,
  account operation, deployment, archive or push. The existing native-archive initiative and its
  separate account acceptance above remain unchanged.
- proposed follow-up: after an ownership refusal on the stopped ordinary
  Telegram container, the user highlighted redundant lifecycle guards.
  The user requested a new fix task, now tracked as
  [container-lifecycle](tasks/10-13-container-lifecycle/prd.md). No service
  conversion was performed.

## Approved lifecycle fix

- task: [container-lifecycle](tasks/10-13-container-lifecycle/task.json)
- source: [PRD](tasks/10-13-container-lifecycle/prd.md),
  [design](tasks/10-13-container-lifecycle/design.md),
  [implementation plan](tasks/10-13-container-lifecycle/implement.md),
  [research](tasks/10-13-container-lifecycle/research/lifecycle.md).
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
  Independent gate 70 passed; final full Docker gate 1067 passed, 1 existing
  missing-Git skip, 3 existing PTB warnings. Bash/whitespace checks and both
  context manifests pass; [validation](tasks/10-13-container-lifecycle/validation.md)
  records intermediate fixes, exact checks and offline evidence limits.
- boundaries: preserve prior work, all stored data, bot/native/public permissions
  and foreign project isolation. Local delivery commits are authorized. No
  private dotenv changes, live operation, archive/push or generic repository
  lock audit in this new task.

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
| 3 | [Telegram /tgsetu, configuration roots and command entry](tasks/10-10-telegram-tgsetu/task.json) | in_progress, implemented and merged; scoped QQ preview ready | Work 2782454 on keiyaku-no-kisu; final combined Docker suite 913 passed/1 host-verified Git skip; official image/RO-cache smoke passed; scoped OneBot preview ready with data retained; Telegram account/deployment acceptance pending, so not archived |
| 4 | [Preview status bot logs](tasks/archive/2026-10/10-11-preview-status-logs/task.json) | completed, archived | Work 2782454; archive 47ea1cc on keiyaku-no-kisu; all acceptance met; fresh 20-case focused gate passed; existing full913 passed/1 skipped and real read-only follow/interrupt smoke preserved bot/NapCat |
| 5 | [Public features, /tguid and preview](tasks/10-12-telegram-tguid/task.json) | in_progress; implemented/checked, locally committed | Work 7da12cd authorized by “提交”; focused 237/independent combined 140 passed, final full Docker 1024 passed/1 skipped/3 existing warnings; no deployment/archive/push |
| 6 | [Unified container lifecycle](tasks/10-13-container-lifecycle/task.json) | implemented/checked; locally committed | Work 6af84c6 authorized by “提交”; independent 70 passed, final full 1067 passed/1 existing skip/3 existing warnings; no live service change/archive/push |

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
  separately scoped deployment/account acceptance remains pending. Its
  [prepared acceptance](tasks/10-10-telegram-tgsetu/live-validation.md) is ready.
  Setu is accepted and archived; no further work or new task is inferred.

## Lifecycle maintenance

Read this record at task start/resume, before commit/archive and next-work
selection. Approved requirement changes update sources/scope/acceptance/work
mapping together. Checks add verified results and remaining limitations; archives
update locations/work and archive commits/remaining scope. Preserve approvals
and source distinctions on rerun; do not create duplicate tasks or work rows.
Use the read-only Pulse and guided/serial/paused boundaries in
[workflow.md](spec/trellis-plus/workflow.md#mainline-continuity).
