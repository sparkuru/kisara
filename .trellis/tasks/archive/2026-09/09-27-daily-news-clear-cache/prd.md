# Manual Daily News Cache Clearing

## Goal

Let an authorized user send `清除新闻缓存` to discard today's cached news and
make the next news request fetch current source content and render a fresh PNG.

## Background

The user requested a manual clearing command after asking about clearing the
current day's image. Task creation was approved on 2026-09-27.
`DailyNews.get()` reuses a dated PNG and otherwise reuses validated dated HTML
before fetching the provider (`src/kisara/application/services/daily_news.py:144`).
Existing news routing accepts no arguments (`src/kisara/bot/dispatcher.py:151`).
Authorization and duplicate rejection precede routing; the existing alias
normalizer also recognizes commands in allowed groups without chat enabled.

## Requirements

- R1: Recognize the exact phrase `清除新闻缓存` through existing command routing.
  Whitespace and the optional hash prefix follow normal alias behavior. Clear
  commands accept no arguments.
- R2: Clear only the current China Standard Time day's `YYYYMMDD.png` from the
  configured news cache and `YYYYMMDD.html` from the existing temporary cache.
  Coordinate clearing with the service's cache-generation lock.
- R3: Return a concise Chinese confirmation when cache files were removed and
  a distinct Chinese response when no current-day files existed. Clearing must
  not fetch or render news. Missing cache directories are a normal empty state.
- R4: Retain existing sender and group allowlist checks and duplicate-event
  rejection. Support authorized private messages and enabled, allowed groups.
  Do not introduce a separate administrator policy.
- R5: Translate filesystem failures to the existing feature error boundary;
  never report successful clearing after a deletion failure. Retain temporary
  HTML directory ownership, mode, and symlink safety checks.
- R6: Update enabled-feature help, implementation documentation, and relevant
  operations/application feature documentation to describe the command.

## Acceptance Criteria

- AC1 (R1-R3): After generating news, the phrase removes both current-day
  files; the next news request performs a second provider fetch and generates
  a usable PNG. Older, future, and unrelated files remain intact.
- AC2 (R2-R3): Clearing before first use, clearing twice, and clearing when only
  one cache layer exists succeed without creating directories or making
  external requests. UTC-to-UTC+8 day selection is covered.
- AC3 (R4): Unauthorized senders, disabled/disallowed groups, and duplicate
  events leave cache files untouched. Authorized private and group messages
  receive a handled text response, including when chat is disabled.
- AC4 (R1,R5): Invalid command arguments return an error without clearing;
  deletion failures and unsafe temporary cache directories produce error
  outcomes rather than successful confirmations.
- AC5 (R6): Help only advertises clearing when the daily-news service is
  enabled; documentation states both cache layers and refresh semantics.
- AC6: Focused news/routing tests and the full existing suite pass through the
  repository's Docker development wrapper. Record actual results and any
  environmental limits.

## Out of Scope

Historical cache purging, immediate regeneration or sending, scheduled delivery
record resets or resend behavior, new configuration, adapter protocol changes,
new storage paths, and deployment/service restarts are outside this change.

## Artifact Status

This is a lightweight PRD-only task. Context manifests identify applicable
specs. The user approved the final planning summary with `开始`; implementation
started on 2026-09-27.
