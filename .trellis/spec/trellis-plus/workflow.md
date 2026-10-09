# Workflow, Delivery, and Continuity

- ownership: project-shared
- source: project-authored
- evidence: user-supplied orchestration instructions, installed Trellis phase
  guidance, repository commit history, Trellis Plus enhancement requirements

## Orchestration and context

Explicit user instructions and active developer/profile instructions select
the mode. Never infer capability mode from model names, reasoning effort,
service tier, or configuration filenames. Higher-priority prohibitions on
delegation always apply.

When high-capability/deep/autonomous orchestration is explicitly selected, do
not use bounded `luna`/`sub_agent` workers; independently useful work may use
available built-in `default`, `worker`, or `explorer` agents. In other cases,
use the explicitly selected available bounded worker, default `sub_agent`.
Delegate only explicit, independently verifiable low-risk work in at most
three relevant files or one focused read-only investigation, when coordination
cost is justified. Ambiguous debugging, security-critical reasoning,
destructive operations, broad changes, and architectural decisions remain
outside bounded-worker delegation.

An active Trellis dispatch instruction takes precedence over these defaults.
For active Trellis implement/check work, use the applicable available role and
its context mechanism. The main session owns coordination, clarification, spec
updates, commit decisions, and wrap-up. Every dispatched task begins with the
active task path; prefer native context injection with child-side loading as
fallback. Workers own explicit boundaries, preserve others' edits, and report
files/results/unresolved decisions. Wait for results and verify their evidence.
Without an active task, this spec update remains in the main session.

## Policy loading

At task start/resume, before commit/archive, and before selecting subsequent
work, the main session reads `index.md`, `.trellis/mainline.md` when present,
the task PRD/design/plan and the applicable detail files. `get_context.py --mode
packages` exposes the trellis-plus layer; it does not itself inject all files.
This is a manual repository discovery step. Neither the managed AGENTS block
nor the protected startup hooks automatically register policy in future tasks.

After normal task creation, use its actual path (not a stale session pointer):

```bash
task_dir='.trellis/tasks/<actual-task-directory>'
python3 .trellis/scripts/task.py add-context "$task_dir" implement .trellis/spec/trellis-plus/index.md 'Shared policy'
python3 .trellis/scripts/task.py add-context "$task_dir" check .trellis/spec/trellis-plus/index.md 'Shared policy'
python3 .trellis/scripts/task.py add-context "$task_dir" implement .trellis/spec/trellis-plus/workflow.md 'Loading and delivery'
python3 .trellis/scripts/task.py add-context "$task_dir" check .trellis/spec/trellis-plus/workflow.md 'Loading and delivery'
python3 .trellis/scripts/task.py add-context "$task_dir" implement .trellis/spec/trellis-plus/development-principles.md 'Development contracts'
python3 .trellis/scripts/task.py add-context "$task_dir" check .trellis/spec/trellis-plus/development-principles.md 'Development contracts'
python3 .trellis/scripts/task.py validate "$task_dir"
python3 .trellis/scripts/task.py list-context "$task_dir"
```

Replace the angle-bracket placeholder before execution. Register validation.md
for checking/development, and architecture/configuration-storage/setu-storage
only when their trigger applies, using the same implement/check argument order.
Preserve existing entries; deduplicate by file path. Index links do not inject
their targets. Inspect resulting manifests and file existence/size; then inspect
native SubagentStart resolved input or the child's reported fallback reads.
Do not claim runtime injection from registration alone. No-task discovery reads
files directly, without creating or activating a task solely for policy loading.

Put required shared policy before large research entries. The installed default
limits are 32768 bytes per spec and 131072 total injected bytes. A truncation or
index-only entry is not a full read, even when the hook marker exists: explicitly
read the relevant full repository file before dependent work. Keep the manifest
entry/reference and preserve task research rather than deleting it to hide a
budget warning. Main session verifies the policy and task artifacts are available
in full; unresolved actual injection remains reported as a loading limitation.

## Submit-ready and commit policy

Use the review decision in [validation.md](validation.md) before staging or
commit. Prepare a concrete commit plan according to the installed workflow,
honor existing authorization, and separate recognized task edits from preexisting
or unrecognized changes. This initialization does not authorize a commit.

Use the repository's short English subject style, including `feat(scope):` and
`chore(task): archive <task-id>`. Each Codex-assisted task receives one exact
trailer on its successful archive commit, including small tasks. Ordinary work,
checkpoints and separate journal/mainline commits do not receive task-level
attribution through this rule. Explicit user attribution instructions override
this default. Preserve Git identity and any other valid co-author trailers.

```text
Co-authored-by: OpenAI Codex <codex@openai.com>
```

The installed `task.py archive` auto-commit has a fixed subject and no message
extension, but supports `--no-commit`. Use this verified route after normal
checks/review and existing archive authorization:

1. Read shared policy, task PRD/results/work-commit evidence and Git status.
   Inspect archive state/history first: never blindly rerun an archive retry.
2. Prepare one proportional archive message identifying the task, delivered
   outcome, actual validation/limitations and work commits, then the exact trailer
   above separated by a blank line. No contribution threshold or long body is
   required. Show it and the explicit candidate paths in the normal archive plan.
3. Run `python3 .trellis/scripts/task.py archive <actual-task-dir> --no-commit`.
   Respect its branch validation; do not invent flags or suppress it routinely.
   Confirm successful movement/completed task state and printed archive path.
