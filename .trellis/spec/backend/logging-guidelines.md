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
