# Logging Guidelines

## Configuration and ownership

`src/kisara/bot/main.py` configures standard-library logging once:

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
```

The application logger is `kisara`; the OneBot adapter uses `kisara.onebot`.
The optional official adapter uses `botpy.logging.get_logger()` and is loaded
only for that engine. `infrastructure/logging/` contains no separate logging
implementation. There is no JSON structured logging framework.

Telegram uses `kisara.telegram` and `kisara.telegram.news`. Suppress SDK/httpx/
httpcore request and exception logging before polling: Bot API URLs embed the
token. Log safe categories at the owned adapter/request/process boundaries,
including startup, fatal polling, and shutdown errors. A safe callback does not
make SDK internal tracebacks safe. Test synthetic token-bearing failures.
Pinned PTB's network loop raises `InvalidToken` without invoking the ordinary
polling error callback. `ManagedPollingBot.get_updates` is the public SDK method
boundary for signaling this fatal condition. It returns an empty fetched update
tuple while the owner stops and raises a bounded error, avoiding an orphan SDK
task exception containing the token. Cleanup continues through SDK failures.
`ManagedPollingBot.initialize()` closes its owned request clients through public
`request.shutdown()` if initialization fails or is cancelled; Application's
shutdown can otherwise return before closing partially initialized clients.

## Existing levels and examples

| Level / call | Existing examples |
| --- | --- |
| `info` | Startup/shutdown in `bot/main.py`; OneBot connection readiness; official bot readiness |
| `warning` | Ignoring malformed OneBot packets, failed quoted lookup, disconnect/retry context |
| `error` | Invalid configuration, missing adapter dependency, unavailable startup state |
| `exception` | Unexpected process/message failure and daily brief failures with traceback |

Use lazy logging arguments, as in `bot/main.py`:

```python
_log.info("Starting Kisara with %s engine", settings.engine)
```

`bot/adapters/onebot_v11.py` demonstrates bounded diagnostics such as
`_log.warning("Ignoring invalid OneBot JSON packet")` without dumping the
packet. Log at the boundary that handles the failure to avoid repeated
tracebacks for the same error.

## Privacy and operational context

Keep tokens, `.env` contents, raw events, message bodies, login QR codes,
provider credentials, and full private URLs out of logs. Existing operational
logs can contain group IDs, quoted message IDs, and official bot display names;
they are not anonymous telemetry. Keep logs private and avoid expanding their
identifying content.

Configured setu media storage is an opt-in persistence exception, not permission
to log or archive general chat history. Safe wrapper exception text does not
make its chained traceback safe automatically. Review underlying exception
content when changing `_log.exception` paths.

Good: describe a failed operation using a bounded safe category. Base: report
engine startup. Bad: debug-dump a raw OneBot payload to diagnose authorization.

## Verification

For logging changes, inspect messages and failure causes alongside
`tests/unit/test_onebot_adapter.py`,
`tests/integration/test_onebot_protocol.py`, and startup handling in
`bot/main.py`. Add focused log assertions only when the changed privacy or
failure contract requires them. Do not claim the existing suite provides a
complete live log privacy audit; live acceptance follows the
[validation profile](../trellis-plus/validation.md).
