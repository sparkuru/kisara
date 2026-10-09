# Trellis Mainline

## Initiative

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
  [PRD](tasks/10-09-trellis-plus-gaps/prd.md),
  [design](tasks/10-09-trellis-plus-gaps/design.md),
  [implementation plan](tasks/10-09-trellis-plus-gaps/implement.md).
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
- Constraints/non-goals: no new product feature, reinitialization/tool upgrade,
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
| 1 | [Trellis Plus remediation](tasks/10-09-trellis-plus-gaps/task.json) | active, checked, uncommitted | Branch chore/trellis-plus-gaps; policy/runtime implemented; final full suite 643 passed; real preview acceptance remains unrun |
| 2 | [Setu archive attachments](tasks/10-09-setu-archive-files/task.json) | in_progress, pending live acceptance | Work commit c3e2f32; automated/byte-transfer evidence below; updated-runtime command/receipts/checkpoints not yet verified; do not activate, deploy or archive as a side effect of remediation |

## Evidence and decisions

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
  regression checks are recorded in [validation](tasks/10-09-trellis-plus-gaps/validation.md);
  independent final gate passed 643 tests (3 existing PTB warnings), shell syntax
  and diff checks. Post-change self-check is 44 PASS / 1 historical GAP /
  7 UNKNOWN / 5 N/A; the 22 prospectively repairable GAPs are addressed.
  Real preview cold-start/image/account/device acceptance is unrun. No work commit/archive exists. Preserve
  the setu task and all prior approvals.
- Next permitted action: finish the explicitly approved work commit, this task's
  archive and bookkeeping; retain all unrun runtime checks as UNKNOWN.
  Actual isolated preview acceptance requires its own authorization.
  Selecting later product work or deploying setu requires its own decision.

## Lifecycle maintenance

Read this record at task start/resume, before commit/archive and next-work
selection. Approved requirement changes update sources/scope/acceptance/work
mapping together. Checks add verified results and remaining limitations; archives
update locations/work and archive commits/remaining scope. Preserve approvals
and source distinctions on rerun; do not create duplicate tasks or work rows.
Use the read-only Pulse and guided/serial/paused boundaries in
[workflow.md](spec/trellis-plus/workflow.md#mainline-continuity).
