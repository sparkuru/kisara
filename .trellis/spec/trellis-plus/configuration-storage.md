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
`OFFICIAL_APP_ID` and `OFFICIAL_APP_SECRET` (legacy `AppID`/`APP_ID` and
`AppSecret`/`APP_SECRET` remain supported); Telegram requires
`TELEGRAM_BOT_TOKEN`. Telegram does not load unrelated QQ feature files or
group overrides. Update `.env.example` and Compose
environment wiring when a runtime variable changes.

## Engine-owned deployment environment

### 1. Scope / trigger

The shared repository dotenv can configure simultaneous engines. Its public
deployment names identify ownership; generic runtime names describe fields
inside one engine process. Keep that boundary explicit when adding settings.

### 2. Signatures

`COMPOSE_PROFILES=onebot,telegram` selects independent Compose services.
`Settings.from_environment() -> Settings` selects one runtime engine using
`KISARA_ENGINE`. `_engine_environment(source: Mapping[str, str], engine: str)`
returns a copied mapping for parsing and never modifies `os.environ`.

### 3. Contracts

Template blocks are deployment/shared services, OneBot/NapCat, Telegram, and
Official. `KISARA_MUSIC_IMAGE` configures shared optional infrastructure.
Engine-owned deployment fields use `ONEBOT_*`, `TELEGRAM_*`, or `OFFICIAL_*`;
NapCat retains `NAPCAT_*`. Keep `KISARA_ENGINE` as a documented explicit runtime
or preview override rather than a default deployment template assignment.

Compose maps `ONEBOT_ALLOWED_USERS`, `TELEGRAM_ALLOWED_USERS`, and
`OFFICIAL_ALLOWED_USERS` to each container's `KISARA_ALLOWED_USERS`; instance,
groups, switches and supported provider/news parameters follow the same rule.
OneBot accepts old `KISARA_*` deployment inputs when their new counterparts are
absent. Official credentials map `OFFICIAL_APP_ID/SECRET` to SDK
`AppID/AppSecret`, retaining the old deployment aliases. Other Compose engines
must not inherit OneBot deployment permissions or credentials.

New variables win by presence, including empty strings and false. Compose
unset-only interpolation is `${ONEBOT_ALLOWED_USERS-${KISARA_ALLOWED_USERS:-}}`.
Direct runtime settings resolve the selected namespace before validation and
retain generic runtime compatibility. A new empty Official credential must
suppress both mixed-case and uppercase SDK aliases. Explicit TOML still wins
over environment, including false, empty lists and empty provider URLs.

For setu ownership, helpers export the host group as `KISARA_HOST_GID`, leaving
new `ONEBOT_SETU_GID` and legacy `KISARA_SETU_GID` available to interpolation.
Do not export a default into a user input name and thereby mask dotenv values.
OneBot source/tianapi aliases are `ONEBOT_SAUCENAO_API_KEY` and
`ONEBOT_TIANAPI_KEY`; transport credentials retain existing OneBot names.

Local migration rereads the latest private file, backs it up with owner-only
permissions, preserves original assignment value syntax and custom settings,
and atomically replaces dotenv at mode 0600. Already-existing new keys win
over old aliases. Never use redacted historical files to overwrite credentials.
Environment changes require container recreation; restart alone keeps old env.

### 4. Validation and error matrix

| Input | Result |
| --- | --- |
| New name absent, legacy runtime/deployment value present | Compatible fallback |
| New allowlist empty, legacy allowlist nonempty | Empty list; no revival of access |
| New switch false, legacy switch true | False unless explicit TOML overrides |
| New required credential empty, legacy credential present | Startup validation fails |
| Other engine namespace present | Does not configure selected engine |
| Explicit TOML value present | TOML wins over new and old env values |

### 5. Good/base/bad cases

Good: migrate a QQ allowlist to `ONEBOT_ALLOWED_USERS` and preserve Telegram
token and its independent access list. Base: an old OneBot dotenv still works.
Bad: use non-empty fallback to restore old permissions after new fields were
explicitly cleared, or pass the complete dotenv to every Compose container.

### 6. Required tests

Settings tests cover selected namespace, unchanged process environment, legacy
fallback, explicit empty/false precedence, required credential alias suppression
and TOML precedence. Deployment tests cover actual synthetic interpolation,
engine-specific credentials/access, host ownership fallback and targeted
lifecycle. Privately compare effective engine environments across migration;
never print secret-bearing rendered Compose output. Use offline project checks
without loading private dotenv or contacting bot APIs.

