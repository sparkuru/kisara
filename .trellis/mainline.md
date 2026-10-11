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
  acceptance remain separate, with no commit/archive authorization.

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
  [setu PRD Goal/Requirements/Acceptance](tasks/10-09-setu-archive-files/prd.md).
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
| 2 | [Setu archive attachments](tasks/10-09-setu-archive-files/task.json) | in_progress, pending live acceptance | Work commit c3e2f32; automated/byte-transfer evidence below; updated-runtime command/receipts/checkpoints not yet verified; do not activate, deploy or archive as a side effect of remediation |
| 3 | [Telegram /tgsetu, configuration roots and command entry](tasks/10-10-telegram-tgsetu/task.json) | in_progress, implemented/verified; scoped QQ preview ready | Branch feat/telegram-tgsetu; latest full Docker suite 893 passed/1 host-verified Git skip; official image/RO-cache smoke passed; separately authorized OneBot preview start/status ready, data retained; Telegram/controlled feature acceptance pending, commit/archive unapproved |
| 4 | [Preview status bot logs](tasks/10-11-preview-status-logs/task.json) | in_progress, implemented/verified | User approved revised continuous-follow plan on 2026-10-11; selected-owned bot logs, per-line redaction and Ctrl+C reader cleanup; final913 passed/1 skipped; real read-only follow/interrupt smoke preserved bot/NapCat; no commit or archive |

## Evidence and decisions

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
  commit or archive. [Evidence](tasks/10-11-preview-status-logs/validation.md).
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
  [2026-10-09 validation](tasks/10-09-setu-archive-files/validation.md) records
  308 focused/580 full Docker tests and one 109092709-byte native transfer with
  independent hash match. These are historical scoped results, not this task's
  revalidation or proof of deployed quoted-command acceptance.
- Pending setu acceptance: progress/result receipts and SQLite completion under
  the updated deployed runtime; separate native private-forward failure remains.
  See [live instructions](tasks/10-09-setu-archive-files/live-validation.md).
  Keep task status in_progress and do not mark acceptance complete from commit.
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
- Next permitted action: deliver latest script-retirement/probe-fix/startup
  evidence and retain the requested running QQ preview. Telegram deployment,
  controlled feature/account acceptance and committing/archive need their own
  scope. [Prepared acceptance](tasks/10-10-telegram-tgsetu/live-validation.md)
  is ready; Setu acceptance remains separately pending.

## Lifecycle maintenance

Read this record at task start/resume, before commit/archive and next-work
selection. Approved requirement changes update sources/scope/acceptance/work
mapping together. Checks add verified results and remaining limitations; archives
update locations/work and archive commits/remaining scope. Preserve approvals
and source distinctions on rerun; do not create duplicate tasks or work rows.
Use the read-only Pulse and guided/serial/paused boundaries in
[workflow.md](spec/trellis-plus/workflow.md#mainline-continuity).
