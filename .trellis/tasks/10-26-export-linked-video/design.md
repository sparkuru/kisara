# Bilibili quoted-video export design

## Scope and execution flow

This is one coherent OneBot export deliverable, not independent platform
projects. Keep one task. Add a feature-owned video export service and a narrow
provider implementation; do not add dynamic plugins or a generic media system.

1. Authorize the incoming event with the existing strict native sender/group
   rules before quote lookup. Suppress duplicate video commands with bounded
   process-local event tracking, scoped by engine/instance/conversation/message.
2. Fetch the quoted message once through the existing ownership-checked gateway.
   Keep `/export-img` and image-specific phrases image-only. Generic `导出`
   selects supported video links when present, otherwise existing images;
   `/export-video` is an explicit video route. Unsupported sources receive a
   useful reply. Bare links without an export request never start a download.
3. Parse normalized text and structured JSON card segments. For the observed
   Bilibili mini-program, read `meta.detail_1.qqdocurl`; never use its QQ launch
   URL or preview image as a media target. Malformed card JSON is a handled
   source error, not a raw exception. Keep protocol payload interpretation in
   the adapter normalization boundary where appropriate.
4. Admit only `b23.tv` and supported `bilibili.com` video URLs; normalize mobile
   variants, BV/av identities and an optional positive `p`. Resolve short links
   without cookies, validating every redirect and the final Bilibili video
   target. Cap hops and reject credentials, unexpected ports, local/IP targets
   and unsupported schemes. Preserve `p`, discard tracking parameters. Do not
   activate yt-dlp's generic extractor for arbitrary input.
5. Deduplicate normalized targets. Process at most three distinct targets per
   quote, sequentially; over-limit requests receive a clear error before media
   work. A link without `p` means part1; do not expand playlists or collections.
6. Acquire one instance-wide video job slot; other active requests receive a
   busy reply rather than creating an unbounded download queue. Send a bounded
   progress reply, then run the provider in an owned subprocess off the adapter
   event loop. Other conversations/ordinary commands remain responsive.
7. Select the highest accessible video quality/resolution and frame rate plus
   appropriate audio. Use compatible codecs as tie-breakers at equal quality,
   not as a reason to discard a better resolution. No fixed1080p cap and no
   silent quality reduction to fit size limits. Use scoped SESSDATA if supplied;
   otherwise anonymous extraction. Explicit session rejection is an actionable
   error; do not silently pretend an authenticated attempt succeeded.
8. Download bounded streams to the owned job directory, merge/remux locally into
   MP4 with FFmpeg, and validate complete playable output with ffprobe. Do not
   re-encode by default. A source with audio must produce audio in the final
   result; unsupported container/codec failures are explicit.
9. Send a native `video` segment from the same conversation through the adapter
   using a file path readable by NapCat. Require a successful API response;
   report safe failure context. Do not automatically switch transport or resend
   after an uncertain timeout. Release the job slot and clean owned artifacts
   according to the send-lifetime rule below.

## Ownership and data contracts

- `application/services/`: export intent/source orchestration, progress/errors,
  per-request decisions and a narrow gateway. Preserve the existing image
  service, sharing quote preparation only where it avoids repeated work.
- `infrastructure/integrations/`: Bilibili resolver/provider, worker lifecycle,
  scoped cookie handling, format selection, bounded download and merge. Worker
  result contains only a relative output filename, public video identity,
  selected quality and size, or a controlled error category.
- `bot/adapters/onebot_v11.py`: normalized source segments, quote ownership,
  native authorization and video send. Never expose yt-dlp internals to it.
- `bot/main.py` / configuration: construct/inject the OneBot service explicitly.
  Other engines must not import yt-dlp or use the supplied session.
- Public command inventory/help: register the native OneBot command using the
  existing feature inventory; it must not become an eligible public exception.

Use `asyncio.create_subprocess_exec` without a shell. Send worker input,
including the optional session, over stdin; never in argv or a URL. Restrict
worker options, environment inheritance and diagnostics. Create an owned
process group so timeout/cancellation terminates both worker and FFmpeg, then
await cleanup. Bound worker stdout/stderr; never return raw extractor errors,
signed media URLs or chained provider tracebacks through the adapter.

## Configuration and runtime preparation

Add `config/onebot/features/export/config.toml.example` with operational keys
`video_enabled`, `max_file_bytes`, `timeout_seconds` and `max_urls`, following
the repository's ordinary TOML/settings injection path. Proposed defaults: linked video enabled,
maximum final file512 MiB, request timeout600 seconds, maximum3 targets,
one active download. Use a bounded total job workspace (including intermediate
streams) of2 GiB and reject over-budget work. Expose meaningful size/timeout
settings; validate types/positive values at startup. Reuse existing size parsing
where its contract matches instead of inventing another grammar.

