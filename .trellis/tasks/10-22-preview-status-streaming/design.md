# Readiness-independent preview log viewing

## Evidence and change boundary

The user's Recent bounded diagnostics marker identifies failure/interruption
diagnostics. Isolated actual-CLI fixtures reproduce bare-start silence before
INT130 and unready-status snapshot/exit1. Current ready live status stayed
attached for a privately captured 12-second read-only observation. There is no
evidence that buffering in the ready follower caused these reported paths.
See readiness-diagnosis.md for exact reproduction.

The proposed behavior changes both entry paths to use live sanitized bot logs
independently of readiness. Readiness checks and truthful summaries remain;
readiness is not relaxed to make viewing work. An application INFO message such
as polling ready is weaker than successful-poll/process-bound preview evidence.

## Parent-owned readers and readiness

Split follower setup/waiting into helpers, e.g. preview_start_log_readers and
preview_wait_log_readers. Call setup directly in the parent so preview_log_pids
and existing EXIT/INT/TERM cleanup own every Docker reader, replacement stage,
sanitizer and display process. Do not background the entire follower in a
subshell that hides owned PIDs.

Start: after existing preparation/start/collection and ownership verification,
start readers immediately; run the existing bounded readiness wait with a
nonblocking reader-failure check between probe passes and before ready output.
On readiness success, print the existing summary and wait on the readers.
Do not restart containers/readers or weaken the deadline/health contract.

Status: collect/verify the existing selected group, inspect current readiness,
print a truthful warning when unready, and start/wait on owned bot readers
instead of returning a diagnostic snapshot solely because of readiness.
Missing/foreign groups retain explicit failure. Auxiliary-only selection stays
finite; actual reader EOF/failure retains stream termination behavior.

## Output and cleanup

Reuse existing FIFO pipeline, last80 lines, per-service ownership/readers,
platform labels and credential replacement before display. Start now requires
mkfifo as well as status. No app logging opt-in is changed.

Track whether live readers have started. During INT/TERM viewing, cleanup stops
only this invocation's readers, returns130/143 and skips the redundant bounded
diagnostic dump. Genuine startup failure/timeout can still use existing bounded
diagnostics, including auxiliary failures; do not suppress all failure
diagnostics merely because one bot reader started. Reader/sanitizer failures
must surface while readiness is pending, with nonzero status and cleanup rather
than a delayed/misleading ready result.

## Compatibility and rollback

CLI spelling/targets stay unchanged. Bare/start preview now remains attached
after its summary; unready status now warns and views logs. These intentional
behavior changes require approval. No automatic log-reader reconnection or
service repair is introduced. Roll back only these scoped helper/call-path/test
changes to restore prior semantics, preserving locale and Telegram work.
