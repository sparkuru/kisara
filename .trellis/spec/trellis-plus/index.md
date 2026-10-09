# Trellis Plus Project Policy

- ownership: project-shared
- source: project-authored
- tracking: commit this file and its referenced project-owned detail files
- initialized: 2026-09-26

## Scope and loading

Kisara is a Python bot with OneBot 11, optional Tencent official, and optional
Telegram adapters, each running in a separate process.
There is no application frontend. The external NapCat administration page is
not a Kisara UI surface. UUPM and Playwright are not applicable to this setup.

Read this index and `.trellis/mainline.md` (when present) at task start, after a
substantial interruption, before commit/archive, and when selecting subsequent
work. Before implementation or review, read the applicable details below and
register them explicitly in both task context manifests. Markdown links do not
inject their targets. Native Codex injection and child-side fallback consume
those manifests; neither automatically adds this policy to a newly created task.
The exact manual registration and verification steps are in
[workflow.md](workflow.md#policy-loading). No protected phase hook or managed
AGENTS block is changed. Without a task, read directly and use the read-only
Pulse; policy discovery does not authorize task creation or implementation.

| Document | Read when |
| --- | --- |
| [Architecture and feature contracts](architecture.md) | Changing routing, services, adapters, utilities, or documentation |
| [Configuration and storage](configuration-storage.md) | Changing configuration, HTTP, cache, SQLite, files, or deployment paths |
| [Setu archive storage](setu-storage.md) | Changing archive filenames, collisions, publication, or media naming compatibility |
| [Validation and development](validation.md) | Before development, checking a change, or requesting manual verification |
| [Workflow and delivery](workflow.md) | Delegating, proposing a commit, continuing work, or updating Trellis |
| [Development principles](development-principles.md) | Task start, scope changes, diagnosis, implementation, and final review |

## Rules

1. Preserve protocol-neutral business behavior, explicit feature wiring,
   authorization before side effects, and the documented configuration chain.
2. Use the existing Docker development wrapper `./hako`. If it becomes absent,
   apply `dev-it-in-docker` before toolchain-dependent work; do not introduce a
   competing wrapper or a host toolchain.
3. Use focused automated validation first. Evaluate the concrete remaining
   risk before the submit-ready human review gate and any commit.
4. Attribute each Codex-assisted task once at successful archival, including
   small tasks, through the verified no-auto-commit route in workflow.md. This
   rule adds no trailer to ordinary work or separate journal commits and never
   repairs historical commits automatically.
5. Default mainline continuity to `guided`. Read the normal mainline record and
   preserve its approval/source boundaries; proposed work is not authorization.
6. Write shared policy here. Preserve Trellis-managed runtime/template files
   and existing generated backend/guide indexes. Personal platform settings
   remain local and are never staged by Trellis Plus.

## Evidence and provenance

The project rules consolidate `docs/application-template.md`,
`docs/operations.md`, `docs/legacy-migration.md`, `readme.md`, current source,
`pyproject.toml`, deployment scripts, and the user's supplied orchestration
instructions. The completed [backend guidelines](../backend/index.md) document
directory, SQLite, error, logging, and quality conventions with source examples.
These detail documents supply the shared feature and delivery policies.

`design.md` contains an earlier rollout plan. Its opening correction and
current source supersede the old first-version bans on databases and external
services and the old group-only-mention/command restriction. SQLite, external
commands, and authorized group phrasebook replies already exist. The original
milestones are not new authorization to implement further product work.

Installed Trellis metadata reports version `0.6.17`. The initial Plus setup
found no Trellis notices in the checkout. During the authorized bootstrap
completion, the exact installed distribution license was copied verbatim to
[the scoped license file](../../LICENSE); package metadata and copied-file
provenance are recorded in [THIRD_PARTY.md](../../THIRD_PARTY.md). Existing bot
resource notices remain separate. No application license or unsupported
copyright notice was invented. The [retained-material inventory](../../../third_party/index.md)
links those scoped originals; resource SOURCES.md records the historical blob
used to restore the missing legacy notice, without inferring community rights.

The original Plus setup created only this directory, without task activation
or commits. The user separately authorized completing and committing the
existing `00-bootstrap-guidelines` task, finished on 2026-09-27. Its completion
includes backend guidelines, shared initialization files, provenance, and
normal archive/journal records. No mainline record was created. None of the
Plus paths is an installed template-hash target; no backup recovery was used.
After `trellis update`, re-read this policy and revalidate referenced paths and
task context rather than restoring additions into upstream files.

The 2026-10-09 user-approved audit remediation updates project-owned policy and
preview contracts. Its task ID is `trellis-plus-gaps`; the mainline records its
current or archived location, approved work and pending acceptance separately. The
original initialization narrative above is historical, not current direction.
