# Setu automatic mode execution plan

## Planning gate

- [x] Inspect existing service, adapter entry, persistence and relevant tests.
- [x] Record restart resetting activation to off, explicitly selected by user.
- [x] Converge PRD and prepare design and curated implementation/check context.
- [x] Present final summary and obtain subsequent implementation approval
  (user: “开始”, 2026-10-31).
- [x] Validate manifests, then run `task.py start` for this task only.

## Implementation

- [x] Dispatch `trellis-implement` with the active task path first and explicit
  ownership of the service, Setu unit tests, OneBot protocol tests and the two
  existing operations/application documentation files. The worker is not alone
  in the repository and must preserve unrelated edits. Prefer native context
  injection; require child-side context loading if injection is unavailable.
- [x] Add isolated memory activation and exact on/off command replies inside
  Setu's existing authorization boundary.
- [x] Add incoming merged-forward selection, reusing the existing source-claim
  and direct-save path. Preserve manual matching, notice ordering and retry
  selectors. If common source handling is extracted, keep it local and prove
  manual equivalence with existing regression tests.
- [x] Extend existing behavioral tests for activation/deactivation, two
  successive forwards, user/instance isolation, restart reset, same-service
  reconnect, duplicate suppression, mixed/nested attachments, empty sources,
  denied/group events, notice failure, partial retry and manual compatibility.
- [x] Add simulated OneBot coverage for raw incoming forwards, actual quoted
  start/result payloads, off followed by a later forward, and existing manual
  and export priority. Use isolated temporary media and simulated peers.
- [x] Update the feature's English module documentation and existing usage
  docs with private scope, memory lifetime and unchanged manual flow.

## Validation and review

Run focused checks through the existing Docker wrapper:

```bash
./hako python -m pytest tests/unit/test_setu.py tests/integration/test_onebot_protocol.py -q
```

If the adapter itself changes, also run its unit suite. Because this changes
native message acceptance, follow focused verification with the full suite:

```bash
./kisara.sh test -q
git diff --check
python3 .trellis/scripts/task.py validate .trellis/tasks/10-31-setu-auto-mode
```

- [x] Dispatch `trellis-check` for independent PRD/design/spec compliance and
  behavioral review; require explicit context loading evidence and check
  results. Do not claim configured lint/type gates absent from this project.
- [x] Fix actual findings and rerun affected checks proportionally. Independent
  review required documentation fixes only. The unrelated preview cleanup
  assertion from the full run passed in isolation; retain both results in
  validation evidence rather than widening scope or claiming a wholly green run.
- [x] Main session updates `.trellis/spec/trellis-plus/architecture.md` and
  `setu-storage.md` to distinguish default/manual behavior from opt-in mode.
- [x] Record exact checks and limits in task validation evidence. Classify any
  human review need based on remaining QQ account risk; do not perform live
  service operations to manufacture evidence.

## Delivery boundary and rollback

Inspect the final diff for unchanged batch schema, file paths, stored media,
permissions and unrelated work. Restart reset must be tested against the same
temporary state directory without erasing stored batches. No database migration
or private configuration mutation is expected. A necessary adapter refactor or
new persistent state is a scope deviation requiring investigation before work.

Task creation does not authorize deployment, commit, archive or push. Prepare
the completed reviewable change and report results; follow later user authority
and normal delivery policy for those actions.

The user's 2026-10-31 “验收通过；可以提交” accepts the result and authorizes
the local work commit, normal archive and session record. No live operation or
push is included. Preserve the full-run exception and successful isolated retry
as recorded evidence rather than rerunning unchanged application code.
