# Telegram /tgsetu command availability and local-only deployment

## Goal

Make the approved Telegram `/tgsetu` workflow discoverable and usable through
the selected local-only Telegram Bot API deployment. When the feature is
explicitly enabled and the sender is authorized, `/help` must list `/tgsetu`
and `/tgsetu on` must reach the native TgSetu workflow instead of returning the
generic unavailable reply. Preserve the existing explicit opt-in,
authorization, Telegram-only scope and archive behavior.

The selected runtime is Kisara's native Telegram engine talking only to the
internal official `telegram-bot-api` service. This is a deployment choice, not
an adoption of a Telegram-to-OneBot bridge. The source may retain an explicit
cloud-mode compatibility path for other deployments, but this task must not
use cloud fallback for the selected Bot or silently switch endpoints.

The user's priority is architectural correctness over deployment effort or
cost. The decision therefore follows platform semantics and ownership
boundaries, not the number of containers: Telegram-native workflows stay on a
Telegram adapter; OneBot remains an independent protocol boundary.

## Confirmed facts

- User report (2026-10-14): sending `/tgsetu on` to the Telegram bot returns
  `This feature is unavailable. Try /help.`; the returned `/help` list does not
  contain `/tgsetu`.
- The static feature registry declares `tgsetu` as a Telegram-only native
  feature: `src/kisara/bot/features.py:41`.
- The generic response is emitted when a registered feature is not eligible:
  `src/kisara/bot/dispatcher.py:156-161`; the native fallback itself also
  returns that response at `src/kisara/bot/dispatcher.py:193-195`.
- Telegram startup loads
  `<engine config root>/features/tgsetu/config.toml` and passes its `enabled`
  value into the dispatcher: `src/kisara/bot/main.py:73-79,135-145`.
- `TgSetuConfig.load()` treats a missing file as disabled:
  `src/kisara/config/tgsetu.py:29-31`. The workspace-local runtime file was
  disabled and ignored by Git; the example carries the same safe default.
- Existing tests cover a synthetic enabled config and assert that `/tgsetu`
  appears in Telegram help (`tests/unit/test_telegram_settings.py:242-265`),
  but the reported runtime symptom was an effective-config/deployment issue,
  not an unregistered command.
- Live evidence (2026-10-14): the Docker Compose target is
  `kisara-telegram-1`; it mounts workspace `config/telegram` read-only at
  `/app/config/telegram`. Its effective TgSetu file had `enabled = false`.
  The global Telegram allowlist contained the reporting sender, while the
  feature file still had only the example user list.
- Live environment evidence (values intentionally not recorded):
  `TELEGRAM_LOCAL_MODE=false`, `TELEGRAM_API_BASE_URL=https://api.telegram.org`,
  and both `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` were empty. No local Bot
  API container existed. Logs confirmed the reported `/help` and `/tgsetu on`
  responses.
- Enabling the existing feature with that environment would fail the startup
  guard in `src/kisara/bot/main.py:80-82`; the current TgSetu media gateway
  requires local Bot API cache paths.