Use `ONEBOT_BILIBILI_SESSDATA` as the public deployment input, mapped only in
the OneBot services to `KISARA_BILIBILI_SESSDATA`, and an injected secret field
excluded from repr. Use the existing selected-engine environment resolution
for direct runs; do not add a second credential TOML field. Operational TOML
values take precedence over their environment fallbacks; explicit empty
session input clears authentication.
Never add speculative ESSID aliases. The temporary file is an authorized
bootstrap/test source, not a hard-coded runtime config path. During approved
setup, copy only its credential into the ignored repository `.env` under
`ONEBOT_BILIBILI_SESSDATA`
through no-overwrite, syntax-aware maintenance; preserve all preexisting values
and report conflicts without printing them. No chat-based credential storage.

Add optional `video` packaging with the pinned yt-dlp base package and Python
>=3.10 marker. Keep the base application's Python >=3.8 declaration and make
unsupported/missing video tooling an actionable feature error without breaking
image export. OneBot deployment uses the existing Python3.12 runtime, selects
the video dependency closure and installs FFmpeg/ffprobe. Synchronize
`deploy/preview-deps.py`, its exact constraints, OneBot build arguments and
preview readiness/dependency checks. Do not install YouTube JS/browser extras.
Ordinary/offline entrypoints must remain credential-free.

## Local media transport and lifetime

Use a dedicated OneBot export spool mounted at the same
`/tmp/kisara/export` path in the application and NapCat, writable only in the
application mount and read-only in the gateway. Do not mount the whole
application state volume into NapCat or introduce an HTTP media server/port.
Docker path ownership and media modes must allow the real configured NapCat
user to read complete video files. Never put credentials into this shared
spool. Named spool storage is transport scratch, not an archive or reusable
authenticated cache.

Create unique application-owned job directories and keep the complete output
until NapCat has returned its send result. Normal success/definite failure
cleans the job. For an uncertain send or cancellation during an in-flight
send, retain that job for a bounded grace period (one hour) and prune it later;
do not race NapCat by deleting immediately or retry the send automatically.
Before admitting authorized video work, lazily initialize the spool, prune only
expired owned job directories, reject unsafe/symlink roots and enforce the total
spool budget. Expiry makes a retained job eligible for pruning at the next
admission; there is no background janitor or unconditional adapter-startup
filesystem sweep. This avoids transport-file effects merely from constructing
an adapter, while retained bytes always count against the2 GiB budget. Never delete
unknown files, login state, Setu media or news/delivery state. No restart resume
or durable delivery guarantee is introduced.

## Failure and compatibility matrix

| Condition | Required outcome |
| --- | --- |
| Unauthorized event / foreign quote | No provider work or media send |
| No quote / malformed or unsupported target | Specific safe guidance |
| Unsupported site after short-link redirect | Reject before credential use |
| No configured session | Best anonymously accessible streams |
| Provided session explicitly rejected | Ask for refresh; no false authenticated success |
| Restricted/deleted/rate-limited video | Safe provider error; no empty file/success |
| File or workspace limit exceeded | Abort, clean owned partials, explain limit |
| Timeout / cancellation | Terminate owned process group and await cleanup |
| Missing worker/FFmpeg / older Python | Actionable video error; image export retained |
| Native send result uncertain | Explain uncertainty, no automatic resend, grace retention |
| Repeated input event | No duplicate video job within bounded process window |

Existing image original-byte behavior, strict group gates, public-command
restrictions, Setu priority after exports, scheduled news, and paused Telegram
work remain unchanged. No database migration is needed.

## Rollout, rollback and remaining risk

Run focused/offline protocol and full regression checks first. Build and check
the OneBot image/toolchain in isolation before any live update. Validate actual
yt-dlp extraction for the two preview inputs with anonymous and provided
sessions, including a complete merge/ffprobe check. Apply only the reviewed
OneBot preview update and necessary dedicated spool mapping for live return;
preserve QQ login, other engines and all existing volumes. Record container
identity changes and actual native receipts. If broader service effects are
needed, prepare the concrete command and obtain that additional authorization.

Upstream metadata probes do not prove native codec acceptance or absence of
platform transcoding. Real reception/playback remains a feature acceptance
gate; do not label it passed from synthetic tests. Rollback restores prior
OneBot source/image/configuration while retaining persistent state and login;
delete only task-owned expired scratch. Commit/archive/push are separate.
