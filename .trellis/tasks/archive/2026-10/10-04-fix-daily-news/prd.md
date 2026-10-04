# Fix daily news failure

## Goal

Restore /news delivery during LyToday's publication delays by sending its
yesterday brief with a prominent warning, while allowing later manual requests
to receive updated news.

## Background

- The user clarified /news is affected; preserve /brief and Chinese aliases,
  with no /daily-news addition (src/kisara/bot/dispatcher.py:159).
- The 2026-10-04 source page prepends 今天的简讯未更新，下面是昨天的简讯！
  to 15 headlines under today's header. The original parser treated the notice
  as a sixteenth headline (src/kisara/application/services/daily_news.py:370).
- The first classification-only patch passed 203 tests but the user's deployed
  scheduler still could not deliver news. The user subsequently approved a
  clearly labeled yesterday brief and avoiding cache that blocks later updates.
  This supersedes notice rejection; stale page headers remain invalid.

## Requirements

- R1: Preserve commands, authorization, argument validation, engine behavior,
  fresh-day caching, and strict date/headline validation.
- R2: Accept a current-day page with exactly one recognized notice and 15 valid
  actual headlines. Retain all page sections; visibly warn in the PNG and
  text replies for both engines that these are yesterday's brief.
- R3: Never retain or reuse fallback HTML/PNG as today's cache. Each result
  owns its image bytes across concurrent requests/cache clearing. Every later
  fallback request refetches; published data resumes normal caching.
- R4: Preserve once-per-day scheduled delivery: successfully sent labeled
  fallback counts as today's delivery. No second automatic push after
  publication; failures retain existing retry/state semantics. Manual /news
  can retrieve updated content.
- R5: Sync implementation docstrings, operations/feature docs, storage spec,
  tests, and final validation evidence.

## Acceptance Criteria

- [x] AC1 / R1: Existing authorized commands and official text behavior pass;
  rejected requests make no provider call.
- [x] AC2 / R2: Observed header+notice+15 headlines generates a valid attributed
  PNG with a prominent warning and handled text/image reply. The same text
  outside the news list is not a publication signal.
- [x] AC3 / R3: No fallback dated HTML/PNG publication; repeated requests refetch;
  earlier results preserve their bytes. Cached fallback HTML refetches and the
  next published page caches normally without manual clearing.
- [x] AC4 / R1/R2: Stale/invalid dates, duplicate notices, and missing, extra,
  empty, oversized actual headlines remain errors.
- [x] AC5 / R4: Scheduler fallback success is checkpointed once per day, with
  no resend of completed targets after publication; failure retry stays intact.
- [x] AC6 / R5: Focused and full Docker tests pass, actual source HTML renders
  a visually checked warning PNG, and docs/specs/final diff match behavior.

## Out of Scope

New command spellings, changing provider, accepting arbitrary stale headers,
sending twice daily, changing retry intervals/permissions/schema, deployment,
runtime restart, and live QQ messages.

## Decisions and Risks

- The user approved labeled yesterday fallback after the deployed failure,
  then authorized the reviewed work commit and task archival. Implementation
  and all acceptance criteria are complete; see validation.md.
- Existing once-per-day semantics are retained: fallback success completes
  scheduled delivery. Document that manual /news retrieves a later update.
- Keep fallback image bytes in the result instead of a shared mutable disk file.
- Source publication and QQ reachability remain external. This revised result
  flow has design.md and implement.md for cross-layer review.
