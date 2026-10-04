# Completion evidence

## Final behavior

The user approved sending LyToday's yesterday brief with an explicit warning
after the first classification-only patch still left deployed delivery blocked.

A current-day page with one recognized warning and 15 valid actual headlines
now produces handled text/PNG output. The original Chinese warning is displayed
prominently before the brief and included in both engines' text. The page date
is distinguished from headline freshness. Actual headlines and every existing
page section remain validated and retained.

Fallback results own immutable PNG bytes with no disk image path. No fallback
dated HTML/PNG is written or reused; cached fallback HTML is discarded and
refetched. Repeated fallback requests fetch again; published data resumes normal
dated caching. Prior results survive later renders, publication, and clearing.

Scheduled successful fallback sends complete today's normal group/private
delivery checkpoint. Publication does not trigger another automatic send;
manual /news can retrieve updated content. Existing failure retry, permissions,
date/headline rejection, commands, configuration, and SQLite schema remain.

## Executed checks

- A new fallback parser regression failed against the previous rejection-only
  code before the final fix (not-yet-available exception instead of a page).
- Final focused command:
  ./hako python -m pytest tests/unit/test_daily_news.py
  tests/unit/test_news_push.py tests/unit/test_news_delivery.py
  tests/unit/test_dispatcher.py -q
  Result: 78 passed in 0.87 s.
- Independent final Trellis check: ./dev.sh --all -q
  Result: 215 passed in 3.89 s, exit 0. Actual concise execution evidence:
  /tmp/kisara-news-fallback-check.txt. Reviewer found no defects or extra edits.
- git diff --check: passed. Task context validation: 7 real entries per manifest.
- Main rendered the saved 2026-10-04 public source HTML through DailyNews using
  the existing ./hako wrapper and an official Noto CJK font kept only in /tmp.
  Asserted exact notice, image_path=None, no dated HTML/PNG publication, and
  successful onebot_image encoding. Output: /tmp/kisara-news-fallback-preview.png,
  valid 960 x 5648 PNG.
- Main and reviewer visually inspected the real-source PNG: the red original
  warning is prominent before the brief; Page date, attribution, and all page
  sections remain visible. This proves rendering, not live QQ delivery.

## Review and limits

Human review is human-optional. A later authorized live /news request can
confirm actual QQ delivery; code completion does not depend on that reply.
Tests used existing offline Docker/Python 3.12, with no claims for other Python
versions. No configured lint/type-check exists. No live QQ, private credentials,
deployment, runtime restart, or scheduled-state migration was performed.

## Delivery state

Implementation, final checks, docs/spec sync, PRD acceptance, and preview are
complete. The user approved the final commit plan, including task archival and
journal recording. Work commit: 0db32e3, fix(news): deliver labeled fallback
during publication delays. Bookkeeping follows through the normal Trellis
commands; no remote push or deployment is included. Existing running containers
need a normal rebuild/restart to use these changes; this was not performed.
