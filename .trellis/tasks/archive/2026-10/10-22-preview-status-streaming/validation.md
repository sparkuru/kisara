# Preview status streaming diagnosis and validation

## Current readiness-path correction

The user's `Recent bounded diagnostics` output identified the readiness-gated
diagnostic path, rather than the continuous follower. Bare preview silence
before INT130 and unready status's diagnostic/exit1 path were reproduced before
the correction. The user approved the revised PRD/design/execution plan with
“确认”; the revised implementation, focused checks and independent full
regression are complete. All revised acceptance criteria are met; changes remain
uncommitted.

Startup now opens sanitized bot readers before bounded readiness checks, prints
the summary only after genuine readiness, and keeps following. Unready status
warns and follows existing owned selected bots without service mutation. Viewing
INT/TERM reaps owned readers without another bulk diagnostic dump. Real startup
failure/timeouts retain bounded diagnostics, including auxiliary information;
reader/sanitizer failures surface during readiness. Real EOF remains finite.

Evidence:

- [Readiness diagnosis](readiness-diagnosis.md): original actual-CLI branch
  reproduction, cause of the earlier incomplete fix, and controlled read-only
  real-Docker unready-status observation. Status stayed attached for 12 seconds,
  warned/followed and emitted no ready or diagnostic banner. All three observed
  container IDs, running states, start times and PIDs remained unchanged.
- [Implementation](streaming-implementation.md): new regressions **8 failed
  before / 8 passed after**; CLI/deployment/preview/readiness gate **289 passed,
  1 existing skip in 547.54s**. Coverage includes delayed output while unready,
  readiness transition, parent-only INT/TERM, stream failure during readiness,
  redaction, retained data and genuine timeout auxiliary diagnostics.
- [Independent review](streaming-review.md): no actionable production defect;
  strengthened delayed UTF-8 output after the ready summary, **4 passed
  in 13.55s**. Full `./kisara.sh test -q`: **1115 passed, 1 skipped, 3 warnings
  in 573.65s**, exit 0. The skip is the existing unavailable-Git image case;
  warnings are existing PTB deprecation notices. The full gate collected before
  the test-only assertion extension; production was unchanged and the
  supplemental four cases passed with the final assertions.
  Bash syntax, help and diff checks passed. Both eight-entry task manifests
  validated. ShellCheck/shfmt are
  unavailable; application lint/type checks are not configured.

The real-Docker observation forces only this invocation's probes to fail; it
does not establish actual service illness or fresh-message delivery. Delayed
output timing is verified by controlled fixtures. No live startup/rebuild,
restart or account message was performed. Commit/archive remain unauthorized.
Human review is **human-optional**; user-side observation can confirm the actual
terminal experience but is not a missing automated acceptance gate.

## Historical locale-only evidence

Everything below records the earlier filter correction and its review. Its
scope, file counts, then-current planning state and test totals are historical;
they do not close the startup/unready-state acceptance criteria above.

## Change boundary

The evidenced gap is loss of ordinary UTF-8 log lines in a byte-oriented host
locale. The existing Docker follow/FIFO pipeline remains attached and delivers
ASCII promptly. The behavior lives in the shared sed QR filter in
`deploy/preview-runtime.sh`; change only that filter and its regression coverage
in `tests/unit/test_preview_lifecycle.py`. Keep follow flags, FIFO ownership,
credential replacement, labels and signal cleanup unchanged. No application
logging, new flags, lifecycle refactor, live credentials or service operation.

## Root cause and reproduction

The former `/[▀▄█]/d` expression is a character class in UTF-8 locales but a set
of individual bytes under `LC_ALL=C` or `LC_ALL=POSIX`. UTF-8 bytes in ordinary
Chinese text overlap that set, so complete lines are silently deleted before
the display stage. For example, escaped test inputs `\u6536\u5230\u6d88\u606f`
and `\u53d1\u9001\u6d88\u606f` both disappear in a direct C-locale sed probe;
the same inputs remain visible under C.utf8. ASCII remains visible in both.

Before the fix, the new canonical CLI regression ran with fake Docker producing
three independent selected streams (NapCat, Kisara, Telegram), delayed Unicode
and ASCII sentinels. It failed in C and POSIX after the ASCII history/fresh
sentinels arrived while status stayed attached, and passed in C.UTF-8. This
isolates suppression in the filter rather than blocked reads or missing follow
mode. Existing fixtures emitted ASCII and inherited UTF-8, leaving this gap.

The correction uses `/▀|▄|█/d` with existing extended sed syntax, matching each
whole UTF-8 QR symbol even in a byte-oriented locale. No forced host locale or
new dependency is needed. Regression covers recent Unicode plus two separately
released fresh Unicode phases before EOF, mixed platform labels, credential
redaction, all three QR symbols, TERM cleanup, and unchanged fake service state.
Existing tests cover INT, FIFO bounds, ownership and failure cleanup.

