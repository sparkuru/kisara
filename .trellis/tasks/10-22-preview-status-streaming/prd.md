# Preview status continuous log output

## Goal

Restore prompt continuous log output from `./kisara.sh preview` and
`./kisara.sh preview status`, including startup/readiness waits, so new logs
appear without an interrupt or another invocation.

## Background

- The user reported that preview status does not continue scrolling logs and
  explicitly requested a new task on 2026-10-22.
- During implementation, the user clarified that the command remains attached
  but new logs do not appear; it does not immediately return to the prompt.
- After reviewing delivery, the user reported that bare `preview` appears stuck
  until Ctrl+C releases logs, while `preview status` prints logs and exits.
  This reopens acceptance: the locale filter correction does not establish
  resolution of the reported end-to-end command behavior.
- `kisara.sh:99` dispatches online operations through `deploy/engines.sh`.
  The status branch in `deploy/preview-runtime.sh:664` calls the existing log
  follower after readiness and summary rendering.
- `deploy/preview-runtime.sh:90` already requests Docker follow mode and uses
  private FIFOs, secret replacement, unbuffered sed, and platform prefixes.
  At planning time the reported failure's root cause was not established; do not assume
  adding follow mode or unbuffered sed alone fixes it.
- `tests/unit/test_preview_lifecycle.py:1091` already exercises delayed output
  using a controlled Docker fixture. That fixture is not evidence that the
  reported real execution path currently works.

## Requirements

- R1: Once startup has created/selected owned application containers, preview
  immediately shows recent and fresh sanitized logs while readiness checks run;
  successful readiness still produces the truthful summary and keeps following.
- R1a: Status inspects current readiness and follows existing owned bot logs even
  if readiness is not yet established. An unready warning must not become a
  ready banner or an immediate diagnostic-only exit. Missing/foreign groups and
  auxiliary-only behavior retain explicit existing boundaries.
- R2: Preserve selected-service ownership checks, platform labels and credential
  redaction before display. Keep memory and temporary storage bounded.
- R3: Preserve Ctrl+C/SIGTERM reader cleanup and existing exit codes. Viewing
  status must not recreate, restart, stop or remove containers or persistent data.
- R4: Locate the failing execution boundary and reproduce it with a focused
  regression before choosing the smallest fix in the existing implementation.
- R5: Ctrl+C/TERM during log viewing must not trigger a second bulk diagnostic
  dump. Real startup failures before live viewing retain bounded diagnostics;
  startup readiness remains bounded and stream failures stay explicit.

## Acceptance Criteria

- [x] AC1 (R1, R4): A regression reproduces the reported interruption/stall;
  after the fix, bare preview emits multiple delayed logs while selected bots
  are still unready, then prints its real ready summary and keeps following.
  No interrupt, EOF or extra invocation is needed to release output.
- [x] AC1a (R1a, R4): Running-but-unready status warns, emits delayed safe logs
  before EOF and stays attached until interruption or a real stream end/failure;
  it has no ready banner, lifecycle mutation or diagnostic-only exit.
- [x] AC2 (R2): Selected single/multiple engine streams retain correct prefixes;
  credentials remain redacted before emission and scratch remains bounded.
- [x] AC3 (R3): Parent-only INT/TERM reaps owned readers, returns 130/143 and
  leaves container state and retained data unchanged.
- [x] AC3a (R5): Interrupting startup/readiness viewing releases no bulk
  end-of-run diagnostic dump; reader failures during readiness do not disappear
  behind a timeout or a ready summary.
- [x] AC4 (R1-R4): Focused canonical CLI/deployment/preview checks and relevant
  shell syntax/lint checks pass; record exact results and remaining limitations.

## Scope

Inspect the canonical dispatch and existing preview log pipeline. Code ownership
is `deploy/preview-runtime.sh`, its existing `deploy/preview-console.sh` help and
regression coverage in `tests/unit/test_preview_lifecycle.py`. Synchronize the
existing operations document and project-owned CLI/validation contracts for the
approved attached-start and unready-status behavior. Record evidence in this task.

## Out of scope

No new status/watch flag, UI redesign, dependency upgrade or change to application
logging configuration. Reuse the existing status credential-redaction policy for
startup viewing; retain readiness truth, ownership and storage boundaries. Do not
restart live bots, inspect or print private dotenv values, send messages, modify stored data,
commit or archive as part of planning. Real-account validation requires separate
authority if deterministic reproduction leaves that necessary.

## Planning status

The first PRD-only plan was approved on 2026-10-22. The user subsequently supplied
the failed/interrupted diagnostic output, confirming a readiness-gated path that
the locale correction did not fix. The revised proposal changes startup and
unready-status viewing semantics. PRD/design/execution plan were reviewed; the
user approved the revised final summary with “确认” on 2026-10-22, authorizing
implementation and verification of these paths.

## Validation status

The readiness-gated stall/exit paths are reproduced and corrected. New actual-path
regressions failed all eight cases before the correction and passed all eight
afterward. The focused CLI/deployment/preview/readiness gate passed 289 tests
with one existing skip; the strengthened post-ready delayed-output check passed
four cases. Independent review found no actionable production defect; full
regression passed 1115 tests, with one existing skip and three existing PTB
warnings. See [validation.md](validation.md) for current evidence
and the separately scoped historical locale correction. Controlled read-only
real-Docker unready status stayed attached for 12 seconds with unchanged
container identities/state. Actual fresh-message delivery was not generated.
Commit approval remains pending.
