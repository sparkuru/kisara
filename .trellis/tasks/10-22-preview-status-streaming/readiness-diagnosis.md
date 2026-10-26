# Reopened command-path diagnosis

The latest user report contains `Recent bounded diagnostics for telegram` and
`kisara`. That exact message is emitted by `preview_diagnostics`, not by the
continuous follower. Therefore this observation reaches the readiness-failure
or interrupted-start cleanup path; it is not evidence of buffering within the
FIFO follower. Application log messages alone do not prove every selected
service passed its actual readiness probe at the command's check time.

## Isolated characterization

Executed `./hako python - < /tmp/kisara-preview-branch-probe.py` against the
existing recording fixture imported from `tests/unit/test_preview_lifecycle.py`.
The probe creates a temporary repository, fake Docker executable and synthetic
Telegram credentials. It performs no live-container/account/API operation.
All three scenarios passed:

| Scenario | Exit | Distinguishing observation |
| --- | --- | --- |
| Bare preview with running, unready Telegram; parent-only INT | 130 | Reaches readiness probe and remains running without any Docker logs call; INT triggers bounded diagnostic output |
| Status of the same running, unready service | 1 | `Service telegram is not ready`, then `Recent bounded diagnostics for telegram`; no `Following` or Docker `--follow`; fixture state unchanged |
| Ready status with finite fake Docker log output | 0 | `System is ready.` and `Following telegram logs`; no bounded-diagnostic marker; fixture state unchanged |

The third scenario is deliberately finite and does not model a live Docker
follow connection. Existing controlled-reader tests cover a persistent stream;
the finite fixture must not be cited as continuous-follow evidence.

`preview_wait` retries startup readiness with a one-second sleep and the existing
`KISARA_PREVIEW_TIMEOUT` deadline (default 90 seconds). `status` returns after its
first failed readiness pass without that retry sleep. Individual probes retain
their existing Docker-exec/inspection timeouts. In the interrupted-start probe,
the deadline was set to 60 seconds and INT was sent only after the first recorded
readiness execution; the observed exit was 130, not a readiness-timeout exit.
`preview_cleanup` prints diagnostics because `preview_started` remains true until
the success path. This explains the abrupt appearance of logs after Ctrl+C.

The wrapper's initial sandboxed run was denied Docker socket access; the narrow
escalated wrapper run succeeded. No automatic approval-review rejection occurred.
No production source or persistent test change was made during characterization.

## Proposed implementation boundary, pending main-session approval

The current project contract explicitly makes unready status finite and leaves
startup logs captured until failure. Continuous logs during startup and unready
status therefore require a stated contract revision, not another sed adjustment.
Do not weaken readiness to achieve an earlier success banner.

The smallest reusable lifetime split is:

1. Extract the existing follower setup into a directly called parent-shell
   helper that creates the same FIFOs and populates `preview_log_pids`.
2. Extract the existing wait loop into a second helper. Never background the
   current whole follower: its PID array would live in a child shell and the
   parent's signal cleanup could not reliably reap its readers.
3. Start readers after collecting verified selected IDs, before startup
   readiness waits. Retain the bounded wait; print the existing success summary
   only after real readiness succeeds, then remain attached to the readers.
4. For status, report current readiness accurately, then follow owned bot logs
   even when currently unready. Missing/foreign IDs retain their existing refusal;
   no partial-group repair or service mutation is introduced.
5. Share nonblocking reader status/error collection with the readiness wait so
   sanitizer/reader failures cannot hide behind a readiness loop or success.
   Require `mkfifo` for startup too. Preserve existing EOF behavior; no automatic
   reconnect/restart is justified by this report.
6. Track successful stream setup so INT/TERM cleanup does not append duplicate
   diagnostics after logs were displayed. Keep genuine startup failure/timeout
   diagnostics (including auxiliaries), 130/143, PID ownership, credential
   filtering and persistent state.

The main session owns the requirement/spec decision and any implementation
authorization. The original locale defect remains valid but does not close the
reopened end-to-end acceptance criteria.

## Read-only runtime observation

The main session inspected only three project container runtime/restart fields
and existing readiness probes. All three (Kisara, Telegram, NapCat) were running,
had restart count0, and passed probes at observation time. A private owner-only
capture of `timeout --foreground --signal=INT --kill-after=5s 12s ./kisara.sh preview status`
returned observer124 after12 seconds and contained `System is ready.`,
`Following onebot logs` and `Following telegram logs`. Only fixed marker/timing
metadata was emitted; the capture was removed. No service or account was changed.
This confirms current ready following but cannot reconstruct the earlier
readiness-failure state. The user's diagnostic marker plus isolated unready
fixtures supplies that missing path evidence.

### Controlled read-only unready-status observation after the correction

A temporary owner-only Docker shim permitted only ps/inspect/info/logs/port,
context inspect and Compose version. It returned1 for exec rather than entering
containers, forcing only this invocation's readiness check to fail. All other
operations were rejected; public status still read the real owned Docker log
streams through the existing command path. The shim/captures were removed.

The same 12-second foreground INT observer returned124 after12 seconds. Fixed
markers showed `not ready`, `Following onebot logs` and `Following telegram logs`;
there was no `System is ready.`, `Recent bounded diagnostics` or stream-failure
marker. Before/after Id, Running, StartedAt and Pid fields were identical for all
three project containers. No service/account operation or live incoming message
was generated. This establishes real-Docker attachment/cancellation for a
controlled failed-probe branch, not actual unhealthy service state or sustained
message-delivery proof. Isolated delayed-line fixtures provide output-timing
coverage separately.

## Bug analysis

1. **Root cause category — coverage gap and implicit assumption:** earlier
   acceptance exercised already-ready services and locale filtering, assuming
   any visible logs came from the follower. Readiness gates select different
   startup/status output paths.
2. **Why the first fix missed:** the QR class was a real independent defect, but
   its passing regression did not reproduce the reported command state. Broad
   test totals were insufficient evidence of the missing unready-state UX.
3. **Prevention:** gate acceptance on delayed output before INT/EOF in ready,
   starting and unready states; distinguish diagnostic and follow markers and
   actual exit codes. This is recorded in the CLI contract and revised plan.
4. **Systematic expansion:** apply this state distinction only to the two
   affected preview entry paths. Application startup info is not a replacement
   for process-bound readiness; keep readiness and log viewing separate.
5. **Knowledge capture:** update existing CLI spec and task artifacts. No new
   runtime framework, generated template tree or unrelated audit is needed.
