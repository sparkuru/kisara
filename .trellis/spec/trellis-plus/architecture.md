# Architecture and Feature Contracts

- ownership: project-shared
- source: project-authored
- evidence: `docs/application-template.md`, `src/kisara/bot/contracts.py`,
  `src/kisara/bot/dispatcher.py`, `src/kisara/bot/main.py`

## Scope and responsibilities

The startup entrypoint assembles dependencies in `bot/main.py`. It imports
only the selected adapter. OneBot is the default engine; official and Telegram
SDK support is optional. A process runs one engine; Compose can run independent
engine containers concurrently. Hot switching, plugin discovery, and automatic
cross-engine failover are not current features.

| Location under `src/kisara/` | Responsibility |
| --- | --- |
| `bot/contracts.py` | Normalized messages, reply payloads, adapter interfaces |
| `bot/adapters/` | Protocol parsing, lifecycle, requests, receipts, sending |
| `bot/dispatcher.py`, `bot/features.py` | Access rules, bounded deduplication, explicit feature/alias routing and effective help |
| `bot/commands/` | Simple command parsing and output |
| `application/services/` | Feature behavior and orchestration |
| `config/` | Startup configuration parsing and validation |
| `infrastructure/integrations/`, `persistence/` | HTTP, SQLite, file storage |
| `resources/` | Versioned package data declared in `pyproject.toml` |
| `utils/` | Small reusable text and file-publication tools |

`domain/` and `shared/` currently contain package placeholders. Add abstractions
only for actual needs. Shared services must not import `botpy` or consume raw
OneBot payloads. Platform-specific workflows declare narrow gateway protocols
such as `SetuGateway` and `ExportImgGateway`.

## Signatures and message contracts

`MessageEvent` contains string identifiers `engine`, `instance_id`,
`message_id`, `conversation_kind`, `conversation_id`, `sender_id`, plus
`segments: Tuple[MessageSegment, ...]` and `reply_context: Mapping[str, Any]`.
Each segment has `kind: str` and `data: Mapping[str, Any]`. `event.text` joins
only text segments. Platform IDs are not interchangeable. Telegram message IDs
are chat-local and must be scoped to the conversation before shared deduplication.

`Dispatcher.dispatch_result(event: MessageEvent) -> DispatchResult` returns
`status`, optional `reply`, `reason`, image URLs, optional music ID and recall
message ID, and immutable attachments. `Attachment(filename, content,
media_type="image/png")` carries bytes without SDK objects. `dispatch_payload()`
produces text or `OutgoingMessage` for the
adapter. Do not infer success from reply wording: statuses are `handled`,
`unhandled`, and `error`.

Adapter reply contract:

```python
async def send_reply(
    self, event: MessageEvent, content: Union[str, OutgoingMessage]
) -> None:
    ...
```

Replies use the source adapter and its reply context. OneBot can send native
image/music segments; the official adapter currently sends text and image URL
links. Telegram uploads news PNG bytes as a captioned document and sends music
as text with a public link. Do not promise equal platform capabilities without
implementation and verification.

## Authorization and failure matrix

| Condition | Required boundary behavior |
| --- | --- |
| Sender absent from global allowlist, including empty allowlist | Return `unhandled`; do not call business or external services |
| Group handling disabled or group absent from allowlist | Ignore group business actions |
| Authorized group with chat responder | Existing phrasebook policy may handle ordinary text; no new mention-only restriction |
| Duplicate event | Return `unhandled`; no repeated business action within cache lifetime |
| Invalid recognized command arguments | Raise `CommandInputError`; dispatcher returns `error` |
| Failed remote command | Raise `RemoteServiceError`; dispatcher returns `error` |
| Quoted history, media export, archive, or recall | Authorize before fetching history/media or executing platform operations |

The current dispatcher deduplication key is `(engine, instance_id, message_id)`.
The cache is bounded by size and TTL, protected by a lock, and cleared on
restart; an empty message ID bypasses deduplication. A feature requiring
cross-restart idempotency must persist its own completion/deduplication record.
Do not claim exactly-once delivery or complete offline message recovery.

Setu is an opt-in OneBot private-chat flow with both global and feature user
allowlists. Normal start words require a command quoting a merged forward or
ordinary file message, then
a confirmation quoting the bot's prompt before expiry (default 60 seconds).
Configured direct confirmation words (default 直接保存) skip the question and
save immediately. Cancellation words have no workflow behavior.
Unconfirmed media is not downloaded.
Plain images and unsolicited forwards do not trigger archive replies.
Image export has a separate authorization gate, precedes archive handling, and
returns original bytes as file attachments without archive persistence.

## Utilities and documentation

