# Kisara

Kisara is a QQ bot with a shared message pipeline and switchable protocol
adapters. The default route is NapCatQQ + OneBot 11; Tencent's official bot
engine remains available as an explicit alternative.

## Quick start

The three entrypoints are:

```bash
./dev.sh              # Interactive offline bot console; no QQ connection or .env needed
./dev.sh --test       # Automated offline functional tests
./dev.sh --all        # Full test suite
./preview.sh          # Start OneBot in the foreground with console logs
./deploy.sh           # Build and start OneBot in Docker in the background
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

All three reuse the existing Docker toolchain. Tests require the development
dependencies installed below. Preview and deployment require a configured
`.env`. Preview also supports `KISARA_ENGINE=official` and
`KISARA_ENGINE=onebot-dev`; deployment uses the NapCat + OneBot stack.

The project runs its Python toolchain in Docker. The host only needs Docker;
Python, pip, and `qq-botpy` stay inside the ephemeral containers managed by
`hako`.

There are three runtime paths:

- `onebot`: `start.sh` starts the Kisara + NapCat Compose stack.
- `onebot-dev`: `start.sh` starts the OneBot stack with source hot reload
  for Kisara development.
- `official`: `start.sh` keeps the existing Tencent official bot path.

1. Copy `.env.example` to `.env` and configure the selected engine. For
   OneBot, set `ONEBOT_WS_URL`, `ONEBOT_ACCESS_TOKEN`, and at least one ID in
   `KISARA_ALLOWED_USERS`. For the official engine, set `AppID` and
   `AppSecret`.
2. For local tests or the official engine, install the project and development dependencies:

   ```bash
   ./hako python -m pip install --user -e ".[dev]"
   ```

   If the official engine is needed, also install its optional dependency:

   ```bash
   ./hako python -m pip install --user -e ".[dev,official]"
   ```

3. Start the bot:

   ```bash
   ./start.sh
   ```

   The interactive menu selects `onebot`, `onebot-dev`, or `official`. It
   can also be chosen directly with `./start.sh onebot`,
   `./start.sh onebot-dev`, `./start.sh official`, or
   `KISARA_ENGINE=onebot ./start.sh`. In non-interactive environments the
   default is `onebot`.

4. Stop the bot and remove its development container:

   ```bash
   ./preview.sh down
   ```

The Kisara bot process does not expose a public application HTTP port.
`./preview.sh` remains attached so connection logs are visible in the current
terminal. For one-off commands, use `./hako`; for example:

For the OneBot runtime, use `./deploy/onebot.sh` instead of a standalone
`hako` bot container so Kisara and NapCat share the same Compose network.

```bash
./hako python --version
./hako python -m pytest
./deploy/onebot.sh ps
```

## Text commands

The shared dispatcher supports these commands for allowed users:

- `/ping` checks whether Kisara is online.
- `/help` lists the available commands.
- `/eat` chooses five suggestions from the packaged legacy food list.
- `/roll [sides]` rolls once from 1 to the given number (100 by default).
- `/roll <minimum> <maximum> [count]` rolls within an inclusive range; each
  roll is independent and at most 30 results are returned.
- `/chat <message>` asks the packaged phrasebook for a reply. Ordinary
  messages can also trigger phrasebook replies when chat is enabled.
- `/tarot [single|spread]` draws a daily tarot reading. The same user receives
  the same result on repeated requests that day, including after a restart.
  Readings use the bundled card descriptions. With the local legacy art installed,
  OneBot also sends one picture per drawn card.

Aliases `/r` and `/dice` are accepted for `/roll`. In groups, every sender and
group must be allowlisted. When phrasebook chat is enabled, ordinary group
messages can trigger its configured random reply.
Chat settings in `.env` control trigger probability, similarity threshold,
display names, the `cute`, `tsundere`, or historical `mixed` phrasebook,
ignored phrases, and per-user reply rules. The offline console uses the `cute`
phrasebook with a
100 percent trigger rate for direct exploration. The source CSV files stay
separate, so their two styles do not mix during conversion. `mixed` preserves
the old generated JSON for users who want its original reply pool.
Tarot day boundaries use China Standard Time; `KISARA_TAROT_SPREAD_RATE`
controls how often plain `/tarot` selects a spread rather than one card.
Place the legacy `tarotCards` directory at `data/kisara/tarotCards` to enable
OneBot tarot pictures. It must contain the card image folders; the image name
index is bundled with Kisara, so the old `tarot.json` is optional.
The pictures are ignored by Git and excluded from the Python package and Docker
image. Compose mounts this directory read-only into Kisara and NapCat at the
same path. For a standalone OneBot run, set `KISARA_TAROT_IMAGE_DIR` to a path
that both Kisara and the OneBot implementation can read. Without the directory,
tarot replies remain text only. The official adapter currently sends text only.
For per-group chat and tarot settings, copy `config/groups.example.json` to
`config/groups.json`, replace the sample ID with an ID in `KISARA_ALLOWED_GROUPS`,
and enable groups. Each group may contain `chat` and `tarot` objects. Chat
accepts `enabled`, `bot_name`, `sender_name`, `trigger_rate`, `similarity_rate`,
`ignored_phrases`, `banned_users`, `always_reply_users`, and
`reply_to_mentions`; tarot accepts `spread_rate`. Percentages range from 0 to
100. Compose mounts the file read-only; it is ignored by Git. Restart Kisara
after changing it. `KISARA_GROUP_CONFIG_PATH` selects a different path for a
standalone run.

The shared dispatcher also supports `/news`, `/wallpaper`, `/ba <name>`,
`/source [similarity]` with an attached image, `/music <song>`, and `/love`.
`/source` needs `SAUCENAO_API_KEY`. `/music` needs a configured
`KISARA_MUSIC_API_URL` pointing to a compatible local search API. `/love` needs
`TIANAPI_KEY` for TianAPI's short text endpoint. The official
adapter sends image URLs as text; OneBot sends native image and music segments.
Remote calls use a ten second timeout and return an error message if their
provider is unavailable.
On OneBot, `/source` also accepts a reply to an image message. `/recall`
removes a quoted bot message; in groups it requires the caller's QQ role to be
admin or owner, or their ID to be in `KISARA_ADMIN_USERS`.
To send the daily brief automatically, enable groups, allowlist each target
group, and set `KISARA_NEWS_PUSH_GROUPS` to a subset of those IDs. The default
push time is 10:30 China Standard Time. Kisara keeps a SQLite delivery record
in a persistent Docker volume so a reconnect or restart does not resend an
already delivered brief. If today's brief is late, it retries every 15 minutes.
Older commands such as `占卜`, `今天吃什么`, `简报`, `#r100`, `#pixiv`, `识图`,
`点歌`, and `撤回` are accepted as aliases. The complete feature inventory and
migration decisions are in [docs/legacy-migration.md](docs/legacy-migration.md).

