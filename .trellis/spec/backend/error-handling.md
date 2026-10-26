# Error Handling

## Error boundaries

Kisara has message routing outcomes rather than HTTP status responses.
Keep startup configuration failures, user argument errors, provider failures,
and protocol request failures distinct.

| Type / source | Boundary behavior |
| --- | --- |
| `ConfigurationError`, defined in `config/feature_files.py` and re-exported by `config/settings.py` | Startup logs the error and returns 2 |
| `FeatureFileError`, `config/feature_files.py` | Subclass of `ConfigurationError`; invalid TOML/keys/types fail at loading |
| `CommandInputError`, `bot/contracts.py` | Dispatcher returns `DispatchResult("error", str(error), "Invalid command arguments.")` |
| `RemoteServiceError`, `infrastructure/integrations/http.py` | Dispatcher returns error status and safe provider failure text |
| `OneBotError`, `bot/adapters/onebot_v11.py` | Protocol connection/request failure handled by adapter lifecycle or operation boundary |

Unauthorized or duplicate events return `unhandled` without invoking feature
services. Unexpected application errors are not converted into successful
replies. The outer startup boundary logs an exception, returns 1, and closes
the adapter; Ctrl-C returns 130.

## Validation and expected failures

`Dispatcher.dispatch_result(event: MessageEvent) -> DispatchResult` owns the
shared routing error conversion. Example from `bot/dispatcher.py`:

```python
try:
    return self._route(event)
except CommandInputError as error:
    return DispatchResult("error", str(error), "Invalid command arguments.")
except RemoteServiceError as error:
    return DispatchResult("error", str(error), "Remote service failed.")
```

`dispatch_payload` turns meaningful output into a string or `OutgoingMessage`;
no reply/action means `None`. Tests should assert status and side effects as
well as text; reply wording alone is not proof of successful execution.

`HttpReader(timeout=10.0, max_bytes=2_000_000)` maps HTTP/network failures,
oversized content, invalid UTF-8, and invalid JSON to `RemoteServiceError`.
It rejects redirects and preserves the original cause with `raise ... from
error` while keeping provider response bodies and secret URLs out of reply text.
`DailyNews` similarly wraps cache filesystem failures and invalid rendered PNGs
in a feature-appropriate `RemoteServiceError`.

## Failure matrix and recovery

| Condition | Result |
| --- | --- |
| Invalid recognized command arguments | Error outcome with usage/validation reply |
| Disallowed sender/group or duplicate message | Unhandled, no external action |
| OneBot invalid JSON/non-object packet | Warning and ignore; connection remains usable |
| Quoted message lookup fails | Adapter warns without logging the full message |
| News group send fails | Do not mark delivery completed; scheduler owns retry |
| Setu media item fails | Report failure; preserve successes for partial retry |
| Unexpected adapter message handler failure | Log at adapter boundary; do not fabricate success |

Broad exception handling exists at process/adapter task boundaries to keep
lifecycle cleanup and diagnostics coherent. In providers and validation code,
catch the specific failures being translated. Inspect exception content before
logging; a chained traceback can contain more than the safe user-facing error.

## Cases and verification

Good: translate invalid JSON to a safe `RemoteServiceError` and assert error
status. Base: `/roll` invalid arguments raise `CommandInputError`. Bad:
swallow every exception and return success, or fetch quoted history before
checking authorization.

Use `tests/unit/test_dispatcher.py` for allowlists, duplicates, and routing
outcomes; `tests/unit/test_public_services.py` and
`tests/unit/test_daily_news.py` for provider failures;
`tests/unit/test_settings.py` for startup rejection; and
`tests/integration/test_onebot_protocol.py` for request failure/lifecycle paths.

Wrong: return raw provider payloads or token-bearing URLs in exceptions.
Correct: report bounded operational context and a safe message, preserving
error causality only where diagnostics remain private and appropriate.

## Telegram startup network recovery

### 1. Scope and trigger

The adapter owns bounded recovery of initialization/getMe and polling-bootstrap
requests before the normal running polling loop exists. A generic process exit
does not identify the historical request failure; do not infer a real incident's
cause from failed-then-successful startup logs alone.

### 2. Signatures

`TelegramAdapter._start_application() -> Optional[Application]` owns attempts;
`_wait_startup_retry(delay: int) -> bool` returns whether shutdown was requested.
`ManagedPollingBot.initialization_cleanup_failed` reports uncertain partial-init
cleanup without reading private SDK state.

### 3. Contracts

Allow three total startup attempts with interruptible 1-second and 2-second
backoff. Retry SDK `NetworkError` except `BadRequest`, which subclasses it.
Preserve the SDK's public error boundary: it can wrap request-provider failures
as NetworkError; do not log their raw causes. Recreate the SDK bot, request
clients and application after successful cleanup; partial initialization may
already have closed requests while SDK initialization flags remain set.
Keep `bootstrap_retries=0` to avoid nested retry policies, and
`drop_pending_updates=False`. Stop requests prevent further attempts. Only the
successful attempt starts application workers; running polling, sends and worker
failures do not enter this startup retry loop.

### 4. Validation and error matrix

| Condition | Required behavior |
| --- | --- |
| Initialization/bootstrap transport failure, attempts remain | Safe phase/category log; close owned resources; bounded backoff and fresh attempt |
| Third transport failure | Nonzero exit; no further attempt |
| InvalidToken, Conflict, Forbidden, BadRequest or RetryAfter | Explicit failure; no startup network retry |
| Programming/application-start or later worker failure | Explicit failure; no startup retry |
| Failed request/poller cleanup | Preserve safe original failure classification; abort retry |
| Stop/cancel during backoff or startup | No further startup attempt or false ready state; close owned resources |

### 5. Good, base and bad cases

Good: a failed getMe followed by a successful fresh-client attempt recovers in
one adapter start. Base: normal startup succeeds once without delay. Bad:
retrying BadRequest as transport failure, reusing closed clients, or publishing
ready before application startup and a successful poll.

### 6. Tests required

Use the pinned SDK protocol fixture in `tests/integration/test_telegram_protocol.py`
to cover getMe/deleteWebhook recovery, exact attempt/delay bounds, fresh client
cleanup ordering, nonretryable subclasses, stop/cancel, cleanup failure and no
false readiness. Startup tests in `tests/unit/test_telegram_settings.py` verify
nonzero process status and safe exception category without token-bearing text.
Keep existing adapter/readiness suites and the full Docker regression gate.

### 7. Wrong versus correct

Wrong: retry the entire adapter runtime, reuse a failed initialized SDK object,
or print a traceback to recover diagnostic detail. Correct: retry only startup
transport operations after verified cleanup and emit controlled phase names
plus exception categories. Keep SDK request/exception log suppression active.
