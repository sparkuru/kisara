# Public command authorization and preview lifecycle design

## Behavior gap and ownership

The shared Dispatcher currently requires sender access for every command and
additionally group enablement/group access for groups. The initial untested
`/tguid` draft adds a Telegram-specific exception. Replace that exception with
a registered-feature policy populated once at startup from selected-engine
configuration. User decisions: dotenv configuration, equivalent platform lists,
and retention of the group master switch.

This is one deliverable: public-feature policy makes `/tguid` usable before
enrollment. Independent child tasks would split the same authorization contract.

## Configuration contract

| Deployment input | Unset default | Explicit empty |
| --- | --- | --- |
| `TELEGRAM_PUBLIC_FEATURE` | `tguid` | No public features |
| `ONEBOT_PUBLIC_FEATURE` | Empty | No public features |
| `OFFICIAL_PUBLIC_FEATURE` | Empty | No public features |

Use the singular names requested by the user. Parse comma-separated canonical
registry feature names, trimming whitespace and deduplicating entries. Names
are lowercase and have no leading slash. Reject unknown names, aliases,
features unsupported by the selected engine, native workflows and scheduled
features before opening a connection. Disabled ordinary features may be listed
but remain disabled; publishing a feature never assembles a missing service.

Append a defaulted immutable `Settings.public_features` field to preserve
existing positional constructors. Direct Settings/Dispatcher fixtures retain
conservative empty public lists unless explicitly supplied. Environment loading
provides the Telegram default. Selected-engine names win by presence, including
empty; map Compose input to internal `KISARA_PUBLIC_FEATURE`. Support this
generic internal runtime input without sharing OneBot's deployment field with
other containers. No new TOML surface, database, dependency or dynamic imports.

## Routing and authorization

Resolve a command through the existing feature registry after the established
platform normalization. Telegram requires slash commands and adapter-address
normalization; OneBot/official retain existing recognized command aliases.
Store public names keyed by engine in Dispatcher; main supplies only the chosen
engine's validated set. Unrelated engine events cannot inherit this set.

Permission for an eligible, registered public ordinary command:

| Conversation | Global access |
| --- | --- |
| Private | Sender allowlist bypassed |
| Group, groups enabled | Sender/group allowlists bypassed |
| Group, groups disabled | Denied |
| Official channel | Existing channel support, sender allowlist bypassed |
| Other unsupported kind | Denied |

Non-public messages use the original policy. Public eligibility applies only
to the resolved command feature; it must not unlock ordinary chat, unknown
commands, QQ fallback handlers, native archives, exports, or scheduled push.
In particular, the existing QQ `ping <arguments>` fallback must not become a
public path into phrasebook handling; use usage validation for callers who
require public access while retaining already-authorized legacy behavior.
Explicitly disabled registered QQ features must stop before fallback for all
callers, including `ping` with arguments; no disabled handler/provider may run.

Keep enablement/platform support and feature-owned checks before effects;
duplicate suppression still occurs once in dispatch. Existing archive/export
allowlists and recall's quoted-bot/admin validation remain in their owners.
Recall's registry support must match its actual OneBot-only handler. Its ordinary
command availability must not depend on PublicServices, because the dispatcher
owns recall without using that service; explicit disablement remains effective.
Feature names cover all existing aliases and subcommands, e.g. `help` includes
`ahelp` and Telegram `start`, and `news` includes cache clearing. Document this
so operators understand the actual scope of a configured feature.

## OneBot preparation boundary

OneBot quote enrichment for `source`/`recall` presently uses a separate strict
allowlist gate before shared dispatch. Public ordinary commands must use the
same command authorization for this preparation, without opening native Setu
or export paths. Add a narrow injected, side-effect-free command authorization
callback if needed; it must not consume dispatch deduplication. Preserve the
strict native workflow gate. Test that denied/disabled/unknown commands perform
no history lookup, and that public quote preparation plus dispatch reply still
works once. Do not broadly replace the adapter's strict authorization helper.
The preexisting preparation order can repeat a quoted-history lookup before
dispatch rejects a duplicate. Preserve that existing limitation; the pure
authorizer does not itself mark events seen, and no new history deduplication
cache or delivery guarantee is introduced.

## /tguid contract

Register `tguid` as a Telegram-only ordinary feature. It accepts no arguments,
returns only normalized `event.sender_id` as plain text, uses the existing
reply path, and neither fetches quoted users nor changes access lists.
Keep existing unsupported update filtering and bot-address checks.
The help description must reflect configuration rather than promise unconditional
public access when the operator explicitly clears the public list.

## Affected files and responsibilities

- `config/settings.py`: selected-engine parsing, validation and immutable field.
- `bot/features.py`, `bot/dispatcher.py`: registry metadata, exact feature
  permission resolution, retained validation and isolated public access.
- `bot/main.py`, `bot/adapters/onebot_v11.py`: injection and authorized quote
  preparation; other adapter protocol behavior stays unchanged.
