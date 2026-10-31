# Bilibili provider and credential research

## User authorization and read-only observations

On 2026-10-26 the user approved Bilibili-only first-iteration scope and allowed
use of `/tmp/tmp/bilibili.env`. A structural inspection found exactly one
nonempty `BILIBILI_SESSDATA` assignment. No value, account identity or raw
credential-bearing payload was printed or written into this task.

The following probes ran in the existing Python 3.12 OneBot container, with
the env file passed over stdin. Only fixed `https://api.bilibili.com` endpoints
received the credential; redirects were rejected. No live package install,
service restart, media download or message send occurred.

| Probe | Anonymous | Supplied session |
| --- | --- | --- |
| `/x/web-interface/nav` | code -101, logged out | code 0, logged in |
| Session premium status | not applicable | inactive |
| Sample `/x/web-interface/view` | code 0, duration 60 seconds, one part | not separately probed |
| Sample `/x/player/playurl`, requested qn127/fnval4048/fourk1 | code 0; qualities16,32; maximum height480 | code 0; qualities16,32,64,80; maximum height1080 |
| DASH audio streams | 3 | 3 |

The sample is the text URL in [preview-samples.md](preview-samples.md).
Signed media URLs and API response bodies were not emitted. Observed qualities
are specific to this video and session at probe time. They do not establish
universal anonymous limits or premium access, or validate yt-dlp extraction,
FFmpeg merging and QQ delivery.

## Selected integration approach

Use pinned `yt-dlp==2026.10.21` through a feature-owned worker and FFmpeg/
ffprobe binaries for local MP4 merging. The existing small `HttpReader`
rejects redirects and is designed for bounded provider text/JSON, not
multi-stream media orchestration. Extending it into a complete downloader
would duplicate quality extraction, segmented transfer and merge logic.

Only Bilibili video targets are admitted, despite yt-dlp's wider capabilities.
Use the Python API with scoped cookies and controlled options; never load
user/system yt-dlp config, browser cookies, external plugins or `--exec` hooks.
Keep raw extractor logging and results private to the worker. The parent sees
only bounded, sanitized result fields and a complete local media path.

## Primary upstream evidence

- [Pinned extractor](https://github.com/yt-dlp/yt-dlp/blob/2026.10.21/yt_dlp/extractor/bilibili.py):
  reads SESSDATA from scoped cookies, exposes available DASH formats and audio,
  and supports a specified anthology part. Disable playlist expansion.
- [Pinned project metadata](https://github.com/yt-dlp/yt-dlp/blob/2026.10.21/pyproject.toml):
  requires Python >=3.10 and has no mandatory dependencies. Add the base package
  only, not the broad default extra. Upstream master now differs, so use the
  pinned release metadata for this design.
- [Pinned documentation](https://github.com/yt-dlp/yt-dlp/blob/2026.10.21/README.md#dependencies):
  FFmpeg/ffprobe binaries support separate audio/video merging. Remuxing is
  distinct from re-encoding; use the former to preserve the selected stream.
- [NapCat native conversion](https://github.com/NapNeko/NapCatQQ/blob/main/packages/napcat-onebot/api/msg.ts):
  handles a `video` message by resolving its file and constructing a native
  send-video element. This is source evidence, not proof for the running
  installation; live acceptance must verify its local-file access and playback.

## Deferred implementation verification

Run the pinned extractor against both real source shapes in isolation after
implementation approval. Inspect actual selected format and the final file
with ffprobe. Confirm both audio/video streams and native QQ reception.
Do not equate the direct official-API probes above with that end-to-end check.

Subsequent implementation-stage extractor, full download/merge, complete audio/
video decoding and shared-volume permission checks passed; see
[validation](../validation.md). Native return remains separately gated on QQ
login recovery and client playback; the earlier API table remains a historical
endpoint-specific observation, not the implementation's fixed quality limit.
