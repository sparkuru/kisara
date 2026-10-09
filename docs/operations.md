# Running Kisara

## Quick start

Common development and runtime commands are:

```bash
./dev.sh              # Interactive offline bot console; no QQ connection or .env needed
./dev.sh --test       # Automated offline functional tests
./dev.sh --all        # Full test suite
./preview.sh          # Prepare missing preview resources, start detached, wait for readiness
./preview.sh status   # Inspect preview state/readiness; no preparation or startup
./preview.sh build    # Explicit preview rebuild; stop an existing preview group first
./preview.sh stop     # Remove only preview-owned containers, preserving storage
./deploy.sh           # Build/start .env-selected engines in the background
./deploy.sh logs      # Follow deployment logs
./deploy.sh down      # Stop the deployment, preserving QQ login data
```

The offline console accepts messages such as `/help`, `/chat hello`, `/eat`, and `/roll 20`
and prints replies from the same dispatcher used by the real bot. It simulates
an allowed private-chat user without loading `.env` or connecting to an engine.
Use `/quit`, `/exit`, Ctrl-D, or Ctrl-C to exit. Source changes take effect after
restarting the console.
The console supports Up/Down for session history, Left/Right for cursor movement,
Ctrl-Left/Right for word movement, Home/End, Delete, and Ctrl-A/E/U/K editing.
History is kept in memory only and is cleared when the console exits.
Each turn shows `[time]` with a timezone offset, `you >` and `kisara >` message
labels, and `[last]` with completion time and dispatch duration in milliseconds
(excluding time spent typing). Multiline replies are indented and turns are
separated by a line spanning the current terminal width (80 columns if unavailable).
`[status] HANDLED` (green) means a command ran successfully; `UNHANDLED`
(yellow) means the message was only received or filtered; `ERROR` (red) means
invalid command arguments or an execution failure. The console remains open
after a command fails, and status labels remain visible without color.

These scripts reuse the existing Docker toolchain. Tests require the development
dependencies installed below. Preview and deployment require a configured
`.env`. Preview also supports `KISARA_ENGINE=official` and
`KISARA_ENGINE=onebot-dev` or `telegram`; deployment follows `COMPOSE_PROFILES`.
See the Compose/Telegram section below for multiple engines and targeted operations.

The project runs its Python toolchain in Docker. Preview requires Bash 4.4+,
Docker/Compose and standard lifecycle tools listed by `./preview.sh --help`;
`ip` is additionally required for local wildcard publishing. Python, pip and
bot SDKs stay inside the existing images/ephemeral containers managed by `hako`.

The existing QQ runtime paths are:

- `onebot`: `start.sh` starts the Kisara + NapCat Compose stack.
- `onebot-dev`: `start.sh` starts the OneBot stack with source hot reload
  for Kisara development.
- `official`: `start.sh` keeps the existing Tencent official bot path.

