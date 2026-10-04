# Labeled publication-delay fallback

## Boundaries and data flow

Keep behavior in `application/services/daily_news.py`, shared by dispatcher
and scheduled factory. Existing callers continue using `get()`, `.text`, and
`.onebot_image()`; no routing or scheduler redesign.

Separate exactly one recognized news-list notice from actual headlines;
validate the remaining 15 entries and current page date. Attach the notice
to `DailyPage` as an optional defaulted field. Duplicate notices stay invalid.
Render it prominently before the brief; retain sections and attribution.

## Result and cache contracts

Extend `DailyNewsResult` so published results still reference dated
`image_path`, while fallback results have immutable PNG bytes, notice, and no
disk image path. `onebot_image()` encodes bytes or reads the fresh cached file;
`.text` shows the warning for both engines. Distinguish the page date from the
headline freshness in fallback text.

Write only published source HTML. Cached fallback HTML is discarded and
refetched through existing recovery. Validate fallback PNGs and return them
in memory; do not write a dated image. Preserve published cache pruning,
locking, atomic writes, and reuse. Independent immutable results avoid races
with later fetches or cache clearing. No persistent fallback cleanup is needed.

## Scheduled delivery and compatibility

The factory still builds ordinary `OutgoingMessage`; a successful fallback
send completes today's delivery checkpoint. There is no automatic resend of
completed targets after publication. Manual /news can fetch newer content.
Failed-target retry and SQLite schema stay unchanged.

No provider, config, dependency, or persistent format is added. Fresh cached
images stay compatible if their layout does not change; only fallback images
show the warning and they are not cached. Rollback removes optional warning
and inline bytes handling; published caches and delivery state stay compatible.
