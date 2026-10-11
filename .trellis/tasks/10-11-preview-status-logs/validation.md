# Preview status continuous log validation

## Delivered behavior

Ready `./kisara.sh preview status` prints the existing readiness summary, then
follows the selected owned application bots with `--tail 80 --follow`. Each
emitted line is sanitized and labeled by service. Concurrent selected bots have
independent FIFO stages; auxiliary-only status remains finite. Existing bounded
failure diagnostics, ownership labels and other lifecycle actions are preserved.
INT/TERM terminates and reaps this invocation's log readers/helpers only.

Implementation changes are confined to `deploy/preview-runtime.sh`,
`deploy/preview-console.sh` and `tests/unit/test_preview_lifecycle.py`.
Operations documentation, shared CLI/validation policy, mainline and this task's
artifacts record the approved contract. All overlapping preexisting changes
remain; the initial source diff is captured under /tmp for review.

## Automated checks

- `bash -n kisara.sh deploy/engines.sh deploy/preview-runtime.sh deploy/preview-console.sh`:
  passed.
- `git diff --check`: passed.
- Final new-behavior gate:
  `./kisara.sh test tests/unit/test_preview_lifecycle.py -q -k 'follows_selected_bot_logs or ready_auxiliary_status or status_rechecks_ownership or status_stream_failure'`:
  20 passed, 89 deselected in 81.90 seconds.
- `./kisara.sh test tests/unit/test_kisara_cli.py tests/unit/test_engine_deployment.py tests/unit/test_preview_readiness.py -q`:
  87 passed, 1 skipped in 10.51 seconds.
- `./kisara.sh test -q`: 913 passed, 1 skipped, 3 existing Telegram
  `PTBDeprecationWarning` warnings in 258.94 seconds.

Streaming cases cover delayed safe output before EOF, default and explicit bot
selection, mixed streams, ownership recheck, parent-only INT/TERM and process-group
INT, disappearance of all captured invocation descendants, FIFO size0 rather
than growing raw/safe files, reader failure with another bot attached, actual
sanitizer failure after a successful preflight, and sanitizer preflight failure.
Tests assert unchanged fake container/data state and no lifecycle mutations.

No configured Python linter/type checker exists. Host ShellCheck and shfmt are
unavailable; no tool installation or configuration change was made. Initial
sandboxed Docker commands were denied socket access; narrow wrapper/read-only
escalations succeeded, with no approval-review rejection.

## Independent review

The Trellis check agent loaded the full task/policy context, inspected source,
tests, help and documentation, and found no contract discrepancy. An isolated
/tmp mutation removes the status follow call; the sustained-output test fails
as expected. Repository source remained unchanged by that experiment.
Independent streaming gate:
`./kisara.sh test tests/unit/test_preview_lifecycle.py -q -k 'status_follows or status_stream or status_rechecks or ready_auxiliary'`:
20 passed, 89 deselected in 82.34 seconds. No source fixes were needed.

## Real current-preview smoke

Observed the authorized current status with
`timeout --foreground --signal=INT --kill-after=5s 12s ./kisara.sh preview status`.
Captured output was stored in an owner-only temporary file and removed after
checking markers, without printing private logs into task evidence.

- Ready summary, `[kisara]` log lines and continuous-follow message were present.
- The observer returned124 after12 seconds, proving the command remained attached
  until the scheduled parent-only interrupt. Synthetic tests separately verify
  the command itself returns130 for INT and143 for TERM.
- Before/after Docker Id, Running, StartedAt and Pid were byte-identical for
  current Kisara and NapCat preview containers; both remained running.
- No recreation, account message, deployment, commit or archive was performed.

## Delivery state

Human review classification: `human-not-needed` for this changed command
behavior, supported by controlled streaming/signal/privacy cases, real
read-only observation and successful final full regression.
The user separately authorized the reviewed combined 105-path work commit,
including implemented Telegram/configuration/canonical-command prerequisites.
Workspace journals, push and archive remain excluded. Preserve both tasks'
in-progress state and the separate pending Telegram live acceptance.
