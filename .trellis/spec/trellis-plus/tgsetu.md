# Telegram automatic media archive

## 1. Scope and trigger

TgSetu is an opt-in Telegram private-chat feature. `/tgsetu on` enables saving
new photo/video/document messages automatically; `/tgsetu off` stops acceptance
while accepted jobs finish. Bare `/tgsetu` or `status` reports activation;
`/tgsetu retry <source-message-id>` retries failed members of the caller's
logical message/album. No finish/confirmation or OneBot alias is introduced.
Activation survives restart; current global and feature permissions still apply.

## 2. Signatures and ownership

- `TgSetuConfig.load(path: Path)` / `.disabled()` own dedicated startup TOML.
- `TgSetu(config, state_dir, instance_id, allowed_users)` owns authorization,
  activation, durable acceptance, naming/grouping and retries.
- `async handle(event: MessageEvent, gateway: TgSetuGateway) -> bool` consumes
  authorized commands/media; `async run(gateway)` owns bounded transfer workers.
- `TgSetuGateway.media_path(media) -> Path` retrieves the SDK `file_id`;
  `send_notice(chat_id, text, reply_to_message_id='') -> str` reports results,
  returning a receipt only when confirmed (queued notices return an empty ID).
- `TgSetuFileSaver.prepare(...)`, `.publish(...)`, `.reconcile(...)` own
  bounded cache copy/hash, no-replace publication and interrupted-intent recovery.
- `TgSetuStore` owns private `tgsetu.sqlite3`: activation keyed by
  `(instance, chat, user)`, logical units and independently claimed members.

SDK imports/objects stay in the Telegram adapter. Main assembles the service
only for configured Telegram and supplies `Dispatcher.authorize_native`.
Normalize one image/video/file segment per actual media, with `file_id`,
`file_unique_id`, `name`, `mime_type`, `size`, `caption`, `title`, ordered `tags`
and chat-scoped `media_group_id`. PhotoSize entries are resolutions, not files.

## 3. Contracts

Host config is `config/telegram/features/tgsetu/config.toml`; Compose mounts it
as `/app/config/telegram/features/tgsetu/config.toml`. Missing file disables the feature;
invalid/unknown keys fail startup. Feature users must be positive canonical
Telegram IDs and a subset of global users. Dedicated file caps use K/M/G binary
size strings. Defaults: 2 GiB/file, 8 GiB/logical unit, 30 files/unit,
200 pending files, 2 workers, 1-second album quiet / 5-second maximum wait.

Authorize engine/instance/private/global/feature eligibility before metadata or
SDK/file effects. Native handlers must not consume shared deduplication and then
fall through to ordinary dispatch. Durable member identity includes instance,
chat/user, source message and item; an album groups by media_group_id in that
scope. Do not identify users from forwarded origins. Recheck resumed-job policy.

Hashtags use SDK UTF-16-aware extraction; remove their spans from title and
append ordered `-@tag` suffixes. Caption dots never supply the extension.
Images/videos use caption title; documents use original stem + caption title +
tags + full original extension, including `.tar.gz`. Preserve meaningful Unicode,
spaces/brackets/hyphens/underscores; normalize unsafe path/control characters.
Album unnamed media add `-001` ordinals before tags. Initial caption selection
uses a bounded metadata window; frozen names/ordinals do not change on retries
or late members. Captionless media uses an original name or stable fallback.
Late captions retain metadata and never rename published files.
Check expired naming windows before enqueueing new media; worker saturation
must not extend the initial caption window or move late members into it.

Flat files live under `save_root` (`/app/tgsetu` in Compose); per-file temporary
bytes are copied in bounded chunks, capped, hashed and synced before Linux
directory-lock/no-replace hard-link publication. Files are 0640. Equal verified
name/content may be reused; different content gets a stable content-hash
disambiguator before tags, never an
overwrite. Persist candidate/hash/size intent before linking and complete the
checkpoint afterward; SQLite and filesystem are not one transaction. Restart
reconciles final bytes before fetching/copying again. Preserve saved siblings
after a partial failure; explicit retry requeues only failed named members.
Seven-day terminal metadata pruning never deletes archived bytes.

The optional internal Bot API server is source-pinned in its Dockerfile; no
host port is published. `TELEGRAM_API_BASE_URL` is a server root, default
`https://api.telegram.org`; `TELEGRAM_LOCAL_MODE=false` preserves ordinary cloud
Telegram. TgSetu requires explicit local mode. API ID/hash belong to the server,
not the bot token or other engines. Cache is mounted at the identical
`/var/lib/telegram-bot-api` path, server writable / bot read-only, with matching
non-root UID 10001 for owner-only cache files. Use SDK getFile then bounded copy;
pinned PTB download_to_drive buffers remote bytes and synchronously copies local
bytes, so it is not a large-file streaming primitive for the event loop.

Helpers start/check the local server before Telegram, preserving legacy Compose
support and targeted lifecycle. Explicit cloud logOut/migration is an account
operation, never automatic startup. TDLib owns cache optimization; it is not a
hard disk quota or archive backup. Keep caches, SQLite and archive distinct.
No broad cache deletion or host permission relaxation is permitted.

## 4. Validation and error matrix

| Condition | Required result |
| --- | --- |
| Missing/disabled feature or user off | No archive acceptance/retrieval |
| Unauthorized/global-empty/group/foreign engine or instance | No metadata/SDK/archive effects |
| Command to another bot or unsupported media | Ignore |
| Duplicate accepted source | No second file job |
| Album member arrives after initial window while on | Append frozen naming/next ordinal; process independently |
| Off with already accepted jobs | Finish those jobs; reject new media |
| Queue/file/unit cap exceeded | Truthful rejection/failure, no partial final bytes |
| Missing/escaping/symlink/non-regular cache source | Fail under confined local path policy |
| Conflicting archive name | Preserve prior bytes, choose no-replace alternative |
| Download/copy/notice failure | Preserve file truth; safe category log, no fabricated completion |
| Crash after publication before checkpoint | Reconcile hash/size and checkpoint without duplicate download |
| Worker cancellation | Stop/join owned copy work before SDK shutdown; retain retry/recovery evidence |

## 5. Good, base and bad cases

Good: enable, forward a mixed album, retain successful files after one failure,
retry just the failed member with frozen names. Base: leave feature config absent
and continue ordinary Telegram news/music. Bad: interpret a polling batch as
the user's selected total, enable saving from ordinary media while off, or use
cloud getFile to promise large-video support.

## 6. Tests required

New config/service/file suites cover exact caption/attachment names, compound
extensions/UTF-8 limits, canonical permission lists, missing/invalid config,
on/off persistence, caps, independent units, album ordering/late captions,
partial retry, collisions, confined paths, >20 MB bounded copy, cancellation,
late members while every download worker is stalled,
notice failures and publication-before-checkpoint restart. Existing Telegram
adapter/settings/dispatcher/protocol suites cover actual SDK normalization,
UTF-16 hashtags, feature help/native gating, endpoint wiring and shutdown order.
Deployment/preview fixtures cover default-cloud isolation, local startup staging,
health/ownership/listeners and targeted stops. Run focused checks then the full
Docker suite. Real forward delivery/large retrieval/UID mounts/account migration
need separate live acceptance; mock tests do not prove those outcomes.

## 7. Wrong versus correct

Wrong: call SDK download_to_drive in the serialized update handler, then replace
the final filename and treat the whole album as successful.
Correct: quickly authorize/persist each real file job, retrieve/copy in owned
bounded workers, publish without replacement, checkpoint individual truth and
report actual received/saved/failed counts.
