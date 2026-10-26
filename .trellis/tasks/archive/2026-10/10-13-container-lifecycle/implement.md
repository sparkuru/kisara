# Implementation plan

## Planning gate

Task creation/fix request and down-only decision are recorded. PRD, design,
research and curated manifests are complete. The final summary was explicitly
approved with “开始”; the task is active for implementation and offline checks.
Existing telegram-tguid work 7da12cd and records 8feaa57 remain unchanged.

## Ordered work

1. Implement the shared exact repository ownership/preflight and scoped down
   helper in the existing deploy layer. Keep source-only helpers side-effect-free.
2. Route ordinary and preview lifecycle through it; replace onebot.sh's duplicate
   lifecycle with scoped forwarding. Retain foreground/detached semantics and
   narrow verified old Official cleanup. Whole-project down-all preflights all.
3. Remove public stop aliases/help/tests; down stops and removes selected objects
   with storage intact. QQ down covers shared modes; startup verifies/removes the
   opposing mode, build/status never switch it.
4. Remove preview fingerprints/config/partial/reuse/build-live refusal and
   bespoke ownership/config/attempt label generation. Preserve recognition of
   existing labels; new Compose objects use standard source identity. Build
   rebuilds app images without lifecycle effects.
5. Stage auxiliary services normally; preserve local API-before-Telegram health.
   Explicit startup recreates selected applications with no-deps for TOML/env
   freshness. Never force-recreate gateway/API/music merely for app startup.
6. Remove attempt-based container rollback: failures leave objects for diagnosis
   and direct retry, return failure without ready; temp logs/readers still clean
   up. Status explicitly handles missing/stopped/uninstrumented selected objects.
7. Improve the existing stateful fixture with real identity and ID/image/config
   reconciliation. Add roundtrip/isolation/data/mode/failure tests; retain prior
   streaming, native/public, local API, offline and canonical CLI regressions.
8. Update operations and runtime help around the simplified commands. Main syncs
   executable code specs, obsolete fingerprint claims and new failure behavior.

## Ownership and scope

Trellis implement owns lifecycle source/affected tests/operations. Main owns
task artifacts, specs, mainline, journal and commit decisions. Workers are not
alone; preserve all other edits. No private dotenv, live containers/accounts,
dependencies, business/auth cleanup, commit/archive or push in implementation.

## Validation

Load shell/Python skills and relevant manifest specs fully; reread in chunks if
native context injection truncates. Approved design supersedes older specs'
preview-exclusive ownership, stop aliases, refusal/rollback behavior.
After spec synchronization, manifests contain about 124000 bytes plus over 17000 bytes
of task artifacts, exceeding the default 131072 total injection limit. Child-side complete bounded
reads are required; preserve all applicable entries and research.

Run bash -n changed shell files and available ShellCheck/shfmt without adding a
toolchain. Existing application lint/type-check is unconfigured.

```bash
./hako python -m pytest tests/unit/test_preview_lifecycle.py tests/unit/test_kisara_cli.py tests/unit/test_engine_deployment.py tests/unit/test_hako_deployment.py tests/unit/test_preview_readiness.py tests/unit/test_telegram_bot_api_deployment.py -q
```

Dispatch independent Trellis check for the complete task boundary, shared
preflight before effects, legacy/foreign exact identity, ordinary roundtrip,
auxiliary preservation and failed-start direct retry. Mechanical scoped fixes
can be made in place; design changes return to main before rewriting.

Then main runs ./kisara.sh test -q and git diff --check, recording exact checks
and human-review classification. Prior 1024-pass result is historical baseline,
not proof of this new task. No live readiness or actual image result is invented.

## Risks and recovery

Exact origin guards can reject an unknown/moved checkout; do not weaken them to
pass a fixture. Startup interrupts selected applications to reload TOML, while
auxiliary state is retained. Failure retains objects; retry reconciles them or
down removes them. Persistent storage is never reset or volume-deleted.

## Delivery evidence

Ordered implementation and spec synchronization are complete. Independent
review corrected preview switch output capture, preserved both QQ-mode
diagnostic queries and fixed one test's argv slicing without relaxing lifecycle
assertions. Independent gate: 70 passed, 163 deselected in 237.94s. Final full
gate: ./kisara.sh test -q, 1067 passed, 1 existing missing-Git skip, 3 existing
PTB warnings in 500.97s. Bash and whitespace checks passed; ShellCheck/shfmt
unavailable and application lint/type-check unconfigured. See validation.md
for the intermediate failed gate, exact review command and evidence limits.

Human-optional for separately authorized real deployment/account checks; code
delivery does not depend on a reply. The user's 2026-10-14 “提交” instruction
authorized local delivery. Work is committed as 6af84c6 on feat/container-lifecycle;
the task remains in_progress without archive. No live operation or push occurred.
