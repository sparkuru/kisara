# Configurable scheduled-news retry

## Configuration flow

Add `Settings.news_push_retry_seconds` with default60 and the ordinary news
TOML key `push_retry_seconds`. Validate a positive integer at startup, rejecting
boolean TOML values and malformed environment strings. Load TOML lazily before
the environment fallback so a valid explicit TOML value masks invalid lower
precedence input. Resolve selected engine aliases through existing settings
machinery. Compose maps public engine variables into the shared runtime name;
OneBot/development keep their existing unset-only legacy fallback behavior.

## Existing scheduler integration

OneBot stores the validated setting on its adapter and uses it for pending
generation/delivery retry waits. Existing delivery checkpoints continue to skip
confirmed group/private targets. This does not upgrade OneBot's existing
delivery guarantee or retry classification.

Inject the setting into TelegramNewsPush without shifting existing positional
clock/timestamp call contracts (prefer a trailing optional parameter). Replace
the900-second generation/rejection deadlines with the configured interval,
measured after the failed operation. Respect a longer server retry-after.
Keep journal state semantics and no-resend guards unchanged. The existing
scheduler polling must support intervals shorter than its30-second cadence;
bound its sleep by the retry interval rather than adding a separate retry task.
Timer scheduling may have ordinary event-loop/polling latency, but must never
retry before the required deadline. No database migration or counter is needed.

## Documentation and rollout

Update both news TOML examples, `.env.example`, affected Compose services,
existing operations guidance and feature docstrings. Source changes require
rebuilding/recreating deployed application containers; this task does not do
that automatically. Private user configuration is not rewritten. Existing
stored Telegram retry deadlines remain persisted; newly failed operations use
the new interval. No live bot/provider calls are part of verification.

## Risk boundaries

Repeated transient failures may continue at the configured interval until the
existing day/lifecycle boundary; there is no new retry-count option. Preserve
target deduplication, cancellable waits, day boundaries, Telegram unknown-result
suppression and server rate-limit waits. Keep unrelated uncommitted work intact.