1. Only if `.env` is absent, copy `.env.example` to `.env`, then configure the selected engine. For
   OneBot, set `ONEBOT_WS_URL`, `ONEBOT_ACCESS_TOKEN`, and at least one ID in
   `ONEBOT_ALLOWED_USERS`. For the official engine, set `OFFICIAL_APP_ID`,
   `OFFICIAL_APP_SECRET`, and `OFFICIAL_ALLOWED_USERS`. Telegram needs
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USERS`. Copy desired feature
   examples to `config.toml` beside each example: OneBot uses
   `config/features/<feature>/`, Official Compose uses
   `config/official/features/<feature>/`, and Telegram uses
   `config/telegram/features/<feature>/`. Direct Official hako preview retains
   its existing root `config/features/<feature>/` path.
2. For local tests, install the project and development dependencies:

   ```bash
   ./hako python -m pip install --user -e ".[dev]"
   ```

   If tests exercise the official engine, include its optional dependency:

   ```bash
   ./hako python -m pip install --user -e ".[dev,official]"
   ```

   Preview itself prepares only missing images/pinned runtime dependencies after
   configuration. It never runs tests or installs the development extra. First
   preparation can download resources and take several minutes. Set
   `KISARA_PREVIEW_OFFLINE=true` to prohibit automatic preparation; arrange the
   documented image/dependency prerequisites explicitly while online first.

3. Start the configured preview:

   ```bash
   ./preview.sh
   ```

   Alternatively `./start.sh` retains engine selection. With no profile selection,
   its interactive menu selects `onebot`, `onebot-dev`,
   `official`, or `telegram`. It
   can also be chosen directly with `./start.sh onebot`,
   `./start.sh onebot-dev`, `./start.sh official`, or
   `KISARA_ENGINE=onebot ./start.sh`. In non-interactive environments the
   default is `onebot` when profiles are absent. `.env` `COMPOSE_PROFILES`
   selects concurrent Compose engines automatically.

4. Stop the bot and remove its development container:

   ```bash
   ./preview.sh down
   ```

The Kisara bot process does not expose a public application HTTP port.
Preview returns after bounded readiness and prints one summary using actual
service listeners/published mappings. Outbound-only engines have no browser URL.
Loopback NapCat access and SSH tunneling remain the default; wildcard addresses
are candidates, not proof of access from another device. Initial NapCat login
and external gateway/network readiness may require user action; failed startup
reports diagnostics and never prints a ready banner.

Healthy, identically configured preview instances are reused. Existing deployment
containers, incomplete/unhealthy groups and changed preview configuration require
explicit recovery; preview does not silently replace them. Stop with
`./preview.sh stop`, then use `build` and `start` when configuration/dependencies
require recreation. Never remove login directories or state volumes as recovery.
Stopping preview does not depend on host-address discovery. OneBot preview
rejects empty/example access tokens before preparation. Telegram preview becomes
ready only after a successful poll while its application is running.

Preview help/status/stop/down do not build, install or start services; verbose
details are captured then redacted, not raw streaming. For deployment logs use
`./deploy.sh logs`; for one-off commands use `./hako`.

For the OneBot runtime, use `./deploy/onebot.sh` instead of a standalone
`hako` bot container so Kisara and NapCat share the same Compose network.

```bash
./hako python --version
./hako python -m pytest
./deploy/onebot.sh ps
```

## Environment ownership and compatibility

The dotenv template groups deployment/shared services, OneBot with NapCat,
Telegram, and Tencent Official. Set the credentials and allowlists in the
selected engine's block:

| Owner | Deployment inputs |
| --- | --- |
| Deployment / shared provider | `COMPOSE_PROFILES`, `KISARA_MUSIC_IMAGE` |
| OneBot | `ONEBOT_INSTANCE_ID`, `ONEBOT_ALLOWED_USERS`, `ONEBOT_ADMIN_USERS`, `ONEBOT_GROUPS_ENABLED`, `ONEBOT_ALLOWED_GROUPS`, `ONEBOT_WS_URL`, `ONEBOT_ACCESS_TOKEN` |
| NapCat / QQ login | `NAPCAT_*` image, device identity, login, WebUI and ownership settings |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_INSTANCE_ID`, `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_GROUPS_ENABLED`, `TELEGRAM_ALLOWED_GROUPS` |
| Tencent Official | `OFFICIAL_APP_ID`, `OFFICIAL_APP_SECRET`, `OFFICIAL_INSTANCE_ID`, `OFFICIAL_ALLOWED_USERS`, `OFFICIAL_GROUPS_ENABLED`, `OFFICIAL_ALLOWED_GROUPS` |

Instance IDs are internal runtime namespaces, not platform account IDs or bot
names. Feature flags and music provider URLs also belong to each engine; a
shared music service does not automatically set any engine's API URL.
Telegram's retained commands currently do not use administrator privileges;
`TELEGRAM_ADMIN_USERS` may remain empty. Official has no scheduled news push.

