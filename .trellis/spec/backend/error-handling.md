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
