# Approved implementation boundary and integration contract

On 2026-10-11 the user approved the latest final planning summary and requested continuation (“嗯，方案合适；继续”). This authorizes implementation/checking of the reviewed scope, not a live service switch, deployment, commit or archive.

## Smallest behavior gap and ownership

Telegram currently admits text only and has no archive service. Add native normalized media reception, a separately configured opt-in archive service, durable per-file jobs, flat safe publication, and an internal local Bot API deployment path. Keep OneBot behavior and its state/files intact. No unrelated refactor or provider/dependency upgrades.

- Core implementer owns new `config/tgsetu.py`, `application/services/tgsetu.py`, `infrastructure/persistence/tgsetu.py`, `infrastructure/persistence/tgsetu_files.py`, and focused new config/service/file tests.
- Adapter implementer owns Telegram adapter, Settings, main, feature/dispatcher native wiring, and corresponding existing Telegram/routing tests.
- Deployment implementer owns deployment files/scripts/examples, the server-only credential exclusion in `hako`, and corresponding deployment/preview/runtime-wrapper tests.
- Main session owns operations/application docs, task/spec records and integration review.

Workers are not alone in the codebase; preserve others' edits and coordinate contract changes. Prefer native task-context injection; explicitly read task artifacts/manifests and missing policy as fallback and report that loading.

## Shared contract

- `TgSetuConfig.load(path: Path)` and `.disabled()`; enabled, allowed_users, save_root, cache_root, max_file_bytes, max_unit_bytes, max_unit_files, max_pending_files, workers, album_quiet_seconds and album_max_wait_seconds. Dedicated TOML once at startup, omitted file disables. Use sizes like existing Setu. Cache root defaults `/var/lib/telegram-bot-api`, save root `data/kisara/tgsetu` outside Compose; feature example overrides save root `/app/tgsetu`.
- `TgSetu(config, state_dir: str, instance_id: str, allowed_users: FrozenSet[str])`; `async handle(event: MessageEvent, gateway: TgSetuGateway) -> bool` handles commands/media with its own enabled/private/global/feature authorization before state/SDK effects; `async run(gateway)` owns the durable worker loop and bounded transfer workers. Adapter owns/cancels/awaits its run task before SDK shutdown.
- Narrow gateway: `async media_path(media: Mapping[str, Any]) -> Path` retrieves using `file_id` and validates local SDK path; `async send_notice(chat_id: str, text: str, reply_to_message_id: str = '') -> str` sends safely and returns the bot receipt ID if known.
- Media `MessageEvent` uses one `image`, `video`, or `file` segment per actual item, `data` keys `file_id`, `file_unique_id`, `name`, `mime_type`, `size`, `caption` (original), `title` (caption with hashtag entity spans removed), `tags` (ordered extracted strings without #), `media_group_id`. Photo chooses one largest PhotoSize. SDK objects stay in the adapter. Animation duplication/unsupported SDK types are explicitly ignored.
- Text commands are normalized `/tgsetu [on|off|status|retry <source-message-id>]`; bare command/status reports activation and usage; retry is explicit, scoped to the authorized user's chat and source identity. Source job names/ordinals are frozen and successes never retried. No finish or quoted-save confirmation.
- Adapter enters native handling only after shared registered feature authorization, and does not then fall through to ordinary dispatch (avoids double dedup). Core service repeats policy checks for defense and direct tests. Disabled feature gives existing unavailable guidance for commands and ignores media.
- Settings owns `telegram_api_base_url`, `telegram_local_mode`; default cloud for existing Telegram behavior, configure local only explicitly. Enabled TgSetu requires local mode/endpoint at startup. Adapter passes settings to its prebuilt ManagedPollingBot/ExtBot constructor. Keep custom lifecycle semantics and SDK imports optional for QQ.
- Draft notices can be English to follow repository Python guidelines; avoid raw captions, URLs, SDK exception messages or credentials in default logs. Filenames/paths can appear in authorized user results as required.

Any necessary contract adjustment should be agreed between implementers and main before use. This contract narrows technical execution; it does not change the approved user behavior.
