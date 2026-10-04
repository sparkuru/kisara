# Telegram entry point, engine selection, and feature routing

## Goal

Add Telegram as another Kisara entry point offering online checks, help, news,
scheduled news, and music. Select concurrent engines through Compose and .env.
Route incoming messages to explicitly enabled, platform-adapted features, with
an extension path for Telegram-only functionality.

## Background

Kisara has separate platform adapters, normalized message/reply contracts,
access rules, shared application services, and feature-local persistence.
OneBot is the default engine and Tencent official support is optional.
Telegram adds another adapter, using independent credentials, IDs, configuration,
and durable state. Private and group access follows user/group allowlists.

## Requirements

- R1: Implement Telegram in this repository and reuse shared news/music behavior.
- R2: Preserve all existing QQ functions, commands/aliases, workflow behavior,
  configuration defaults, account/login state, and news completion records.
- R3: Define and verify the Telegram command, switch, routing, and deployment
  contracts before delivery.
- R4: Isolate engine credentials, access IDs, subscriptions, and state. One .env
  may select engines and contain deployment inputs, while each container receives
  only its required credentials.
- R5: Provide an extension boundary for native Telegram handlers without requiring
  equivalent QQ features or reducing native interactions to plain text.
- R6: Use Telegram's supported Bot API through a maintained Python wrapper and
  document library ownership/runtime requirements accurately.
- R7: Telegram offers /ping, /help, /news, /music <query>, and scheduled news.
  /start provides help/onboarding; news-cache clearing is a news maintenance
  action. Music returns the existing title/artist/link result on Telegram.
- R8: Only allowed private users and allowed users in enabled, allowlisted groups
  invoke business behavior. Scheduled private/group targets must be authorized.
- R9: Selected engines run concurrently in distinct processes/containers.
  Targeted lifecycle operations preserve other running engines and their state.
- R10: .env selects one or multiple engine profiles for Compose startup.
  Inactive engines and exclusive dependencies do not start automatically.
  Existing single-engine startup has a documented compatible migration path.
- R11: The five Telegram features expose independent effective switches and
  platform adaptation. Disabled functionality does not invoke handlers/providers
  or create background work.
- R12: Incoming messages pass through authorization, feature/alias matching,
  enablement/platform checks, execution, and source-engine replies. Use explicit
  registration instead of a duplicated Telegram dispatcher or plugin discovery.
- R13: Help reflects the current engine's enabled/supported inventory. Aliases
  cannot bypass switches. Manual news and scheduled news are independent.

## Acceptance criteria

- AC1 (R7, R8): Authorized Telegram private/group users receive correct responses
  for /ping, /help, /news, /music; other users/chats cause no business/provider
  effects. /start never grants access or creates a subscription.
- AC2 (R7): News preserves date, attribution, readable PNG output, and publication-
  delay warnings. Cache maintenance does not clear other engines' caches.
- AC3 (R8, R13): Authorized configured private/group recipients receive news at
  the configured UTC+8 time. Confirmed completions survive restart; known failures
  and unknown outcomes have distinct documented recovery behavior.
- AC4 (R9, R10): OneBot-only, Telegram-only, and combined .env selections start
  the expected services/dependencies. Targeted stop/rebuild leaves other engines
  and state intact. Existing official support remains selectable.
- AC5 (R4, R11): Inactive-engine credentials are not required by active engines,
  and containers receive only their required secrets. A disabled feature invokes
  no handler/provider; disabled push starts no loop.
- AC6 (R12, R13): Registry, aliases, help, switches, and adaptation agree.
  Unsupported Telegram commands never fall into QQ-only behavior or echo/chat.
- AC7 (R2): Existing QQ behavior/configuration/state stays compatible, verified
  against the current full regression suite and deployed completion fixtures.
- AC8 (R5, R6): Shared services remain SDK-free; native future Telegram handlers
  have an explicit registration/authorization boundary.

## Out of scope

Other Telegram feature families; native music-card/audio-download parity;
generic plugins; future Telegram-only product features; cross-platform identity
merging/bridging/failover; exactly-once guarantees; source/resource cleanup;
runtime-data deletion; live deployment merely from planning consent.

## Key behavior and limitations

Feature defaults permit the five Telegram features; scheduled work still requires
explicit recipients. Missing music-provider configuration produces a clear command
response rather than a fabricated result. Effective feature settings are loaded
at startup and applied after restart. Group use supports explicit bot-addressed
commands; ordinary messages stay silent.

Scheduled delivery catches up today only. A successful labeled publication-delay
fallback completes that day's push. Unknown send outcomes do not trigger automatic
Telegram resending; /news remains available for manual retrieval. Live account,
provider, and network behavior requires separate acceptance evidence.

## Artifact status

PRD, design, implementation plan, and curated context manifests were approved.
Implementation and independent review passed; the user approved commit
`1152184` on `feat/telegram-bot`, with real account acceptance still pending.
