# Design: archive original-name placement

Status: implementation approved on 2026-10-09 following final planning review.

## Boundaries and flow

Reuse OneBot authorization/quoted-forward resolution, `Setu._extract`, durable batch claims/checkpoints, `SetuGateway.media_location`, and `SetuFileSaver`. Archive naming belongs in feature file persistence, not shared utilities or raw adapter routing. Collection already accepts `file`; do not introduce an archive-only eligibility filter.

Flow: authorize → bounded forward collection → existing prompt/direct claim → location resolution after confirmation → bounded temporary copy and SHA-256 → destination selection → publish complete file → checkpoint actual path/size/hash → existing result/retry handling.

User-approved alternate entry: after authorization, resolve the command's quoted
message as currently done, and accept its ordinary `file` segments as well as
merged-forward segments. Retain `setu_source_id` for the quoted source identity;
the service's existing extraction already accepts file segments without forward
recursion. Limit the new direct source form to file-kind segments, not image or
video quotes. Reuse the same store/claim/save/result flow without a schema change.
Generalize prompt/guidance wording to message rather than falsely describing an
ordinary file as a merged forward. Update exact text assertions accordingly.

No saving starts from an unsolicited file. Prompt/direct-save commands still
require their quoted source, feature/global allowlists, and private conversation.
The new entry avoids multi-forward context lookup but does not guarantee native
download of every ordinary private file. Normal-source live acceptance remains
required; the failed forwarded source is not silently marked repaired.

Current metadata (`kind`, `file`, `name`, `url`, `size`) and saver result (`path`, `size`, `sha256`) suffice when a real name is present. Inspect representative OneBot payloads during implementation; change metadata/resolution only if evidence requires it. Do not treat an opaque file ID as an original name. No schema migration is currently planned.

The reported live failure now supplies that evidence: NapCat file segments use
`file` for the basename and a distinct `file_id` for cached native lookup. For
file-kind collection, prefer `file_id` for the internal resolver identifier
while keeping the basename as `name`. Non-file extraction stays unchanged.
The `get_file` request waits for full download, so give it an explicit bounded
operation-specific response deadline independent of short chat APIs. The
installed cached-element/model download waits up to 120 seconds, and native
file-assistant fallback uses a size-based bound capped at 30 minutes. Select
the file wait from these observed bounds plus a small response margin; enforce
the existing pre-resolution file/batch size checks first. This changes only
local response correlation, not NapCat download controls or arbitrary input
timeouts. No new config key or schema migration is needed.

Do not switch to `get_private_file_url` as a blanket workaround: installed
NapCat constructs HTTP private URLs, which conflict with the existing HTTPS
fetch contract. Validate any kernel-returned local path against the existing
mounted-cache allowlist. At the protocol request boundary, log safe action,
timeout/retcode categories, never raw parameters or response text.

Long native file waits can exceed the existing confirmation deadline. Extend
the existing `SetuStore.finish` transition with optional completion/window
parameters and an atomic SQL CASE update: renew only `saving` → `awaiting`
whose stored expires_at has already passed. Supply these parameters for failed
file-containing saves only; other callers and early/unstarted/image-only paths
keep their prior deadlines. No schema change. This makes result-based retries
usable after a slow failure without weakening pre-save confirmation expiry.

## Naming contract

- Recognize archive suffixes case-insensitively from the original basename and retain its case/full compound extension.
- Override hash-basename generation only for archive file attachments. Normal paths: `<root>/<YYYY-MM-DD>/<original>` in `date_original`; `<root>/<original>` in `timestamp_hash`.
- Images, videos, audio, and other non-archives retain existing placement, hash naming, and repeated-save/collision rules. Do not route these through timestamp collision handling, even when their input name resembles an archive suffix.
- Validate identifiable archive names without the existing lossy sanitization when needed to preserve exact names. Unsafe or unrepresentable names cause normal item failures. Opaque nameless files cannot be classified by suffix and retain existing generic-file fallback; do not add archive-content inspection or reject those generic files.
- Reuse identical content at an existing destination. Different-content archive collisions cannot use the current numbered-renaming branch.

## Archive collision policy

The user approved an archive-only `_timestamp.ext` suffix on different-content name conflicts. Keep the same parent directory; do not create collision subdirectories. Split the longest recognized archive extension, e.g. `backup.tar.gz` becomes `backup_<timestamp>.tar.gz`, preserving actual case and Unicode.

Use a UTC+8 timestamp with sufficient precision (e.g. `YYYYMMDD-HHMMSS-ffffff`). If a generated name is occupied by different content, advance to another timestamp candidate rather than overwriting. Reuse matching content at an existing original or recognized timestamp variant, preserving retries without extra copies. Persist the actual destination using existing checkpoints. Publish archive files with an operation that cannot overwrite an occupied path under concurrency. Keep non-archive publication semantics unchanged.

Examples: first archive `backup.tar.gz`; a different archive with the same name `backup_20261009-153000-123456.tar.gz`. Existing images retain their configured hash/original placement and repeated-save behavior.

## Compatibility and boundaries

No archive extraction or new dependency. Preserve configuration, authorization, transfer limits, approved HTTPS QQ hosts, local NapCat media-cache allowlist, file permissions, and retry/state contracts. Preserve complete bytes, valid Unicode, and compound suffixes. Do not rename historical files.

Live settings currently use `date_original`, 2G/10G caps, and `/app/setu`. Planning does not alter these. Production OneBot uses a built image, so source edits alone do not deploy behavior.

## Live cache and expired-source corrections

The latest ordinary-file download returned a direct child of
`local_media_root/NapCat/temp`, present in the existing read-only mount. Only
explicit file segments add this exact layout to the local allowlist; resolve
symlinks first and reject nested/sibling/private directories. The actual file
is `0600` owned by UID 1000, while OneBot UID 10001 cannot read it despite shared group 1000.
On file-kind PermissionError, call the existing native download_file_stream by
canonical ID over the authenticated WS. Validate correlated metadata, ordered
64 KiB decoded chunks, byte caps and exact completion totals; spool 1 MiB then
private temporary disk storage and pass its BinaryIO into the same saver.
Do not change source permissions or the global base64 configuration.

Retained seen IDs blocked expired failed batches in the previous direct-source
lookup. prepare_source owns an atomic source-state transition and returns an
action plus original row. Fresh source intent can reopen expired unfinished
work; normal commands prompt again and direct commands claim saving. Preserve
original batch/date/checkpoints/budget; refresh only unfinished file/url after
ordered kind/name/size equality. Busy/completed/missing/changed states are
distinct, old confirmations still expire, and unexpired normal duplicates
retain their window. No schema change or live database repair is required.

## Save-start notification

The user requested one start/progress explanation before the existing final
result. Own this in Setu._save after the durable claim and before native lookup,
using the same pangu/private reply helper and current command quote. Count only
unfinished file/video/image/record entries; omit zero categories and include
audio when present. Do not replace stored prompt/result IDs with this notice.
A safe best-effort send failure must not strand claimed work. All source forms,
normal/direct actions and retries share this boundary. Verify notice ordering,
counts, quote identity, no pre-consent effect and unchanged final/retry selection
in focused service and simulated protocol tests.

## Rollout and rollback

After approved implementation and automated checks, prepare a concrete live QQ archive case with known original name and digest. Any separately authorized rebuild targets only OneBot. Keep Telegram/NapCat and their state running. Roll back code/service image without deleting saved files or resetting SQLite.
