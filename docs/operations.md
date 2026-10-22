# Running Kisara

## Quick start

Common development and runtime commands are:

```bash
./kisara.sh console         # Interactive offline bot console; no .env needed
./kisara.sh test            # Full test suite
./kisara.sh test tests/unit/test_offline_commands.py  # Focused offline tests
./kisara.sh preview         # Prepare/start preview and wait for readiness
./kisara.sh preview status  # Inspect readiness, then follow current bot logs
./kisara.sh preview build   # Rebuild selected images; running bots stay unchanged
./kisara.sh preview down    # Remove selected repository containers, preserving storage
./kisara.sh up              # Build/start selected engines in the background
./kisara.sh logs            # Follow deployment logs
./kisara.sh down            # Stop/remove selected containers, preserving login/state data
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
`.env`. Preview and deployment use effective `COMPOSE_PROFILES`; an explicit
command target overrides that list. `KISARA_ENGINE` selects an application
runtime engine and does not narrow preview selection.
See the Compose/Telegram section below for multiple engines and targeted operations.

The project runs its Python toolchain in Docker. Preview requires Bash 4.4+,
Docker/Compose and standard lifecycle tools listed by `./kisara.sh preview --help`;
`ip` is additionally required for local wildcard publishing. Python, pip and
bot SDKs stay inside the existing images and ephemeral development containers.

Configuration is selected once at startup from `config/<engine>`. Ordinary
features, dedicated Setu/TgSetu and default group JSON use this same root in
Compose, hako and direct runs. No other engine or old root is searched as a
fallback. Shared fonts stay under `config/fonts`.

When upgrading the old OneBot layout, copy private
`config/features/<feature>/config.toml` to
`config/onebot/features/<feature>/config.toml`, and old `config/groups.json` to
`config/onebot/groups.json`. Preserve original bytes/permissions and retain the
old files as ignored backups. Compare existing targets first: equal files need
no copy; differing files require resolving the conflict before migration, never
overwrite them silently. The tracked examples already use the new layout.
This checkout's existing private chat/news/setu files have been copied and
verified without changing their values.

This layout changes Compose mounts, so activate updated code with targeted
recreation (`./kisara.sh up <engine>`). A restart alone retains the previous
container's mounts. After recreation, TOML-only changes use ordinary restart.

Explicit startup recreates selected application bots to reload current environment
and same-path TOML. Unchanged NapCat, music and local Bot API auxiliaries use
normal Compose reconciliation. Build prepares images without changing running
containers; another startup applies those images. Preview has no configuration
fingerprint or complete-group/reuse gate.

The canonical user entrypoint is `./kisara.sh`. It delegates offline console/tests
to `hako` and online operations to `deploy/engines.sh`. The previous `dev.sh`,
`deploy.sh`, `preview.sh` and `start.sh` have been removed. Select the preview
target with command arguments or configuration. No command alone changes engine
permissions.

The existing QQ runtime paths are:

- `onebot`: `./kisara.sh preview start onebot` starts Kisara + NapCat preview.
- `onebot-dev`: `./kisara.sh preview start onebot-dev` starts the OneBot preview with source hot reload
  for Kisara development.
- `official`: `./kisara.sh preview start official` uses its Compose-built application image.

1. Only if `.env` is absent, copy `.env.example` to `.env`, then configure the selected engine. For
   OneBot, set `ONEBOT_WS_URL`, `ONEBOT_ACCESS_TOKEN`, and at least one ID in
   `ONEBOT_ALLOWED_USERS`. For the official engine, set `OFFICIAL_APP_ID`,
   `OFFICIAL_APP_SECRET`, and `OFFICIAL_ALLOWED_USERS`. Telegram needs
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USERS`. Copy desired feature
   examples to `config.toml` beside each example: OneBot uses
   `config/onebot/features/<feature>/`, Official uses
   `config/official/features/<feature>/`, and Telegram uses
   `config/telegram/features/<feature>/`. Compose, hako and direct runs select
   the same `config/<engine>` root. Legacy OneBot files under `config/features`
   are migration backups, not shared fallback configuration.
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
   ./kisara.sh preview
   ```

   Choose an explicit target with `./kisara.sh preview start telegram`,
   `onebot`, `onebot-dev` or `official`; explicit target arguments win over
   inherited environment and .env selection. With no target, effective
   COMPOSE_PROFILES selects every listed bot, defaulting to OneBot only when unset.
   Inherited same-key environment values override `.env`, including empty values;
   an empty or invalid profile list is an error. KISARA_ENGINE is not a preview selector.
   Comma-separated profile targets select a Compose group.

4. Stop the selected bots and remove their containers with data retained:

   ```bash
   ./kisara.sh preview down
   ```

For a code/settings update, use the same selected group throughout:

```bash
./kisara.sh preview build
./kisara.sh preview
```

Down removes selected owned container objects while retaining volumes and
login/state/cache/media. Build explicitly rebuilds every selected application
image from current source and manifests, including existing tags and Official-only
preview; it never starts services. Docker layer caching remains enabled and
unchanged auxiliary images are retained. The next start uses the prepared tags,
current engine-specific runtime settings and existing TOML binds. Explicit targets
can isolate this sequence, for example `preview build telegram`, then
`preview start telegram`. Down is optional cleanup; it stops and removes selected
containers while retaining storage. `stop` is no longer a command or alias.

An old owned Official hako preview uses the persisted `hako.service=bot` identity.
`preview down official` can remove it only after checking the repository, scope,
service and actual Official runtime engine; its mounted data stays intact.
Explicit startup removes that verified old runtime before creating its Compose
replacement. Build leaves it untouched; status reports a missing Compose bot
until explicit startup. Foreign containers are never adopted or removed automatically.

The Kisara bot process does not expose a public application HTTP port.
Preview start returns after bounded readiness and prints one summary using actual
service listeners/published mappings. Outbound-only engines have no browser URL.
Loopback NapCat access and SSH tunneling remain the default; wildcard addresses
are candidates, not proof of access from another device. Initial NapCat login
and external gateway/network readiness may require user action; failed startup
reports diagnostics and never prints a ready banner.

Ordinary deployment and preview share one repository ownership check. Containers
from this checkout can be removed through either down entry, even if stopped or
created in the other mode. Exact Compose project, service, deployment directory
and base configuration file identify ordinary containers; previously stored
preview labels remain recognized. Foreign or unverifiable source identity fails
before any selected container is changed. No manual label edits or Docker rm
steps are needed for switching:

```bash
./kisara.sh preview start telegram
./kisara.sh up telegram
./kisara.sh preview down telegram
```

Startup reconciles partial/stopped groups. A failed startup keeps selected
containers available for diagnosis, emits bounded redacted preview errors and
never prints ready. Correct the reported cause and retry `preview start`; use
`down` for explicit removal. Never remove login directories or volumes as recovery.
OneBot startup switches the repository-owned opposing application mode; OneBot
down covers both modes and NapCat. Build/status do not switch modes. Down-all
preflights the entire Compose project and removes its repository-owned containers,
including a verified old Official preview, while retaining data and networks.

Stopping preview does not depend on host-address discovery. OneBot preview
rejects empty/example access tokens before preparation. Telegram preview becomes
ready only after a successful poll while its application is running.

Preview help/status/down do not build, install or start services; verbose
preparation details are captured then redacted. After successful readiness,
`./kisara.sh preview status` shows the selected bot's last 80 log lines and
continuously follows new lines, with credentials redacted before display.
User/chat/account IDs, bot names and ordinary numbers remain visible.
Receive/reply/no-reply summaries retain their message previews;
each line uses a `platform | log` prefix: NapCat and either OneBot application
both show `onebot`, Telegram shows `telegram`, and Official shows `official`.
Both OneBot streams retain their contents and separate internal readers. Follow
hints use the same platform names. Telegram message
summaries still require `TELEGRAM_MESSAGE_LOG_ENABLED=true` in the bot's startup
configuration. Use `./kisara.sh preview status telegram` for an explicit engine.
OneBot selections also follow their owned NapCat gateway, which emits QQ
receive/send records. Music and the local Bot API are omitted from successful
status log following.
Press Ctrl+C to stop viewing; the bot keeps running. Unready status retains
bounded failure diagnostics and exits with failure. Log-following errors also
exit with an error; status does not monitor or restart the bot.
For deployment logs use `./kisara.sh logs`; for one-off commands use `./hako`.

NapCat readiness and socket inspection use the existing container Python3
standard library, requiring WebUI HTTP success and the OneBot TCP listener.
The probe uses `/webui/` directly; the root browser URL redirects there.
The default NapCat image provides Python3; a custom image must provide it too.
Local probes bypass ambient HTTP proxies. Kisara's current authenticated
WebSocket readiness marker is checked separately.

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
`.env` changes by targeted recreation (`./kisara.sh up telegram` or
`./kisara.sh up onebot`); `restart` keeps the previous container environment.

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
./kisara.sh preview start onebot
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
consistent when switching between `./kisara.sh preview` and `./kisara.sh up`.
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
./kisara.sh down
```