Compose maps each block to its container's existing `KISARA_*` runtime fields;
credentials, access IDs, mounts and state remain independent. `KISARA_ENGINE`
is a direct-runtime/preview override and is not assigned in the Compose
configuration template. It does not select multiple containers. Direct
`Settings` loading also resolves the selected engine's names without changing
process environment or the existing preview topology/configuration paths.

Old OneBot deployment `KISARA_<suffix>` fields remain fallbacks for
`ONEBOT_<suffix>`, including chat/tarot/news/music settings and
`ONEBOT_WATCH_INTERVAL` / `ONEBOT_SETU_GID`. `KISARA_MUSIC_IMAGE` stays shared.
Advanced provider aliases `ONEBOT_SAUCENAO_API_KEY` and `ONEBOT_TIANAPI_KEY`
fall back to `SAUCENAO_API_KEY` and `TIANAPI_KEY`; prefer their feature TOML.
Official credentials fall back to `AppID` / `AppSecret` (direct loading also
retains `APP_ID` / `APP_SECRET`). New names win by presence: an explicit empty
allowlist revokes that access, and an empty new credential fails validation
rather than falling back to an older credential. Empty booleans retain parser
defaults, while explicit `false` disables the corresponding flag.

For private file migration, back up the latest `.env`, rename only assignment
keys, preserve their value syntax and custom inputs, and retain an existing new
key if both aliases are present. Do not overwrite filled values with template
placeholders or a redacted historical file. Template additions should not
mask custom old inputs. Keep the resulting `.env` private and ignored by Git.

Explicit feature TOML keys take precedence over both new and legacy environment
values, including `false`, empty lists and an empty music URL. To use `.env`
for a setting, omit that key from the engine's TOML; copying an example with
`push_users = []` makes the environment recipient list ineffective. Apply
`.env` changes by targeted recreation (`./deploy.sh up telegram` or
`./deploy.sh up onebot`); `restart` keeps the previous container environment.

## OneBot deployment

The normal OneBot path is implemented as a two-service Compose stack:

- `napcat` runs NapCatQQ, owns QQ login state, and exposes the OneBot 11
  forward WebSocket only inside the Compose network.
- `kisara` is built from `deploy/Dockerfile` and connects to
  `ws://napcat:3001`.

Prepare the configuration and start it:

```bash
cp .env.example .env
# Edit at least ONEBOT_ALLOWED_USERS and ONEBOT_ACCESS_TOKEN.
# A URL-safe token can be generated with: openssl rand -hex 32
./start.sh onebot
```

The deployment entrypoint writes NapCat's `onebot11.json` from the same
`ONEBOT_ACCESS_TOKEN`, so the Kisara and NapCat tokens stay synchronized.
QQ login is still a manual first-run step. NapCat state is persisted in
`data/napcat/QQ` and its configuration in `data/napcat/config`; stopping the
stack does not remove these directories.

Preview and deployment use the same Compose project (`kisara` by default),
NapCat service, and login directories. NapCat's hostname and MAC address are
fixed by `NAPCAT_HOSTNAME` (default `kisara-qq`) and `NAPCAT_MAC_ADDRESS`
(default `02:42:0a:a0:d0:02`). Keep these values and `COMPOSE_PROJECT_NAME`
consistent when switching between `./preview.sh` and `./deploy.sh`.
Do not run separate NapCat instances against the same QQ data directory.

These settings take effect when Compose next recreates NapCat; adopting a new
hostname may require one more QR login. Stable hostname, MAC, and persisted
login data reduce device changes but do not guarantee that QQ will never ask
for authentication again. Set `NAPCAT_ACCOUNT` to the intended QQ account for
the image's quick-login startup path. For multiple independent instances,
choose a different MAC and separate login data for each instance.

The NapCat WebUI is bound to `127.0.0.1:6099` by default. On a remote PVE
host, use an SSH tunnel and open `http://127.0.0.1:6099/webui` locally:

```bash
ssh -L 6099:127.0.0.1:6099 pve
```

