# Trellis Plus audit-gap remediation

## Goal and approval

Repair all applicable GAPs from the full 01-33 audit against the 2026-10-08
baseline. The user approved the concrete audit plan and then explicitly approved
creating this task and proceeding with planning/implementation on 2026-10-09.
Keep future agents independent of the author's skill installation.

After reviewing the completed implementation and the 643-test result, the user
said "可以归档" on 2026-10-09. This authorizes the normal work commit,
single-task archive and session/mainline bookkeeping. It supersedes the initial
no-staging/commit/archive restriction below only for this completed task.
Unrun preview/account/device checks remain reported limitations; no deployment,
push, other-task archive or live-service operation is authorized.

## Requirements

- R1: Complete loading (05), development/scope/diagnosis/document rules
  (09, 10.2, 11.1, 12) and incremental environment policy (21.1). Register
  shared index/workflow/details in both manifests, including the existing setu
  task without changing its state.
- R2: Correct prospective Codex attribution (28.1, 29.2): exactly once at
  successful task archival, with the supported --no-commit route; no contribution
  threshold or automatic work/journal trailer. Historical 28.2 stays reported.
- R3: Repair CLI/lifecycle/preparation/output/diagnostics/endpoint/readiness
  (16, 18, 19). Start returns after bounded readiness; reuse healthy matching
  instances; reject changed/unhealthy ones without automatic replacement.
  Help/status/stop/down never prepare/start; stop/down preserve persistent data.
- R4: Repair dotenv precedence and first-use documentation (20.2/20.3), including
  NAPCAT_UID/GID. Parse data, never source dotenv; preserve all local values.
- R5: Import source/approval boundaries and lifecycle (30.1, 31.1) to normal
  mainline data. Current task requirements retain recorded approvals; old
  milestones remain proposed/superseded where authority is unknown.
- R6: Restore missing retained-data notice (08.2) exactly from verified repository
  history, recording revision/blob. Do not invent upstream provenance or rights.

## Acceptance criteria

- AC1 (R1/R2/R5): Repo-only agents find triggers/actions/commands/exceptions and
  verification; manifests explicitly reference shared details; mainline separates
  verified implementation from pending live acceptance and unapproved direction.
- AC2 (R3): Behavior fixtures cover missing/prepared resources, healthy reuse,
  changed/unhealthy/incomplete instances and failed build/install/rechecks. Prepare
  only missing resources, with pinned Python 3.12 constraints; no automatic tests,
  runtime secret injection or port publishing during preparation.
- AC3 (R3): Summary uses actual readiness/listeners/mappings, full service-grouped
  URLs and local/internal scopes; wildcard discovery covers every eligible host
  address; context beats host; old CLI and remote failures are explicit. Outbound
  bots must not acquire an invented HTTP endpoint/listener.
- AC4 (R3): Failures retain original status, show bounded redacted diagnostics
  before cleanup, never fall back to raw logs, remove only newly created owned
  resources, preserve persistent data and leave no success-looking summary.
- AC5 (R4): Fixtures verify dotenv quoting/presence/empty values/environment
  overrides/UID-GID defaults. Existing .env bytes remain unchanged; safe new
  example keys update actual consumers and local keys are appended only if absent.
- AC6 (R6): Notice bytes match their historical blob; provenance and packaging
  references resolve. Final reporting covers all current checklist IDs and
  accurately retains historical GAP and unrun UNKNOWN results.

## Constraints and exclusions

No staging, commit, archive, push, deployment or existing online-service
operations. Existing dotenv assignments/format remain intact; only missing new
safe preview keys may be appended under the approved incremental policy, after
temporary-fixture verification. Do not modify protected Trellis/platform files, README, network/auth
defaults, user data or unrelated bot behavior. No UUPM/Playwright initialization.
Keep loopback/SSH-tunnel/internal-only constraints and existing Docker wrapper.
Temporary recording/stub fixtures and focused regression checks are approved
implementation validation. Actual Docker preview cold-start/lifecycle, real
accounts and network checks remain separately authorized UNKNOWN work.

## Sources

The prior full audit/approval; current CHACKLIST.md/source procedures;
.trellis/spec/trellis-plus and backend quality; existing scripts/Compose/tests;
design.md and task approval/validation records. External skill paths are source
material for this inspection, never installed project runtime dependencies.
