# Telegram /tgsetu approved design

D1–D5 and the operating defaults below were approved by the user's 2026-10-11 continuation after the final planning review. Implementation follows the recorded [boundary/contract](research/implementation-boundary.md).

## Interaction and grouping

User-approved shell consolidation is specified in
[unified entrypoint](research/unified-entrypoint.md); it preserves feature and
preview lifecycle behavior while making kisara.sh the canonical user command.

Confirmed D4: `/tgsetu on` enables automatic saving for an authorized private user. Each received supported media file is durably queued and saved independently, with no finish or per-submission confirmation. `/tgsetu off` stops new acceptance; already accepted jobs retain truthful status and complete through the same pipeline. Media while off is ignored by the archive workflow.

Standalone messages are independent units. Albums use instance/chat/media_group_id; members deduplicate and sort by destination message_id. A photo contributes its largest resolution only. Preserve sender authorization on the outer submitted message, not forwarded origin.

Album grouping is for captions and notification aggregation, not an all-files commit barrier. A short metadata quiet window may gather initial captions, but does not prove completeness or stop acceptance. Late members received while on are still queued, including after earlier members are saved; retries reuse each member's frozen name/ordinal. Off never silently admits new late members. No original client multi-select count is required or claimed.

Final-review operating default: persist activation per instance/chat/user until explicit off, including restarts, but recheck current authorization/feature settings before processing. Bare `/tgsetu` reports current status and on/off usage; it does not implicitly turn archiving on. Report accepted/saved/failed statuses distinctly, actual filenames/directories and an explicit failed-item retry selector. Notifications may aggregate recently received work, but must not label a timing-based group as the complete original selection.

Bound queued jobs, logical-unit file/byte caps and workers; do not treat an indefinitely enabled user as an unbounded single batch. Reject excess work with a truthful notice. Preserve durable accepted jobs and keep ordinary commands/polling responsive. A separate quoted-media shortcut is not required for this MVP. This project interaction is inspired by PikPak's documented user flow, not a verified account of its internals.

## Naming

Extract ordered hashtag entities with SDK UTF-16-aware caption/text parsers. Remove their spans from the title; append deduplicated `-@tag` suffixes in order. Do not rewrite every literal hash. Normalize line breaks/repeated whitespace and path/control characters while preserving Unicode, spaces and meaningful brackets/dots/hyphens/underscores.

| Case | Name |
| --- | --- |
| User video example | `[xxxx] 视频资源_1080p-aaaa.bbbb.cccc-@tag1-@tag2-@tag3.mp4` |
| Shared caption, first album image | `[aaaa] bbbb-cccc_dddd-001-@tag1-@tag2.jpg` |
| Same album, second item video | `[aaaa] bbbb-cccc_dddd-002-@tag1-@tag2.mp4` |
| pack.tar.gz + 资源合集 #tag1 #tag2 | `pack-资源合集-@tag1-@tag2.tar.gz` |
| pack.zip + tags only | `pack-@tag1-@tag2.zip` |
| No caption/name | `tg-<chat-id>-<message-id>.ext` |

D5 confirms named attachments retain their stem and append the caption title followed by tags, retaining the full original extension. Omit an empty title or empty tag sequence without extra separators; an attachment with no caption keeps its valid original name.

Final-review album defaults: use a short bounded initial metadata window (1 second of quiet, at most 5 seconds from first member) solely to choose a shared caption and initial order. Select the first nonempty caption by message-ID order within that window and freeze that choice. Retain all original captions in state; do not concatenate duplicates or borrow neighboring-message text. Freeze initial ordinals in message-ID order; later members get the next unused ordinal, never renumber earlier files. Ordinals precede tags for unnamed image/video siblings; documents keep their own stems, adding ordinals for duplicate derived names. This window does not close acceptance, define a multi-select batch or prove completeness.

If the initial album has no caption, use a stable group-derived fallback stem with member ordinals; a late caption is retained as metadata but does not rename published files or change the group's frozen naming plan. A captionless standalone item uses a valid original filename if available, otherwise `tg-<chat-id>-<message-id>.ext`. Report late-caption fallback in the result when it affects expected naming. Retries always reuse the stored naming plan.

