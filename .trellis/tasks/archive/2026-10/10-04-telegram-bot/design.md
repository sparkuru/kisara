# Telegram, Compose profiles, and feature routing design

Status: implementation and review complete; committed as `1152184` on
`feat/telegram-bot`. Live account setup/acceptance remains pending.

## Deployment

Use one Compose application with engine profiles. The deployment .env selects:

    COMPOSE_PROFILES=onebot,telegram

OneBot owns the existing Kisara/NapCat pair; Telegram owns a separate bot service;
official owns its optional bot service. Each process receives one KISARA_ENGINE.
Profiles are the deployment selector; process identity is not another competing
engine-list setting. Optional music infrastructure uses a separate optional
profile and shared internal networking, without publishing its provider port.

Preserve the current QQ service/volume/project/login identities. Existing
single-engine helpers keep their defaults when profile selection is absent;
the unified entrypoint uses explicit profiles when configured. Reject conflicting
OneBot production/development ownership. Document direct Compose commands and
wrapper overrides, which may explicitly target a service despite its profile.

A shared .env is used for interpolation. Explicit environment mappings supply
only each engine's credentials and access/settings values; do not inject the
whole file into every container. Use namespaced Telegram deployment fields mapped
to common runtime settings. Mount Telegram feature configuration independently
at /app/config and a separate state volume at /app/state. Keep QQ configuration,
SQLite, login data, archived media, fonts, and art mappings usable as before.

Changing profile selection affects startup; it does not stop a previously
running engine automatically. Provide targeted stop/restart/rebuild operations.
A whole-stack operation is explicit. Ordinary stop retains volumes. Build
tags/targets cannot cause one engine's rebuild to replace another running bot.