The WebUI binding can be changed with `NAPCAT_WEBUI_BIND` and
`NAPCAT_WEBUI_PORT`. Do not expose the WebUI or the OneBot port publicly
without an explicit access-control plan; the OneBot port is intentionally
not published to the host.

For active Kisara development, use the `onebot-dev` path:

~~~bash
./kisara.sh preview start onebot-dev
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
./kisara.sh preview start onebot
~~~

## Feature operations

Daily news reads the dated HTML from `https://60s.lylme.com/` on a cache miss.
The validated source page is temporarily kept in `/tmp/kisara-daily-news-<uid>/`;
the generated PNG is retained under the news `cache_dir` setting. In Compose,
that image directory is `/app/state/daily-news` in the persistent `kisara_state`
volume. `cache_days` in `config/onebot/features/news/config.toml` controls PNG retention.
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
the existing user/group allowlists unless that engine publishes `news` through
its public-feature list. Groups always require group enablement; chat may be
disabled. It confirms removal or reports that
no current-day cache exists. Clearing does not fetch, render, or send news;
the next `/news` request fetches a fresh page and regenerates the image.
Historical files and scheduled delivery records are preserved, so clearing
does not cause completed scheduled pushes to resend. Unsafe temporary cache
directories and filesystem failures return an error; retry after correcting
the underlying permissions or storage problem.