Import utilities from their concrete modules. `pangu(text)` operates on plain
text: extract text before use on HTML and do not rewrite raw Markdown/HTML.
`wrap_text(text, max_width, text_width)` uses the caller's measurement function
and requires positive width. `atomic_write_bytes(path, content)` requires an
existing parent directory and publishes a complete file atomically; it does
not download, validate, resume, or select cache expiry.

Utilities do not own routing, authorization, feature configuration, platform
APIs, or database state. Keep single-feature rules in that feature.

Feature usage, triggers, engine/session scope, configuration, workflow,
storage, and failure/retry behavior belong in the implementation module's
opening English docstring. Multi-feature modules describe each feature. If
there is no service module, document the actual implementation module and its
ownership in `application/services/__init__.py`. Update `bot/commands/help.py`
and explicit aliases when relevant. Keep `readme.md` concise; operations belong
in `docs/operations.md`, historical behavior in `docs/legacy-migration.md`.

## Cases and verification

- Good: a new local command uses a service, is explicitly routed and assembled,
  updates help and module documentation, and is tested with normalized events.
- Base: a fixed reply may need only a command wrapper and explicit route.
- Bad: adding a service without routing it, auto-enabling group access, or
  performing a history lookup before authorization.

Before a new feature, use `docs/application-template.md` to record its trigger,
scope, permissions, inputs/outputs, dependencies, configuration, cache, state,
database needs, retries, affected files, and validation. Map requirement to
code, configuration, storage, and checks; mark unnecessary fields with a reason.
At delivery, fill in actual behavior and evidence rather than only the plan.

Verify authorized and rejected senders/groups, argument errors, duplicate
events, reply status/payload, and feature-specific failure paths. Adapter changes
also need protocol tests. Shared utilities need independent contract checks in
`tests/unit/test_utils.py` and coverage in their consuming feature.

Wrong: putting a raw OneBot API call and access-control rule into `utils/`.
Correct: authorize at routing/adapter entry, express feature behavior in an
application service, and inject a narrow platform gateway implemented by the
adapter.

## Registered feature routing contract

### 1. Scope / trigger

Applies to command aliases, help, startup switches, and future native platform
features. Shared routing must check access before invoking a handler.

### 2. Signatures

`FeatureDefinition(name, aliases, help_text, engines, trigger, telegram_aliases)` describes a static
feature. `RegisteredFeature(definition, handler)` binds its application handler.
`FeatureRouter(registrations, enabled)` exposes `match(command, engine="")`,
`eligible(name, engine) -> bool`, and `help(engine) -> str`.
`Dispatcher.authorize_native(event, feature) -> bool` supplies the shared access,
feature eligibility and deduplication gate for future adapter-native handlers.

### 3. Contracts

