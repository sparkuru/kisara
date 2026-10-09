# Development Principles

- ownership: project-shared
- source: project-authored
- read when: task start/resume, diagnosis, implementation, scope change, review

## Development default and evidenced exceptions

Kisara is under active development. Change unreleased behavior directly when
there is no compatibility obligation; update callers, configuration and tests
together and remove superseded prototype paths. Do not add legacy aliases,
adapters or migration chains merely because a name once existed.

Real QQ/Telegram accounts, persistent delivery/batch checkpoints, confirmed
setu files and login state already exist. They are not disposable development
data. Existing engine namespace/TOML precedence, explicit-empty permissions and
documented protocol/naming behavior remain actual contracts. Describe any
affected release, external consumer or retention obligation in the task before
changing it; neither the label dev nor one released surface establishes the
status of every other surface.

Keep the project's evidenced network exception: NapCat WebUI defaults loopback
with SSH-tunnel access; OneBot/music remain inside Compose; outbound bots expose
no application HTTP port. Preserve explicit restrictions rather than switching
to LAN publishing automatically. If a task explicitly authorizes LAN access,
document its configured bind/mapping and candidates in the preview profile;
do not change firewall rules or publish another internal service.

For repeated development checks prefer offline console, simulated peers and
separate test fixtures/accounts. Simplify unnecessary dev-only interaction only
through explicit development configuration and the existing auth design. Never
reuse production credentials, commit secrets, weaken production defaults or
bypass the permissions/auth behavior a test is meant to exercise.

## Implementation scope

- Solve the current approved acceptance criteria and evidenced near-term needs.
  Reuse existing services, adapters, models, utilities, configuration and tests;
  modify their real execution paths instead of creating a parallel wrapper.
- Add abstractions, flags, state machines, caches or fallback chains only for
  an actual contract/need. The placeholder domain/shared packages are not a
  reason to introduce a generic architecture.
- Preserve data unless disposability is established and replacement is within
  the user's authorized operation. Rebuilding a genuinely disposable fixture
  never authorizes resetting an unknown database or runtime directory.
- Keep changes limited to the requested outcome. Do not bundle neighboring
  renames/refactors, mass formatting, directory moves, dependency upgrades or
  unrelated fixes. Include another issue only when it blocks/invalidates this
  result or the user requests it; record why in the existing task plan.
- Add a dependency only for a concrete benefit unavailable reasonably through
  existing dependencies, standard facilities or a small local implementation.
- Handle plausible expected failures with explicit status/error/recovery.
  Do not hide a critical missing resource behind a warning, silently fall back
  to old behavior, or return a success-looking default.

## Diagnosis and verification

Before fixing a bug, establish behavior, reproduce when possible, collect root
cause evidence, and locate the real execution path. When reproduction is
unavailable, record that limitation and label hypotheses. Changing code and
tests around a guess is not proof of the original cause. Keep diagnostics in
the task's research/check records, not a second audit system.

Validate agreed user behavior and contracts. Do not weaken assertions, mock
away the behavior under test, hide errors or test only favorable cases to get
green results. Controlled protocol/provider fixtures must state their boundary.
Run the smallest useful existing checks in [validation.md](validation.md), then
the required risk-based broader checks. Build/lint/types, HTTP 200, page loading
or container running each prove only their own scope.

Report exact commands, actual results and implemented-but-unverified portions.
Do not add frameworks, permanent checker scripts, CI gates, extra documents or
repeated reviews without a meaningful requirement. Human feedback is for the
specific residual account/device/private-environment/product risk after runnable
automation; follow the existing submit-ready classification.

## Workspace and documentation

Treat preexisting changes as user-owned. Inspect overlap, preserve intent, and
never revert/reset/clean unknown files or stage unrelated edits. Remove only
known temporary debug code/fixtures/scratch created by this task; retain
intentional tests and evidence. Use /tmp for temporary artifacts and validate
their ownership before cleanup.

README is human-owned presentation: read it for context, but create/edit it only
when explicitly requested. Store agent development policy here, necessary help
in scripts, operational usage in the existing operations document, and required
PRD/design/implementation/evidence in normal Trellis tasks. Do not manufacture
redundant guides, migration notes, TODO documents, comments or audit systems.

Read mainline and task acceptance at start/resume and retain the original scope
throughout execution. Approved requirement changes and verified results update
mainline; implementation drift does not redefine acceptance. Before completion
inspect the diff for unrelated cleanup, speculative compatibility, dependencies,
README expansion, user-work loss and claims unsupported by actual validation.