For scheduled OneBot news, copy `config/onebot/features/news/config.toml.example` to
`config/onebot/features/news/config.toml` if needed and configure personal QQ numbers
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
`api_url = "http://music:3000"` in `config/onebot/features/music/config.toml` and start
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
./kisara.sh preview start telegram  # Explicit preview target overrides env
./kisara.sh up                      # Build/start selected engines in the background
./kisara.sh up telegram             # Build/recreate Telegram only
./kisara.sh down telegram           # Stop/remove Telegram only; keep QQ and all volumes
./kisara.sh restart telegram
./kisara.sh logs telegram
./kisara.sh ps
./kisara.sh down-all                # Explicit whole-project shutdown; retains volumes
```

`./kisara.sh preview` follows effective `COMPOSE_PROFILES`, including all listed
bots even when `KISARA_ENGINE=onebot` is present. All engines use the existing
Compose image path, including `./kisara.sh preview start official`; explicit
targets override default selection without rewriting `.env`.
`./deploy/onebot.sh` forwards scoped QQ commands into the same lifecycle helper.
Its down removes both OneBot application modes and NapCat, with login/state data
intact; it leaves Telegram/Official untouched. Ordinary QQ logs/ps/status include
NapCat and both application modes after ownership preflight. `down-all` explicitly removes all
repository-owned containers in the configured project. All affected objects are
verified before removal. Networks and volumes remain; no stop alias is accepted.
Use the canonical commands above for repository preflight. Direct Compose commands
remain available to administrators, but do not perform that repository check.

The existing `kisara`/`kisara-dev`/`napcat` service names, project default
`kisara`, `kisara_state` volume, QQ login/config/art/archive mounts, network and
loopback NapCat WebUI binding retain their identities. Telegram has
`telegram_state:/app/state` and `config/telegram:/app/config/telegram:ro`;
OneBot uses `config/onebot:/app/config/onebot:ro`, and official uses
`official_state` plus `config/official:/app/config/official:ro`. Shared fonts
remain at `config/fonts:/app/config/fonts:ro`. Service-specific build
outputs install only the selected SDK extra. Each container receives explicit
engine-specific credentials/settings; `.env` is for interpolation, not an
all-secrets container env file. Keep these volumes private and back them up
before deployment/rollback. Rollback restores code/images/Compose while
retaining state/login volumes; no cleanup or data deletion is needed.

### Telegram setup and commands

Configure `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS` (positive numeric ID
strings), and optionally `TELEGRAM_GROUPS_ENABLED=true` plus
`TELEGRAM_ALLOWED_GROUPS` (negative group/supergroup IDs). Non-public group
commands also require the caller in the user allowlist. IDs and credentials
are independent from QQ.
Create the token with Telegram's BotFather; keep it out of Git/logs. The bot
uses outbound long polling, so no inbound port/webhook is required. Only one
poller may own a token. Telegram network reachability still needs a real
account/environment check.

By default, anyone can privately send `/tguid` to receive their own numeric
Telegram user ID, then give it to the operator for `TELEGRAM_ALLOWED_USERS`.
In ordinary groups, `/tguid@YourBot` requires `TELEGRAM_GROUPS_ENABLED=true`;
the caller and group need not be allowlisted. It accepts no arguments, returns
only the sender's ID, and grants no access.

Each engine owns a comma-separated public ordinary-feature list in `.env`:

```dotenv
TELEGRAM_PUBLIC_FEATURE=tguid
ONEBOT_PUBLIC_FEATURE=
OFFICIAL_PUBLIC_FEATURE=
```

An unset Telegram list defaults to `tguid`; OneBot/Official default to empty.
An explicitly empty list disables public exemptions, including `/tguid`.
Use canonical lowercase registry feature names without `/`, such as `ping`,
`help`, `news`, or `music`. Names are trimmed and deduplicated. Unknown names,
aliases (e.g. `song`), unsupported platforms, native workflows (`tgsetu`, Setu,
image export), and scheduled features (`news_push`) fail startup validation.
Disabled or unassembled ordinary features may be listed but remain unavailable.

A public feature bypasses sender/group allowlists only for its registered
commands. Groups still require that engine's `GROUPS_ENABLED=true`; other
commands and ordinary text keep existing access rules. The list covers all
aliases and subcommands: `help` also publishes `ahelp` and Telegram `/start`,
and `news` publishes cache clearing as well as `/brief`. Feature switches,
argument validation, duplicate suppression, and feature-specific restrictions
(such as recall's quoted-bot/admin checks) remain effective. Native archives,
exports and scheduled recipients never inherit this exception.

Compose maps only the selected platform's deployment list to internal
`KISARA_PUBLIC_FEATURE` (both OneBot profiles support its generic fallback).
Direct runtime loading also accepts that internal name, with a selected
`*_PUBLIC_FEATURE` taking precedence by presence, including empty values.
Changing `.env` requires targeted recreation, for example
`./kisara.sh up telegram`; a container restart retains its previous environment.

Copy desired examples from `config/telegram/features/<name>/config.toml.example`
to `config.toml` beside them. The same directory is
`/app/config/telegram/features` in the Telegram container; editing
`config/onebot/features` does not configure Telegram.
Optional flags for `ping`, `help`, `news`, and `music` default enabled. News has
independent `enabled` (manual requests/cache clearing) and `push_enabled`
(scheduled work). TOML explicit values, including `false` and empty lists,
override environment fallbacks. Environment-only flags are
`TELEGRAM_PING_ENABLED`, `TELEGRAM_HELP_ENABLED`, `TELEGRAM_NEWS_ENABLED`,
`TELEGRAM_NEWS_PUSH_ENABLED`, and `TELEGRAM_MUSIC_ENABLED`. Existing QQ uses the
corresponding `ONEBOT_*` names (legacy `KISARA_*` remain fallbacks). Apply TOML
changes with a targeted restart.
For `.env` or code/image changes use `./kisara.sh up telegram` to rebuild/recreate
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

The native TgSetu path does not use these conversation previews. It logs safe
failure categories; captions/filenames remain in authorized result messages and
archive metadata. Its bounded notification queue is in memory and does not
replay on restart. A missing notification does not undo saved bytes or durable
jobs; inspect the archive and use the source message ID for eligible retries.

Successful text chunks and documents are logged only after confirmed SDK
success, including scheduled news through the shared sending path. Chunk logs
use a sanitized preview of the complete message and part index/count so a token
crossing a chunk boundary cannot expose fragments. Documents
log bounded caption/filename/type metadata and byte count, never media bytes.
Allowed messages without a reply show a no-reply processing line. A bounded
`Telegram polling ready` line follows completed polling/application startup.
Changing this switch requires targeted recreation (`./kisara.sh up telegram`).

Private/group commands (public access follows the configured feature list):

| Command | Result |
| --- | --- |
| `/ping` | `pong` online check |
| `/tguid` | Your own numeric Telegram user ID; public by default, with groups enabled for group use |
| `/help`, `/start` | Effective enabled/supported help; no access grant/subscription |
| `/news` (alias `/brief`) | Readable PNG document with date/source and any publication-delay warning |
| `/news_clear` | Clear only today's engine-local news cache; scheduled receipts remain |
| `/music <query>` (alias `/song`) | Title/artist/public music link |
| `/tgsetu`, `/tgsetu status` | Private archive status and usage, when configured |
| `/tgsetu on`, `/tgsetu off` | Enable/disable automatic saving of newly received private media |
| `/tgsetu retry <source-message-id>` | Retry failed files of that user's source message/album; retain successful files |

Group privacy mode supports explicit `/ping@YourBot` and other addressed
commands. Commands addressed to other bots are ignored. Ordinary text stays
silent; authorized disabled/unsupported/unknown commands provide concise help guidance.
Channel, edited/service-only, anonymous-sender, and topic messages are ignored.
Help derives from the same effective registry used by routing. Unavailable
providers return a clear failure without fabricated data.

For music, set Telegram `music.api_url` or `TELEGRAM_MUSIC_API_URL`. Optional
internal infrastructure uses `COMPOSE_PROFILES=telegram,music` and
`http://music:3000`; it publishes no host port and does not start inactive bots.
An empty TOML URL overrides an environment URL, so either configure the file
or leave `api_url` absent when using the environment fallback.