The effective inventory requires platform support, an assembled service where
needed, and its configured enablement; an explicit true cannot invoke a missing
service. It owns help and invocation eligibility. Aliases share their
feature's switch. Register explicitly in code; configuration supplies values,
never import paths or executable plugins. Telegram's inventory is ping, help,
news, news_push, and music. `/start` is Telegram onboarding through help, without
access grants or scheduled subscriptions. Manual news and news_push are separate
features. News maintenance is part of manual news.
Telegram advertises `/news_clear`, normalized by its adapter to the registered
news maintenance action; native command names use letters, digits and underscores.
See [Telegram commands](https://core.telegram.org/bots/features#commands).

Native SDK handlers remain in adapters and must pass authorization and feature
eligibility before SDK/business effects. Shared services consume normalized data
and narrow gateways, never raw SDK updates.

### 4. Validation & error matrix

| Condition | Behavior |
| --- | --- |
| Duplicate registered alias | Reject registration |
| Disallowed sender/chat or duplicate command | No handler/provider effects |
| Disabled feature or unsupported Telegram slash command | Concise unavailable guidance without invocation |
| Unknown Telegram slash command | Safe help guidance without echoing the input |
| Ordinary Telegram text or another bot's addressed command | Ignore |
| QQ/local service absent without explicit disablement | Preserve existing echo/phrasebook fallback; omit the unavailable feature from help |
| Explicit false with or without a service | No feature invocation; retained command returns unavailable |
| Manual news disabled, push enabled with recipients | Scheduler remains eligible |
| Push disabled or recipient lists empty | No background scheduler |

### 5. Good / base / bad cases

Good: disable music once and its aliases and help all reflect that switch.
Base: enable ping and help with no provider configuration. Bad: bypass the
registry for an alias or fabricate a Telegram route to a QQ-only service.

### 6. Tests required

Check effective help, alias switch consistency, platform support, authorized and
denied private/groups, no side effects on rejection, independent news switches,
and equal Telegram message IDs in distinct chats. Adapter protocol tests verify
addressing, readable document bytes/caption, lifecycle, and secret-free failures.

### 7. Wrong versus correct

Wrong: maintain a separate Telegram command inventory and invoke a provider
before checking enablement. Correct: authorize and resolve a registered feature,
check its platform/switch, invoke its handler, then send through the source adapter.

## Setu quoted save contract

### Scope and trigger

Applies to private OneBot archive commands and their result callbacks.

### Signatures

`Setu.is_start_word(text: str) -> bool` owns both normal and configured direct
triggers; the adapter uses it before resolving the quoted forward/file message.
`Setu.is_authorized(event: MessageEvent) -> bool` owns the feature's engine,
private-session, and user gates; the adapter combines it with global access
before lookup/handling, and the service reuses it before collection/confirmation.
`SetuConfig.direct_confirm_words: Tuple[str, ...]` defaults to `(直接保存,)`;
`confirm_words` defaults to `(保存,)`, `confirm_timeout_seconds` to `60`.

### Contracts

The adapter adds `setu_source_id` only after resolving an authorized quoted
merged forward or ordinary file message. Global and feature allowlists must
both pass before lookup. Ordinary file messages use the same state/confirmation/
direct-save flow; unquoted files and plain image/video quotes do not start Setu.
Only the quoted source's forward/file segments enter collection, so a separate
attachment on the command itself cannot be archived under that source identity.
Normal saves require the quoted bot prompt ID; direct saves immediately claim
the batch and use the same file saver and result counts/directory callback.
Each save result replies to the user command that triggered that attempt:
the confirmation message for normal saves, or the direct-save message for
direct saves. A retry result replies to the retry command. This reply target
is separate from the stored prompt/result ID used to select unfinished items.
Once a save has been claimed, send one progress-start notice quoting that same
command before any location resolution/download/copy. Report only unfinished
file/video/image counts (audio when present), omitting zero categories, e.g.
正在保存以上 2 个文件、1 个视频、3 张图片。 Normal/direct/retry attempts share
this boundary. The notice never replaces a stored prompt/result ID, and a
notice-send failure is safely logged while the claimed save proceeds.
For direct partial failures, the result message ID becomes the confirmation ID
for retrying unfinished items. Source deduplication and completed files survive
retries; no database schema changes are needed. Legacy `cancel_words` is accepted
by the loader but has no runtime effect. Explicit timeout/confirmation settings
remain effective; the prompt describes the configured timeout.

### Validation and error matrix

| Condition | Behavior |
| --- | --- |
| Direct words overlap normal start/confirmation words, or either list is empty | ConfigurationError |
| Missing quote or quote containing neither a merged forward nor a file | No download |
| Confirmation has no matching unexpired prompt | Guidance reply; no save |
| Repeated direct command for completed or processing source | Distinct completed/actively saving reply; no duplicate save |
| Direct command targets an existing pending source | Save that batch without another question |
| Fresh quoted-source command targets expired unfinished batch | Rearm original batch, retain completed checkpoints and refresh only matching unresolved metadata |
| Old prompt/result confirmation has expired | No save; fresh quoted-source intent is required |
| 取消 or legacy cancellation alias | Unhandled by Setu; pending state stays intact |
| Attachment save fails | Result reports failure; only failed items remain retryable until expiry |
| A save completes or partially fails | Result replies to the triggering user command ID |
| Save claimed with unfinished attachments | One pending-kind progress notice precedes resolution and final result |
| Start notice delivery fails | Continue the claimed attempt; preserve result/checkpoint/retry state |

### Good, base, and bad cases

Good: quote a forward with 直接保存, receive a start notice then one result, then quote that result
with 保存 to retry a failed file. Base: quote a forward with /setu, then quote
the question with 保存 within 60 seconds. Bad: save an unquoted forward or use
a global latest-batch fallback for an unrelated quote.

### Required tests

Unit checks cover immediate save, duplicate sources, pending-to-direct save,
partial retry without replacing successes, removed cancellation, configured
aliases, result reply targets, and expiry at the deadline. Protocol checks
verify quoted lookup, confirmation and direct result reply segments, and result
sending without a confirmation question for default and configured words.
Assert start notices precede resolution, quote the current command, count only
pending items on retry and cannot be selected as a confirmation target. Rejected,
expired, duplicate and unconfirmed actions do not emit progress notices.

### Wrong versus correct

Wrong: hard-code direct words only in the adapter, or skip state claiming when
saving directly. Correct: share trigger recognition through Setu and reuse
the durable batch claim/checkpoint/result flow.

Wrong: quote the original forward or bot prompt in the final result. Correct:
pass the current user command ID into the save result callback, while keeping
the stored bot result ID as the retry selection target for direct failures.
