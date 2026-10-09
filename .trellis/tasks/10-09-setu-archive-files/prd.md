# /setu archive attachments with original filenames

## Goal

Extend the existing private OneBot `/setu` workflow to save common archive attachments with their original filenames from quoted merged forwards or ordinary file messages, using the same confirmation, direct-save, result, and retry logic as other attachments.

The user requested task construction on 2026-10-09 and approved the final plan with 开始实现 after review. Implementation is authorized. Live deployment/service changes are not included in that approval.

## Confirmed background

Source line anchors below describe the inspected pre-implementation baseline `473267b`.

- The project's OneBot, Telegram, and NapCat containers were running with restart count 0 on 2026-10-09, having started on 2026-10-04. OneBot uses the ordinary deployment service, not the dev service. Container state does not establish account connectivity or successful file transfer.
- The running OneBot config enables setu with `date_original`, `/app/setu`, `/app/.config/QQ`, a 2G per-file cap, and a 10G batch cap. No private IDs or credentials were recorded.
- Generic `file` segments are already collected without extension filtering: `src/kisara/application/services/setu.py:51`, `src/kisara/application/services/setu.py:176`. Original names come from `file_name`, `name`, or `file`: `src/kisara/application/services/setu.py:181`.
- File locations use OneBot `get_file` when needed: `src/kisara/bot/adapters/onebot_v11.py:426`.
- Hash mode replaces basenames, and different-content collisions append a number: `src/kisara/infrastructure/persistence/setu_files.py:42`, `src/kisara/infrastructure/persistence/setu_files.py:98`, `src/kisara/infrastructure/persistence/setu_files.py:105`. Both conflict with the requested archive original-name guarantee.
- Existing nested-forward placement tests cover images/videos in both modes, but do not establish archive-specific behavior: `tests/unit/test_setu.py:88`.

## Requirements

| ID | Required behavior |
| --- | --- |
| R1 | Save archives in quoted merged forwards (including nested forwards) and quoted ordinary file messages through existing `/setu`, 保存, setu, and configured direct-save actions. Preserve private-chat/allowlist gates, confirmation expiry, and traversal bounds. |
| R2 | Explicitly support `.tar`, `.tar.gz`, `.tgz`, `.zip`, and `.7z`, plus common `.rar`, `.tar.bz2`, `.tbz2`, `.tar.xz`, `.txz`, `.tar.zst`, `.tzst` formats. Recognize suffixes case-insensitively; classification controls archive naming and must not reject other currently supported files. |
| R3 | Retain a valid archive's original basename, including Chinese, spaces, case, and complete compound extensions, in both placement modes. When the name conflicts with different content, the user-authorized exception is inserting `_timestamp` before the complete extension. Do not replace the archive's original stem with a hash or cache ID. |
| R4 | Never overwrite different archive content. Reuse matching archive name/content; for a different-content name conflict save `original_timestamp.ext` in the same directory. Preserve compound extensions, e.g. `backup_timestamp.tar.gz`. Timestamp suffixing applies exclusively to archive attachments. |
| R5 | Save unchanged bytes without extraction, repacking, or archive-content inspection. Preserve source boundaries, permissions, streaming caps, atomic publication, partial failures, and retry behavior. |
| R6 | Preserve image/video/audio and non-archive file behavior exactly. The user clarified that existing hash naming and repeated-save behavior for images and other existing media must stay as before: repeated saves of the same file keep targeting its corresponding hash file rather than creating timestamp variants. Do not migrate previously saved files or reset persisted batches. |
| R7 | Include archives in the prompt's file count. Results retain correct saved/failed counts, directory reporting, and triggering-command quote targets. Retries leave completed files intact. |
| R8 | Prevent path traversal without silently renaming identifiable archives. Unsafe or unrepresentable original basenames produce item failures rather than invented names. Archive detection uses filename suffixes; a nameless opaque file ID cannot establish an archive type or original name and retains existing generic-file behavior. Do not introduce content sniffing or reject all nameless generic files. |
| R9 | Resolve real NapCat file segments correctly: retain the canonical `file_id` independently of the original `file` basename, and use a separate bounded wait for `get_file`, which may download the complete attachment before replying. Keep the existing short timeout for chat APIs and existing source/size limits. Emit safe action/category diagnostics without raw identifiers, URLs, filenames, or response bodies. |
| R10 | When a failed file-containing save completes after its original confirmation deadline, provide a usable configured retry window from completion. Renew only that expired retry transition; ordinary unstarted prompt expiry, image-only saves, short failures, and completed items retain their existing behavior. |
| R11 | The user-approved additional entry is a command quoting an ordinary OneBot file message. It uses the same confirmation/direct-save, canonical ID, state claiming, naming/caps/results/retries as forward files. Ordinary non-archive file segments retain existing generic-file naming, while plain image/video quotes are not newly accepted by Setu. Unquoted file messages do not auto-save or prompt. |