- `.env.example`, `deploy/compose.yaml`: independent platform inputs, unset-only
  defaults for both OneBot services and other engines.
- Existing routing/settings/adapter/protocol/deployment tests: observable
  allow, deny, no-side-effect, precedence and source-UID behavior.
- `docs/operations.md`, service ownership docstring and applicable project-owned
  specs: configuration, alias scope, native limits and deployment instructions.
- Private `.env`, only if present: append the three missing keys with safe
  defaults, preserving existing/custom/empty values and formatting. Do not log
  values, create a partial dotenv, or add a permanent migration tool.

## State, failures, rollout and rollback

No persistent state or schema migration. The existing bounded in-memory
deduplication cache remains the only per-message state for lookup. A failed
send follows existing adapter diagnostics; no new retry or fake success.

Automated tests use synthetic identities/providers and protocol peers without
account credentials. Real account delivery and deployment are unrun unless
separately authorized. Dotenv changes need targeted recreation rather than
restart; document it without operating existing services.

Rollback of policy configuration is an explicitly empty selected-engine public
list; normal allowed commands still work. Source rollback removes only the
reviewed feature/config changes, preserving private data and existing work.

## Preview follow-up — approved scope

The user explicitly chose the same task for this follow-up and confirmed that
"all bots according to .env" means the `COMPOSE_PROFILES` list, not credential
detection. The public-feature source work is already checked and must be retained.
The user approved this additional design and final summary with “可用”.

### Default selection

Use one profile-list resolution for no-target down/build/start/status. Default
input is effective `COMPOSE_PROFILES`, loaded through the existing literal
dotenv parser with inherited same-key environment precedence. Stop consulting
`KISARA_ENGINE` as a selection override; it remains an application runtime field
set separately for each selected service. Explicit targets still win, including
when default selection is invalid. Missing profiles defaults to `onebot`; empty,
unknown, duplicate and conflicting OneBot modes retain errors.

### Build and settings freshness

The expected update sequence is `preview down`, `preview build`, then `preview`.
Down removes only the selected owned runtime containers, preserving volumes,
login/state/cache/media. Build validates current Compose input and explicitly
builds every selected application image, even if the tag already exists.
Current Dockerfile source COPY and package manifest supply current build context;
normal Docker cache invalidation handles changed source. New runtime credentials,
permissions and engine settings are loaded at the next container creation,
while established engine-only TOML binds retain their paths.

Prefer the existing Compose image path for all selected application bots,
including Official-only preview. Remove the special Official hako startup and
dependency-preparation path rather than maintaining two different build models.
Hako stays the offline development/test executor. Preserve exact preview
ownership identifiers; do not rename existing persisted labels.

Retain a narrow cleanup path for the existing owned Official hako identity
(`hako.service=bot`): selected Official down can stop/remove that old owned
container with data intact; start/build must prevent a duplicate conflicting
legacy instance. Do not adopt, stop or remove a non-preview container. In
particular, the previously inspected stopped ordinary Telegram deployment needs
separate user-directed migration; code work does not authorize that operation.

For auxiliary images, prepare missing prerequisites with current explicit/offline
rules; rebuilding application images does not mean blindly upgrading NapCat,
music, the base toolchain or pinned packages. Local Bot API remains staged before
Telegram where configured. Build never starts the group, and start after an
explicit build uses the prepared tag without another rebuild.

### Platform log names

Map actual owned service identities to presentation names only:

| Owned stream | Displayed source |
| --- | --- |
| napcat, kisara, kisara-dev | onebot |
| telegram | telegram |
| official (and any retained old Official diagnostic identity) | official |

Keep the selected NapCat/app stream contents. Internal ownership checks, FIFO
names, container lookup and cleanup still use unique service identities, so two
streams labeled `onebot` cannot overwrite each other's pipes/readers. Follow
progress hints and emitted `platform | log` lines use the same platform name.
Preserve incremental credential redaction, history count, continuous following,
status exit codes and interruption cleanup. Music/local API success streams stay
omitted. Ready summaries/ownership diagnostics may still use service identities
where needed to identify actual infrastructure; the requested change is log
source labeling, not Docker service renaming.

### Affected boundary and evidence

Implementation belongs in `deploy/preview-runtime.sh` and its existing console
helper, with root/engines forwarding changed only if required. Update existing
preview lifecycle/CLI fixtures, operations and relevant project-owned specs.
No bot business-service refactor, dependency upgrade, automatic dotenv rewrite,
new command runner, live startup or credential use is included.

Test no-target profile selection with a conflicting KISARA_ENGINE; mixed and
Official-only build paths; down/build/start with changed source/settings and
existing images; no duplicate rebuild on start; explicit-target isolation;
foreign/legacy ownership boundaries; platform prefix mapping for both OneBot
streams; redaction/readers/Ctrl+C preservation and all native/public regressions.
Synthetic Docker peers establish routing/lifecycle calls; actual account or
network readiness remains unverified unless separately authorized.
