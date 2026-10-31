# OneBot quoted Bilibili video export

## 1. Scope and trigger

Applies to native OneBot video export, optional Bilibili authentication and
temporary media transport. Generic `导出` or `/export` selects supported video
links before image fallback; `/export-video` explicitly selects video.
`/export-img` and image-specific wording preserve original-file export.
Bare shared links never trigger a download. Other engines/providers,
collections, live streams and per-user credential management are unsupported.

## 2. Signatures and ownership

- `Settings.export_video: ExportConfig`; `ExportConfig.load(root, environment)`
  validates limits once at selected-engine startup; `sessdata` is excluded from
  repr. Configuration lives in `config/export.py`, not message parsing.
- `VideoExport.handle(event, gateway) -> bool` coordinates normalized sources,
  source-aware image fallback, progress, duplicate suppression and one active
  video request per service instance.
- Adapter `_read_segments` projects a verified Bilibili mini-program's
  `meta.detail_1.qqdocurl` into a normalized `link` segment. Services do not
  interpret raw OneBot JSON cards.
- `resolve_video_url(value, timeout=10.0) -> VideoTarget(video_id, part=1)`
  resolves only supported public video identities; no session is sent during
  short-link resolution.
- `BilibiliDownloader.download(target) -> DownloadedVideo(path, job, height,
  fps, size)` owns an isolated subprocess and complete output validation.
  `release(video, uncertain=False)` removes owned jobs or starts send grace.
- `OneBotV11Adapter.send_exported_video(event, video) -> None` requires a native
  receipt; `VideoSendError.uncertain` controls retention and user guidance.

## 3. Configuration, worker and transport contracts

TOML: `config/onebot/features/export/config.toml`; missing file retains normal
defaults. Keys are `video_enabled`, `max_file_bytes`, `timeout_seconds`,
`max_urls`. Explicit operational TOML wins lazily over matching environment
fallbacks. Size strings use shared positive whole K/M/G binary units through
`feature_files.size_bytes`; Setu retains its matching grammar/error behavior.

Deployment inputs are `ONEBOT_EXPORT_VIDEO_ENABLED=true`,
`ONEBOT_EXPORT_MAX_FILE_BYTES=512M`, `ONEBOT_EXPORT_TIMEOUT_SECONDS=600`,
`ONEBOT_EXPORT_MAX_URLS=3`, and optional `ONEBOT_BILIBILI_SESSDATA`.
Compose maps these into corresponding `KISARA_EXPORT_*` and
`KISARA_BILIBILI_SESSDATA` only for OneBot profiles. Direct runs use existing
selected-engine resolution. Explicit empty session disables authentication;
no chat input or second credential TOML field exists. Reject invalid cookie
characters without echoing the value. Preview redaction includes SESSDATA.

Accept BV/av video URLs (including normalized mobile forms), supported
`b23.tv` shares and the observed Bilibili mini-program card. Keep only a valid
positive `p`; absent means part1, never a whole playlist. Deduplicate targets
and enforce the configured target cap. Cap URL input and redirect hops; every
resolved target must remain on admitted Bilibili hosts/video paths. Reject
userinfo, unsafe authorities, unsupported schemes and arbitrary providers.

Worker entry: `python -m kisara.infrastructure.integrations.video_worker`.
Stdin JSON contains canonical `url`, optional `sessdata`, `max_file_bytes` and
`workspace_bytes`. Secrets never enter argv, signed URL filenames or shared
storage. Worker stdout contains only bounded safe JSON (`status`, `height`,
`fps`, or controlled `error`); raw third-party diagnostics are discarded.
The parent ignores caller-supplied output paths and accepts only its job's
complete `video.mp4`. Limit stdout, actual transfer bytes and aggregate storage;
timeout/cancellation terminates/reaps the owned worker and merger group.

Use only the pinned Bilibili extractor, scoped `.bilibili.com` cookies and
controlled API options. No external config/plugins/browser cookies/exec hooks
or generic website extractor. Select best accessible video resolution/fps
before codec tie-breaks, plus audio when present; never silently reduce quality
to fit limits. Validate a supplied session and explicitly report rejection.
Merge/remux with FFmpeg without re-encoding, then verify final streams/duration
with ffprobe. Anonymous availability is provider/session/time-specific: do not
encode a universal 480p/720p limit from one API observation.

Optional `video` extra pins yt-dlp2026.10.21 for Python >=3.10; base application
support remains >=3.8. OneBot Python3.12 images select `KISARA_EXTRA=video` and
include FFmpeg/ffprobe. Preview exact dependency checks must include the
selected package and binaries; other engine dependency closures stay separate.

Dedicated named volume `onebot_export` is mounted at `/tmp/kisara/export` in
both containers: application read/write, NapCat read-only with `volume.nocopy`.
Image copy-up owns it as application UID10001; validate actual configured
NapCat UID read access before live delivery. Do not share all application state
or expose an HTTP media port. This is transport scratch, not an archive/cache.

Spool setup/pruning occurs before authorized video admission, not simply when
constructing an adapter. Enforce a2 GiB total workspace budget, including
retained jobs and intermediates; configured final-file cap defaults512 MiB
and cannot exceed1 GiB. Confirmed/definitely rejected sends release jobs;
unknown/cancelled in-flight sends retain files for a1h grace before eligibility
for pruning on the next admission. There is no background expiry timer.
Only exact owned marked job directories may be removed; reject unsafe roots,
links and unexpected file types. Preserve unknown data and all other volumes.

## 4. Validation and error matrix

| Condition | Required behavior |
| --- | --- |
| Unauthorized sender/group or foreign quote | No provider/media operation |
| Public export feature configuration | Reject; native strict gates remain |
| Missing quote or unsupported/malformed source | Safe specific guidance |
| Disabled video / missing tooling | Explicit unavailable reply; images still export |
| Missing session | Best anonymously accessible format |
| Supplied session rejected | Safe refresh guidance; no false authenticated success |
| Format/size/workspace/merge failure | No incomplete or silently downscaled return |
| Timeout/cancellation | Reap owned subprocess group; clean appropriate partials |
| Definite native rejection | Error and normal job cleanup |
| Native result unknown/async/missing receipt | No auto retry; grace retention |
| Duplicate command event / another active request | No duplicate/new concurrent download |

## 5. Good, base and bad cases

Good: quote a card, export its actual short-link target as complete MP4, then
release it after a confirmed native receipt. Base: missing session uses available
anonymous streams; explicit image export still sends original file bytes.
Bad: download a card thumbnail, cap every anonymous export at480p, put SESSDATA
in command arguments, or delete media while a timed-out native send may use it.

## 6. Required tests

Use `test_bilibili.py`, `test_export_video.py`, `test_video_worker.py`,
`test_export_settings.py`, `test_export_deployment.py` and
`integration/test_video_export_protocol.py`, plus existing image/Setu/settings/
deployment/preview coverage. Assert actual effects/order and failures: source
normalization, safe redirect/cookie scope, >1080p selection, audio preservation,
whole-file validation, worker limits/cleanup, strict auth/quote isolation,
native certainty/lifetime and explicit-empty/other-engine config isolation.
Run focused checks then the full Docker gate. Distinguish synthetic protocol
coverage, real provider/merge probes, native receipts and client playback.

## 7. Wrong versus correct

Wrong: let the old image handler reject every generic export before inspecting
the source, or send a Bilibili CDN URL directly to NapCat without required
headers/audio merging. Correct: prepare an authorized quote once, route by
normalized source, produce a bounded complete local MP4, send through the
original conversation gateway and manage its receipt-dependent lifetime.
