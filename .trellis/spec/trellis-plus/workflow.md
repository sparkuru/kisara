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

For future task context, register this index and the relevant detail files in
both implement/check manifests using the installed `task.py` context commands.
Do not rely on an index link alone to inject every detail document.

## Submit-ready and commit policy

Use the review decision in [validation.md](validation.md) before staging or
commit. Prepare a concrete commit plan according to the installed workflow,
honor existing authorization, and separate recognized task edits from preexisting
or unrecognized changes. This initialization does not authorize a commit.

Recent commit history uses short English subjects, sometimes `feat(scope):`,
without an established Codex attribution trailer. Classify each work commit:

| Attribution | When | Commit content |
| --- | --- | --- |
| `yes` | Significant feature work, non-obvious design/debugging, cross-layer work, substantial validation, or explicit user request | Dense completion body plus the trailer below |
| `no` | Trivial/mechanical/config follow-ups, user-only changes, archive/journal bookkeeping, or manually committed work | Normal project-style message, no automatic trailer |
| `ask` | A genuinely ambiguous established project attribution convention near the threshold | Resolve that specific ambiguity |

For `yes`, explain the original request/problem, key rationale, resulting
behavior, preserved constraints, executed checks, unavailable checks, and any
material follow-up. Preview the body and trailer in the commit plan. Use:

```text
Co-authored-by: OpenAI Codex <codex@openai.com>
```

Do not use the user's identity for AI attribution or attach it merely because
Codex touched a file. Preserve a future explicit project trailer convention.

## Mainline continuity

Default to `guided`; this setup declares no new product initiative and creates
no `.trellis/mainline.md`. The older `design.md` milestone list is reference
material, not bounded serial authorization.

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

Task artifacts, checks, human review, commit decisions, and archive evidence
still apply under serial mode. Parent/child tasks remain the normal work system;
the control record is not a scheduler. Only create `.trellis/mainline.md` after
an initiative is approved. Do not treat `completed` as an automatic continuation
hook: archive removes the active task pointer.

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