### Telegram media archive and local Bot API

TgSetu is an opt-in private-chat feature, separate from OneBot `/setu`.
Copy `config/telegram/features/tgsetu/config.toml.example` to `config.toml`
beside it, enable it and add feature user IDs that are also in
`TELEGRAM_ALLOWED_USERS`. Missing configuration disables this feature. Telegram
`/setu` is unavailable. TgSetu requires an explicit local API endpoint/mode;
existing Telegram text/news/music can keep the default cloud endpoint.

`/tgsetu on` authorizes automatic archiving of supported photos, videos and
documents sent or forwarded into that private chat. Activation persists through
restart. `/tgsetu off` stops new acceptance; accepted work finishes and retains
its result. No per-forward finish/confirmation is required. Ordinary text,
groups, edited/channel/topic messages and unsupported paid/live media are not
archive inputs. Access and feature policy are checked before metadata/transfer
effects, including resumed jobs. Multi-selection has no original batch/count
field: results describe received work, never the number selected in the client.

Image/video filenames use the caption title followed by `-@tag` suffixes;
documents prepend their original filename stem. For example `pack.tar.gz` with
caption `Resource pack #tag1 #tag2` becomes
`pack-Resource pack-@tag1-@tag2.tar.gz`. A photo contributes its largest available
Telegram resolution; send it as a document if preserving the uploaded original
bytes matters. The actual file extension is independent of dots in the caption.
An album shares its initial caption and uses stable `-001` member ordinals
before tags. A bounded metadata window chooses initial naming, not album
completeness. Late members are accepted while on; an already frozen fallback
caption/name is retained rather than renaming earlier published files.

