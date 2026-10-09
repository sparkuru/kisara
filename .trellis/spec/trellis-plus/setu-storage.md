# Setu archive file placement

### 1. Scope / trigger

Private OneBot setu accepts commands quoting merged forwards or ordinary file
messages. Both global and feature allowlists precede quoted lookup/download;
unquoted/unsolicited files and plain image/video quotes do not start Setu.
The ordinary-file entry reuses the same confirmation/direct-save, source
deduplication, counts, result quote, placement, and failed-item retry contracts.
Prompt wording describes a message rather than calling every source a forward.
Only `kind=file`
with a recognized archive filename suffix uses the archive original-name rule.
Supported suffixes are `.tar`, `.tar.gz`, `.tgz`, `.zip`, `.7z`, `.rar`,
`.tar.bz2`, `.tbz2`, `.tar.xz`, `.txz`, `.tar.zst`, and `.tzst`, matched
case-insensitively. This classification controls naming, not file eligibility.
Images/videos/audio and other files retain existing naming and repeated-save
behavior even if their supplied name resembles an archive.

### 2. Signatures

`SetuFileSaver.save(source: Dict[str, object], location: Union[str, BinaryIO], timestamp: float,
remaining_bytes: int) -> Dict[str, object]` consumes existing `kind`, `name`,
and `file` metadata. It returns the actual `path`, byte `size`, and `sha256`
for the existing Setu checkpoint/retry flow. No new config key, protocol API,
SQLite column, or archive tool dependency is needed.

File collection prefers raw `file_id` for internal `file` resolution while
retaining the original basename from raw `file_name`/`name`/`file` as `name`.
NapCat can provide both fields with different meanings; do not choose a
basename as the resolver ID when its canonical ID is available.
`OneBotV11Adapter._request(action, params, timeout_seconds=None, stream_handler=None)` preserves the
ordinary request deadline unless a caller provides an operation-specific one.
`SetuStore.finish(batch_id, state, completed_at=None, retry_window_seconds=0)`
can atomically renew an expired deadline during `saving` → `awaiting`. The
service supplies this completion/window only for failed file-containing saves.
`SetuStore.prepare_source(instance_id, user_id, source_id, media, now,
retry_window_seconds, direct)` returns an action and the original batch under
`BEGIN IMMEDIATE`. `OneBotV11Adapter.download_file(media, output, maximum)`
writes a bounded canonical-ID download to a caller-owned binary spool.

### 3. Contracts

Archive bytes are copied without extraction or inspection. Retain a valid
original basename exactly, including Unicode, spaces, case, and compound
extensions. In `date_original`, choose `YYYY-MM-DD/original-name`; in
`timestamp_hash`, choose `original-name` directly under the save root. The
archive naming exception does not change configured placement for other media.

Matching original/stamped archive names with equal content are reusable.
Different-content name conflicts insert a UTC+8 timestamp before the full
archive extension, e.g. `backup_20261009-153000-123456.tar.gz`, in the same
directory. Keep earlier content intact, and choose another timestamp if the
candidate is occupied by different content. Archive publication must avoid
overwrites and duplicate same-content copies under concurrent calls. The
supported Docker runtime is Linux; archive directory locking uses Unix flock
and complete temporary files are published by hard link without replacement.
Downloads occur before acquiring the directory lock.

File-kind `get_file` may await full NapCat download rather than simple URL
lookup. Its response deadline is `max(120, min(10 + size / 262144, 1800)) + 5`
seconds (125–1805), derived from the inspected NapCat 4.18.28 native/model and
file-assistant bounds. Unknown/invalid sizes use the minimum. Preserve existing
size checks before resolution and keep short chat deadlines unchanged. This
controls response correlation only; it cannot override native transfer timeout
or guarantee an inaccessible forwarded file will become downloadable.

At the OneBot request boundary, log a controlled action/category, bounded
numeric retcode or timeout duration. Do not log parameters, identifiers,
basenames, signed URLs, response bodies, or raw server error strings. A
wrapper exception must use the same bounded fields because outer traceback
logging can expose its message. A private-file URL in this NapCat version uses
HTTP and is not a drop-in replacement for the HTTPS source policy. Stream download shares the native
resolver. Inner private/group origin must be established before selecting any
platform-specific alternate action; outer private chat alone is insufficient.

