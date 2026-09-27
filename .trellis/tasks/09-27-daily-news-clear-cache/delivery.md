# Daily News Cache Clearing: Delivery Review

## Result

The user-approved trigger `清除新闻缓存` removes the current UTC+8 day's PNG
and validated temporary HTML cache through `DailyNews.clear_cache() -> bool`.
It reports cleared/empty outcomes in Chinese, preserves existing authorization
and event deduplication, and lets the next news request fetch and render again.
The service prevalidates the temporary directory and serializes deletion with
generation. Filesystem failures produce safe errors and permit a new request
to retry partially completed deletion.

Historical/future/unrelated files and scheduled delivery records remain intact.
Help, operations docs, feature documentation, and storage specs are synchronized.
No deployment or live-service changes were made.

## Validation

- Implement agent: `./hako python -m pytest tests/unit/test_daily_news.py
  tests/unit/test_dispatcher.py tests/unit/test_news_delivery.py` — 46 passed.
- Independent check agent: full-scope code/spec review — no task findings or
  required corrections.
- Initial full suite from repository cwd: `./hako python -m pytest tests` —
  152 passed, 3 existing settings tests failed. Those tests clear environment
  variables but inherit local feature TOML through cwd-relative
  `load_feature()`; unlike later settings tests, they do not isolate cwd.
  Private configuration was neither read nor changed to resolve this.
- Full suite with temporary cwd and the same repository tests — 155 passed:

```bash
./hako python -c 'import os, tempfile, pytest; temporary = tempfile.TemporaryDirectory(prefix="kisara-offline-tests-"); os.chdir(temporary.name); raise SystemExit(pytest.main(["/app/tests"]))'
```

- `git diff --check` — passed.
- Runtime: Python 3.12.14 through the existing Docker wrapper. Other declared
  Python versions were not exercised. No configured lint/type-check commands.
- Review classification: `human-not-needed`; changed behavior has offline
  coverage and adapter/live-sending behavior is unchanged.

## Proposed Work Commit

Subject: `feat(news): add manual current-day cache clearing`

Explicit file list:

```text
src/kisara/application/services/daily_news.py
src/kisara/bot/dispatcher.py
src/kisara/bot/commands/help.py
tests/unit/test_daily_news.py
docs/operations.md
docs/application-template.md
.trellis/spec/trellis-plus/configuration-storage.md
.trellis/tasks/09-27-daily-news-clear-cache/prd.md
.trellis/tasks/09-27-daily-news-clear-cache/implement.jsonl
.trellis/tasks/09-27-daily-news-clear-cache/check.jsonl
.trellis/tasks/09-27-daily-news-clear-cache/task.json
.trellis/tasks/09-27-daily-news-clear-cache/delivery.md
```

Proposed body:

```text
Add the 清除新闻缓存 trigger so allowed users can discard today's
news PNG and HTML cache and fetch fresh content on their next request.
Clearing both layers prevents regeneration from reusing stale source HTML.

Serialize clearing with generation, validate temporary-directory safety,
and report cleared, empty, or safe failure outcomes. Keep authorization,
deduplication, historical files, and scheduled delivery records unchanged.
Synchronize help, operations documentation, and storage contracts.

Validation: 46 focused tests and 155 full-suite tests passed in Python
3.12.14. The full suite used a temporary cwd to isolate private local
feature TOML; the initial root run had 3 preexisting settings-isolation
failures. No lint/type-check commands are configured; other Python
versions and live QQ operations were not exercised.

Co-authored-by: OpenAI Codex <codex@openai.com>
```

Unrecognized dirty files: none at review time. Private configuration and
personal platform/runtime files are excluded.

## After Commit Approval

Commit the reviewed paths on the current `keiyaku-no-kisu` branch; do not push.
Then archive this task and record its work-commit hash in the developer journal,
using the standard separate bookkeeping commits. This task was never PR-backed
and no PR was requested, so use archive's documented `--skip-branch-validation`
option for its same-branch metadata.

Implementation and checks are complete. The user approved this commit and
archive plan with `可以提交` on 2026-09-27.