Complete files are published directly under configured `save_root`, normally
host `data/kisara/tgsetu` mounted at `/app/tgsetu`. There is no message subfolder.
Conflicting different-content names are disambiguated without overwriting;
partial message failure preserves successful siblings. The durable
`/app/state/tgsetu.sqlite3` queue/activation/checkpoints are private metadata,
separate from files and the Bot API cache. Notices distinguish acceptance from
saved completion and give actual paths and explicit failed-file retry commands.
Restart reconciles publication-before-checkpoint interruptions. Size, pending
queue and worker limits are configured in the feature example; they are not
removed by enabling the local API.

The bundled local server is built from the official source at the pinned commit
in `deploy/telegram-bot-api.Dockerfile`. It requires your own
`TELEGRAM_API_ID` and `TELEGRAM_API_HASH` from `my.telegram.org`, distinct from
the BotFather token. Configure `.env` for a planned local deployment:

```dotenv
TELEGRAM_LOCAL_MODE=true
TELEGRAM_API_BASE_URL=http://telegram-bot-api:8081
TELEGRAM_API_ID=<your-api-id>
TELEGRAM_API_HASH=<your-api-hash>
```

`TELEGRAM_BOT_TOKEN` remains required by the Kisara Telegram process and is
still the BotFather token used for Bot API requests. `TELEGRAM_API_ID` and
`TELEGRAM_API_HASH` belong only to the local `telegram-bot-api` server; they do
not replace or authenticate the bot token. Local mode is not offline: the
official server still reaches Telegram's network, and it exposes the Telegram
Bot API rather than OneBot. Telegram-OneBot bridges are a separate deployment
option and are not installed or selected by this setup.