Long file downloads can outlast the original confirmation window. On a failed
file-containing save finishing after that window, atomically extend retry
expiry by one configured confirmation window from completion. Retain existing
deadlines for unstarted prompts, successful saves, short failures and image-only
batches. Use stored state/deadline in the transaction rather than a stale
direct-save batch snapshot. The result's retry instruction must identify a
still-selectable batch, and renewed expiry remains a hard boundary.

Every claimed save with unfinished items sends one start notice before source
resolution/copy. Use current command quote and pending-kind counts, not total
historical batch counts; omit zero categories and include audio when present.
The final result still reports cumulative saved/failed counts and actual
directories. Start notice IDs are informational and never replace the stored
confirmation/result selector. Send failure cannot strand a saving batch;
log only a safe error category and continue the existing save path.

Existing HTTPS/cache source restrictions, per-file/batch caps, `0640` file
permissions, result quote targets, confirmation, and retry contracts remain
effective. No historical-file migration occurs.

For local sources, resolve symlinks and require an existing file inside
`local_media_root`. The existing `nt_qq*/nt_data/{Video,Pic,Audio,File,Record}/...`
media allowlist remains. Explicit file-kind attachments also accept direct
children of `local_media_root/NapCat/temp`: the installed runtime's successful
ordinary-file `get_file` download returned this precise path. Other NapCat
directories, nested temp paths, outside-root links, and image/video/record or
missing-kind sources in temp remain rejected. Do not allow the whole QQ mount
or general temporary directories. Copy complete bytes under the same caps.

The observed downloaded file has `0600`, owner UID/GID 1000, while OneBot runs
as UID 10001 with supplementary group 1000. Group membership cannot read that
file. On a file-kind `PermissionError`, use NapCat's existing
`download_file_stream` over the authenticated OneBot WebSocket and canonical
file ID. Do not change account-directory permissions, run the bot as root,
enable whole-file base64 conversion, or trust a new arbitrary local path.
Correlate each stream by echo. Require one positive bounded `file_info`,
ordered base64 `file_chunk` records with indexes and actual sizes, at most
65536 decoded bytes per chunk, and a `file_complete` response whose totals
match both the transferred and declared sizes. Ordinary API futures must not
complete on intermediate packets. On malformed/oversize/partial/rejected or
lost/timed-out streams, fail the item; no completed archive is published.
Keep only 1 MiB in a `SpooledTemporaryFile`, spill to private temporary storage,
then use the same bounded saver and publication rules. Close the spool on
success/failure/cancellation. Internal binary streams are capability inputs,
never protocol/user-provided metadata locations. Unrelated source errors keep
their existing resolver/refresh behavior; images/videos do not get this fallback.
If the async save is cancelled while a background copier still owns a spool,
cancel its completion future as well. The guarded worker callback still releases
its slot and skips an orphaned result/error; temporary-copy cleanup handles a
closed input without leaving an unobserved future exception.
If completion already failed just before cancellation, consume that completed
future's exception; cancelling an already completed future does not clear it.

`seen` records source identity, not save completion. A fresh explicit command
quoting the original source can rearm an expired unfinished batch. Preserve
batch ID, first_at/date, completed file checkpoints and cumulative byte usage;
refresh only unfinished `file`/`url` when the entire ordered kind/name/size
signature still matches. Direct source actions claim saving in the transaction;
normal source actions rearm a confirmation prompt. In-flight and complete
batches produce distinct truthful direct replies without another save. A
missing retained batch is reported as expired metadata, not completed work.
Unexpired normal duplicates stay quiet and retain their original window.
Old prompt/result confirmations alone still expire at the original deadline;
only renewed source intent can open a new window. No schema reset is needed.

### 4. Validation and error matrix

