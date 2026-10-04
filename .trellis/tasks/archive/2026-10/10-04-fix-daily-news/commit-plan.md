# Proposed commit plan

Approved by the user and executed: work commit 0db32e3. Task archival and
journal recording use the approved bookkeeping steps below.

## Work commit

Subject: fix(news): deliver labeled fallback during publication delays

Explicit files:

- src/kisara/application/services/daily_news.py
- tests/unit/test_daily_news.py
- tests/unit/test_news_push.py
- docs/operations.md
- docs/application-template.md
- .trellis/spec/trellis-plus/configuration-storage.md

Body and attribution:

    Restore /news when LyToday serves yesterday's brief under today's
    page header with an unpublished-news notice.

    Separate one recognized warning from 15 validated actual headlines
    and prominently retain it in image and text. Return immutable inline
    fallback PNG bytes without dated HTML/PNG cache publication, so later
    requests refetch and published news resumes normal caching. Preserve
    existing date/headline checks, permissions, aliases, engine behavior,
    and scheduled retry/state. A successful fallback push completes the
    day's delivery; publication does not automatically send it again.

    Update feature docs and storage contracts. Validation: the fallback
    regression failed before the fix, 78 focused and 215 full Docker tests
    passed, and actual source HTML generated a visually checked 960x5648
    warning PNG with no dated cache. git diff --check passed.
    Python 3.12 was exercised; no live QQ or deployment checks were run.
    Running containers still need a normal rebuild/restart to apply the fix.

    Co-authored-by: OpenAI Codex <codex@openai.com>

## Bookkeeping after the work commit

With the same approval, archive this task and record the session using normal
Trellis bookkeeping commits. Preserve unrelated files; no push or deployment.
No unrecognized dirty files were found. The task has no PR and was developed
on the existing branch, so use the installed explicit non-PR archive option:

    python3 .trellis/scripts/task.py archive 10-04-fix-daily-news --skip-branch-validation

Record the journal with the resulting work commit hash. Do not fabricate branch
or merge records. This plan supersedes the held classification-only proposal.