Useful operations:

```bash
./deploy/onebot.sh logs
./deploy/onebot.sh ps
./deploy.sh down
```

The WebUI binding can be changed with `NAPCAT_WEBUI_BIND` and
`NAPCAT_WEBUI_PORT`. Do not expose the WebUI or the OneBot port publicly
without an explicit access-control plan; the OneBot port is intentionally
not published to the host.

For active Kisara development, use the `onebot-dev` path:

~~~bash
./start.sh onebot-dev
~~~

This mode mounts the local `src/` directory into a separate `kisara-dev`
service. Changes to Python source files restart only the Kisara process;
NapCat and the persisted QQ login state are not restarted. The watcher is a
polling development helper, so changes to `pyproject.toml`, `Dockerfile`,
or other image contents still require starting the mode again so the image
can be rebuilt. Set `ONEBOT_WATCH_INTERVAL` in `.env` to adjust the
polling interval.

Switch back to the normal image-based runtime with:

~~~bash
./preview.sh down
./start.sh onebot
~~~

## Feature operations

Daily news reads the dated HTML from `https://60s.lylme.com/` on a cache miss.
The validated source page is temporarily kept in `/tmp/kisara-daily-news-<uid>/`;
the generated PNG is retained under the news `cache_dir` setting. In Compose,
that image directory is `/app/state/daily-news` in the persistent `kisara_state`
volume. `cache_days` in `config/features/news/config.toml` controls PNG retention.
Older temporary HTML is pruned on the next HTML fetch or cleared by `/tmp`.
When today's page says `今天的简讯未更新，下面是昨天的简讯！` above 15 valid
headlines, `/news` sends that yesterday brief with the original warning in its
text and prominently above the PNG's headlines. The reply and image distinguish
the page date from headline freshness; official-engine replies include the
warning as text. Fallback results own immutable image bytes in memory, so no
fallback dated HTML or PNG is cached, and later requests or cache clearing
cannot change an earlier result. Each fallback request refetches the provider.
After publication, `/news` caches the fresh brief normally without manual
clearing. Cached fallback or invalid HTML is discarded and fetched again.
Stale page dates still return `Today's daily news is not yet available.`;
duplicate notices and malformed or incomplete actual headline lists are errors.
The image includes the page's headlines, hot lists, history, almanac, and quote.
Set `font_paths` in the same feature file to an ordered list of font files;
the first CJK-capable path inside the container is used, then bundled Noto CJK
fonts are tried. A layout version change
regenerates older images automatically. After changing fonts, remove that day's
cached PNG to regenerate it.

Send `清除新闻缓存` to remove only the current China Standard Time day's
`YYYYMMDD.png` and temporary `YYYYMMDD.html`. Surrounding whitespace and the
optional `#` prefix are accepted; arguments are rejected. The command uses
the existing user/group allowlists in private messages and enabled, allowed
groups, including when chat is disabled. It confirms removal or reports that
no current-day cache exists. Clearing does not fetch, render, or send news;
the next `/news` request fetches a fresh page and regenerates the image.
Historical files and scheduled delivery records are preserved, so clearing
does not cause completed scheduled pushes to resend. Unsafe temporary cache
directories and filesystem failures return an error; retry after correcting
the underlying permissions or storage problem.

For scheduled OneBot news, copy `config/features/news/config.toml.example` to
`config/features/news/config.toml` if needed and configure personal QQ numbers
as strings:

```toml
push_groups = []
push_users = ["123456789", "987654321"]
push_time = "10:30"
```

Add each personal recipient to `ONEBOT_ALLOWED_USERS` in `.env`. Numbers must
be positive decimal strings without leading zeros. Private push works with
`ONEBOT_GROUPS_ENABLED=false`; configured groups still require enabled groups
and membership in `ONEBOT_ALLOWED_GROUPS`. Both target kinds share `push_time`
in UTC+8 (default 10:30), and scheduled push requires the OneBot engine.
An empty `push_users` disables private push; an empty `push_groups` disables
group push. Without the TOML key, `ONEBOT_NEWS_PUSH_USERS` provides a
comma-separated fallback; explicit TOML values, including `[]`, take precedence.
Restart Kisara through the normal deployment path after configuration changes;
the running process does not reload feature configuration.

