# Running Kisara

## Quick start

Common development and runtime commands are:

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

These scripts reuse the existing Docker toolchain. Tests require the development
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
   `AppSecret`. Copy the examples for any features you want to configure from
   `config/features/<feature>/config.toml.example` to `config.toml` in the
   same directory.
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

## Feature operations

Daily news reads the dated HTML from `https://60s.lylme.com/` on a cache miss.
The validated source page is temporarily kept in `/tmp/kisara-daily-news-<uid>/`;
the generated PNG is retained under the news `cache_dir` setting. In Compose,
that image directory is `/app/state/daily-news` in the persistent `kisara_state`
volume. `cache_days` in `config/features/news/config.toml` controls PNG retention.
Older temporary HTML is pruned on the next HTML fetch or cleared by `/tmp`.
The image includes the page's headlines, hot lists, history, almanac, and quote.
Set `font_paths` in the same feature file to an ordered list of font files;
the first CJK-capable path inside the container is used, then bundled Noto CJK
fonts are tried. A layout version change
regenerates older images automatically. After changing fonts, remove that day's
cached PNG to regenerate it.

For the setu archive, Compose maps `data/kisara/setu` to `/app/setu` and keeps
SQLite state in the `kisara_state` volume. The startup wrapper prepares the
host directory. With direct Compose usage, create and grant group access first:

```bash
mkdir -p data/kisara/setu
chmod 2770 data/kisara/setu
```

Set `KISARA_SETU_GID` to the output of `id -g` when the host's primary group ID
is not 1000. After saving, inspect files with `ls -lah data/kisara/setu` or:

```bash
docker compose --env-file .env -f deploy/compose.yaml --project-name kisara exec kisara ls -lah /app/setu
```

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