## Acceptance criteria

Latest live failure requirements (2026-10-09):

- R12: A fresh command quoting an expired unfinished source can resume the same
  batch with new consent, saved checkpoints and byte totals preserved. Distinguish
  actively saving, completed, expired/missing and changed metadata truthfully;
  source deduplication must not imply save completion. Old expired confirmations
  alone remain unable to save.
- R13: Support the actual ordinary-file native download inside the existing QQ
  mount. Approve only the observed file cache layout. Handle owner-only native
  files through bounded authenticated native chunks rather than changing account
  permissions, widening the mount, or loading entire files as base64 in memory.
- R14: After claiming a save and before resolving/downloading attachments, send
  one progress-start notice quoting the triggering command: 正在保存以上 with
  counts of pending files/videos/images (audio when present). Normal, direct and
  retry saves share this notice; completed items are excluded on retry. Keep
  the final 归档完成 result and its confirmation/checkpoint identity. Duplicate,
  expired, unauthorized and unconfirmed actions do not send a start notice.

- AC1 (R1, R2, R7): Mixed/nested forwards show correct counts, cause no download before confirmation, and save after the established confirmation or direct action.
- AC2 (R2, R3, R6): Each supported archive format retains its valid original basename when free in both modes, including uppercase/compound extensions and Chinese/spaces. Images/videos retain their existing placement and repeat-save behavior without archive timestamp suffixes.
- AC3 (R4, R7): Duplicate confirmation and matching archive name/content do not create an extra copy. Different-content archive name conflicts yield `original_timestamp.ext` without overwriting earlier content or adding subdirectories; compound extensions stay intact. Further timestamp collisions also cannot overwrite a file.
- AC4 (R5, R7): Source/destination bytes match. Excessive sizes, unavailable/empty/rejected sources yield accurate failures and no published partial file; applicable failures remain retryable.
- AC5 (R1, R6): Unauthorized users, groups, unquoted attachments, unrelated quotes, and expired confirmations have no new archive effects. Existing non-archive tests pass.
- AC6 (R8): Identifiable archives with unsafe/unrepresentable names cannot escape the archive root or silently become renamed successes. Opaque nameless file segments retain generic-file behavior without an invented original archive name.
- AC7 (R1, R7): Simulated OneBot file ID/URL/cache resolution and result/retry targets pass. A prepared live QQ case separately verifies actual NapCat transfer capability.
- AC8 (R9): A real-shape segment containing different `file` and `file_id` values uses the canonical ID while preserving its original archive name. File resolution can wait beyond the ordinary chat deadline within its dedicated bound; timed-out/failed responses preserve item failure/retry and log only safe operation metadata. Ordinary chat APIs retain their previous deadline.
- AC9 (R10): A deterministic long file failure crossing the original deadline remains selectable by its quoted retry result/prompt for one configured window from completion, retries only unfinished items, and expires at the renewed deadline. Short/image-only failure and unstarted prompt deadlines are unchanged.
- AC10 (R11): Authorized commands quoting ordinary file messages create the established confirmation or immediate direct save; original name and canonical ID are preserved, no native download begins before consent, and repeated source/confirmation actions do not duplicate files. Unauthorized/group/unquoted/plain-image quotes remain without new Setu effects. Guidance, prompts, and existing feature documentation correctly describe both forms. Setu is not advertised in the help registry, so no unrelated help route is introduced.
- AC11 (R12): Expired-awaiting and persisted-expired failed batches resume by
  fresh normal/direct source commands, preserving ID/date/completed files and
  budget, refreshing only matching unfinished metadata. Concurrent claims save
  once; stale confirmations and changed source shape do not save.