The connection owns one news loop. At the due time it sends the same dated
text and image to pending groups and users. It records only confirmed successes
in `news_delivery.sqlite3` under `KISARA_STATE_DIR` (Compose `/app/state` in
`kisara_state`). Group `deliveries` and `private_deliveries` are separate, so
equal user/group numbers do not collide. Initialization preserves old group
records; completion writes prune both tables beyond 30 days. Failed or
unrecorded targets retry after 15 minutes without resending recorded successes.
Successfully sending the labeled yesterday brief counts as today's completed
delivery. It does not trigger a second scheduled push after publication;
request `/news` manually to retrieve updated content.
Late startup catches up today's news only. Disconnect cancels the task, and
reconnect consults durable state. An unknown remote result or failed local
completion write may still lead to duplicate delivery.

For live acceptance, use an allowed QQ recipient the logged-in account can
contact, set a shared time a few minutes ahead, restart Kisara, and confirm the
dated image arrives in that private chat. After receipt, restart Kisara again
on the same day and confirm no extra news arrives. When configured, group
delivery should still arrive at the shared time. Restore the intended schedule
afterward. Simulated protocol tests do not prove actual QQ reachability.
When rolling back to an older version, remove `push_users` from runtime TOML
before startup; the added private table can remain alongside the group table.

For the setu archive, Compose maps `data/kisara/setu` to `/app/setu` and keeps
SQLite state in the `kisara_state` volume. The startup wrapper prepares the
host directory. With direct Compose usage, create and grant group access first:

```bash
mkdir -p data/kisara/setu
chmod 2770 data/kisara/setu
```

Set `ONEBOT_SETU_GID` to the output of `id -g` when the host's primary group ID
is not 1000. After saving, inspect files with `ls -lah data/kisara/setu` or:

```bash
docker compose --env-file .env -f deploy/compose.yaml --project-name kisara exec kisara ls -lah /app/setu
```

Quoted ordinary file messages and merged forwards can include archive attachments (`tar`, `tar.gz`,
`tgz`, `zip`, `7z`, `rar`, `tar.bz2`, `tbz2`, `tar.xz`, `txz`, `tar.zst`, and
`tzst`). They use the existing private `/setu` confirmation or direct-save flow
and count as files in the prompt. Archives keep their original names in either
save mode; a name already occupied by different content produces
`original_timestamp.ext` in the same directory, with compound extensions intact
(for example `backup_20261009-153000-123456.tar.gz`). Matching archived content is
reused. Timestamp suffixing applies only to these archive file attachments;
images, videos, audio, and other files retain their existing rules.

For an ordinary file, send it as a file message in an authorized private chat,
then quote that message with `/setu` and confirm the prompt, or quote it with
直接保存. Plain file messages without a quoted save command do not auto-save.
The new entry accepts file-kind segments, including generic files with their
existing placement; it does not add Setu saving for plain image/video quotes.
After confirmation or 直接保存, the bot first replies with a start notice such
as `正在保存以上 2 个文件、1 个视频、3 张图片。`, then performs the transfer and
sends 归档完成 with saved/failed counts. Retry notices count only unfinished
attachments. The notice is informational; use the existing confirmation prompt
or direct failure result to select a retry.
This route avoids merged-forward retrieval, but actual native ordinary-file
download depends on the selected NapCat runtime. Local sources must resolve
inside `local_media_root` under approved QQ media directories. Explicit file
attachments can also use direct files in `NapCat/temp`, where the inspected
runtime places ordinary native downloads; other NapCat directories and nested
temp paths remain rejected.