| Condition | Required behavior |
| --- | --- |
| Recognized archive with valid available name | Save original basename in either mode |
| Matching original or stamped name/content | Reuse file without replacement or another copy |
| Different-content archive name conflict | Add timestamp before full extension; never overwrite |
| Occupied timestamp candidate, symlink, or directory | Do not overwrite or reuse it as an archive success |
| Archive name has path/control/unsafe syntax or is unrepresentable | Item failure rather than lossy sanitization |
| Opaque file ID without identifiable archive name | Existing generic-file fallback; do not invent original archive metadata |
| Source unavailable, rejected, empty, or excessive size | Existing item failure/retry rules; no published partial file |
| Raw file basename differs from canonical file_id | Resolve canonical ID, preserve basename for placement |
| File response arrives after ordinary chat deadline | Wait within dedicated file deadline; chat deadline unchanged |
| Native download rejects or times out | Item failure with safe action/retcode diagnostics; do not claim transfer success |
| Failed file save completes after original confirmation deadline | Renew one retry window from completion, retaining completed items |
| Unstarted prompt, short failure, success, or image-only batch | Existing deadline behavior remains unchanged |
| Explicit file downloaded directly to mounted NapCat/temp | Accept under the existing size/byte/publication rules |
| Temp source has another/missing kind, nested path, private sibling, or escaping symlink | Reject without a published file |
| Native file is owner-only/unreadable to OneBot | Canonical-ID bounded native stream; no permission change |
| Native stream has invalid order/encoding/size/totals or lacks completion | Fail with no published partial file |
| Failed expired source receives a fresh quoted-source command | Reuse original batch/checkpoints with renewed consent |
| Source is saving, saved, mismatched or its metadata was pruned | Truthful status/guidance; no duplicate or unrelated save |
| Confirmed/direct/retry save starts | Pending-kind notice before resolution, then final archive result |
| Start notice send fails | Save still runs and checkpoints normally; no success inferred from notice |

### 5. Good / base / bad cases

Good: save two different `资料.tar.gz` files as the original and a timestamp
variant, then reuse the correct variant on repeat. Base: a quoted ZIP follows
the existing confirmation flow. Bad: change an image's hash filename or add
timestamp copies of images as part of this feature.

### 6. Required tests

Cover every archive suffix in both modes, case/Unicode/spaces/full extensions,
same-content reuse including stamped variants, different-content and concurrent
collisions, occupied timestamps, unsafe names/symlinks/directories, bytes and
source/size failures. Verify mixed/nested forward counts, normal/direct saves,
partial retry preserving completed files, and unchanged non-archive placement.
Simulated OneBot coverage resolves archive file IDs to mounted cache paths or
approved URLs. Live QQ transfer remains a separate acceptance check.
Include actual dual-field NapCat shapes, different IDs with equal basenames,
size rejection before native download, delayed replies beyond tiny simulated
chat deadlines, capped file waits, privacy-safe failures, and retry checkpoints.
Use mocked clocks to cross the original expiry during normal/direct file saves;
verify actual quote-based retry selection, exact renewed expiry, and untouched
short/image-only/unstarted-prompt deadlines.
Exercise quoted ordinary files with actual dual-field metadata in normal/direct
modes, no forward lookup, no download before consent, duplicates, generic-file
compatibility, and global/feature/group/unquoted/plain-image rejection.
Include real-shaped `get_file` responses using `NapCat/temp/<basename>` in the
protocol matrix, both layouts and consent modes. Assert byte/hash/name/permissions
and reject non-file kinds, nested paths, sibling config/data directories, and
symlinks after resolution. A live temporary copy may establish native bytes;
it does not establish deployed command receipt or persisted completion.
Cover native stream exact bytes, correlation through intermediate/complete
packets, malformed and oversized metadata/chunks, out-of-order and incorrect
completion counts, failure/timeout/disconnect cleanup, and retry checkpoints.
Test expired-awaiting and marked-expired batches for normal/direct source
actions, zero/partial completed work, unchanged original ID/date/size budget,
safe metadata refresh, old confirmation rejection, simultaneous claims and
truthful processing/completed/missing statuses.
Verify start-notice send/resolver/result order and command quote in service and
protocol tests, retry counts exclude saved entries, notice IDs cannot confirm
anything, and send failure does not prevent a claimed attempt from completing.

### 7. Wrong versus correct

Wrong: apply archive timestamps to all media, split `tar.gz` using only
`Path.suffix`, or publish archives with a check-then-overwrite operation.
Correct: require archive `file` classification, retain the longest complete
suffix, and publish complete bytes without replacing occupied paths while
preserving existing non-archive code paths.
Wrong: treat `get_file` as an instant metadata lookup or mock it only with
pre-supplied URLs. Correct: test canonical IDs and a delayed full-download
response, and distinguish bot deadlines from native download failures.
Wrong: treat a retained seen key as saved work or weaken the cache mount to
read owner-only files. Correct: use the actual batch state and explicit renewed
source intent; read inaccessible native file bytes through validated chunks.