### 7. Wrong versus correct

Wrong: `${ONEBOT_ALLOWED_USERS:-${KISARA_ALLOWED_USERS}}` revives a legacy list
when the new one is deliberately empty. Correct: use unset-only fallback and
validate the resulting runtime field after selected-engine resolution.

## Setu transfer size settings

### 1. Scope / trigger

The private `config/features/setu/config.toml` and its `.example` set transfer
caps for the OneBot setu archive. Load once at startup through `SetuConfig.load`.

### 2. Signatures

`SetuConfig.load(path: Path) -> SetuConfig` parses the TOML file.
`SetuConfig.max_file_bytes` and `max_batch_bytes` are byte integers consumed by
the media saver; the TOML source values are size strings.

### 3. Contracts

`max_file_bytes = "100M"` and `max_batch_bytes = "1G"` preserve the default
100 MiB and 1 GiB caps. A size is a positive whole number followed immediately
by `K`, `M`, or `G` (case insensitive); each unit uses a 1024 multiplier.
Omitted settings use these defaults. A missing setu config disables the feature.

### 4. Validation & error matrix

| Input | Startup behavior |
| --- | --- |
| `"10M"`, `"1G"`, `"1024K"` | Convert to byte integers |
| TOML integer, boolean, zero, negative, fraction, unknown unit, or whitespace | `ConfigurationError` naming the invalid field |
| Converted batch cap below file cap | `ConfigurationError` |

### 5. Good / base / bad cases

Good: `"2M"` and `"1G"` load as byte limits. Base: omit both keys and receive
100 MiB / 1 GiB. Bad: leave an old unquoted `104857600` value; startup rejects
it rather than silently guessing units.

### 6. Tests required

`tests/unit/test_setu_config.py` checks conversions, defaults, invalid source
types and strings, and the converted batch-versus-file relation.
`tests/unit/test_setu.py` checks the media saver against byte limits.
Tests of environment defaults should change to `tmp_path` before loading
settings, so private `config/features/*/config.toml` files in the repository
cannot change their expected input.

### 7. Wrong versus correct

Wrong: parse size strings in the media saver or accept old TOML integers.
Correct: validate and normalize sizes once in `SetuConfig.load`, then pass byte
integers to the service.

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
| Telegram user ID not positive canonical decimal, or group ID not negative canonical decimal | Configuration failure |
| Empty global user allowlist | Startup can validate, but dispatcher denies every sender |

For new dedicated configuration, document missing-file, invalid-value, disabled,
and override behavior. Do not assume a new feature inherits group overrides.

## Retained-feature switches

`Settings.ping_enabled`, `help_enabled`, `music_enabled`, `news_enabled`, and
`news_push_enabled` default to true. `config/features/ping/config.toml`, help,
and music accept `enabled`; news accepts `enabled` and `push_enabled`. Explicit
TOML booleans override `KISARA_PING_ENABLED`, `KISARA_HELP_ENABLED`,
`KISARA_MUSIC_ENABLED`, `KISARA_NEWS_ENABLED`, and `KISARA_NEWS_PUSH_ENABLED`.
Missing keys preserve environment/default fallback. Invalid values fail startup.
Manual news and push are independent; no recipients means no scheduler.
Apply TOML changes through a targeted bot restart. Apply `.env` container
environment changes through targeted recreation (`./deploy.sh up telegram`);
Compose restart retains the previous container environment.

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

Setu archive-specific filename, collision, and publication contracts live in
[Setu archive storage](setu-storage.md); load that document when changing or
reviewing archive placement. General configuration/state contracts stay here.

## Telegram news delivery journal

### 1. Scope / trigger

Telegram scheduled private/group news needs durable evidence before a remote send.
One runtime owns its state directory; transactions never span generation/network
work. Isolate state and news caches between engine containers.

### 2. Signatures

`TelegramNewsStore(state_dir)` uses `telegram_news.sqlite3`.
`claim(day, kind, target, now) -> bool`, `complete(day, kind, target, message_id)`,
`reject(day, kind, target, next_attempt, permanent=False)`,
`uncertain(day, kind, target)`, `prune(day)`, and `status(day, kind, target)` own
persistence. `TelegramNewsPush(...).deliver_due()` coordinates the gateway.

### 3. Contracts

