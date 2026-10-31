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
Startup failures report a controlled phase (`initialize`, `polling_bootstrap`
or `application_start`) and exception type/category, with an attempt count for
retryable phases. The process-level Telegram failure also retains the exception
type. Never format the exception value, response body or chained traceback to
add detail. The bounded startup retry/cleanup contract is recorded in
[error handling](error-handling.md#telegram-startup-network-recovery).

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
provider credentials, and full private URLs out of logs by default. The
explicit Telegram summary opt-in below is the authorized exception for bounded
message previews and sender/chat IDs. The approved
[QQ login presentation](../trellis-plus/cli-entrypoints.md#8-qq-login-png-in-attached-logs)
is a separate interactive exception: a login/PNG-saved event renders its PNG
inside the attached terminal log view. Captured diagnostics and redirected
logs retain QR/URL suppression; no authentication payload or image belongs in
application logs, task evidence or tracked files. Existing operational
logs can contain group IDs, quoted message IDs, and official bot display names;
they are not anonymous telemetry. Keep logs private and avoid expanding their
identifying content.

Display redaction must not rewrite structural metadata that later controls a
reader, freshness check or replay boundary. In the QQ log path, preserve only
the validated private Docker timestamp prefix until its consumer removes it;
redact the message normally. Discover credentials by semantic field names:
`*_URL` is a configured URL, while `EXPORT_MAX_URLS` is a public integer count.
Test short numeric credential collisions separately from nonsecret counts.

Configured setu media storage is an opt-in persistence exception, not permission
to log or archive general chat history. Safe wrapper exception text does not
make its chained traceback safe automatically. Review underlying exception
content when changing `_log.exception` paths.

Good: describe a failed operation using a bounded safe category. Base: report
engine startup. Bad: debug-dump a raw OneBot payload to diagnose authorization.

## Opt-in Telegram receive/send summaries

### 1. Scope / trigger

The user explicitly approved NapCat-like Telegram receipt/reply visibility,
including sender/chat IDs and bounded content previews. This overrides the
default message-body policy only when the engine-owned opt-in is enabled.
It does not authorize SDK request logs, raw events or unsolicited live tests.

### 2. Signatures

`Settings.telegram_message_log_enabled: bool = False` is an appended field.
`TELEGRAM_MESSAGE_LOG_ENABLED` configures only Telegram, in direct settings
and its Compose service. The public dotenv default is false; this user's local
deployment explicitly enables it. Use existing `kisara.telegram` INFO logs.
`message_preview(text: str, token: Optional[str], limit: int = 120) -> str`
owns content redaction, escaping and length bounding in the adapter.

### 3. Contracts

Adapter summaries describe allowed incoming messages, confirmed outgoing text
chunks/documents and optional handled-without-reply outcomes. Include bounded
conversation kind, sender/chat IDs and a one-line text/caption preview. The
existing access sets determine whether incoming details may be logged, without
changing handler invocation, routing or dedup behavior. Unsupported or denied
updates do not disclose identities or text.

Redact the configured bot token and token-bearing Bot API URL fragments before
truncation, then escape control/newline/terminal-formatting characters and bound
the resulting preview to 120 display characters. Format document names through
the same bounded helper; log metadata rather than media bytes. Emit success
only after SDK confirmation, including scheduled news through the same send
path. For multi-chunk text, sanitize the whole original message before splitting
and use that one preview with confirmed part index/count. Sanitizing individual
chunks can leak token fragments when a token crosses a UTF-16 split boundary.
Keep SDK/httpx/httpcore suppression and bounded failure categories.
Polling readiness is emitted only after polling and application start succeed.

### 4. Validation and error matrix

| Condition | Log behavior |
| --- | --- |
| Switch absent/false | No message summaries |
| Switch invalid | Telegram startup configuration error |
| Allowed text, switch true | Received summary; optional no-reply state |
| Denied or unsupported update | No identifying/content summary |
| Confirmed text/document send | Destination/content or caption/metadata summary |
| Send raises, result unknown | Existing safe failure log; no false success |
| Long, multiline, control or token-bearing input | Bounded escaped/redacted preview |

### 5. Good/base/bad cases

Good: log a configured user's `/ping` and confirmed `pong`. Base: default
deployment retains quiet message handling. Bad: enable SDK HTTP logs, log
credentials before sanitizing, or disclose denied sender text for debugging.

### 6. Required tests

Assert enabled and disabled behavior, allowed/denied/unsupported reception,
no-reply processing, SDK-confirmed text/chunk/document/news sends and failed
sends without success records. Cover configured-token and URL redaction before
the length bound, multiline/control input, document metadata, readiness ordering
and unchanged SDK suppression. Configuration tests cover default/true/false,
invalid values and engine isolation. Synthetic tests do not log real messages.

### 7. Wrong versus correct

Wrong: truncate incoming content before token replacement, or emit `sent`
before awaiting the SDK. Correct: sanitize before bounding and emit success
only after a receipt. User opt-in changes observability, not authorization.

## Terminal-control redaction locale

### 1. Scope and trigger

Applies to shared preview/attached QQ sanitization, captured diagnostics,
stream preflight/filtering and login snapshots. Terminal ANSI ranges describe
ASCII bytes; caller collation must not change their meaning.

### 2. Signatures

`preview_filter_logs [sed-options]` executes the shared filter array with
`LC_ALL=C` scoped to sed for diagnostics, preflight and snapshots.
`preview_replace_secrets` scopes `LC_ALL=C` locally for OSC/CSI and remaining
ASCII control normalization before literal replacement. The background streaming sanitizer launches
`LC_ALL=C sed -u -E ... &` directly so its recorded PID remains sed itself.

### 3. Contracts

Normalize before replacing secrets: later ANSI/control stripping can reconstruct
a credential separated by escape sequences, CR, backspace, tab or DEL. Both Bash's CSI
matcher and sed need deterministic byte semantics. Preserve the caller's locale,
including an unset LC_ALL, and ordinary UTF-8 text. QR suppression matches whole
UTF-8 symbols with alternatives. Controlled interactive PNG rendering remains
the separately authorized path. No global locale export or new dependency.
Do not wrap a tracked background sanitizer in a helper shell that hides its PID.
Before removing remaining controls, canonicalize only valid Bearer prefixes and
their whitespace to a plain separator, retaining token bytes for later literal
replacement. Otherwise tab-separated generic tokens lose their recognizer.
Do not pre-redact a partial token before normalizing a split configured secret,
or make separators optional and overredact ordinary `Bearerword` text. The
rest-scanning loop must advance past each match rather than rescan inserted text.

### 4. Validation and error matrix

| Condition | Required behavior |
| --- | --- |
| C/POSIX/C.UTF-8/en_US/zh_CN caller | Same byte-defined sanitizer behavior |
| ANSI/control-interleaved synthetic credential | Normalize then redact before display |
| Chinese ordinary message | Preserve complete UTF-8 text |
| Caller LC_ALL set/unset | Preserve caller state after processing |
| sed unavailable/fails | Nonzero fail-closed path; no raw fallback |
| Reader cleanup | Track and terminate the actual sanitizer process |

### 5. Good, base and bad cases

Good: en_US startup/snapshot/stream preserves Chinese and redacts hidden secrets.
Base: C.UTF-8 output is unchanged. Bad: fix only sed while Bash preprocessing
can still miss an escape-separated credential, or leave a hidden sed child.

### 6. Tests required

Use `test_preview_redaction_locale.py` for the three production boundaries,
internal locale observations, caller restoration, ANSI/OSC/CR/tab/DEL hidden secrets,
Unicode, failure closure and sanitizer PID identity. Test real installed
en_US/zh_CN collations when available; missing-locale fallback to C is not
evidence. Report container skips and use bounded actual host shell probes when
those locales exist. Preserve QR/preview/export redaction regressions.
Cover known/unknown Bearer values with tab/CR/VT/FF separators, control-split
known values, multiple/already-redacted/empty/non-token words and quote/comma/
semicolon boundaries. Preserve strict existing generic syntax.

### 7. Wrong versus correct

Wrong: run byte ranges under arbitrary collation, globally change the user's
locale, or background a helper whose PID differs from the sanitizer.
Correct: scope byte semantics to internal processing and preserve direct
background-process ownership plus the surrounding terminal locale.

## Verification

For logging changes, inspect messages and failure causes alongside
`tests/unit/test_onebot_adapter.py`,
`tests/integration/test_onebot_protocol.py`, and startup handling in
`bot/main.py`. Add focused log assertions only when the changed privacy or
failure contract requires them. Do not claim the existing suite provides a
complete live log privacy audit; live acceptance follows the
[validation profile](../trellis-plus/validation.md).
