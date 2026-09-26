# Configuration, Cache, and Storage Contracts

- ownership: project-shared
- source: project-authored
- evidence: `docs/application-template.md`, `docs/operations.md`,
  `src/kisara/config/`, `src/kisara/infrastructure/`, `deploy/compose.yaml`

## Scope and configuration signatures

Load configuration at startup, then inject dependencies in `bot/main.py`.
Do not reread configuration on every message.

Ordinary feature wiring is:

```text
config/features/<feature>/config.toml.example
  -> config/feature_files.py: FEATURE_KEYS and type validation
  -> config/settings.py: Settings fields, defaults, from_environment()
  -> bot/main.py: dependency assembly
  -> service or adapter consumption
  -> tests/unit/test_settings.py: loading, precedence, invalid input
```

`load_feature(name: str) -> Mapping[str, Any]` returns `{}` for a missing
ordinary feature file. Explicit TOML values override legacy environment values;
missing fields use legacy environment values or code defaults. TOML chat/tarot
group overrides take precedence over legacy `config/groups.json` values.
Group overrides must refer to allowed groups. Setu uses its separate
`config/setu.py` loader; a missing setu file disables that feature.

`Settings.from_environment()` selects `KISARA_ENGINE`, default `onebot`.
Validate credentials only for the selected engine: OneBot requires
`ONEBOT_ACCESS_TOKEN` and a `ws://` or `wss://` URL; official requires
`AppID`/`APP_ID` and `AppSecret`/`APP_SECRET`. Update `.env.example` and Compose
environment wiring when a runtime variable changes.

## Validation and error matrix

| Input or state | Result |
| --- | --- |
| Unknown engine or blank instance ID | `ConfigurationError` before adapter connection |
| Malformed ordinary feature TOML or unknown key | `FeatureFileError`, a `ConfigurationError` subtype |
| TOML percent value is bool, non-integer, or outside 0–100 | Reject at configuration loading |
| Invalid key type or unauthorized group override | Configuration failure; no silent coercion |
| Admin users outside global allowlist | Configuration failure |
| Enabled setu users outside global allowlist | Startup configuration failure |
| Group news push without groups enabled or outside group allowlist | Configuration failure |
| Personal news push outside user allowlist, or either push kind in official mode | Configuration failure |
| Empty global user allowlist | Startup can validate, but dispatcher denies every sender |

For new dedicated configuration, document missing-file, invalid-value, disabled,
and override behavior. Do not assume a new feature inherits group overrides.

## Storage contracts

| Data | Runtime/host location | Compose location and lifetime |
| --- | --- | --- |
| Private environment | `.env`, copied from `.env.example` | Only intentional runtime injection; ignored by Git |
| Private feature config | `config/features/<feature>/config.toml` | `/app/config`, read-only; reload through restart |
| SQLite application state | `KISARA_STATE_DIR`, default `data/kisara` | `/app/state`, `kisara_state` named volume |
| News PNG cache | news `cache_dir`, default `data/daily-news` | `/app/state/daily-news`, persistent state volume |
| Temporary external cache | `/tmp/kisara/<feature>/` for new features | Container-local; may disappear on recreation |
| Persistent external cache | `data/kisara/<feature>/cache/` when required | Needs an explicit writable bind mount; not automatically mounted |
| Confirmed setu files | `data/kisara/setu` | `/app/setu`, separate media bind mount |
| Optional tarot art | `data/kisara/tarotCards` | `/app/tarot-cards`, read-only for Kisara/NapCat |
| QQ login and NapCat config | `data/napcat/QQ`, `data/napcat/config` | `/app/.config/QQ`, `/app/napcat/config`; sensitive persistent data |

Daily news already uses `/tmp/kisara-daily-news-<uid>/` for temporary HTML;
retain that existing path unless a task deliberately changes it. `/tmp` is not
a database or permanent archive. Host `data/kisara` is not the Compose state
volume. New paths require host/container mapping, permissions, retention,
backup boundaries, and operations documentation.

