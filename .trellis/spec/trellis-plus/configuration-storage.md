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
| News push without groups enabled, in official mode, or outside group allowlist | Configuration failure |
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