`deliveries` columns are `day TEXT`, `kind TEXT`, `target TEXT`, `status TEXT`,
`next_attempt REAL DEFAULT 0`, and nullable `message_id TEXT`, with primary key
`(day, kind, target)`. Day is the scheduled UTC+8 day; kind separates private and
group recipients. States are pending, claimed, retry, rejected, confirmed, and
uncertain. Claim is atomic before sending. Startup changes leftover claimed rows
to uncertain. Only a confirmed remote receipt advances claimed to confirmed.
Unknown outcomes and local completion failures never become new work. Known
transient rejection or generation failure retries after 15 minutes or a longer
server retry-after; permanent rejection stops for that day. Retention uses the
current day minus 30 days. Catch-up is for today only. A successfully sent warned
publication-delay fallback completes today's scheduled send.

### 4. Validation & error matrix

| Event | Evidence / recovery |
| --- | --- |
| Existing confirmed, rejected, uncertain or claimed row | Claim denied |
| New target or due retry | Claim before send |
| Timeout/network result unknown | Uncertain; no automatic resend |
| Cancellation after claim | Claim survives; restart makes it uncertain |
| Remote success followed by failed completion write | Claim evidence retained; no automatic resend |
| Generation fails before remote operation | Known retry; no confirmed completion |

### 5. Good / base / bad cases

Good: checkpoint the returned message ID, restart, and skip the confirmed target.
Base: no recipients creates no scheduled work. Bad: mark only after sending while
leaving no prior evidence, allowing a crash to replay an already delivered message.

### 6. Tests required

Verify atomic claims, private/group key separation, confirmed restart, interrupted
claim recovery, retry deadlines, permanent rejections, unknown sends, failed local
completion writes, cancellation, retention, today-only catch-up, and successful
fallback completion. Inject safe synthetic errors without real credentials.

### 7. Wrong versus correct

Wrong: retry every SDK exception or fall back from an unknown document send to a
photo send. Correct: classify known rejection separately, retain uncertain send
evidence, and leave manual `/news` available.

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

Compose engine profiles are `onebot`, `onebot-dev`, `telegram`, and `official`;
`music` is optional infrastructure. `.env` `COMPOSE_PROFILES=onebot,telegram`
selects concurrent containers. `deploy/engines.sh <action> [profile,...]` powers
the unified entrypoints, with a compatible OneBot fallback when no selection is
configured. Reject simultaneous onebot/onebot-dev owners. Each container runs
one `KISARA_ENGINE` and receives explicit environment mappings, never the entire
shared `.env`. Telegram's namespaced deployment access/feature fields map to
runtime `KISARA_*` fields and `TELEGRAM_BOT_TOKEN`. Its read-only configuration
mount is `config/telegram:/app/config` and its independent `telegram_state` volume
is mounted at `/app/state`; official uses config/official and official_state.

`stop`/`down`, restart, logs, and rebuild through explicit targets affect only
selected engines. `down-all` is the explicit whole-project operation. Changing
profile selection does not stop previously running engines. Ordinary stop keeps
volumes. Validate profile selection and credential isolation with placeholders,
never by printing rendered real secret-bearing configuration.

