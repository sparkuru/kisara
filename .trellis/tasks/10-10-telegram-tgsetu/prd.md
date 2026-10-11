# Telegram /tgsetu media archive

## Goal

Provide a Telegram-native archive for received/forwarded images, videos and attachments, using message descriptions and hashtags as searchable filenames in one configured directory. On 2026-10-11 the user approved the latest final planning summary and requested continuation (“嗯，方案合适；继续”), authorizing implementation and checking. Live deployment, endpoint switching, commits and archive remain outside this authorization.

## Confirmed facts and decisions

- D1 (user request): Telegram uses `/tgsetu` and does not support `/setu`; preserve OneBot behavior.
- D2 (user response, 2026-10-10): include a local Bot API Server in the first version for large files. This does not authorize a live endpoint switch during planning.
- D3 (user response, 2026-10-10, “用 A”): publish each complete file atomically directly under save_root. A logical message/album may partially succeed; retain successful file checkpoints and retry only unfinished files. Do not introduce per-message archive subdirectories or whole-message rollback.
- D4 (user response, 2026-10-10, “可以”): use PikPak-style automatic saving after `/tgsetu on`; `/tgsetu off` stops accepting new tasks. No finish command or per-submission confirmation is required. Media received while off is not archived.
- D5 (user response, 2026-10-10, “A”): attachments use original-stem + caption title + tag suffix + original full extension. Example: `pack.tar.gz` with `资源合集 #tag1 #tag2` becomes `pack-资源合集-@tag1-@tag2.tar.gz`.
- Planning baseline: SDK is pinned to python-telegram-bot 22.8 (`pyproject.toml:19`); Telegram handled text only and Setu was OneBot-only. Implementation now extends Telegram separately.
- Albums are separate API messages linked by chat-scoped `media_group_id`. PhotoSize entries are resolutions of one photo.
- Incoming Update/Message fields expose no client multi-selection count/batch ID or album completion marker; only received counts can be reported. See [research](research/sdk-and-repository.md).
- Existing Setu atomically publishes individual files and checkpoints partial successes (`src/kisara/infrastructure/persistence/setu_files.py:88`; `src/kisara/application/services/setu.py:291`). It does not commit all album files atomically.
- Planning baseline: Telegram had separate config/state but no media/cache mount; implementation adds distinct cache/archive mounts.

## Requirements

| ID | Outcome |
| --- | --- |
| R1 | Telegram-only `/tgsetu`, accurate enabled help, no Telegram `/setu` alias. |
| R2 | One configurable archive directory, separate from OneBot; missing config disables the feature, invalid config fails startup. |
| R3 | `[xxxx] 视频资源_1080p-aaaa.bbbb.cccc #tag1 #tag2 #tag3` becomes `[xxxx] 视频资源_1080p-aaaa.bbbb.cccc-@tag1-@tag2-@tag3.<actual media extension>`. |
| R4 | Attachments retain their original stem/full extension and insert the message description and `-@tag` suffixes before the extension, as confirmed by D5. Album siblings follow the common naming policy; collision ordinals precede tags. |
| R5 | Each logical message uses its own caption/tags and is processed independently. Album members share the initial selected caption, with frozen names and stable ordinals; delayed caption/member behavior follows the final-review design. Missing captions/names have a deterministic fallback. No caption borrowing from unrelated neighboring messages. |
| R6 | Publish complete individual files atomically directly under save_root, without overwriting existing files. Preserve successful file checkpoints across partial message/album failure; explicit retry processes only unfinished files. |
| R7 | Support several submitted messages; report received logical-message and file counts, never an invented original selection count. |
| R8 | Use existing SDK and local Bot API for large files, bounded copy memory/workers, byte caps, separate cache/archive, owned shutdown. |
| R9 | Global and feature authorization before metadata persistence, getFile, copy or publication; keep chat-scoped IDs and secret-free logs. |
| R10 | `/tgsetu on` enables automatic media-to-save for the authorized private user. `/tgsetu off` stops new acceptance; already accepted work retains its save/failure status. Do not require finish or per-submission confirmation. |

## Acceptance criteria