If the downloaded native file is owner-only (`0600`) and the OneBot container
cannot read it, file attachments use NapCat's bounded `download_file_stream`
interface over the existing authenticated WebSocket. Chunk order, sizes and
completion totals are checked before publication; binary copies keep the same
archive naming and size limits. No account-directory chmod or global base64
setting is needed.

After a failed batch's retry window expires, quote the original file/forward
message again with `/setu` to get a fresh prompt, or with 直接保存 to resume
immediately. The existing batch and saved items remain; only failed items are
retried. Quoting an expired old prompt/result alone does not renew consent.
Repeated completed sources and active saves have distinct status replies.

Archive bytes are saved without extraction. Existing source restrictions,
per-file/batch limits, and failed-item retries still apply. Archive detection
uses filename suffixes; opaque IDs without original-name metadata cannot
establish an archive type or its original name. Invalid archive names produce
item failures instead of silently sanitized names. No private configuration or
historical-file migration is required for this feature.

NapCat file segments may expose the original name in `file` and a different
canonical lookup key in `file_id`. Kisara keeps those roles separate. Without
a supplied URL, `get_file` waits for the complete NapCat download; file requests
therefore use a separate bounded response wait of 125–1805 seconds based on
reported size, while ordinary chat requests keep their short deadline. This
does not extend NapCat's own native transfer timeout. Request failures log safe
action/reason/retcode details without raw file IDs or URLs.
If a failed file save outlasts its original confirmation window, its result
opens one configured retry window from completion. Unstarted confirmations,
short failures, and image-only batches keep their existing deadlines.

A failed native transfer is not a successful archive save. The inspected NapCat
4.18.28 runtime returned `get_file` retcode 1200 after 120 seconds for one
private forwarded archive, and its private URL action could not resolve that
file. Longer Kisara waits alone do not repair an unavailable native forward
resource. HTTPS/cache protections remain effective; raw HTTP links and arbitrary
NapCat temporary paths are not accepted as an automatic workaround.

The optional music API runs only on the Compose network. Set
`api_url = "http://music:3000"` in `config/features/music/config.toml` and start
its profile with:

```bash
docker compose --env-file .env -f deploy/compose.yaml --profile music up -d music
```

Offline functional scenarios use the same normalized dispatcher as the bot:

```bash
./hako python -m pytest tests/unit/test_offline_commands.py
```

## References

1. QQ Bot official documentation: <https://bot.q.qq.com/wiki/>
2. Tencent `botpy` SDK: <https://github.com/tencent-connect/botpy>
3. NapCat Docker: <https://github.com/NapNeko/NapCat-Docker>
4. NapCat network configuration: <https://napneko.github.io/config/basic>

## Compose engines and Telegram

Set `COMPOSE_PROFILES` in the repository `.env` to choose startup engines:

```dotenv
COMPOSE_PROFILES=onebot,telegram
```

Supported profiles are `onebot`, `onebot-dev`, `telegram`, `official`, and
optional `music`. Choose one OneBot owner (`onebot` or `onebot-dev`) per QQ
login/state directory. The helper rejects selecting both. Direct Compose users
must also avoid starting both. Missing profile selection keeps the original
OneBot default in the helpers. Each bot container runs a single `KISARA_ENGINE`;
profiles determine which containers start. Changing the profile list does not
stop an already running engine.

```bash
./start.sh                 # Select/start preview; explicit argument/env overrides
./deploy.sh                # Build/start the selected engines in the background
./deploy.sh up telegram    # Build/recreate Telegram only
./deploy.sh down telegram  # Stop Telegram only; keep QQ and all volumes
./deploy.sh restart telegram
./deploy.sh logs telegram
./deploy.sh ps
./deploy.sh down-all       # Explicit whole-project shutdown; retains volumes
```