Do not log message bodies by default, raw events, tokens, login QR codes, or
persist general chat history. Explicit `TELEGRAM_MESSAGE_LOG_ENABLED=true`
permits bounded, escaped, token-redacted Telegram previews and IDs under the
[logging contract](../backend/logging-guidelines.md#opt-in-telegram-receivesend-summaries).
The configured setu archive is an explicit opt-in
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

## Daily news publication-delay fallback

### Scope and trigger

Applies to /news aliases and scheduled generation when today's LyToday page
prepends 今天的简讯未更新，下面是昨天的简讯！ to yesterday's 15 headlines.
The user approved clearly labeled yesterday content during publication delays.

### Signatures

`_page_for_today(html: str, today: date) -> DailyPage` validates the page;
`DailyPage.notice: str = ""` stores the optional source warning.
`DailyNews.get() -> DailyNewsResult` supplies `.text` and `.onebot_image()` to
existing callers. Result fields are `day: date`, `image_path: Optional[Path]`,
`image_bytes: bytes = b""`, and `notice: str = ""`. Published results retain the
dated path; fallback results use `image_path=None` and immutable PNG bytes:

```python
DailyNewsResult(today, None, image_bytes=bytes(image), notice=page.notice)
```

### Contracts

Remove exactly one recognized news-list notice before checking the 15 actual
headlines; duplicate notices remain invalid. Preserve the notice separately
and display it prominently in the PNG and result text for both engines.
The page header must still match the requested China Standard Time date.

Fallback results retain immutable image bytes with no reusable disk image.
Do not write fallback dated HTML or PNG. Discard cached fallback HTML and
refetch rather than returning it. Subsequent requests refetch until publication,
then resume normal atomic dated caching. Cache clearing or later requests must
not alter previously returned fallback bytes.

Scheduled successful fallback sends count as that day's completed delivery.
Do not automatically resend after publication; users can request /news manually.
Keep failure retry, authorization, and existing delivery tables unchanged.

### Validation and error matrix

| Source state | Outcome |
| --- | --- |
| Current header, one recognized notice, 15 valid actual headlines | Handled labeled fallback text/PNG; no dated cache publication |
| Stale/invalid header | Existing freshness/date failure |
| Current page without notice and 15 valid headlines | Normal dated render/cache/reuse |
| Duplicate notices or extra/missing/empty/oversized actual headlines | Invalid-headlines failure |
| Cached HTML with notice | Discard and refetch before rendering |
| Successful scheduled fallback send | Record completion; no second scheduled send that day |

### Good, base, and bad cases

Good: two fallback requests each fetch; after publication, a third caches fresh
news while prior results keep their own bytes. Base: fresh content reuses a
dated PNG. Bad: cache yesterday's fallback under today's reusable filename or
let an earlier result point at a fallback file another request overwrites.

### Required tests

News tests assert handled image/text warnings, 15 valid actual headlines,
malformed rejection, no fallback cache publication, repeated refetch, cached
fallback recovery, byte isolation, and publication recovery. Verify PNG warning
drawing as well as source attribution. Scheduler tests assert fallback payload
and durable once-per-day completion. Permanent fixtures use synthetic headlines.

### Wrong versus correct

Wrong: reject a valid warned page as unavailable, silently drop the warning,
or persist yesterday's brief as today's normal cache.
Correct: preserve/display the warning, render validated actual headlines,
return immutable fallback bytes, and refetch on later manual requests.

## Manual current-day news cache clearing

### Scope and trigger

`清除新闻缓存` is a shared news command, normalized to `/news-clear`.
It works for globally allowed senders in private conversations and enabled,
allowed groups, including when chat is disabled. Authorization and message
deduplication precede cache access; no separate admin policy applies.

### Signatures

`DailyNews.clear_cache() -> bool` returns whether either current-day cache file
was removed. The route accepts no arguments and returns a handled text reply
for both removed and empty outcomes.

### Contracts

Determine the date in UTC+8, then unlink only `<cache_dir>/YYYYMMDD.png` and
`<temp_dir>/YYYYMMDD.html` under the same service lock as `get()`. Do not create
directories, fetch news, or render during clearing. Validate any existing
temporary directory's owner, restrictive mode, and non-symlink directory type
before deleting either file. Missing files/directories are normal empty state.
Preserve historical/unrelated files and scheduled delivery SQLite records.
The next news request fetches and renders again: deleting only the PNG would
reuse stale HTML. Clearing a shared cache affects all users of that service.

### Validation and error matrix

| Condition | Outcome |
| --- | --- |
| At least one dated file removed | `handled`, cleared confirmation |
| Both dated files missing | `handled`, empty-cache reply |
| Command arguments present | `CommandInputError`, no deletion |
| Unauthorized sender/group or duplicate message | `unhandled`, no cache access |
| Existing temporary directory unsafe | `RemoteServiceError`, no deletion |
| Filesystem deletion failure | `RemoteServiceError`, no successful confirmation |

Deletion is not a transaction across two files: an I/O failure after the first
unlink can leave partial clearing. Report the error and allow a fresh clearing
request to retry; never reset scheduled delivery records as recovery.

### Good, base, and bad cases

Good: clear both layers after a news request, then obtain updated content with
a new fetch. Base: clear before first use and receive an empty-cache reply.
Bad: delete all PNGs or reset sent records to force news regeneration.

### Required tests

`tests/unit/test_daily_news.py` must assert two-layer deletion and a subsequent
provider refetch, empty/idempotent and single-layer states, UTC+8 date selection,
preservation of older/future/unrelated files, allowed/rejected group and sender
events, duplicate suppression, argument errors, unsafe directories, deletion
failures, and enabled-feature help visibility.

### Wrong versus correct

Wrong: implement deletion in the adapter, skip allowlists, or delete only PNG.
Correct: normalize the phrase in shared routing and call `DailyNews.clear_cache()`
after authorization, with both dated paths owned by the service.

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