The server uses its own internal Compose profile and no host port. Deployment
and preview helpers select it only for local-mode Telegram, start/check it
before Telegram, stage local-server restarts before restarting Telegram, and
remove only the selected group on down, retaining its persistent cache/state. The cache/state
is mounted at the identical `/var/lib/telegram-bot-api` path in both containers,
writable for the server and read-only for Kisara. Both use UID 10001 so
owner-only downloaded cache files remain readable; archive ownership uses the
existing host-group convention. SDK `get_file()` yields a confined cache path;
Kisara copies it in bounded chunks rather than buffering an entire large file.

For a first cloud-to-local switch, stop the existing Telegram token owner first
and explicitly call cloud `logOut` once before starting the local owner, as
required by [Telegram's migration procedure](https://github.com/tdlib/telegram-bot-api#moving-a-bot-to-a-local-server).
This is a planned account operation, never an automatic startup action. A
trusted one-shot SDK call can keep the token in environment configuration:

```bash
./kisara.sh down telegram
HAKO_SERVICE=bot KISARA_ENGINE=telegram ./hako python - <<'PY'
import asyncio
import os
from telegram import Bot
from telegram.error import TelegramError
from kisara.bot.adapters.telegram import quiet_sdk_logging

async def logout() -> None:
    quiet_sdk_logging()
    try:
        async with Bot(os.environ["TELEGRAM_BOT_TOKEN"]) as bot:
            if not await bot.log_out():
                raise RuntimeError("Cloud logout was not confirmed")
    except TelegramError as error:
        raise RuntimeError("Cloud logout failed: " + type(error).__name__) from None

asyncio.run(logout())
PY
./kisara.sh up telegram
```

Do not run this during offline checks or while another process owns the token.
Endpoint/environment edits need recreation; TOML edits need restart. Cloud
rollback preserves archive/state/cache volumes, requires a controlled local
owner logout/stop, and respects Telegram's documented 10-minute cloud re-login
restriction after cloud logout. Never use a project-wide volume reset to switch
endpoints. `--local` mode is not a host/LAN exposure request.

The upstream server enables TDLib's storage optimizer. Cache is disposable
transfer state; it is not an archive backup and GC is not a hard disk quota.
Reserve space for concurrent full cache downloads plus archive temporary and
final copies, monitor the cache volume and archive filesystem, and stop new
archiving with `/tgsetu off` before maintenance. Kisara does not delete the
read-only server cache. Keep archive/state backups separate and do not remove
active downloads or server session/database files as a cleanup shortcut.

Before real use, verify one captioned image, a mixed-media forwarded album,
a named compound-extension document and a file larger than 20 MB. Then check
off/denied media produces no files, partial failure retries only failed members,
and restart preserves activation/success checkpoints. Offline fixtures prove
these code boundaries; actual client delivery, cache permissions, Telegram
network retrieval and endpoint migration require account/environment acceptance.

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
./kisara.sh test
```

Offline tests simulate SDK/protocol/provider/storage failures and selected
Compose operations. Before real deployment, verify authorized and denied private
and group messages, own/other bot targeting, news readability/attribution/warning,
configured music provider, one near-term private/group push, and restart without
replaying confirmed sends. Check QQ while Telegram runs and after targeted
Telegram down/rebuild. Real credentials/accounts/provider/network behavior needs
human acceptance; tests do not start real bot services.
