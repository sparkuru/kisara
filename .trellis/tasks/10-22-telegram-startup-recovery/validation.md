# Telegram startup recovery implementation validation

## Diagnosis and boundary

The four supplied log lines prove one failed start followed by a successful
start. They do not identify the first exception or who initiated the second
start. No private environment, live Telegram API, account or service was
accessed during this implementation.

An offline pinned PTB 22.8 BotPeer fixture confirmed the implementation gap:
NetworkError from initialization/getMe or polling-bootstrap/deleteWebhook
aborted the adapter before the SDK's running polling retry loop. The outer
process logger hid even the safe exception class. These are verified code
defects; they are not proof of the original incident's precise cause.

Recovery stays in TelegramAdapter. It uses three total startup attempts,
interruptible 1/2-second delays, fresh SDK applications and request pairs only
after cleanup. BadRequest is excluded despite its NetworkError inheritance;
InvalidToken, Conflict, Forbidden, RetryAfter and unrelated initialization or
application/worker errors retain failure behavior. Failed partial-init request
cleanup is tracked separately, preventing replacement while preserving the
original safe startup category. Main logs the safe exception type and returns
1 for adapter failures. SDK logging remains suppressed and exception values
and tracebacks are never logged by the changed handling boundaries.

## Before/after commands and results

- Initial sandbox invocation of the offline wrapper could not access the
  Docker socket (exit126). The same narrow wrapper command was permitted
  with session escalation; no raw Docker operation was substituted.
- Before the source fix:
  `./kisara.sh test tests/integration/test_telegram_protocol.py -q -k startup_transport_failure_recovers`
  produced **2 failed, 12 deselected**. Both simulated transient requests
  propagated NetworkError; no replacement clients or ready application existed.
- The same focused reproduction after the fix produced
  **2 passed, 12 deselected**.
- Expanded startup classification/cleanup/cancellation development selection:
  `./kisara.sh test tests/integration/test_telegram_protocol.py -q -k 'startup or failed_cleanup'`
  produced **31 passed, 12 deselected**. Six PTB RetryAfter construction warnings
  from those new fixtures were eliminated by explicitly exercising PTB's
  supported timedelta setting in that parameterized test.
- Final approved focused gate:
  `./kisara.sh test tests/unit/test_telegram_adapter.py tests/unit/test_telegram_settings.py tests/integration/test_telegram_protocol.py tests/unit/test_preview_readiness.py -q`
  produced **173 passed, 3 existing PTB warnings**. This includes cancellation
  during initialization/bootstrap and backoff, close during backoff and app
  startup, fatal ownership failure during app startup, app-start NetworkError
  without restart, exact attempt/delay counts, cleanup-before-replacement,
  cleanup uncertainty, all nonretryable subclasses, no false readiness, one
  successful worker lifecycle and synthetic-secret log assertions.
- `git diff --check` passed for the working tree after implementation.

## Limits and handoff

Pinned BaseRequest wraps unknown exceptions raised by do_request as
NetworkError. Recovery classifies the public SDK exception at the owned
initialization/bootstrap boundary; it does not infer an underlying incident
cause from that wrapper. Direct request-initialize/application-start programming
errors remain nonretryable.

Pinned HTTPXRequest.initialize has no suspension points. The injected request
fixtures cover initialization failure and cancellation but do not claim generic
support for arbitrary async request implementations whose sibling initializer
continues after PTB's default gather fails. Production still uses the existing
HTTPXRequest clients, without a new transport wrapper or SDK private state.

## Independent review

The dispatched check agent inspected the adapter/process/test diff and the
updated backend error-handling and logging contracts. No source or test issue
requiring a fix was found. The review traced the pinned SDK's public
initialize, shutdown, polling-bootstrap and HTTPXRequest ownership paths;
checked the BadRequest subclass exclusion, cleanup uncertainty, fatal/stop
guards, readiness, bounded backoff and secret-safe diagnostics; and preserved
the separate preview-status changes. There is no private SDK-state access,
dependency change, retry of sends or running workers, or live lifecycle action.

Native context injection included a truncation notice. The check agent read
the saved hook output and then explicitly loaded check.jsonl, PRD, design,
execution plan and all nine manifest documents in full through direct/chunked
reads, including the updated backend error/logging docs. It also loaded the
applicable common, Python, before-dev and check skills, guide index and current
mainline, retaining the narrow startup approval and paused TgSetu boundary.

The independent full offline gate, `./kisara.sh test -q`, passed with
**1107 passed, 1 skipped, 3 existing PTB warnings in 513.23s** (exit0).
The skip remains the existing missing-Git container case and the warnings
remain PTB RetryAfter deprecations from existing fixtures. The initial sandbox
invocation returned126 on Docker socket access; the same narrow wrapper command
was then approved with session escalation. A final `git diff --check` passed.
Lint and static type checking are **not configured/not run**, rather than
claimed passing gates; pyproject.toml and the repository tool configuration
inventory agree with the backend quality policy. No toolchain was installed.

## Submit-ready review boundary

Classification: **human-optional**. Deterministic pinned-SDK protocol tests
cover the approved recovery and diagnostic contracts. Observing a future normal
Telegram startup may add incident-specific evidence, but this implementation's
commit gate does not depend on a live check or service mutation. The original
four lines still cannot identify their original exception. The source changes
have not been rebuilt or applied to an existing image/container; deployment,
restart and account/cutover acceptance remain outside this task.

No configured lint/type-check gates exist. This wrapper run uses Python3.12;
it does not prove every declared supported Python version, live account
capability or sustained external network reliability. TgSetu rollout remains
paused. Preview streaming edits were preserved. No commit, archive, endpoint
change, deployment, service restart or persistent-data operation occurred.