References: [Compose profiles](https://docs.docker.com/compose/how-tos/profiles/)
and [predefined variables](https://docs.docker.com/compose/how-tos/environment-variables/envvars/).

## Feature routing

Use the normalized message path:

    adapter -> authorization/deduplication -> feature router
      -> feature enabled/platform supported -> handler/service
      -> structured reply -> source adapter

Reuse existing authorization and message contracts. Add an explicit typed
registry for feature names, aliases, help metadata, supported engines, and
handlers. Shared check/help/news/music handlers use existing services.
Keep existing QQ-only command/workflow owners, semantics, and fallback behavior
compatible; Telegram's effective inventory contains only its five features.
Do not require migrating unrelated QQ media workflows to implement this release.

The router's effective inventory is the source of help and feature eligibility.
Registration is static code, not plugin discovery or import paths supplied by
configuration. Match aliases only once and check enablement before business
effects. Future SDK-native Telegram handlers join feature authorization and
enablement without being fabricated as text commands.

Use established feature TOML loading with enabled fields for ping/help/music,
and enabled plus push_enabled for news. These correspond to independently
registered news and news_push triggers. Explicit TOML overrides environment
fallbacks; missing flags default enabled for compatibility. Empty recipient
lists disable scheduling even when push_enabled is true. Explicit false stops
that feature's handlers/workers after restart. Preserve existing QQ chat/tarot/
setu settings and defaults.

Each definition declares supported engines independently of configuration.
Disabled or unsupported Telegram slash commands return concise unavailable/help
guidance without business effects; ordinary non-command messages stay silent.
Unknown slash commands do not echo arbitrary message text. QQ responses and
aliases remain as currently defined. Help/onboarding cannot grant authorization.

News generation is assembled when either news or news_push requires it.
Music-provider absence retains a clear unavailable/configuration response.
Provider failures and invalid arguments preserve structured dispatch outcomes.

## Platform adaptation

Keep raw SDK events/objects/API calls in platform adapters. Shared services use
normalized inputs and outputs. Narrow platform gateways own native actions
when necessary. Telegram normalizes /command@this_bot, ignores other bot targets,
and preserves native reply context. Include chat scope in Telegram message
identity or the shared deduplication key; equal message IDs in different chats
must not collide. Advertise Telegram's native `/news_clear`, adapting it to the
existing news maintenance route. Native Telegram command names use letters,
digits and underscores; existing QQ naming remains unchanged.

Private/group/supergroup messages are supported with user/group allowlists.
Explicit bot-addressed commands work with group privacy mode. Ignore channel,
edited/service-only, anonymous-sender, and unsupported topic-specific events.
Neither Telegram allowlisting nor /start implies a scheduled subscription.

OneBot music-card output remains unchanged. Telegram uses music title/artist/
public link. Official support retains its current channel behavior; scheduled
news has adapters only for OneBot/Telegram, with unsupported capability shown
accurately rather than silently enabled.

## Telegram library and lifecycle

Use pinned python-telegram-bot==22.8 as a Telegram-only optional dependency.
It is a community Python wrapper around the official Bot API. The existing
Python 3.12 runtime is compatible; Telegram installation requires Python 3.10+.
Base/OneBot installation does not import or require PTB; errors identify the
missing Telegram extra clearly.

Use outbound long polling with finite timeouts, a bounded queue, owned startup/
shutdown, and sequential command processing. Execute blocking shared services
outside the event loop. Avoid SDK create_task ownership of an infinite scheduler
if it would make stop wait forever; explicitly cancel/await owned background work
before completing shutdown. Verify lifecycle details against the pinned library.

Do not drop pending updates by default or promise restart-exact command
deduplication/full offline capture. Invalid credentials and competing pollers
have sanitized diagnostics. Suppress token-bearing HTTP request logging and
raw SDK/provider exception text. Tests use synthetic secret-bearing failures.

## News output and scheduling

Expose neutral PNG bytes/attachments from DailyNewsResult while preserving
onebot_image() behavior for all existing QQ callers. Telegram news uses one
captioned PNG document for readability and one send operation per target.
Preserve the source/date and publication-delay notice in the caption/image.
Text-only replies split within Telegram limits with plain formatting.

Register news_push as a scheduled feature whose eligibility controls task
creation. Keep QQ's existing scheduler as a compatibility runner with its current
timing, retry, and completion tables. A Telegram scheduled-feature runner uses
the same generator and a narrow Telegram delivery gateway; do not move or change
unrelated QQ scheduling behavior to satisfy a common abstraction.

Telegram state records day, target kind/ID, status, next-attempt time, and optional
returned message ID. Claim atomically before sending; do not hold a SQLite
transaction across network work. Confirmed sends record success. Known transient
rejections/generation failures retry after 15 minutes or a longer retry-after;
permanent permission/target failures do not repeat that day.

Unknown network send results remain uncertain and are not automatically resent.
On restart, unfinished claims become uncertain. A confirmed remote send followed
by a failed local completion write leaves claim evidence so restart cannot resend
it as new. Retain 30 days of records, preserve separate target kinds, and catch up
today only. A successful warned fallback counts as the day's completion.

Private Telegram recipients must have started the bot and groups must permit
sending. These conditions require real-account verification; a configured ID
alone does not prove them.

## Verification and rollback

Use fake SDK/OneBot protocols and recording Compose commands for routing,
switches, isolation, output, recovery, and migration checks. Preserve the entire
existing QQ test suite. Compare current QQ behavior/configuration fixtures,
including random-chat, tarot, archive/export/recall, to avoid broad refactor drift.

Validate one-engine/combined/official selection with placeholder inputs; never
print rendered real secrets or change live services for automated checks.
Rollback restores code/images/Compose while retaining existing state/login
volumes. Shared changes must pass QQ regressions before delivery.

## Evidence

- [Repository fit](research/repository-fit.md)
- [Library investigation](research/telegram-library.md)
- [Routing and Compose investigation](research/feature-routing.md)
- [Architecture](../../../../spec/trellis-plus/architecture.md)
- [Configuration/storage](../../../../spec/trellis-plus/configuration-storage.md)
- [Validation](../../../../spec/trellis-plus/validation.md)
