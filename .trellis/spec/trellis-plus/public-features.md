# Per-engine public ordinary command features

## 1. Scope and trigger

Applies to global command access and Telegram `/tguid`. User decisions on
2026-10-12: configure independent engine lists in `.env`, retain the group
master switch, and implement the reviewed policy. Public access bypasses only
global sender/group allowlists for the resolved ordinary command; it does not
enable features or grant broader conversation access.

## 2. Signatures

- `Settings.public_features: FrozenSet[str]`: immutable startup names, appended
  with an empty constructor default for existing fixtures/callers.
- `Settings.from_environment() -> Settings`: selected namespace resolution,
  canonical registry validation and environment defaults.
- `Dispatcher(..., public_features: Optional[Mapping[str, FrozenSet[str]]])`:
  engine-keyed sets; main injects only the chosen engine's validated set.
- `Dispatcher.authorize_command(event: MessageEvent, feature: str) -> bool`:
  side-effect-free exact ordinary-command authorization for OneBot quote
  preparation, without consuming duplicate tracking.
- `/tguid`: no arguments, Telegram only, plain text sender UID.

## 3. Configuration and behavior contracts

| Deployment input | Unset default |
| --- | --- |
| `TELEGRAM_PUBLIC_FEATURE` | `tguid` |
| `ONEBOT_PUBLIC_FEATURE` | Empty |
| `OFFICIAL_PUBLIC_FEATURE` | Empty |

Names are singular, case-sensitive canonical feature names, without a slash,
comma-separated and trimmed/deduplicated. Selected names win by presence,
including an explicitly empty value. Compose maps each engine's input to
internal `KISARA_PUBLIC_FEATURE`; both OneBot services use their OneBot list.
Generic internal runtime input is supported; deployment inputs do not leak
between engines. Missing Telegram input uses the default, while an explicitly
empty input provides no public exception. No new TOML, state or DB schema.

Validate against the static registry: unknown names, command aliases used as
feature names, unsupported platforms, native features and scheduled features
are configuration errors. Listing a disabled ordinary feature is valid but
does not enable it or assemble a missing service.

Registered aliases/subcommands share their feature's public status: `help`
includes `ahelp` and Telegram `start`; `news` includes cache clearing. Resolve
the exact normalized registered command before granting access. Unknown and
prefix-like commands, plain chat fallback and unrelated handlers cannot inherit
the permission. Preserve already-authorized QQ legacy behavior; a public caller
using `ping <arguments>` receives usage guidance rather than chat fallback.
Explicitly disabled registered QQ features return unavailable before any
fallback, including `ping` with arguments. Recall is a OneBot-only ordinary
command owned by Dispatcher, with no PublicServices availability dependency;
its configured disablement, quoted-bot validation and group admin rule remain.

Private public commands bypass sender membership. Public groups require
`groups_enabled`, then bypass sender/group membership. Disabling group handling
denies public commands too. Official channel support retains its existing
conversation behavior with the public sender exception. Unsupported normalized
conversation kinds are denied. Other messages follow existing allow rules.

OneBot quoted `source`/`recall` preparation may use the injected pure command
authorizer. It must check the resolved feature and effective inventory before
history lookup, without consuming the later dispatch deduplication. Native
Setu/image export/TgSetu and scheduled news keep their existing strict gates;
public configuration does not replace dedicated or administrator checks.
The existing OneBot preparation order may repeat a quoted-history lookup before
dispatch rejects a duplicate; public policy adds no new history-dedup cache or
stronger delivery guarantee.

`/tguid` returns `event.sender_id`, never chat/group/quoted-user IDs. It grants
no access, performs no external query and accepts no alternate-user argument.
Telegram adapter addressing/filtering and chat-scoped dispatch deduplication
remain effective. A failed send uses the existing safe adapter diagnostics,
without new retry state. Help describes the command independently of whether
the operator has made it public.

Receive/send log disclosure remains controlled by the original allowlists and
opt-in logging switch; public callers are not automatically added to detailed
conversation logging.

## 4. Validation and error matrix

| Case | Required behavior |
| --- | --- |
| Telegram input absent | Public `tguid` only |
| Input explicitly empty | No public feature; allowed commands still work |
| Another engine input set | No effect on selected engine |
| Invalid/alias/native/scheduled/unsupported name | Startup ConfigurationError |
| Public feature disabled or service missing | No provider or quote effects through public permission |
| Public group, group switch false | Silent denial despite empty allowlists |
| Public group, group switch true | Eligible command works without sender/group membership |
| Public command alias | Same access as canonical feature |
| Similar prefix or ordinary text | Original policy; no public fallback |
| `/tguid` with arguments | Error status with usage guidance |
| Addressed to another Telegram bot | Ignored before dispatch |
| Duplicate dispatch | No repeated handler/reply within existing cache lifetime |
| Native workflow or scheduled recipient | Existing strict authorization unchanged |

## 5. Good, base and bad cases

Good: `TELEGRAM_PUBLIC_FEATURE=tguid,help` lets a new user obtain their UID and
help privately; `/start` shares help's permission. Base: public OneBot/official
lists stay empty and their normal access rules are preserved. Bad: using public
`ping` to invoke phrasebook fallback or clearing a list with a nonempty-default
interpolation that silently restores `tguid`.

## 6. Tests required

Settings/deployment checks cover defaults, explicit empty, canonical validation,
selected-engine isolation, internal runtime mapping and both OneBot services.
Routing checks cover private/group/channel cases, retained group switch, enabled
and missing services, aliases, argument errors, engine isolation, native denial
and public QQ fallback prevention. Adapter/protocol checks assert actual source
UID and source reply chat/quote, another-bot silence, duplicate replies,
equal message IDs across Telegram chats and authorized OneBot quote preparation.
Use synthetic providers/peers through the existing offline Docker wrapper; real
account delivery is separate evidence.

## 7. Wrong versus correct

Wrong: grant public access by command prefix, copy each adapter's permission
logic, bypass group enablement, or authorize native export because another
ordinary feature is public. Correct: resolve one registered ordinary feature,
check its engine-specific public membership and effective availability, retain
the group switch and feature-owned restrictions, then execute the existing path.

Wrong: `${TELEGRAM_PUBLIC_FEATURE:-tguid}` revives permission after explicit
empty. Correct: `${TELEGRAM_PUBLIC_FEATURE-tguid}` distinguishes unset from empty.
