# Container lifecycle validation

## Scope and acceptance

The user requested a new fix task after preview refused a stopped ordinary
Telegram container. They chose down only, merging stop/down into stop-and-remove
with persistent storage retained, and approved the final summary with “开始”.
Implementation and offline checks were authorized by the planning approval.
The user's 2026-10-14 “提交” instruction subsequently authorized local delivery
commits. Live bot/account operations, private dotenv changes, archival and push
remain outside scope.

## Root cause and prevention

Ordinary deployment and preview independently controlled the same Compose
services. Preview-exclusive ownership, configuration fingerprints, reuse and
partial-group refusal gates combined with a third OneBot lifecycle and automatic
rollback to obstruct otherwise valid repository-owned transitions.

Use the single sourced deploy/lifecycle.sh for exact source identity, all-target
preflight, opposing-mode cleanup and scoped ID removal. Existing preview labels
remain recognizable; contradictory/foreign source metadata fails before effects.
Build prepares images without runtime mutation. Explicit startup refreshes only
selected application bots; auxiliaries use ordinary reconciliation. Failed
preview startup retains objects and bounded redacted diagnostics for direct retry.
Ordinary foreground Compose output keeps its existing semantics. Stateful
fixtures cover observable IDs/configuration/data rather than encoding obsolete
refusal gates. Executable contracts are captured in the existing CLI/validation
specs and engine/storage guidance.

## Evidence

- Both context manifests validate with ten registered entries. Their combined
  specs/research plus task artifacts exceed the native 131072-byte injection
  limit; complete bounded child-side reads are required. No applicable entry was
  dropped to conceal truncation.
- Implementation-stage focused six-suite command from implement.md:
  276 passed, 1 skipped, 1 failed in 435.88s. The new auxiliary-separation
  assertion searched all argv and mistook `--profile music` for an up service;
  the checker owns correcting the assertion to examine operation targets.
  This intermediate result is not a passing final gate.
- Independent review fixed preview switch output capture and retained the old
  OneBot diagnostic scope for both QQ modes. The inaccurate auxiliary assertion
  now examines the service targets after up. No remaining blocker was found.
- Independent core/log regression: 70 passed, 163 deselected in 237.94s. It
  covers ordinary/preview transitions, exact identity, QQ switching, whole-project
  preflight, legacy Official removal, build/runtime separation, failure retention
  and retry, down-only and teardown input independence. New switch-output cases
  cover preview success/failure redaction and unchanged ordinary raw output;
  read-only forwarding cases cover active dev logs/ps/status and foreign rejection.
  Existing status signal/redaction and stream failure cases remain included.

  ```bash
  ./hako python -m pytest tests/unit/test_preview_lifecycle.py tests/unit/test_engine_deployment.py -q -k 'captures_switch_output or diagnostics_cover_dev or ordinary_preview_roundtrip or foreign_collision or existing_preview_labels or qq_switch or build_failure_keeps or down_all_preflights or failed_app_start or down_ignores_unrelated or stop_removed or down_removes_exited or status_follows_selected or status_stream_failure or selected_engines_start_only_targets or selected_official_manages_verified_legacy'
  ```

- Final full regression: `./kisara.sh test -q`, 1067 passed, 1 skipped,
  3 warnings in 500.97s. The skip is the existing missing-Git check in the
  Docker test image; the three PTB retry_after timedelta warnings predate this
  change. This gate covers the final reviewer fixes and last-added teardown case.
  Prior task's 1024-pass result is historical only.
- Main Bash syntax check passed for kisara.sh, lifecycle.sh, engines.sh,
  onebot.sh, preview-console.sh and preview-runtime.sh; diff whitespace checks
  passed, and were reconfirmed after final code edits. Independent whitespace
  checking also covered the newly added lifecycle helper.
- ShellCheck/shfmt are unavailable; no toolchain was installed. Application
  lint/type-check commands are unconfigured. Both context manifests passed
  validation again after specification synchronization.

## Practical limits

Offline fake-Docker checks exercise real shell entrypoints with synthetic
containers, repository/source labels, image/config snapshots and stable IDs.
They do not establish live Telegram login/readiness, actual application image
builds, network reachability or deployed command acceptance. No live container
was switched or removed for this task. Selected applications are intentionally
recreated on startup; failed startup may leave them unavailable until retry.
Persistent data and verified external containers remain outside removal scope.

## Delivery state

Local branch feat/container-lifecycle; work committed as
6af84c646c07c069d8f35f77308e509b401b29ee after the user's “提交” instruction.
Task remains in_progress without archival. Code-review
classification: human-optional for separately authorized real Docker/image/account
verification; offline code delivery does not depend on a reply. No automatic live
acceptance or deployed readiness is inferred from these fixtures.

Commit-time Bash syntax and staged whitespace checks passed. No code changed
after the final full gate, so the full suite was not repeated for bookkeeping.
Git identity was preserved; no amend, push, merge or live operation occurred.