The reproduction establishes a real locale-dependent defect; the user's private
runtime/locale was not inspected, so it does not establish that their exact
environment used C/POSIX. No live-account smoke or private dotenv read occurred.

## Implementer checks

- Baseline original stream/failure tests:
  `./kisara.sh test tests/unit/test_preview_lifecycle.py -k 'status_follows or status_stream_failure' -q`
  — **18 passed, 161 deselected** in 82.56s.
- New regression against original runtime:
  `./kisara.sh test tests/unit/test_preview_lifecycle.py -k status_keeps_delayed_unicode -q`
  — **2 failed, 1 passed, 179 deselected** in 38.71s; C/POSIX timed out waiting
  for the Unicode line after delivering its ASCII sentinel, UTF-8 passed.
- Same new regression after the filter correction:
  **3 passed, 179 deselected** in 18.83s.
- `bash -n kisara.sh deploy/engines.sh deploy/preview-runtime.sh deploy/preview-console.sh`
  — passed.
- `git diff --check` — passed.
- ShellCheck and shfmt are unavailable on the host; no installation attempted.
- Required combined regression:
  `./kisara.sh test tests/unit/test_kisara_cli.py tests/unit/test_engine_deployment.py tests/unit/test_preview_lifecycle.py -q`
  — **269 passed, 1 skipped** in 560.53s. The existing skip is the image's
  unavailable Git executable; no new skip or warning was introduced.

Initial sandboxed wrapper execution could not connect to the Docker socket;
the narrow authorized `./kisara.sh test` escalation succeeded. Tests execute
inside the existing Python 3.12 wrapper against isolated fake Docker state;
they do not use the daemon for any application lifecycle operation. No approval
review rejection, live service change, commit or archive occurred.

## Independent Trellis review

Context loading: the native check hook supplied a truncated view and a saved
full-output path. The reviewer read that artifact and explicitly loaded the
PRD, both six-entry manifests and every check manifest document from the
repository; no design/implementation-plan files exist for this approved
PRD-only task. Both manifests pass `task.py validate`. The applicable
`common`, `code-shellscript`, `code-python` and `trellis-check` skills were read.

The reviewer inspected the complete changed diff, including mainline and the
CLI contract, plus canonical dispatch, status attachment, sanitizer, FIFO and
cleanup code. No mechanical or design issue was found; no source/test fix was
needed. `kisara.sh` uses `exec`, status invokes the follower directly after its
summary, and the follower has no total runtime timeout. The change preserves
credential replacement before emission, platform labels, reader identity,
bounded FIFOs and signal cleanup. The new regression releases two separate
Unicode phases for all three selected readers before EOF and checks redaction,
QR suppression, termination and unchanged fixture service state. Existing
coverage verifies parent-only INT, stream/sanitizer failures and FIFO bounds.

Independent direct sed probing in C, POSIX and C.UTF-8 reproduced the former
filter's suppression of receive/send Chinese lines only in the first two
locales; the replacement retained those lines in all three locales and still
suppressed each of the three QR symbols. This corroborates the filter boundary
without using private inputs.

Independent checks:

- `bash -n kisara.sh deploy/engines.sh deploy/preview-runtime.sh deploy/preview-console.sh`
  — passed.
- `git diff --check` — passed.
- `python3 .trellis/scripts/task.py validate .trellis/tasks/10-22-preview-status-streaming`
  — both manifests passed, six entries each.
- Python lint/type checking: not configured by this repository; not claimed.
  ShellCheck/shfmt are unavailable on the host; not installed for this task.
- `./kisara.sh test -q` — **1071 passed, 1 skipped, 3 warnings** in 550.46s,
  exit 0. The skip is the existing missing-Git environment case; warnings are
  the existing PTB `retry_after` deprecation notices. The initial sandbox
  invocation returned 126 because Docker socket access was denied; the narrow
  wrapper escalation was approved and completed the offline test container.

Residual boundary: fixture and direct-filter evidence establishes the
locale-dependent defect, not the cause of the user's exact command session.
No other concrete attachment defect was found by code review. The user confirmed
that their command remains attached while newly generated logs fail to appear,
which is compatible with line suppression. The agent host's observed UTF-8
locale does not establish the user's invocation locale. No private dotenv,
live service, account operation or actual incoming log was inspected.

Human review classification: `human-optional` for this deterministic filter
repair; the required focused and full automated gates passed.
A later user-side `./kisara.sh preview status` observation of a newly produced
ordinary log can confirm the original environment; if it still stalls/exits,
that symptom needs follow-up diagnosis. This optional observation does not
authorize live account actions and is not a prerequisite for the evidenced
filter fix. Commit/archive remain separate main-session decisions.
