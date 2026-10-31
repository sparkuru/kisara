# 扩展引用消息视频导出：Bilibili 小程序与链接

## Goal

Allow an authorized OneBot/QQ user to quote a Bilibili share and receive its
video, using the best quality accessible with the configured session or
anonymously. Preserve the existing original-image/sticker export.

## Background and owner decisions

- The initial request explicitly authorized creating this task and inspecting
  recent preview messages as test inputs.
- The subsequent answer approved first-iteration scope of Bilibili mini-program
  cards, short links and ordinary video URLs; other providers are deferred.
- The user supplied `/tmp/tmp/bilibili.env` and authorized using its session.
  Its actual variable is `BILIBILI_SESSDATA`; no ESSID-specific handling is needed.
- The supplied credential is a deployment credential for this implementation's
  preview validation, not a request for chat-based credential collection or
  a per-user credential-management feature.

## Requirements

- R1: Add Bilibili linked-video export to the existing quoted-message workflow.
  The normal `导出` request chooses the quoted source; add an explicit video
  command while retaining `/export-img` and image-specific phrases.
- R2: Accept structured Bilibili mini-program cards, `b23.tv` short links, and
  ordinary BV/av video URLs. Resolve short links only to supported Bilibili
  video targets. Respect a video's `p` parameter; without it export the first
  part rather than expanding an entire anthology. Deduplicate repeated targets
  in one quoted message; process distinct supported targets sequentially.
- R3: Use the supplied/configured SESSDATA when available, scoped to Bilibili
  requests. Without credentials, select the highest anonymously accessible
  format. Never silently limit resolution to 480p/720p/1080p or claim a premium
  entitlement. Explicitly report an expired/rejected provided session.
- R4: Produce a complete MP4 with video and audio where the source has audio,
  then send it as a native video to the requesting conversation. Preserve
  quality during local merging; report actual selected quality and operational
  failures. Do not silently return a thumbnail, page link, or audio-only file.
- R5: Preserve original-image/sticker export, its file attachment behavior,
  strict sender/group authorization and quote conversation ownership checks.
  Public command exceptions must not authorize this native export.
- R6: Reuse the observed preview message formats as sanitized test fixtures.
  Verify anonymous/authenticated format selection, download/merge and native
  return separately; record actual evidence and any remaining live gate.
- R7: Bound download size, runtime, concurrent work and temporary retention.
  Explain limit failures instead of silently choosing lower quality. Avoid
  automatic resend after an uncertain send outcome; duplicate deliveries of
  the same command must not repeat new video work within the process window.
- R8: Keep credentials out of logs, replies, process arguments, shared media
  storage and version control. Wire the optional session through the existing
  OneBot configuration/deployment chain; preserve explicit-empty semantics and
  keep other engines isolated. The supplied temporary file is not a permanent
  hard-coded application dependency.
- R9: Repair the user's follow-up preview blocker: terminal-control cleanup and
  redaction must work under real non-C collation locales as well as C/POSIX/
  C.UTF-8. Preserve the caller's locale, Unicode text, existing QQ terminal-QR
  work and fail-closed diagnostics. This is an execution blocker fix inside
  the current task, not new provider scope or account-reset authorization.

## Acceptance Criteria

- [x] AC1 (R1, R2, R4): Quoting each preview-supported input shape and asking
  for export returns a complete video to the original conversation. Direct BV,
  av, short-link, specified-part and duplicate-target cases have coverage.
- [x] AC2 (R3, R4): Missing credentials select the best anonymous format;
  configured credentials select the best format accessible to that session.
  Include a fixture above 1080p to prevent accidental fixed-resolution caps.
  Expired-session, restricted-video and provider errors produce safe replies.
- [x] AC3 (R1, R5): Image/sticker commands retain original-byte file export;
  generic export routes to the appropriate source without being consumed by
  the old image-only rejection. Setu and ordinary command routing still work.
- [x] AC4 (R5, R7): Unauthorized sender/group and foreign-conversation quotes
  cannot trigger downloads or media sends. Duplicate video command events do
  not start duplicate work; unsupported/malformed sources fail explicitly.
- [x] AC5 (R6): The evidence record distinguishes real message inspection,
  official API format probes, automated protocol/worker tests, and real native
  video reception/playback. No unrun gate is reported as passed.
- [x] AC6 (R7): Oversized/unknown-length transfers, timeouts, cancellation,
  concurrency saturation and interrupted temporary files are bounded; files
  remain available to NapCat for their required send lifetime and are cleaned
  without touching unrelated files or persistent application state.
- [x] AC7 (R8): Configuration tests prove startup validation, explicit-empty
  suppression and engine isolation; synthetic secrets never appear in captured
  logs, replies, worker arguments or artifacts. OneBot runtime preparation
  includes the selected downloader and merger; existing image export does not
  require Bilibili credentials.
- [x] AC8 (R9): Buffered diagnostics, live stream/preflight and QQ snapshots no
  longer fail with `Invalid range end` under installed en_US/zh_CN UTF-8
  collations. ANSI-interleaved synthetic secrets remain redacted, Chinese
  logs remain intact, the caller's locale is unchanged and QR presentation
  regressions still pass.

## Evidence and constraints

- Before implementation, native export was OneBot-only:
  `src/kisara/application/services/export_img.py:37` recognizes export phrases;
  `src/kisara/application/services/export_img.py:45` rejects non-image quotes.
  `src/kisara/bot/adapters/onebot_v11.py:249` invoked it before other routing.
  The conversation-ownership boundary was at
  `src/kisara/bot/adapters/onebot_v11.py:317`.
- No preexisting Bilibili provider or SESSDATA configuration was found.
  [Preview evidence](research/preview-samples.md) records the card's actual
  `meta.detail_1.qqdocurl` target and text URL.
- [Provider research](research/bilibili-provider.md) records the supplied
  session's successful login probe and this sample's anonymous 480p versus
  authenticated 1080p format availability. These are metadata/API observations,
  not proof of a downloaded or delivered file.
- Current app packaging declares Python >=3.8; deployment uses Python 3.12.
  Preserve the existing base support declaration; optional video dependencies
  have their own evidenced runtime requirements.
- On 2026-10-26, after reviewing the final planning summary and linked artifacts,
  the user answered “开始”, approving implementation, checking and the described
  targeted OneBot/NapCat preview validation. Keep unrelated engines/data intact.

## Out of scope

Other websites, arbitrary URL downloading, other bot engines, Bilibili live/
bangumi/course/interactive-video exports, whole collections/playlists,
chat-based or per-user credential management, persistent video archives,
cross-restart exactly-once delivery, and unrelated Telegram work.

Deployment and live video testing follow the reviewed implementation/validation
plan; commit, archive and push are not part of the implementation approval.

## Current acceptance state

All acceptance criteria are closed. Implementation and independent full
regression passed; real sample MP4 files were downloaded, merged and decoded
successfully. On 2026-10-31 the user confirmed “qq 回传确认了。通过”, closing
the remaining native QQ return acceptance after the earlier login blocker.
This is user-reported live acceptance; no additional receipt IDs or playback
measurements were collected in this delivery session.

The locale-dependent ANSI filter blocker is verified by the narrow repair,
real host locale/CLI probes and the combined full gate (1305 passed,7 skipped,
3 existing warnings). See [validation](validation.md) and
[locale research](research/preview-redaction-locale.md) for scoped evidence.
The user explicitly authorized committing and archiving this task on
2026-10-31. The separate QQ terminal-QR task remains outside this delivery.