| ID | Observable result | Maps to |
| --- | --- | --- |
| A1 | Disabled, off, unauthorized, other-bot-addressed input produces no archive/SDK effects; Telegram help and OneBot regressions match scope. | R1, R2, R9, R10 |
| A2 | User caption example produces the requested filename; emoji/non-BMP entities and caption dots are handled correctly. | R3 |
| A3 | One file per album media member, not per photo resolution; deterministic sibling names, shared-caption policy, original attachment/compound suffix behavior. | R4, R5 |
| A4 | Different messages keep separate captions/counts/failure boundaries; missing caption/name has a defined fallback. | R5, R7 |
| A5 | Files are flat under save_root. A failed/cancelled member leaves no partial final file; successful siblings remain saved. Collisions never overwrite; retry/restart reconciles publication-before-database interruption without duplicating successful files. | R6, R9 |
| A6 | A controlled >20 MB file is copied through local Bot API with bounded memory; outside-cache/oversize/unreadable sources fail safely. | R8, R9 |
| A7 | Activation, off, late album members and restart have explicit outcomes; accepted files do not require a finish/confirmation command, and a grouping timer neither proves completeness nor discards late members. | R6, R7, R10 |

## Scope boundaries

MVP: authorized private-chat photo/video/document archiving under the approved on/off interaction, local Bot API setup, flat individual-file publication and durable save/retry state. Final-review operating details: activation persists until off, including restart; current feature/global authorization is rechecked before processing. Bare `/tgsetu` reports status. Off stops new acceptance while already accepted work finishes.

Out of scope: MTProto/user-account login, arbitrary channel/history scraping, archiving while off, a separate quoted-message save shortcut, collection/finish/confirmation workflows, OneBot changes, transcoding/archive extraction, arbitrary chat-supplied paths, rich/paid/live-photo/sticker support, and live deployment in this planning turn.

## Approved configuration follow-up — 2026-10-11

The user approved unifying configuration under `config/<engine>/features` and
fixing the Compose/hako/direct-run mismatch. [Boundary and acceptance](research/config-root-unification.md)
define the added scope: explicit selected-engine root, isolated Compose paths,
safe OneBot migration, private-file ignores and regression checks. This adds
no universal per-feature allowlist or live deployment operation.

This follow-up is implemented and independently reviewed: final offline gate
825 passed, 1 separately verified Git-dependent skip, 3 existing PTB warnings.
Existing private OneBot settings were copied without overwrite, originals
retained. The new mount layout has not been activated in live services.

## Approved CLI follow-up — 2026-10-11

The user approved a unified `./kisara.sh` command interface backed by hako and
deploy/engines.sh, with the earlier proposed temporary forwarding entrypoints.
[CLI boundary](research/unified-entrypoint.md) defines routes, compatibility,
offline isolation, preview targets and validation. No service operation or
commit/archive is authorized by this source change.

Implemented and independently reviewed; the final canonical full gate is
907 passed, 1 Git-dependent skip, 3 existing PTB warnings. CLI/preview fixtures
and real offline console startup/exit passed. Temporary compatibility scripts
and persistent preview ownership labels remain. See [validation](validation.md).

Subsequent approved revision removes the four old root scripts outright and
migrates executable fixtures/callers to kisara.sh. This supersedes temporary
compatibility retention and removes the old selection menu. The user then
approved conversion of stopped QQ deployment containers to the canonical
OneBot preview, preserving mounted login/data and leaving Telegram untouched.
See the latest sections of [CLI boundary](research/unified-entrypoint.md).

Retirement and the runtime-discovered NapCat probe correction are complete and
independently reviewed. Final canonical gate: 893 passed, 1 Git-dependent skip,
3 existing PTB warnings. The authorized OneBot preview start/status both return
ready; login/data storage remains and Telegram is untouched. Controlled feature
acceptance, Telegram activation and commit/archive remain outside this result.

## Artifact status

Research completed; D1–D5 and final-review operating defaults were approved on 2026-10-11. [Design](design.md) specifies behavior and [implementation plan](implement.md) specifies execution/validation. The task is now `in_progress` on branch `feat/telegram-tgsetu`. Source-pinned server build, cache read permissions/disk retention and real-account verification are explicit execution follow-ups; they must be resolved or accurately classified before delivery. No live service change is authorized by this implementation approval.

Implementation and independent offline review are complete: [validation](validation.md)
records the initial 786-test gate, subsequent configuration-root/CLI gates and
latest 893-test retirement/probe gate, plus a successfully built official server image
with synthetic read-only cache permission checks. Real account retrieval,
actual deployment/disk monitoring and endpoint migration remain unexecuted;
[prepared acceptance](live-validation.md) records their concrete steps.