Use original media filename/full suffix, known MIME mapping or SDK file-path metadata for the extension; caption punctuation never supplies it. Retain compound extensions. Unknown types use `.bin`. Bound final UTF-8 bytes under filesystem NAME_MAX, reserving tags, ordinal, conflict suffix and extension; shorten the title first and append a short digest of the unshortened planned name to avoid truncation ambiguity. If mandatory suffixes alone cannot fit, fail the item with an explicit naming error rather than silently dropping tags/extensions. Different-content collisions use a timestamp/disambiguator before tag suffixes and never overwrite earlier content; same-name equal-content publication may reuse the verified existing file.

## Individual-file atomic publication (D3 confirmed)

The user selected A: files go directly under save_root. Each file uses private temporary bytes on the destination filesystem, bounded chunk copy/hash, sync/close and no-replace publication. Successful files become visible independently; albums/messages may partly succeed. Persist successful file checkpoints and retry only unfinished members. Keep successful siblings when another member fails; no whole-message rollback or per-message archive subdirectory is introduced.

Filesystem publication and SQLite are not one transaction. Persist each member's prepared intent/planned name/hash before publication, then mark its saved path afterward. Under the publication lock, record the final selected conflict name before linking the complete temporary file. Restart reconciles that candidate against identity/state/hash, so publication-before-DB crashes do not duplicate successful files. Interrupted temporary bytes remain subject to bounded retention and explicit retry. Do not delete earlier successful archives. Distinguish visibility from power-loss durability; sync files/directories on the supported Linux filesystem.

Independent logical messages remain independent. Reuse Setu's bounded-copy/hash and archive lock/no-replace approach if extracting a small primitive is needed. Do not treat its generic check-then-os.replace branch as a concurrent no-overwrite guarantee or reuse NapCat path rules for Telegram.

## Boundaries

The user-approved configuration follow-up supersedes the original mount-based
root assumption: all entrypoints now target `config/<engine>/features`, with
same-path engine-specific Compose mounts. [Follow-up contract](research/config-root-unification.md)
defines safe migration and explicit selected-root loading.

Proposed modules: `config/tgsetu.py`, `application/services/tgsetu.py`, `infrastructure/persistence/tgsetu.py` and `tgsetu_files.py`. Keep SDK imports in the Telegram adapter. Services use normalized immutable metadata and a narrow gateway; SQLite owns user activation, unit/member jobs, claims and recovery in `tgsetu.sqlite3`.

Explicitly wire feature registration/help/native eligibility and configuration/main assembly. Global plus feature allowlists precede metadata/SDK/file effects. Do not consume event deduplication twice through authorize_native followed by ordinary dispatch. IDs include instance/chat; file_unique_id identifies media, file_id retrieves it. Missing feature config disables archiving.

Runtime `config/telegram/features/tgsetu/config.toml` uses the identical Telegram config mount; host examples belong under `config/telegram/features/tgsetu/`. Archive root is separate from state and OneBot.

## Local Bot API (D2 confirmed)

Keep pinned PTB 22.8. Add official tdlib/telegram-bot-api in --local mode; pin/build an evidence-backed server version during implementation, not an unverified community image. API ID/hash are user environment values separate from the token.

Proposed internal-only service telegram-bot-api on HTTP 8081, no host ports. Server-owned writable cache/state volume is mounted read-only into Telegram at the identical absolute path. Archive bind mount: `data/kisara/tgsetu:/app/tgsetu`; SQLite retains `telegram_state:/app/state`.

Configure endpoint/local-mode/cache-root on ManagedPollingBot/ExtBot construction: the existing Application receives a prebuilt bot, so builder-only endpoint settings are insufficient. After authorized acceptance while on, SDK get_file returns a local cache path; validate resolved paths inside the explicit cache mount and copy chunks in an owned worker. Document names/user text never become source paths. Verify cache read permission for the existing non-root bot without granting broad host access.

Pinned download_to_drive buffers remote bytes and performs synchronous local copy. Use getFile plus bounded validated local copy for large files, rather than calling that method in the event loop. Known-size checks precede retrieval; actual copy enforces caps/hashes. Server cache growth/retrieval precedes some Kisara enforcement, so include disk budgets and cache retention. No-size-limit API does not mean unlimited application policy.

Own workers through shutdown/cancellation. Local/cloud switching is explicit; no automatic cloud fallback. Live migration needs controlled cloud logOut and targeted restart; rollback respects the documented 10-minute cloud re-login restriction and preserves state/cache/archive volumes. No live switch in this task's planning phase.

## Remaining verification

No real Telegram account/media was accessed. Forwarded album grouping/captions, multi-client ordering, large retrieval, cache UID/GID and server image/version require later checks. Offline SDK fixtures do not establish those live outcomes.