- AC12 (R13): Real-shaped NapCat/temp get_file paths and 0600 source conditions
  save exact original archive bytes/names through validated native chunks with
  the same caps/permissions/publication rules. Invalid, oversized or partial
  streams never publish success; pending stream/spool resources are cleaned.
  Validate the reported real file's copied digest independently of mocks.
- AC13 (R14): Start notice precedes first resolution/copy and final result for
  normal/direct and retry attempts, reports exact unfinished-kind counts, and
  quotes the triggering command. No redundant notice for inactive/rejected
  actions; notice delivery failure cannot strand an otherwise claimed save.

## Out of scope

- Unquoted/unsolicited attachment saving, plain-image/video quote saving through Setu, groups, Telegram/official setu support, or a new command.
- Extraction, conversion, archive-tool dependencies, additional users, relaxed source protections, or increased configured limits.
- Private-config changes, historical-file migration, SQLite resets, preview rebuild/restart, or deployment during planning.

## Decisions

On 2026-10-09 the user approved `_timestamp.ext` for archive name conflicts, and clarified that the new stamp rule applies only to archive files. Existing images and other media retain their original hash/repeated-save rules. No additional collision subdirectory is needed. The original-name requirement therefore has one explicit exception: the timestamp inserted on an archive name conflict.

After the native private-forward download failure was isolated, the user
explicitly selected 增加引用普通文件消息保存 in the scoped question describing
the same archive naming/confirmation logic. This authorizes that additional
entry within the ongoing implementation, not an HTTP/mount relaxation or a
NapCat dependency patch.

## Live failure and deferred evidence

After initial implementation, the user externally recreated the preview stack and reported a real 7z direct-save failure after approximately ten seconds. Read-only target inspection confirmed one approximately 104 MiB file with distinct basename/opaque ID and no URL. Installed NapCat 4.18.28 source shows `get_file` awaits full download (normally up to 120 seconds) while the bot's request wait was only ten seconds. The existing extractor also selected the basename ahead of the canonical ID. Source/timing establish a contract mismatch; the persisted generic error alone does not establish the exact live exception reason. See `research/napcat-file-resolver-live-failure.md` for evidence and source anchors.

This evidence activates the originally planned evidence-backed resolver correction. No new access, HTTP allowance, broad cache mount, or account-send behavior is authorized. Target resolution/cache visibility and corrected live behavior remain to be verified.

The target canonical get_file probe failed with retcode 1200 after 120.01
seconds. Private URL lookup also failed immediately; the inner node is private
with one file segment and no group source. Bot-side ID/deadline fixes alone
therefore do not establish successful live saving. See
`research/live-file-probes.md` and `research/napcat-forward-file-native-limit.md`.

At that stage ordinary-file saving was approved as an alternate entry, with
actual native download still unverified. The later isolated validation in
research/live-cache-and-expired-retry.md established its exact cache location,
owner-only permission condition and corrected complete-byte saving capability;
deployed quoted-command/checkpoint acceptance is still pending. The failing private forwarded
resource remains unsupported by the observed native/URL responses; no dependency
patch or relaxed source policy is implied by adding the alternate entry.

Archive recognition is suffix-based. Original-name metadata remains a prerequisite for the archive-specific guarantee; opaque unnamed attachments cannot supply it. This technical limit preserves existing generic-file compatibility and avoids unrequested content inspection.