Choose no database for independent stateless requests, bounded memory for
process-only deduplication, and feature-local SQLite under `KISARA_STATE_DIR`
when restart recovery or durable idempotency is required. There is no shared
ORM or general migration framework. Define columns, keys/indexes, transaction
boundaries, retention, completion timing, and upgrade/failure recovery for
schema changes. Use parameterized SQL and short-lived transaction connections.

Current examples: `NewsDeliveryStore.was_sent(day, group_id)` and
`mark_sent(day, group_id)` use `deliveries(day TEXT, group_id TEXT)` with a
composite primary key; only successful sends are marked. `SetuStore` separates
batch state from media files and records seen `(instance_id, message_id)` keys.
It already handles legacy state through `PRAGMA user_version`; do not assume
databases will be recreated on deployment.

## External requests and resumable cache

`HttpReader(timeout=10.0, max_bytes=2_000_000)` provides bounded UTF-8/JSON
reads and rejects redirects. Network/HTTP failures, oversized payloads, invalid
UTF-8, and invalid JSON become `RemoteServiceError`. Reuse that boundary or
document equivalent time, size, URL, redirect, and failure constraints.

Existing external providers do not all implement general resumable caching.
For new fetching/downloading work, define a stable key from normalized target
identity and result-affecting parameters; do not put secrets or full private
URLs in filenames. Reuse only complete, valid, unexpired content. Keep bounded
partial downloads plus metadata; use Range/ETag/Last-Modified only when server
semantics support safe reuse, otherwise restart and atomically publish the
validated full file. Coordinate concurrent requests for the same target.
Specify size limits, expiry, pruning, and sensitive-data access scope.

Cross-recreation cache requires an explicit durable mount and a recreation
check. Cross-machine reuse needs transfer/shared storage; local `/tmp` does
not provide it. `atomic_write_bytes(path, content)` publishes a complete file;
resume logic remains the downloader's responsibility.

## Privacy and deployment boundaries

Do not log message bodies, raw events, tokens, login QR codes, or persist
general chat history. The configured setu archive is an explicit opt-in
exception; its metadata, media, and backups remain sensitive. Inspect exception
text before logging so provider URLs and credentials do not leak. Use Python
logging as already configured in `bot/main.py`; protocol/application failures
must remain diagnosable without dumping private payloads.

OneBot stays inside the Compose network. NapCat WebUI defaults to loopback
and remote access uses an SSH tunnel. Optional music service has no host port.
Keep one Kisara runtime and one NapCat owner per QQ data directory; normal stop
retains login data and state. Hot reload restarts Kisara only. Cleanup must be
scoped to project labels/Compose project, never host-wide process or volume
cleanup. Image pinning and tested version pairs need a separate validated
change: current Compose defaults still use `latest` for external images.

## Cases, tests, and corrections

- Good: explicit TOML `false` overrides an older environment `true` value;
  a missing feature file falls back without enabling setu.
- Base: stateless `/roll` adds no database or runtime volume.
- Bad: writing a cache into the source tree, treating a partial file as a
  cache hit, or storing a database at an unmounted container path.

Configuration checks assert loading, precedence, rejection, and actual service
consumption. Storage checks cover first run, duplicates, reopening state,
partial failure, retry, and any changed upgrade path. Cache checks assert a
second target request avoids a duplicate fetch, interruption resumes or safely
restarts, and stale/corrupt data is fetched again. Verify sensitive media stays
out of resources and Git.

Wrong: mark a remote send complete before its receipt, or retry an unknown
send outcome automatically. Correct: record successful completion after the
confirmed result, distinguish known failure from unknown outcome, and define
retry/idempotency semantics for each side effect.

## Scheduled news to groups and private QQ recipients

### Scope and trigger

