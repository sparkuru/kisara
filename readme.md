# Kisara

Kisara is a QQ bot with a shared message pipeline and switchable protocol
adapters. The default route is NapCatQQ + OneBot 11; Tencent's official bot
engine remains available as an explicit alternative.

## Quick start

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
   ./dev.sh down
   ```

The Kisara bot process does not expose a public application HTTP port.
`./dev.sh` remains attached so connection logs are visible in the current
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

The NapCat WebUI is bound to `127.0.0.1:6099` by default. On a remote PVE
host, use an SSH tunnel and open `http://127.0.0.1:6099/webui` locally:

```bash
ssh -L 6099:127.0.0.1:6099 pve
```

Useful operations:

```bash
./deploy/onebot.sh logs
./deploy/onebot.sh ps
./dev.sh down
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
./dev.sh down
./start.sh onebot
~~~

## Repository layout

The `data/` directory is runtime state and is intentionally ignored by Git.

```text
.
├── start.sh                         # Select an engine and start the service
├── dev.sh                           # Start/stop the selected service
├── hako                             # Run commands inside Docker
├── deploy/
│   ├── compose.yaml                 # Kisara + NapCat OneBot stack
│   ├── Dockerfile                   # Kisara runtime image
│   ├── kisara-dev-watch.sh          # Development source watcher
│   ├── onebot.sh                    # Compose lifecycle wrapper
│   └── napcat-entrypoint.sh         # Generate OneBot config
├── src/
│   └── kisara/
│       ├── config/                 # Common and engine-specific settings
│       ├── bot/                    # Protocol-neutral bot pipeline
│       │   ├── adapters/            # OneBot 11 and official SDK adapters
│       │   ├── commands/            # Shared command handlers
│       │   ├── contracts.py         # Normalized message and adapter types
│       │   └── dispatcher.py        # Access control and routing
│       ├── application/
│       │   └── services/            # Application use cases
│       ├── domain/
│       │   ├── models/              # Domain models
│       │   └── repositories/        # Repository interfaces
│       ├── infrastructure/
│       │   ├── integrations/        # External APIs
│       │   ├── persistence/         # Database, cache, and files
│       │   └── logging/             # Logging
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