For a self-hosted music search API, the optional Compose `music` profile uses
the [NeteaseCloudMusicApiEnhanced Docker image](https://github.com/LittleChest/NeteaseCloudMusicApi#docker-%E9%83%A8%E7%BD%B2%E8%AF%B4%E6%98%8E).
Set `KISARA_MUSIC_API_URL=http://music:3000` in `.env`, then start the service
with `docker compose --env-file .env -f deploy/compose.yaml --profile music up -d music`.
The service is available only on the Compose network.

To check these features without starting an engine, run the offline functional
scenarios. They construct normalized local message events and call the shared
dispatcher directly:

```bash
./hako python -m pytest tests/unit/test_offline_commands.py
```

## OneBot deployment

The normal OneBot path is implemented as a two-service Compose stack:

- `napcat` runs NapCatQQ, owns QQ login state, and exposes the OneBot 11
  forward WebSocket only inside the Compose network.
- `kisara` is built from `deploy/Dockerfile` and connects to
  `ws://napcat:3001`.

Prepare the configuration and start it:

```bash
cp .env.example .env
# Edit at least KISARA_ALLOWED_USERS and ONEBOT_ACCESS_TOKEN.
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
can be rebuilt. Set `KISARA_WATCH_INTERVAL` in `.env` to adjust the
polling interval.

Switch back to the normal image-based runtime with:

~~~bash
./preview.sh down
./start.sh onebot
~~~

## Repository layout

The `data/` directory is runtime state and is intentionally ignored by Git.

```text
.
├── start.sh                         # Select an engine and start the service
├── dev.sh                           # Open offline console or run tests
├── preview.sh                       # Start/stop the foreground service
├── deploy.sh                        # Start/manage the background Docker stack
├── hako                             # Run commands inside Docker
├── deploy/
│   ├── compose.yaml                 # Kisara + NapCat OneBot stack
│   ├── Dockerfile                   # Kisara runtime image
│   ├── kisara-dev-watch.sh          # Development source watcher
│   ├── onebot.sh                    # Compose lifecycle wrapper
│   └── napcat-entrypoint.sh         # Generate OneBot config
├── config/groups.example.json       # Optional per-group overrides
├── src/
│   └── kisara/
│       ├── config/                 # Common and engine-specific settings
│       ├── bot/                    # Protocol-neutral bot pipeline
│       │   ├── adapters/            # OneBot 11 and official SDK adapters
│       │   ├── commands/            # Shared command handlers
│       │   ├── contracts.py         # Normalized message and adapter types
│       │   └── dispatcher.py        # Access control and routing
│       ├── application/
│       │   └── services/            # Dice, food, and phrasebook use cases
│       ├── domain/
│       │   ├── models/              # Domain models
│       │   └── repositories/        # Repository interfaces
│       ├── infrastructure/
│       │   ├── integrations/        # External APIs
│       │   ├── persistence/         # Database, cache, and files
│       │   └── logging/             # Logging
│       ├── resources/               # Versioned food and chat data
│       └── shared/                  # Shared definitions
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── config/
├── scripts/
├── docs/
└── data/                            # Ignored NapCat runtime state
```

## References

1. QQ Bot official documentation: <https://bot.q.qq.com/wiki/>
2. Tencent `botpy` SDK: <https://github.com/tencent-connect/botpy>
3. NapCat Docker: <https://github.com/NapNeko/NapCat-Docker>
4. NapCat network configuration: <https://napneko.github.io/config/basic>
