# Daily news private scheduled push design

## Feature specification

| Field | Contract |
| --- | --- |
| Trigger | The existing OneBot daily-news background loop; no incoming message or new command |
| Scope | OneBot private recipients and existing groups; personal-only scheduling works with groups disabled |
| Schedule | One shared `push_time`, UTC+8, default 10:30; late connection catches up today only; serial sends within each iteration |
| Authorization | `push_users` is a subset of `KISARA_ALLOWED_USERS`; existing group authorization remains unchanged |
| Input and output | Configured QQ numbers; existing dated `OutgoingMessage` text and image; no synthetic `MessageEvent` |
| Dependencies and cache | Existing `DailyNews` provider, thread-pool factory and dated image/HTML caches; no new dependency or cache |
| Configuration | News TOML `push_users = ["123456789"]`; `KISARA_NEWS_PUSH_USERS` comma-separated fallback; explicit TOML including `[]` wins; empty default disables private push |
| State | Existing `news_delivery.sqlite3` under `KISARA_STATE_DIR`; Compose `/app/state` on existing `kisara_state` volume |
| Failure | Record only confirmed successes; retry failed/unrecorded targets after 900 seconds; no historical backfill; unknown remote outcomes retain the existing possible-duplicate limitation |
| Platform limits | OneBot-only; private delivery depends on the logged-in QQ account being able to contact that recipient; automated tests use simulated transport |

## Requirement-to-implementation mapping

Source paths below are relative to `src/kisara/` unless qualified otherwise.

| Requirements | Code/configuration | State | Verification |
| --- | --- | --- | --- |
| R1–R2 | `config/feature_files.py`, `config/settings.py`, `config/features/news/config.toml.example` | None | Config loading, precedence, deduplication, QQ-number validation, allowlist and engine rejection, personal-only mode |
| R2–R3 | `bot/main.py`, `bot/adapters/onebot_v11.py` | Inject existing store when either recipient collection is nonempty | Startup wiring and simulated private request with expected image/text |
| R4 | `infrastructure/persistence/news_delivery.py` | Add private completion table beside unchanged group table | Open pre-feature DB, preserve group records, same number across kinds, reopen, pruning |
| R5 | Existing news loop and connected-session lifecycle | Confirmed completion per day/target/kind | Due time, late startup, isolated failures, retry, cancellation and reconnect |
| R6 | Service opening docstring, news config example, `docs/operations.md`, relevant template rows; Compose environment passthrough | Document current state volume | Documentation/source checks, focused suites and `./dev.sh --all` |

## Configuration and startup

Add `news_push_users: FrozenSet[str] = frozenset()` to `Settings` without
reordering existing positional fields. Register `push_users` in `FEATURE_KEYS`.
Load through the existing `words()` helper, then reject values that are not
canonical positive ASCII decimal QQ-number strings. Leading/trailing spaces
are trimmed by the existing loader; duplicated numbers collapse into the set.
Check the user allowlist and reject either kind of enabled scheduled push on
the official engine. Group-enabled checks remain conditional on group targets
only.

Enable the news factory in `main()` when groups OR users are configured. The
OneBot adapter receives both sets through the existing settings object, sorts
them for deterministic iteration, and launches one existing news task when
either set is nonempty. No additional scheduler task or framework is needed.
Pass `KISARA_NEWS_PUSH_USERS` into both production and development Compose bot
services, and document this optional fallback in `.env.example` and operations.
Feature TOML remains the primary user-facing configuration.

## Scheduler data flow

1. Compute today's due time using the existing UTC+8 clock and wait if early.
2. Query pending groups and private recipients independently.
3. If either list is nonempty, invoke the existing content factory once in
   the executor, reusing the dated news cache and the same payload for all
   targets in this iteration.
4. Send groups with `send_group_msg/group_id` and individuals with
   `send_private_msg/user_id`, converting configured QQ numbers with existing
   `_as_api_identifier()` and encoding `OutgoingMessage` through the existing
   encoder.
5. After each successful API response, record completion in that target's
   table. Catch target-level failures so later recipients still get sent.
6. Keep the current 900-second retry/recheck and next-day sleep rules.

The connection owns the single task: on disconnect it is cancelled and awaited;
on reconnect a fresh task checks persisted completion. Do not swallow task
cancellation or create a new thread/event loop for scheduling.

## Additive database compatibility

Keep the deployed `deliveries(day TEXT NOT NULL, group_id TEXT NOT NULL,
PRIMARY KEY(day, group_id))` table and its existing `was_sent(day, group_id)` /
`mark_sent(day, group_id)` API unchanged.

Create `private_deliveries(day TEXT NOT NULL, user_id TEXT NOT NULL,
PRIMARY KEY(day, user_id))` using `CREATE TABLE IF NOT EXISTS` in the same
database. Expose `was_private_sent(day, user_id)` and
`mark_private_sent(day, user_id)` using parameterized SQL and short-lived
transactions. This separates target kinds without rebuilding deployed group
state or changing old calls. Both kinds of marks prune records older than 30
days in both tables relative to the supplied delivery day.

Initialization is idempotent for empty, existing-group-only and already-updated
databases. A failed additive initialization can be retried without losing the
original table. A rollback to the old application can ignore the extra table;
group state and config must remain usable (remove new TOML keys before running
an older parser). No existing database or volume will be deleted.

## Validation and review boundaries

Use fake clocks/waits and simulated WebSocket responses; assert actual outgoing
actions, identifiers, message segments and durable outcomes. Include startup
coverage proving personal-only subscriptions are wired and a connection-level
test proving cancellation/reconnect does not leave overlapping news tasks.
Configuration and state changes require focused suites followed by the existing
full regression command. Documentation-only source claims and paths get checked
separately.

Live QQ reachability and sustained real-account delivery cannot be proven by
simulated protocol tests. Do not modify real QQ recipients, send live messages,
or restart services for validation without user authorization. Report the exact
remaining live acceptance procedure at delivery; a commit/deployment decision
remains separate from implementation approval.
