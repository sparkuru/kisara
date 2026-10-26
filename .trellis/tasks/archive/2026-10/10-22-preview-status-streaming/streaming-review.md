# Independent review of reopened startup/status streaming

## Scope and context

Reviewed the approved revised PRD/design/execution plan and all eight files in
both task manifests. The native hook output was truncated; the saved hook
output and relevant complete repository files were read directly. Re-read the
current CLI/validation specs and operations documentation after main-session
updates. Preserve the earlier locale fix and concurrent Telegram recovery work.

The previous locale-only acceptance did not cover the user's startup or unready
status paths. The diagnostic marker, isolated pre-change command reproduction,
and new delayed-output regressions establish this separate correction's scope.

## Findings (fixed)

- File: `tests/unit/test_preview_lifecycle.py`.
  The new startup test proved safe delayed output before readiness and an
  attached process after the ready summary, but did not release another line
  after that summary. With main-session approval and implementer ownership
  coordination, enabled the existing localized producer in this test and
  released/asserted another safe delayed line from NapCat, Kisara and Telegram
  after actual readiness. The four startup cases pass with this stronger check.
  No production source fix was needed during independent review.

## Findings (not fixed)

No actionable production defects found. Main-session-owned PRD/status/mainline
reconciliation remains separate from this independent review report.

Reviewed the parent-shell setup/check/wait split, inherited dynamic-local secret
arrays in asynchronous stages, per-service FIFO identities, ownership recheck,
bounded scratch and credential filtering before display. Readiness remains real
and bounded, checks reader failures between probe passes and before success,
and controls the truthful summary. Unready status follows owned bots without
repairing services; missing/foreign groups and auxiliary-only failures retain
their explicit boundaries. Real EOF is finite, without reconnect logic.

The cancellation flag skips duplicate diagnostics only for INT/TERM after live
viewing starts. Genuine startup failures/timeouts retain auxiliary diagnostics.
The same owned PID list supports failure and signal cleanup, preserving 130/143
and containers/data. Both start/status check for mkfifo before runtime effects.
Help and project-owned contracts describe the approved behavior.

The two revised legacy fixture expectations are intentional: mocked finite EOF
now returns 0 after an unready warning. Persistent-reader tests separately prove
attachment, so those finite fixtures are not continuous-follow evidence.

## Verification

- `bash -n kisara.sh deploy/preview-runtime.sh deploy/preview-console.sh deploy/engines.sh`:
  pass.
- `git diff --check`: pass before and after review edits.
- Lint: no configured application command. ShellCheck and shfmt are unavailable
  on both the host and the existing Docker wrapper; neither was installed.
- TypeCheck: no configured command; not run and not claimed as passed.
- Supplemental final-test check:
  `./kisara.sh test tests/unit/test_preview_lifecycle.py -k start_streams_during_readiness -q`:
  **4 passed, 186 deselected in 13.55s**.
- Full `./kisara.sh test -q`: **1115 passed, 1 skipped, 3 warnings in 573.65s**.
  The skip is the existing unavailable Git executable in the development image;
  the three existing warnings concern PTB's future retry_after timedelta type.
  This run collected the original test definition before the supplemental
  assertion-only extension; production source was unchanged. The separate
  four-case check above covers the final strengthened definition.
- Implementer's recorded four-suite command:
  `./kisara.sh test tests/unit/test_kisara_cli.py tests/unit/test_engine_deployment.py tests/unit/test_preview_lifecycle.py tests/unit/test_preview_readiness.py -q`:
  **289 passed, 1 existing skip in 547.54s**. Its complete report and the eight
  before/after cases are in `streaming-implementation.md`; these focused totals
  were inspected, not independently rerun by this reviewer.
- The main session's controlled real-Docker status observation in
  `readiness-diagnosis.md` forced the probe to fail without container exec and
  allowed only read Docker operations. Status remained attached for 12 seconds,
  warned and followed both platform streams, with no ready/diagnostic/failure
  marker and identical three-container Id/Running/StartedAt/Pid fields. This
  supports attachment/cancellation with real Docker logs; it does not prove
  actual unhealthy state or fresh-message output. The delayed-output fixtures
  establish timing separately.

The initial sandboxed full-wrapper invocation failed because Docker socket
access was denied. Narrow wrapper escalation then ran successfully; no automatic
approval-review rejection occurred. Tests use Python 3.12 and isolated recording
Docker fixtures, without private dotenv/account/API/service operations. No live
startup, rebuild, restart, account message, commit or archive was performed by
this reviewer.

## Human review classification

Classify as **human-optional**: deterministic tests and full regression passed
for the changed command behavior; a user-side observation of the actual
terminal/runtime may add signal but is not required for commit readiness.
Neither fixture results nor prior ready-only runtime observation establish a
live startup or reproduce a historical private runtime's readiness state.
The main session owns any separate read-only runtime observation and final
delivery/commit decision.