`./preview.sh` follows profile selection unless `KISARA_ENGINE` explicitly
overrides it. `./start.sh onebot` and `./start.sh onebot-dev` retain QQ selection
through the existing engine lifecycle; `./start.sh official` retains the hako
configuration path with detached preview ownership. Compose
`official` is an additional independent deployment path.
`./deploy/onebot.sh down` now stops only QQ services. Logs/status operations in
that helper are
also scoped to QQ. `down` in the unified helper means selected-service stop;
`down-all` is the explicit whole-stack operation. Stop does not remove state.

Equivalent Compose commands (explicit service targets can override profiles):

```bash
docker compose --env-file .env --project-name kisara -f deploy/compose.yaml up -d --build
docker compose --env-file .env --project-name kisara -f deploy/compose.yaml stop telegram
```

The existing `kisara`/`kisara-dev`/`napcat` service names, project default
`kisara`, `kisara_state` volume, QQ login/config/art/archive mounts, network and
loopback NapCat WebUI binding retain their identities. Telegram has
`telegram_state:/app/state` and `config/telegram:/app/config:ro`; official
Compose uses `official_state` and `config/official`. Service-specific build
outputs install only the selected SDK extra. Each container receives explicit
engine-specific credentials/settings; `.env` is for interpolation, not an
all-secrets container env file. Keep these volumes private and back them up
before deployment/rollback. Rollback restores code/images/Compose while
retaining state/login volumes; no cleanup or data deletion is needed.

### Telegram setup and commands

Configure `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS` (positive numeric ID
strings), and optionally `TELEGRAM_GROUPS_ENABLED=true` plus
`TELEGRAM_ALLOWED_GROUPS` (negative group/supergroup IDs). A group caller must
also be in the user allowlist. IDs and credentials are independent from QQ.
Create the token with Telegram's BotFather; keep it out of Git/logs. The bot
uses outbound long polling, so no inbound port/webhook is required. Only one
poller may own a token. Telegram network reachability still needs a real
account/environment check.

Copy desired examples from `config/telegram/features/<name>/config.toml.example`
to `config.toml` beside them. That directory becomes `/app/config/features` in
the Telegram container; editing QQ `config/features` does not configure Telegram.
Optional flags for `ping`, `help`, `news`, and `music` default enabled. News has
independent `enabled` (manual requests/cache clearing) and `push_enabled`
(scheduled work). TOML explicit values, including `false` and empty lists,
override environment fallbacks. Environment-only flags are
`TELEGRAM_PING_ENABLED`, `TELEGRAM_HELP_ENABLED`, `TELEGRAM_NEWS_ENABLED`,
`TELEGRAM_NEWS_PUSH_ENABLED`, and `TELEGRAM_MUSIC_ENABLED`. Existing QQ uses the
corresponding `ONEBOT_*` names (legacy `KISARA_*` remain fallbacks). Apply TOML
changes with a targeted restart.
For `.env` or code/image changes use `./deploy.sh up telegram` to rebuild/recreate
only Telegram; restarting an existing container does not reload its environment.

Telegram receive/send summaries are an explicit opt-in:
`TELEGRAM_MESSAGE_LOG_ENABLED=true` (default `false`). They log only allowed
normalized user conversations at INFO, with private/group kind, user/chat IDs
and up to 120 characters of single-line preview. Newlines, control characters
and terminal formatting are escaped; the configured token and Bot API URL token
fragments are redacted before bounding or escaping. Denied senders/chats and
unsupported update types disclose no content or IDs. These logs contain private
conversation details: keep deployment logs private. SDK HTTP/error logs remain
suppressed regardless of this switch.

Successful text chunks and documents are logged only after confirmed SDK
success, including scheduled news through the shared sending path. Chunk logs
use a sanitized preview of the complete message and part index/count so a token
crossing a chunk boundary cannot expose fragments. Documents
log bounded caption/filename/type metadata and byte count, never media bytes.
Allowed messages without a reply show a no-reply processing line. A bounded
`Telegram polling ready` line follows completed polling/application startup.
Changing this switch requires targeted recreation (`./deploy.sh up telegram`).

Authorized private/group commands:

| Command | Result |
| --- | --- |
| `/ping` | `pong` online check |
| `/help`, `/start` | Effective enabled/supported help; no access grant/subscription |
| `/news` (alias `/brief`) | Readable PNG document with date/source and any publication-delay warning |
| `/news_clear` | Clear only today's engine-local news cache; scheduled receipts remain |
| `/music <query>` (alias `/song`) | Title/artist/public music link |

Group privacy mode supports explicit `/ping@YourBot` and other addressed
commands. Commands addressed to other bots are ignored. Ordinary text stays
silent; disabled/unsupported/unknown commands provide concise help guidance.
Channel, edited/service-only, anonymous-sender, and topic messages are ignored.
Help derives from the same effective registry used by routing. Unavailable
providers return a clear failure without fabricated data.

For music, set Telegram `music.api_url` or `TELEGRAM_MUSIC_API_URL`. Optional
internal infrastructure uses `COMPOSE_PROFILES=telegram,music` and
`http://music:3000`; it publishes no host port and does not start inactive bots.
An empty TOML URL overrides an environment URL, so either configure the file
or leave `api_url` absent when using the environment fallback.

### Telegram scheduled news and recovery

Configure `news.push_users` and/or `news.push_groups` with allowed ID strings,
or their `TELEGRAM_NEWS_PUSH_USERS`/`TELEGRAM_NEWS_PUSH_GROUPS` comma-separated
fallbacks. Groups require enabled group access. Private targets must first start
the bot; groups must permit document sending. Configuration alone cannot prove
reachability. Default `push_time` is `10:30` UTC+8 (environment fallback
`TELEGRAM_NEWS_PUSH_TIME`). Empty targets or `push_enabled=false` create no
scheduler. Manual news and scheduled news are independent.

Each send is one captioned PNG document, generated once per pending pass.
Today's uncompleted work catches up after startup; older days are never
backfilled. A confirmed warned publication-delay fallback completes the day's
push; `/news` can later fetch newly published content. The private journal
`/app/state/telegram_news.sqlite3` separates day/kind/target and retains 30 days.
A short transaction claims before sending; confirmed receipts checkpoint the
returned message ID. Known transient rejection or generation failure retries
after 15 minutes, extended for longer Telegram retry-after. Known forbidden/bad
target rejections stop for that day. Unknown network results remain uncertain
and are not automatically resent. Restart turns unfinished claims into uncertain;
a failed local completion write retains its claim, avoiding an automatic replay.
Use `/news` for manual recovery and inspect safe warning categories; automatic
exactly-once delivery is not promised. A storage failure stops the bot so restart
can recover its claims rather than leaving an unnoticed dead scheduler.

SDK/HTTP request logs are suppressed because Telegram request URLs include the
token; application warnings contain operation/error categories only. Telegram
supports future native handlers through explicit feature registration and
`Dispatcher.authorize_native()` before SDK effects. Shared services stay SDK-free.

### Offline and live acceptance

Telegram uses pinned `python-telegram-bot==22.8`, a community Python wrapper
around the official Bot API, and requires Python 3.10+. Docker runs Python 3.12;
base/QQ installation does not require/import this extra.

```bash
./hako python -m pip install --user -e ".[dev,telegram]"
./hako python -m pytest tests/unit/test_telegram_adapter.py tests/unit/test_telegram_news.py tests/unit/test_telegram_settings.py tests/integration/test_telegram_protocol.py tests/unit/test_engine_deployment.py
./dev.sh --all
```

Offline tests simulate SDK/protocol/provider/storage failures and selected
Compose operations. Before real deployment, verify authorized and denied private
and group messages, own/other bot targeting, news readability/attribution/warning,
configured music provider, one near-term private/group push, and restart without
replaying confirmed sends. Check QQ while Telegram runs and after targeted
Telegram stop/rebuild. Real credentials/accounts/provider/network behavior needs
human acceptance; tests do not start real bot services.
