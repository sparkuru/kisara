# Daily news private scheduled push implementation plan

## Pre-start gate

- [x] Inspect existing settings, assembly, private API, news loop and database.
- [x] Confirm user decision: group and private push share `push_time`.
- [x] Record PRD, technical design and requirement/verification mapping.
- [x] Validate curated implement/check context manifests (`task.py validate`
  passed for both manifests).
- [x] Present final planning summary and obtain explicit approval in a later
  user message before `task.py start` or product-code changes (user: 开始).

## Execution order and ownership

After approval, the main session activates the task and dispatches
`trellis-implement` with native context injection preferred and child-side
loading as fallback. One implementer owns the tightly coupled product change
below; the main session retains planning, spec changes, review, and delivery.
The implementer must preserve the earlier uncommitted schedule-template work
and all other contributors' edits.

1. Load approved task artifacts and relevant backend/Trellis Plus specs; read
   `code-python` before writing Python.
2. Add `push_users` registration, trailing default settings field, startup
   validation and TOML/environment precedence. Update config example,
   `.env.example` and both bot-service Compose mappings.
3. Add the idempotent private completion table and private APIs, preserving
   group schema and calls. Add legacy/reopen/isolation/pruning state tests.
4. Enable startup factory and connected-session scheduler for either target
   kind. Extend the existing loop to send the shared content to private users
   with isolated failure handling; preserve cancellation and retry rules.
5. Add behavior tests: personal-only startup, empty targets, shared due time,
   correct private/group API payloads, one factory per iteration, same number
   across target kinds, partial failure/retry, restart deduplication, task
   cancellation and reconnect. Use existing test files or a focused news-push
   test module if keeping scheduler cases together improves clarity.
6. Update the opening `daily_news.py` docstring, operations and relevant
   `application-template.md` news rows while preserving the new D section.
7. Run focused checks, inspect the diff and then run full regression.
8. Dispatch `trellis-check` for independent specification/behavior review;
   resolve supported findings and rerun only affected checks when needed.
9. Main session records evidence and updates applicable database/configuration
   specs through the spec-update workflow. Assess the human review gate and
   propose any commit separately; no live deployment or automatic commit.

## Expected product paths

- `src/kisara/config/feature_files.py`
- `src/kisara/config/settings.py`
- `src/kisara/bot/main.py`
- `src/kisara/bot/adapters/onebot_v11.py`
- `src/kisara/infrastructure/persistence/news_delivery.py`
- `src/kisara/application/services/daily_news.py` (opening docstring only)
- `config/features/news/config.toml.example`
- `.env.example`
- `deploy/compose.yaml`
- `docs/operations.md`
- `docs/application-template.md` (news-related descriptions only)
- `tests/unit/test_settings.py`
- `tests/unit/test_news_delivery.py`
- `tests/unit/test_onebot_adapter.py` or a focused news-push module
- `tests/unit/test_news_push.py` (new focused startup/scheduler tests)
- `tests/integration/test_onebot_protocol.py`

## Validation commands

```bash
./hako python -m pytest tests/unit/test_settings.py tests/unit/test_news_delivery.py tests/unit/test_daily_news.py tests/unit/test_onebot_adapter.py tests/integration/test_onebot_protocol.py
./dev.sh --all
git diff --check
python3 ./.trellis/scripts/task.py validate .trellis/tasks/09-27-daily-news-private-push
```

Include any new news-push test module in the focused invocation. Do not run
lint/type commands that this repository has not configured. Do not print a
resolved secret-bearing Compose configuration. Inspect the explicit changed
paths and verify documentation/code references. Record checks actually run and
the exact results or environment blockers.

## Risks and rollback points

- Deployed state: additive table initialization must preserve old group data;
  validate against a manually created old schema, not only fresh state.
- Outbound duplicates: API receipt plus local write is not atomic. Keep current
  retry behavior and describe unknown-outcome limitations without promising
  strict exactly-once delivery.
- Lifecycle: personal-only config must launch exactly one scheduler and
  disconnect must cancel it before another connected session starts.
- Product rollback: revert this feature's exact code/config changes; preserve
  private state tables and existing group records. Old parsers require removing
  `push_users` from actual runtime TOML first.
- Live checks: real QQ reachability requires separately authorized account
  verification. Automated acceptance does not require sending live messages.

## Evidence

The user approved implementation with 开始; the task is `in_progress` on
`feat/daily-news-private-push`. Implementation is complete, including a new
`tests/unit/test_news_push.py` and simulated connection/protocol tests. Main has
updated database/configuration specs. Independent full-scope review has passed.

| Check | Actual result |
| --- | --- |
| `./hako python -m pytest tests/unit/test_settings.py tests/unit/test_news_delivery.py tests/unit/test_daily_news.py tests/unit/test_onebot_adapter.py tests/unit/test_news_push.py tests/integration/test_onebot_protocol.py` | 82 passed in 1.07s |
| `./dev.sh --all` | 129 passed in 3.24s |
| `git diff --check` | Passed |
| `task.py validate` | Both manifests passed with 11 real entries each |

Tests ran on Python 3.12.14 through the existing Docker wrappers. The initial
Docker-socket sandbox denial was resolved by narrow wrapper escalation; no
wrapper/policy change was needed. No application lint/formatter/type command is
configured. No live account message, private configuration change or deployment
has occurred. Actual private QQ reachability and dated-image receipt
at the shared time remain separate live acceptance steps in operations.

Independent review is now complete: no product/spec defects and no review edits;
all ACs have automated or documentation evidence recorded in `review.md`.
Human review is required for the explicitly deferred real QQ acceptance only.
The user accepted the result and authorized committing all dirty files and
preserving them on `keiyaku-no-kisu`. Work commit `cce8c9d` includes the feature,
earlier template documentation, and additional user-edited ignore rules/font
guidance. The user-edited TOML example passed parsing through the Docker wrapper;
no product code changed after the full 129-test run. Real QQ acceptance remains
separately deferred. Task archive/journal bookkeeping and the authorized local
fast-forward into the original mainline follow the work commit.
