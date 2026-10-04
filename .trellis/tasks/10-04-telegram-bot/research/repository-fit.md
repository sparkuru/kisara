# Telegram repository fit

Scope note: this file records the initial repository investigation and earlier
brainstorm recommendations. The user's latest reduced feature inventory and
shared .env/Compose selection supersede its earlier broad-command and separate-
deployment recommendations. See feature-routing.md and the current PRD/design
for active decisions. Evidence about the existing source remains useful.

Scope: focused architecture and extension assessment; no implementation or
live account/network verification.

## Evidence and conclusions

- `src/kisara/bot/contracts.py` defines protocol-neutral `MessageEvent`,
  `OutgoingMessage`, and `MessageAdapter`. Events already carry engine and
  instance identifiers.
- `src/kisara/bot/main.py:create_adapter` loads one selected adapter, while
  `main` assembles common services and `Dispatcher`.
- `src/kisara/bot/dispatcher.py` routes normalized events without a platform
  SDK dependency. Local commands and text-based application behavior provide
  useful reuse seams.
- `.trellis/spec/trellis-plus/architecture.md` explicitly specifies one engine
  per process. Concurrent QQ/Telegram containers are a compatible extension
  direction; multi-engine orchestration inside one process would change that
  contract and is not necessary to establish repository fit.
- `design.md` is the original dual-engine design and contains historical
  deployment-verification status. The user's report that the current bot works
  supersedes that historical status; no live health check was performed here.

Conclusion: the existing repository is a suitable home for Telegram when the
bot shares Kisara's behavior. Keep platform connection and sending mechanics in
an adapter. A separate repository becomes useful if product purpose, business
rules, or release ownership diverge substantially.

## Constraints to address in the eventual design

1. `config/settings.py:SUPPORTED_ENGINES` and `bot/main.py:create_adapter`
   currently accept only OneBot and official adapters.
2. `bot/dispatcher.py:_route` gates news and tarot images on OneBot; recall is
   explicitly OneBot-only. Text reuse does not imply media parity.
3. `bot/main.py:daily_news_factory` uses `result.onebot_image()` and the OneBot
   adapter owns scheduled delivery. Shared generation and platform delivery
   need a defined boundary if Telegram news images or scheduling enter scope.
4. `config/settings.py` restricts scheduled news to OneBot and validates private
   recipients as canonical QQ numbers. Telegram target validation and feature
   configuration cannot inherit these rules unchanged.
5. `infrastructure/persistence/news_delivery.py` completion keys contain dates
   and target IDs without engine/instance identifiers. Separate state stores
   avoid cross-platform collisions; shared state would require namespacing.
6. `deploy/compose.yaml` hardcodes the OneBot engine and ties Kisara to NapCat.
   A Telegram service needs an independent launch/configuration path.
7. Current dispatcher deduplication uses `(engine, instance_id, message_id)`.
   Telegram ordinary message IDs are unique within a chat, so normalization
   must preserve chat scope or the deduplication contract must be extended.
8. Telegram `/command@botname` addressing, group privacy, media input/download
   behavior, API failures, and update-offset handling need focused research
   and acceptance coverage if their corresponding features enter scope.

## External references checked on 2026-10-04

- [Telegram Bot API: Message](https://core.telegram.org/bots/api#message):
  `message_id` is scoped to a chat.
- [Telegram Bot API: getUpdates](https://core.telegram.org/bots/api#getupdates):
  long polling receives updates; offset controls confirmation; getUpdates is
  unavailable while an outgoing webhook is configured.
- [Telegram Bots FAQ: getting updates](https://core.telegram.org/bots/faq#how-do-i-get-updates):
  polling and webhooks are alternatives.

Long polling is a candidate for an initial container deployment because it
does not require a public inbound webhook endpoint. This is a technical
recommendation; deployment network reachability has not been verified.

## Confirmed extension intent

The user confirmed that Telegram is another Kisara entry point and that future
Telegram-only features are desired through an official SDK. Shared behavior
should continue to use platform-neutral application services. Telegram-specific
interactions should have their own handler/workflow boundary and a narrow
platform gateway where business orchestration is involved. The shared message
contract need not represent every native Telegram event; any native event path
must still apply the relevant authorization policy before business effects.

This is a design direction, not a commitment to implement any specific future
Telegram feature in the first release.

## Official API and library distinction

- [Telegram Bot API](https://core.telegram.org/bots/api) is the official
  HTTP interface for bots.
- [Telegram's library examples](https://core.telegram.org/bots/samples#python)
  list Python wrappers including aiogram, python-telegram-bot, and
  pyTelegramBotAPI. Being listed there is not evidence of Telegram ownership.
- [TDLib](https://core.telegram.org/tdlib) is Telegram's client library for
  building custom Telegram applications; it is a different integration choice
  from using the HTTP Bot API.
- This repository declares Python >=3.8. Any chosen wrapper version must be
  checked against the actual container runtime and supported Python versions.
  No Python upgrade or SDK selection has been approved yet.

Do not silently interpret "official SDK" as either a required TDLib dependency
or an approved community Python wrapper. Explain the distinction during planning.

## First-release scope confirmed

The user selected common commands, image replies, and daily news including
scheduled push. Full QQ parity and archive/export workflows are deferred.

Further inspection:

- `bot/commands/help.py` lists local commands, chat/tarot, provider-dependent
  public commands, and news. The final command inventory should be explicit;
  "common commands" should not accidentally imply full input/media parity.
- `bot/dispatcher.py:_is_allowed` currently checks sender allowlists for every
  accepted message and group allowlists for group messages. `_mentions_bot`
  currently reads the OneBot-shaped `qq` mention field. Telegram group scope
  needs a deliberate mapping or a compatible neutral mention field.
- `config/features/news/config.toml.example` documents UTC+8 scheduling and
  separate private/group subscriptions. Preserve QQ semantics and define how
  Telegram subscriptions are isolated if both platforms run together.
- `deploy/Dockerfile` uses Python 3.12, although the package metadata permits
  Python 3.8. A modern wrapper can run in the existing container runtime;
  package compatibility outside Docker still needs a deliberate dependency
  declaration or minimum-version decision.

## Chat scope and deployment lifecycle

The user accepted private and group chats with existing-style user/group
allowlists. Group handling needs targeted command addressing and authorization
checks in addition to basic message normalization. Channel publishing, forum
topics, and anonymous-sender support are not established by that decision.

`deploy/onebot.sh` currently runs `docker compose down` for its stop action;
`start.sh` selects one engine; `deploy.sh` delegates to the OneBot script.
If concurrent QQ/Telegram use is confirmed, lifecycle isolation needs to extend
beyond separate Python processes: an existing QQ stop action must not remove
the Telegram service. Separate Compose projects/files or deliberately scoped
stop commands are candidate designs. Keep default QQ startup compatible and
test independent start/stop behavior before delivery.