- `TELEGRAM_BOT_TOKEN` is sufficient for ordinary cloud Bot API polling and
  sending. `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are credentials for the
  self-hosted local Bot API server, not a second Bot token. The local server
  still connects to Telegram's servers and Kisara's requests still carry the
  BotFather-created token.
- Parent-task delivery already contains the local Bot API Docker implementation:
  `deploy/telegram-bot-api.Dockerfile`, its entrypoint and probe, the Compose
  `telegram-bot-api` service/profile, matching cache volume and lifecycle
  readiness. The live configuration had not selected that profile.
- The local server is an HTTP implementation of Telegram's Bot API, not a
  Telegram user client and not an OneBot endpoint. It still connects to
  Telegram's servers and therefore does not make the Bot independent of the
  Telegram network.
- OneBot's official ecosystem distinguishes a platform-facing OneBot
  implementation from an SDK and lists Telegram implementations under
  OneBot 11/CQHTTP, including
  [`Gensokyo-telegram`](https://github.com/hoshinonyaruko/gensokyo-telegram)
  and [`Tele-KiraLink`](https://github.com/Echomirix/Tele-KiraLink).
  `Gensokyo-telegram` documents Telegram Bot API polling/webhook plus a
  OneBot v11 reverse WebSocket; Tele-KiraLink documents a Java Telegram Bot
  API backend and OneBot v11 WebSocket/API compatibility. These are separate
  Telegram-to-OneBot protocol servers, not features of the official local Bot
  API. See the [official OneBot ecosystem list](https://onebot.dev/ecosystem).
- Mainstream NapCat/Lagrange/go-cqhttp usage remains a QQ-side OneBot
  deployment. A Telegram OneBot implementation is therefore possible, but it
  must own the Telegram Bot API update/send path and is a separate architecture
  from Kisara's native Telegram engine.

## Architecture decision

Keep the native Telegram engine with the official local Bot API as the selected
architecture even when operational cost is not a concern:

- `telegram-bot-api` is the correct local transport/backend for a Telegram Bot;
  it preserves Telegram Bot API semantics and the existing `file_id`, album,
  caption, message-ID and local-cache contracts.
- OneBot v11 is not a lossless platform-neutral domain model. Its public API is
  strongly QQ-shaped (for example group administration, friend requests and
  QQ-style identifiers), while TgSetu is deliberately Telegram-native.
- A Telegram-OneBot implementation is a valid integration when the goal is to
  reuse OneBot clients/plugins. It should be an explicit additional adapter or
  separate Bot, not a replacement transport hidden behind Kisara's native
  Telegram feature. Making it the current Bot's transport would add a semantic
  translation boundary and a second protocol owner without solving a current
  product requirement.
- If future product scope requires one application to serve Telegram and QQ
  through one business layer, the right follow-up is to move genuinely shared
  behavior behind Kisara's normalized contracts or adopt a multi-platform
  framework with separate Telegram and OneBot adapters. It is not to make the
  Telegram Bot API server speak OneBot.

## Requirements

| ID | Outcome |
| --- | --- |
| R1 | Record the concrete reason the reported runtime omitted `/tgsetu` from `/help`, distinguishing disabled feature configuration from sender authorization. |
| R2 | With the dedicated feature explicitly enabled and the sender authorized, expose `/tgsetu` in Telegram `/help` and route `/tgsetu on` to the native TgSetu service. |
| R3 | Keep missing or explicitly disabled configuration safe and deterministic: no archive/SDK effects, no accidental auto-enable, and an accurate help surface. |
| R4 | Preserve Telegram-only scope, private-chat and user authorization checks, `/setu` isolation, archive naming/queue semantics, and existing OneBot behavior. |
| R5 | Add or adjust focused regression coverage for the effective configuration/startup boundary and local-only deployment contract. |
| R6 | Run the selected Telegram Bot only through `http://telegram-bot-api:8081`; start and health-check the local service before Telegram, with no cloud endpoint fallback in that runtime. |
| R7 | Keep `TELEGRAM_BOT_TOKEN` in the Bot process configuration and pass `TELEGRAM_API_ID`/`TELEGRAM_API_HASH` only to the local Bot API service; never treat either pair as interchangeable. |
| R8 | Use a controlled one-time cloud-to-local Bot API cutover, including cloud `logOut` as required by Telegram, without deleting Bot state, local cache or TgSetu archive data. |
| R9 | Keep OneBot separate from the local Bot API. Record verified Telegram OneBot implementations and their boundaries, but do not add a Telegram-OneBot bridge or reroute Kisara's Telegram feature through OneBot in this task. |

## Acceptance criteria

| ID | Observable result | Maps to |
| --- | --- | --- |
| A1 | Task evidence explains why the live `/help` omitted `/tgsetu`: the dedicated config was disabled, while the global sender authorization was not the cause. | R1 |
| A2 | Focused tests prove that an explicitly enabled, authorized Telegram feature lists `/tgsetu` and reaches native handling, while missing/disabled config remains inert. | R2, R3, R5 |
| A3 | The local Bot API image, Compose service/profile, cache mount, UID and health probe remain covered; local deployment rejects missing/invalid API ID/hash and wrong endpoint before switching the Bot. | R5, R6, R7 |
| A4 | After the controlled cutover, the Telegram container receives updates through the internal local endpoint, the local server is healthy, and `/help` lists `/tgsetu`; `/tgsetu on` no longer returns the generic unavailable response. | R2, R6, R8 |
| A5 | Bot token, API ID/hash, Telegram state, local cache and TgSetu archive remain in their separate ownership boundaries; rollback does not delete or reset them. | R7, R8 |
| A6 | Existing OneBot tests and runtime are unchanged. Task documentation states that Telegram OneBot cases exist, but `telegram-bot-api` itself does not speak OneBot and no bridge is installed by this task. | R4, R9 |

## Scope boundaries

In scope: offline diagnosis, local-only configuration/startup validation,
focused tests and documentation, enabling the already implemented TgSetu
feature in the ignored runtime TOML, the controlled Bot API cloud-to-local
cutover, targeted Telegram recreation, and authorized command smoke checks.

Out of scope: automatic enablement when configuration is absent, relaxing
authorization, adding a Telegram `/setu` alias, cloud-download fallback or a
second media backend, changing archive naming/queue semantics, replacing the
native Telegram adapter with OneBot, adding Gensokyo/Tele-KiraLink/tgonebot,
credential rotation, deleting volumes/files, or unrelated live services.

The source-level cloud endpoint support is retained as an explicit compatibility
path for other deployments and rollback planning; it is not selected for this
Bot and is not a runtime fallback in this task.

## Operational prerequisites

- The operator must populate the private repository `.env` with a valid
  `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` obtained from `my.telegram.org`.
  Values must not be pasted into chat or committed.
- `TELEGRAM_BOT_TOKEN` and the existing Telegram allowlist must remain valid.
- A cloud-to-local switch requires stopping the current token owner and the
  documented one-time cloud `logOut`; the local server must then become the
  sole update owner. No second poller may run during the switch.

## Planning status

The user selected local-only Telegram deployment and requested a OneBot/TG
ecosystem check. Research is complete: Telegram OneBot implementations exist,
but they are separate protocol endpoints and are not part of this repair.
Planning was approved on 2026-10-14 and the implementation phase is active.
Offline implementation and verification are complete. Live account changes
remain intentionally pending until the private local Bot API credentials pass
preflight; no credential values belong in this task record.
