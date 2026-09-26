# Trellis Plus Project Policy

- ownership: project-shared
- source: project-authored
- tracking: commit this file and its referenced project-owned detail files
- initialized: 2026-09-26

## Scope and loading

Kisara is a Python QQ bot with OneBot 11 and optional Tencent official adapters.
There is no application frontend. The external NapCat administration page is
not a Kisara UI surface. UUPM and Playwright are not applicable to this setup.

Read this index at the start of each Trellis Plus run. Before implementation or
review, load the relevant documents below and register their repository paths
in the active task's `implement.jsonl` and `check.jsonl` through Trellis's
existing context commands. This spec does not install automatic phase hooks.
Without an active task, read the specs directly; do not create or activate a
task merely to install this policy.

| Document | Read when |
| --- | --- |
| [Architecture and feature contracts](architecture.md) | Changing routing, services, adapters, utilities, or documentation |
| [Configuration and storage](configuration-storage.md) | Changing configuration, HTTP, cache, SQLite, files, or deployment paths |
| [Validation and development](validation.md) | Before development, checking a change, or requesting manual verification |
| [Workflow and delivery](workflow.md) | Delegating, proposing a commit, continuing work, or updating Trellis |

## Rules

1. Preserve protocol-neutral business behavior, explicit feature wiring,
   authorization before side effects, and the documented configuration chain.
2. Use the existing Docker development wrapper `./hako`. If it becomes absent,
   apply `dev-it-in-docker` before toolchain-dependent work; do not introduce a
   competing wrapper or a host toolchain.
3. Use focused automated validation first. Evaluate the concrete remaining
   risk before the submit-ready human review gate and any commit.
4. Keep significant Codex authorship visible through a completion body and
   selective co-author trailer; trivial edits and bookkeeping do not qualify.
5. Default mainline continuity to `guided`. No approved ongoing initiative or
   serial authorization was supplied by this initialization request.
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
copyright notice was invented.

The original Plus setup created only this directory, without task activation
or commits. The user separately authorized completing and committing the
existing `00-bootstrap-guidelines` task, finished on 2026-09-27. Its completion
includes backend guidelines, shared initialization files, provenance, and
normal archive/journal records. No mainline record was created. None of the
Plus paths is an installed template-hash target; no backup recovery was used.
After `trellis update`, re-read this policy and revalidate referenced paths and
task context rather than restoring additions into upstream files.
