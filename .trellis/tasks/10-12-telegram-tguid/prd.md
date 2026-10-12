# Public features, Telegram /tguid and preview lifecycle

## Goal

Let a Telegram user obtain their own numeric UID before the operator adds them
to the user allowlist, through a public-feature list independently owned by each
engine. Task creation was approved on 2026-10-12.
The user subsequently requested preview build/start/status improvements and
explicitly chose to extend this same task rather than create another task.

## Background

The protocol-neutral Dispatcher is shared by OneBot, official QQ, Telegram and
local console. Existing Telegram private commands require sender allowlist
membership; group commands additionally require group enablement and group
allowlist membership. Telegram normalization already supplies the sender UID
and rejects commands addressed to other bots.

The user asked whether public lookup requires major authorization changes and
whether Dispatcher is shared with OneBot. The authorization exception must be
explicitly limited to the Telegram engine and exact `/tguid` command.
The user subsequently requested a `TELEGRAM_PUBLIC_FEATURE` list and equivalent
support for OneBot and the other bot engines, replacing the command-specific
exception with a shared public-feature policy.

## Requirements

- `/tguid` returns only the sender's own numeric Telegram UID as plain text.
- Provide independently owned public-feature lists for Telegram, OneBot and
  official QQ. A platform's list must not configure another platform.
- Public lists are `.env` configuration, explicitly selected by the user:
  `TELEGRAM_PUBLIC_FEATURE`, `ONEBOT_PUBLIC_FEATURE`, and
  `OFFICIAL_PUBLIC_FEATURE`. Values are comma-separated canonical feature names.
  Unset Telegram defaults to `tguid`; unset OneBot/official defaults to empty.
  An explicitly empty value disables public access for that engine.
- Resolve public entries through the existing feature registry rather than
  inventing a second command inventory. Exact alias matching must not grant
  public permission to unrelated or prefix-like commands.
- Supported Telegram users can use it without user allowlist membership.
  The user explicitly chose to retain the group master switch: public group
  commands require that engine's `GROUPS_ENABLED=true`, then bypass sender and
  group allowlists. Private public commands bypass the sender allowlist.
- `/tguid@ThisBot` works; another bot's addressed command stays ignored.
- Features absent from the selected public list retain existing authorization.
  All public features retain platform support, enablement, argument validation,
  duplicate suppression and their feature-specific restrictions. Lookup neither
  enrolls the sender in the allowlist nor modifies configuration.
- Public lists cover registered ordinary command features. Scheduled tasks and
  dedicated native archive/export workflows retain their existing authorization.
  Unknown names, aliases in place of feature names, unsupported platforms, and
  non-command features are configuration errors rather than ignored entries.
- Lookup retains existing chat-scoped duplicate suppression.
- Arguments yield usage guidance; other-user lookup is outside this change.
- Telegram help and existing operational documentation describe the public scope.
  Unsupported/anonymous/channel/topic updates retain their existing behavior.

## Acceptance Criteria

- An unlisted user receives their own UID in private chat with an empty allowlist.
  In groups, lookup works with empty user/group allowlists when group handling is
  enabled, and produces no reply when group handling is disabled.
- The returned value is the sender ID, rather than the group/chat/quoted user's
  ID. Commands addressed to other bots produce no reply.
- With only `tguid` public, an unlisted sender receives no reply or provider
  effects for other commands.
  Prefix-like command names do not inherit public permission.
- Empty OneBot/official public lists preserve their existing allowlist behavior.
  Adding a supported feature to one engine's public list does not expose it on
  another engine. Local console behavior remains unchanged.
- Explicitly clearing a public list does not restore its default or another
  engine's list. Disabled/unavailable features and argument-bearing commands
  cannot use public permission to enter another feature's fallback handler.
- Duplicate events do not produce another reply; equal message IDs in different
  Telegram chats remain independent.
- Argument guidance and Telegram help agree with the requirements.
- Focused routing/Telegram protocol checks and the normal full suite pass, or
  an environment limitation is reported accurately.

## Out of Scope

Automatic allowlist enrollment, other-user lookup, new dependencies, live account
operations, deployment, and changes to the pending TgSetu task. Commits were
initially excluded; the later “提交” instruction authorizes local delivery only.

## Preview Follow-up Requirements

- The default `preview down` -> `preview build` flow must prepare bot containers
  using current repository source and effective configuration. The next
  `preview` start must use those rebuilt artifacts and current settings.
- No-target `./kisara.sh preview` must start all bots selected according to
  `COMPOSE_PROFILES`, explicitly chosen by the user. It must not narrow that
  list using `KISARA_ENGINE` or infer activation from credential presence.
  Existing same-key environment-over-dotenv precedence remains; explicit command
  targets override defaults. An absent list defaults to OneBot; empty is invalid.
- `preview status` log source display must use platform names such as `onebot`
  and `telegram`, rather than `napcat`/`kisara` service names. Retain gateway and
  application content: NapCat and both OneBot app variants display as `onebot`,
  Telegram as `telegram`, and Official as `official`.
- A selected bot uses a built application image, including Official-only
  preview, so build/start behavior is consistent for single and mixed selections.
  Docker layer caching is valid; this change does not upgrade pinned dependencies
  or force downloading unchanged auxiliary images.
- Preserve public-feature behavior already implemented and verified, data,
  strict permissions, secret redaction and status reader-only interrupt cleanup.

### Confirmed Existing Behavior

- No-target preview currently lets `KISARA_ENGINE` override `COMPOSE_PROFILES`.
- Explicit `preview build` already rebuilds selected Compose bot images, while
  Official-only preview uses a mounted hako runtime. Start reuses existing
  matching previews and only prepares missing images/dependencies.
- Status presently follows both OneBot application and NapCat gateway streams.
- A stopped ordinary Telegram deployment exists; preview refuses containers
  without preview ownership. No removal/conversion/live deployment is authorized.

### Preview Acceptance Criteria

- With `COMPOSE_PROFILES=onebot,telegram,official`, no-target down/build/start
  consistently select those bots even if `KISARA_ENGINE=onebot` is present.
- Editing source or effective settings, then down/build/start, uses current
  application build input and new settings; build itself never starts services.
- All selected application images rebuild even if old images already exist.
- Explicit targets still isolate other engines and do not rewrite `.env`.
- Status follows the selected bot/gateway streams with platform prefixes; old
  service names are absent from the displayed log-source prefix and follow hint.
- Ctrl+C/TERM stop only status readers; redaction, readiness, volumes/state,
  strict preview ownership, offline mode and credential validation are retained.
- Existing owned Official hako previews can be cleaned up through the explicit
  selected preview-down lifecycle without orphaning or concurrently running a
  duplicate Official bot. Foreign deployments are not implicitly removed/adopted.
- Focused lifecycle/CLI checks, appropriate shell checks and the full regression
  suite pass, while preserving previously verified public-feature behavior.

## Planning Status

The user approved the public-feature planning summary with “开始” on 2026-10-12;
that implementation/checking is complete with the recorded 997-pass full gate.
The user approved the updated preview design/plan and final summary with “可用”.
Preview implementation and offline validation are now authorized in this task.
The original implementation scope spans
configuration, shared routing, OneBot command preparation and deployment wiring.
See `design.md`, `implement.md` and `validation.md`. The initial untested
route/help draft was replaced by the approved per-engine public policy and
mandatory group master switch; recorded tests cover that final implementation.