The OneBot daily-news loop supports both group and personal subscriptions. It
runs only while the WebSocket session is connected and uses one shared UTC+8
`push_time`, default 10:30. Private-only subscriptions must activate the factory
and scheduler even when group functionality is disabled.

### Signatures

- `Settings.news_push_users: FrozenSet[str]`, empty default, appended to the
  dataclass to preserve existing positional arguments.
- Existing group `NewsDeliveryStore.was_sent(day: str, group_id: str) -> bool`
  and `mark_sent(day: str, group_id: str) -> None` stay unchanged.
- Personal APIs: `was_private_sent(day: str, user_id: str) -> bool` and
  `mark_private_sent(day: str, user_id: str) -> None`.
- Additive DB table: `private_deliveries(day TEXT NOT NULL, user_id TEXT NOT
  NULL, PRIMARY KEY(day, user_id))`; deployed `deliveries` remains unchanged.

### Configuration, payload and state contracts

```toml
push_users = ["123456789"]
push_groups = []
push_time = "10:30"
```

`push_users` uses a string array of canonical positive ASCII decimal QQ numbers
(no leading zero), trimmed and deduplicated. Its explicit TOML value overrides
comma-separated `KISARA_NEWS_PUSH_USERS`, including `[]`; the fallback is passed
to both Compose bot services. Every recipient must be in
`KISARA_ALLOWED_USERS`. Group authorization remains independent.

The scheduler sends the same encoded `OutgoingMessage` to groups with
`send_group_msg/group_id` and to personal recipients with
`send_private_msg/user_id`. Use the existing API identifier conversion, do not
fabricate an incoming message. Content is generated once per pending iteration
through the executor. Each successful API receipt is recorded in its own table;
either mark method prunes both tables before the 30-day retention boundary.
Initialization uses `CREATE TABLE IF NOT EXISTS`, preserves old group records,
and supports repeated opening of the same database.

### Validation and error matrix

| Condition | Required behavior |
| --- | --- |
| Non-list, non-string/empty item, or non-canonical QQ number | Startup `ConfigurationError` or its `FeatureFileError` subclass |
| Personal recipient absent from global user allowlist | Startup `ConfigurationError`; no send |
| Only personal targets, groups disabled | Valid configuration; start one news task |
| Either target kind on official engine | Startup `ConfigurationError` |
| Both target lists empty | No scheduled news task |
| User and group have identical numeric ID | Independent completion in their respective tables |
| Known send failure | No completion record; continue other recipients and retry after 900 seconds |
| Remote result unknown or send succeeds before local checkpoint failure | Preserve existing retry semantics and possible duplicate limitation; do not promise exactly-once delivery |
| Disconnect | Cancel and await news task before starting another session's task |

Late connection sends today's unrecorded news only; earlier days are not
backfilled. Private failure logs must not include message payloads or recipient
numbers. Real QQ reachability requires separately authorized live acceptance.

### Good, base and bad cases

- Good: with groups disabled, subscribe allowed QQ `123456789`, receive one
  confirmed dated image and skip it after restarting on the same day.
- Base: group-only configuration and deployed group completion records retain
  their existing behavior.
- Bad: reuse the group table for a user with the same numeric ID, start private
  scheduling only when group targets exist, or bypass the global user allowlist.

### Required tests

Configuration tests assert TOML/env precedence, explicit empty override,
deduplication, canonical-number rejection, allowlist rejection, engine gating
and personal-only operation. State tests open an old group-only schema, retain
old records, isolate identical IDs by kind, reopen private state and prune both
tables. Scheduler/protocol tests assert due-time waiting, late catch-up, exact
private `user_id` and text/image payloads, shared factory invocation, isolated
partial failure/retry, recorded-success suppression, startup wiring and
cancel/reconnect without overlapping loops.

### Wrong versus correct

Wrong: check only `news_push_groups` at startup or mark a personal send in
`deliveries(day, group_id)`. Correct: enable one scheduler when either target
set is nonempty and checkpoint personal sends in `private_deliveries` only
after successful API responses.
