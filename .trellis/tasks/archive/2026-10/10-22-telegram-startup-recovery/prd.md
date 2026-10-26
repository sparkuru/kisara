# Telegram startup recovery and safe diagnostics

## Goal

Recover from temporary Telegram startup transport failures without requiring
manual process restarts, and report a useful safe failure category when startup
cannot succeed.

## Evidence and limits

- User-provided logs on 2026-10-22 show startup at 13:04:16.800, the generic
  process failure at 13:04:21.826, another startup at 13:05:13.823 and polling
  ready at 13:05:15.043. They establish one failed attempt followed by success,
  not the original exception or who initiated the second attempt.
- `src/kisara/bot/main.py:203-210` intentionally hides raw Telegram exceptions
  to protect token-bearing SDK URLs. It also hides the exception type.
- `src/kisara/bot/adapters/telegram.py:323-334` awaits SDK initialization and
  polling bootstrap once, explicitly using `bootstrap_retries=0`.
- The installed pinned PTB 22.8 source initializes the bot through getMe and
  polling bootstrap through deleteWebhook. Either startup request can raise
  a transport error before the running polling retry loop exists.
- Existing cleanup closes clients after partial initialization; a retry must
  not reuse closed request clients or depend on private SDK state.
- The historical exception cannot be recovered from these four lines. A
  transient network problem is a plausible explanation, not an established
  diagnosis of that particular run.

## Requirements

- R1: Startup transient network failures receive up to three total attempts,
  with 1-second and 2-second interruptible backoff before the remaining attempts.
- R2: Invalid credentials, conflicting polling ownership, forbidden/bad
  requests, configuration/programming errors and unrelated worker failures
  must not enter the startup network retry loop.
- R3: Startup failures identify the controlled startup phase and safe exception
  category without raw exception text, token-bearing URLs, response bodies or
  SDK tracebacks.
- R4: Clean up each failed attempt before retrying, keep one poller owner,
  preserve queued updates, and publish readiness only after successful startup
  and a successful poll. Stop/cancellation interrupts retry waiting.
- R5: Preserve current Telegram message authorization, sends, archive semantics,
  endpoints and the separately paused TgSetu deployment/account work.

## Acceptance Criteria

- [x] Transient getMe/initialization and polling-bootstrap failures followed by
  success recover within one adapter start; no false ready log or marker is
  emitted for failed attempts.
- [x] Repeated transport failure exhausts exactly three total attempts with
  safe phase/category diagnostics and a nonzero process result.
- [x] InvalidToken, Conflict, Forbidden, BadRequest and unrelated exceptions
  fail without network retry, even where SDK exception inheritance overlaps.
- [x] Every failed attempt's requests/tasks close before replacement; shutdown
  during backoff stops promptly and cannot start another poller.
- [x] Synthetic secret-bearing exceptions remain absent from all captured logs;
  focused Telegram/startup/readiness tests and required full regression pass.

## Scope and non-goals

Modify existing adapter startup/process diagnostics and their regression tests.
Do not enable SDK request/exception logging, add an infinite restart loop, retry
message sends, discard updates, alter credentials/proxies/endpoints, operate
live services or modify persistent data. The request narrowly resumes Telegram
startup diagnosis/repair; TgSetu rollout, cloud logOut, local Bot API cutover and
other Telegram feature implementation remain paused. Preserve the independently
checked preview-status-streaming changes, which await commit approval.

## Planning status

The user approved the final planning summary with “可以” on 2026-10-22.
PRD, design, execution plan and curated context are ready for implementation.

## Validation status

Implementation and independent review passed. The original public-SDK fixture
failed for both simulated startup network-failure paths; both recover after the
fix. Focused Telegram/startup/readiness checks passed 173 tests. Independent full
regression passed 1107 tests, with one existing skip and three existing warnings.
See [validation.md](validation.md) for cleanup, classification, cancellation,
readiness and secret-safe logging evidence. Human review is optional for this
deterministic repair. The historical exception remains unknown and current
images/containers have not received these source changes. Commit approval is
pending; TgSetu deployment/account work remains paused.
