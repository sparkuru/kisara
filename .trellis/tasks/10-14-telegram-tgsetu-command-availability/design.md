# Design: native Telegram through the local Bot API

## Problem and boundary

The live Telegram process currently uses the cloud Bot API and loads a
disabled TgSetu TOML. The command is therefore correctly omitted from `/help`,
and `/tgsetu on` receives the generic unavailable response. Enabling the
existing feature while still using the cloud endpoint would fail the existing
startup guard because the archive gateway expects the local Bot API cache.

The repair selects the already implemented local deployment shape:

```text
Telegram user
    -> Telegram servers
    -> telegram-bot-api:8081 (--local, internal Compose network)
    -> Kisara telegram engine (/tgsetu + ordinary Bot API calls)
```

The local server is an HTTP implementation of Telegram's Bot API. It is not a
Telegram user client, not an offline server and not a OneBot endpoint. The
source-level cloud endpoint remains available as an explicit compatibility
configuration for other installations, but this Bot is not allowed to fall
back to it after local-only cutover.

## Why this is the architecture-first choice

The choice is not based on avoiding a bridge's deployment cost. It preserves
the correct ownership and semantic boundaries:

1. The official local server is a transport/backend substitution: the native
   Telegram adapter still sees Telegram `file_id`, albums, captions, chat-local
   message IDs and the local cache path. This is exactly what the existing
   TgSetu gateway consumes.
2. OneBot v11 is a protocol boundary with a QQ-shaped public API. Telegram
   implementations exist, but they must translate Telegram events and actions
   into that API. Group administration, friend requests, identifiers, media
   semantics and some event types are not lossless across that boundary.
3. Routing this Bot through a Telegram-OneBot implementation would make the
   native Telegram feature depend on a second protocol server and would move
   the Bot API update owner outside Kisara. That is an architectural change,
   not a local endpoint setting.
4. If one shared business behavior is needed later, keep platform adapters
   separate and move only platform-neutral behavior behind Kisara contracts.
   A future OneBot bridge may be added as an explicit adapter/Bot when its
   compatibility matrix and ownership migration are approved.

## Credential and ownership matrix

| Item | Owner | Purpose | Live exposure |
| --- | --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Kisara `telegram` container | Authenticates this Bot's Bot API requests | Bot container only; value remains in private `.env` |
| `TELEGRAM_API_ID` | `telegram-bot-api` container | Local server application credential | Local server only |
| `TELEGRAM_API_HASH` | `telegram-bot-api` container | Local server application credential | Local server only |
| `/var/lib/telegram-bot-api` | Local server writable / Kisara read-only | Bot API transfer cache and state | Internal named volume |
| `/app/state` | Kisara Telegram | Durable activation/queue state | Telegram named volume |
| `/app/tgsetu` | Kisara Telegram | Published archive files | Host bind mount |

API ID/hash never replace the Bot token. They are passed only to the local
server by the existing Compose definition. Kisara still constructs Bot API
requests with the BotFather token, but the request root is the internal local
URL rather than `https://api.telegram.org`.

## Startup and configuration flow

1. The operator fills private `.env` values for `TELEGRAM_API_ID` and
   `TELEGRAM_API_HASH`; no credential is printed or committed.
2. `TELEGRAM_LOCAL_MODE=true` and
   `TELEGRAM_API_BASE_URL=http://telegram-bot-api:8081` select local-only mode.
3. `deploy/engines.sh` detects local mode, adds the `telegram-local` Compose
   profile, starts the local server, waits for its health probe, then
   recreates Telegram. The server has no host-published port.
4. The existing local server entrypoint validates numeric API ID and 32-hex
   API hash. The deployment helper rejects an absent/invalid pair or a wrong
   endpoint before switching the application.
5. Telegram startup loads
   `config/telegram/features/tgsetu/config.toml`. The ignored runtime TOML is
   explicitly enabled only for the already authorized private user. The
   source example remains disabled so a missing/configuration-free installation
   never auto-enables archiving.
6. Existing `main.py` local-mode guard and `TelegramAdapter.media_path()`
   cache confinement remain the archive boundary. No cloud temporary download,
   cloud-size cap or media fallback is added.

The ordinary Telegram command registry and native authorization remain the
same. Once the feature config is enabled, `/help` derives `/tgsetu` from the
effective feature registry; `/tgsetu on` reaches the existing native service.
Private-chat, global allowlist and feature allowlist checks remain before SDK
or archive effects.

## Controlled cloud-to-local cutover

The live migration is an account operation and is performed only after offline
checks and a private configuration backup:

1. Record a checksum and owner-only rollback copy of the ignored TgSetu TOML;
   do not print its contents.
2. Verify API ID/hash presence and local endpoint values without logging
   secrets. Build the selected application and local server images as needed.
3. Stop the current cloud Bot token owner. Do not run a second poller.
4. Call Telegram cloud `logOut` once using the existing Bot token, with the
   documented guarded helper. A failed/unconfirmed logout stops the cutover.
5. Start `telegram-bot-api`, wait for its health probe, then start/recreate
   only the Telegram application with the local endpoint.
6. Verify redacted startup/readiness evidence, `/help`, `/tgsetu on`, and one
   authorized private command. Do not retrieve archive media merely to prove
   command registration.

Telegram documents a restricted cloud re-login interval after cloud logout;
the operator procedure must preserve that condition and must not promise an
instant cloud rollback. The existing operations guide remains the authoritative
runbook for the one-shot logout and rollback ordering.

## OneBot boundary

OneBot Telegram implementations such as Gensokyo-telegram and Tele-KiraLink
are protocol servers that consume Telegram Bot API updates and expose OneBot
HTTP/WebSocket to an upper framework. They are valid examples of Telegram plus
OneBot, but they do not make the official local Bot API OneBot-compatible.

This task deliberately keeps:

- Kisara's native Telegram adapter as the Telegram owner;
- Kisara's OneBot adapter as the QQ/OneBot engine boundary;
- no bridge dependency, OneBot Telegram event mapping, or duplicate Bot owner.

If a future task selects a Telegram-OneBot bridge, it must replace the owner
and define Telegram/QQ semantic gaps (group administration, IDs, media and
event coverage) separately. It must not be installed alongside this Bot's
active polling/local Bot API owner.

## Failure and rollback behavior

- Missing/disabled feature TOML: no `/tgsetu` help entry, archive acceptance,
  SDK media retrieval or state effect.
- Invalid local API credentials/endpoint: fail before application switch; keep
  the current containers/data untouched.
- Local server health failure: do not start/recreate Telegram; inspect bounded
  private logs and retain persistent volumes.
- Startup or command smoke failure after cutover: restore the exact ignored
  feature TOML, stop the failed Telegram group through the scoped lifecycle,
  and preserve state/cache/archive. Do not reset volumes.
- Cloud rollback remains an explicit account operation subject to Telegram's
  post-logout restriction; it is not an automatic fallback.

## Expected source/doc changes

The parent task already supplied the local server, Compose, lifecycle, cache
and adapter implementation. This child should therefore make the smallest
changes needed for the discovered boundary:

- focused regression/deployment tests only where local-only behavior or the
  effective feature config is not already covered;
- operator documentation that distinguishes the two credential pairs and
  records the selected local-only runbook;
- task research/spec records for the OneBot findings.

Do not implement the superseded cloud-download staging plan, remove the
general cloud endpoint code, or modify the OneBot adapter in this task.