4. Inspect `git status --short` and `git diff --name-only`. Candidate paths are
   the exact moved source task, exact archive destination, and any identified
   child task.json bookkeeping the archive actually changed. The default helper
   can stage the entire archive subtree; do not use its auto-commit for this rule.
   Exclude other archives, journals, personal files and protected material.
5. With commit authorization, stage explicit reviewed paths only, check staged
   names and `git diff --cached --check`, then commit using a message file in /tmp
   and the same reviewed pathspecs (`git commit -F <message-file> -- <exact-reviewed-paths>`).
   This path-limited commit preserves unrelated pre-staged work. Deletions at the known source are part of
   the inspected path set; never broaden staging to the tasks/archive tree.
6. Inspect `git show --format=full --name-status HEAD`: correct task paths,
   successful archive evidence and exactly one matching trailer. Record archive
   destination/commit in mainline; later mainline or journal commits omit it.

If archive succeeded but its explicit commit failed, resume only that pending
commit after inspecting history/pending paths; do not repeat the move or collect
new unrelated changes. Existing historical archives without attribution are
reported, not amended; no empty attribution-only commit is created. Unrelated
user-only historical tasks do not acquire invented Codex authorship.

If a later installed version loses both message customization and no-auto-commit,
report `archive-attribution-blocked` before archival; do not patch protected
runtime, add global hooks, or silently archive with missing attribution.

`add_session.py` supports `--no-commit`; default journal auto-commit stages the
current developer workspace and resolved current-task records. Inspect its
candidate scope before use or select no-commit and explicitly review paths.
Separate journal commits use the normal subject and no task trailer.

## Mainline continuity

Default to `guided`. `.trellis/mainline.md` summarizes approved/proposed direction
and evidence; normal source PRDs/designs and task records remain authoritative.
Import relevant existing sources without moving or rewriting them: preserve
source path/section, approval/supersession, scope/non-goals, acceptance and open
decisions. Draft-only imports stay proposed/not-yet-approved. With no relevant
source or declared objective, leave a record absent rather than inventing goals.
The older design.md milestones are not bounded serial authorization.

For relevant no-task continuation/status requests or after archive, run a
read-only Project Pulse: read mainline if present, task/archive evidence, git
state, and checks; report objective/completed evidence, blockers/dirty state,
one uniquely ready candidate if supported, and the next permitted action.

- No declared objective: report the missing direction and request the one
  priority decision needed before creating work.
- `guided`: recommend evidence-backed work and wait for the user's selection.
- `paused`: report state only; do not create tasks or implement.
- `serial`: advance only an explicitly authorized, listed, ready child in its
  recorded order; stop for ambiguity, scope change, risk, dirty/unresolved work,
  missing dependencies, or an unapproved decision.

Read mainline and approved task acceptance at start and after interruption.
Map task scope to the approved outcome; resolve actual conflicts rather than
silently changing the objective. On an approved change update sources, scope,
acceptance, affected work and decision together. Task creation/start links the
normal task and readiness/dependencies only within approved work. After checks
record verified results separately from implemented-but-unverified portions.
At archive update task location/work and archive commits/completed scope,
remaining work and next decision. Reapplication preserves approvals and user
edits without duplicate work rows; code drift never weakens acceptance.

Task artifacts, checks, human review, commit decisions, and archive evidence
still apply under serial mode. Parent/child tasks remain the normal work system;
the control record is not a scheduler. Proposed direction grants no task/start
or product-priority authority. Do not treat `completed` as an automatic
continuation hook: archive removes the active task pointer.

## File ownership and update resilience

Shared additions live in `.trellis/spec/trellis-plus/`; task evidence belongs
to normal task directories. Trellis-managed workflow, scripts, agents, config,
ignore file, version/hash metadata, backups, managed AGENTS block and generated
platform files are read-only during Trellis Plus setup. Existing generated spec
indexes remain intact. Local agent settings are not shared policy and must not
be staged; preserve existing ignore behavior.

Before any future staging, inspect status/diff and classify every candidate.
Stage explicit authorized project paths only. Do not use broad/forced staging
to collect personal or protected files. Inspect the staged path list and run
`git diff --check`; for new untracked files, also check their contents directly.
The commit candidates from this setup are precisely:

```text
.trellis/spec/trellis-plus/index.md
.trellis/spec/trellis-plus/architecture.md
.trellis/spec/trellis-plus/configuration-storage.md
.trellis/spec/trellis-plus/validation.md
.trellis/spec/trellis-plus/workflow.md
```

Those candidates and exclusions describe the original Plus-only setup. The
user separately requested completing and committing the existing bootstrap
task, finished on 2026-09-27. That delivery also tracks the reviewed shared
`.gitattributes`, `AGENTS.md`, initialized `.trellis/` framework, completed
backend specs, exact upstream license/provenance, and task/workspace records.
Stage an explicit reviewed file list; local identity/session/runtime state and
personal `.agents/` / `.codex/` files remain excluded. Executable framework
templates remain unchanged. See [index.md](index.md) for notice provenance.

After `trellis update`, validate this directory, runtime command paths, context
manifests, and any approved mainline record. If update state is unclear, inspect
the installed metadata/backups and dry-run update output read-only. Never
restore Plus content to protected upstream paths or add protected files to
update skip lists merely to preserve this policy.
