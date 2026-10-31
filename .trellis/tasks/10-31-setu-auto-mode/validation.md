# Setu automatic-mode validation

## Delivered behavior

Authorized OneBot private chats can toggle `/setu on` and `/setu off`.
Activation is an isolated `(instance_id, user_id)` set in service memory.
Process restart resets it; reconnect with the same service retains it.
While on, incoming merged forwards use the existing extraction, transactional
batch claim and direct-save path, quoting the source for pending-item start
counts and the final result. Manual normal/direct/confirmation/retry paths
remain authoritative and usable in either mode. No adapter, schema, dependency,
private configuration or media transport changes were made.

## Automated checks

| Check | Actual result |
| --- | --- |
| `./hako python -m pytest tests/unit/test_setu.py tests/integration/test_onebot_protocol.py -q` | 276 passed in 17.26s; run by implementation agent |
| `./kisara.sh test -q` | 1 failed, 1342 passed, 7 skipped, 3 PTB deprecation warnings in 690.25s; preview process-cleanup failure detailed below |
| `./kisara.sh test -q 'tests/unit/test_preview_lifecycle.py::test_status_follows_selected_bot_logs_and_reaps_readers[2-False-onebot-dev-expected1]'` | Isolated retry passed: 1 passed in 4.98s |
| `git diff --check` | Passed after implementation and independent review |
| `python3 .trellis/scripts/task.py validate .trellis/tasks/10-31-setu-auto-mode` | Passed; 11 real entries in each manifest |

The initial sandbox runs could not reach the Docker socket. Both application
test commands used the approved narrow project-wrapper escalation afterward,
without loading private dotenv or operating live bot services. The project has
no configured application lint/type-check command; neither is claimed passed.

## Full-suite exception

The full run failed at `tests/unit/test_preview_lifecycle.py:1284`, in
`test_status_follows_selected_bot_logs_and_reaps_readers[2-False-onebot-dev-expected1]`.
The status process exited with its expected SIGINT result and recorded log
readers were reaped, but the final immediate `/proc` assertion found at least
one snapshotted descendant still present. The exact case passed on an isolated
retry. A timing-sensitive cleanup assertion is plausible, but this run does
not establish its root cause or a permanent preview fix.

`git diff --quiet HEAD -- tests/unit/test_preview_lifecycle.py
deploy/preview-runtime.sh deploy/lifecycle.sh deploy/preview-console.sh
deploy/engines.sh kisara.sh hako` returned 0. Source inspection of the fixture
at line 249 confirms it copies deployment inputs and writes synthetic
`src/example.py`; it does not execute Setu. These files and the remaining
deployment inputs are outside this task's changed paths. No deployment code
or assertion was changed to hide this result. The full suite is **not reported
as wholly passing**; the Setu/protocol gate passed, and the unrelated full-run
failure was not reproduced by the isolated retry.

## Behavioral evidence

- Service tests verify default-off, repeated on/off, two independent incoming
  forwards, source/result quote targets, actual saved bytes and saved-batch
  deduplication. Isolation tests cover separate users and bot instances.
- Restart coverage constructs a new service over retained SQLite/files and
  confirms activation is off while a saved batch and its file inode remain.
  Starting/cancelling the scheduler twice on the same service retains activation.
- Manual normal/direct saves run with automatic mode on and off. Existing
  confirmation behavior remains intact, including confirming a pending batch
  after switching off.
- Denied sender/group/engine and standalone media cases have no new archive
  effects. Empty or unexpandable forwards create neither batches nor false
  saving/completion replies.
- A nested partial-failure case preserves the completed file, rejects the
  informational notice as retry selector, and retries only the unfinished item
  through the actual failure result after switching off. Notice-send failure
  still completes the claimed save.
- A raw OneBot protocol case queues on / forward / forward / off / forward
  events together. It verifies existing conversation ordering, forward lookup,
  exact source-quoted start/results, no manual `get_msg` lookup, two durable
  completed batches and no post-off automatic save. Global-denial protocol
  cases now include both mode commands with and without a quote.

Existing tests continue covering mixed attachment counts, file layouts,
size/source restrictions, export priority, expiry, checkpoint recovery and
other manual workflows through the reused save path.

## Independent review

`trellis-check` found no functional defects. It fixed two older architecture
statements by qualifying the unsolicited-forward prohibition as default-off
behavior and the final-result command-quote rule as manual-save behavior.
No Python source or tests changed during review, so the full-suite source
snapshot remains valid. Main-session diff inspection confirmed these fixes.

Implementation and review agents reported visible native-context truncation
and explicitly restored task artifacts/applicable curated spec contents with
bounded reads of the saved hook output and source documents. Manifest
registration alone is not claimed as proof of complete native injection.

## Human review and delivery boundary

Classification: **human-optional** for the Setu change. Existing
native transport/download behavior is reused; the changed acceptance and
source-quote behavior are exercised with simulated peers and temporary local
media. The full-suite exception is recorded separately above. The agent has not
independently revalidated actual QQ delivery/account behavior. Progress does
not depend on a live-account operation.

An optional authorized private-chat check is: send `/setu on`, two merged
forwards, `/setu off`, then another forward. Expect two source-quoted save
notices/results and no automatic result for the last forward. Existing manual
quoted saving should remain usable. Process-restart resetting is automated
evidence; this task did not restart the live bot to repeat that check.

## Owner acceptance and delivery approval

On 2026-10-31 the user reported “验收通过；可以提交”. This closes the owner's
acceptance decision and authorizes local commit and normal task wrap-up. It is
an owner-reported pass, not a new agent-observed per-case QQ trace. The recorded
full-suite exception remains unchanged; no new application tests were needed
because source and tests have not changed since the verified implementation.

Local delivery uses a work commit, task archive and session-record commit.
No deployment, live-service restart or push is authorized or performed.
