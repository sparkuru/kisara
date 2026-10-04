# Proposed work commit

Status: user approved the reviewed work commit with pending live checks;
committed as `1152184`. Deployment and pushing remain separate.

1. `feat(bot): add Telegram entry point and engine-aware routing`

   Scope: reviewed product code, tests, deployment/config examples, operations
   documentation, project-owned specs, and this task’s planning/validation artifacts.

## Exact file list

- `.env.example`
- `.trellis/spec/backend/database-guidelines.md`
- `.trellis/spec/backend/directory-structure.md`
- `.trellis/spec/backend/logging-guidelines.md`
- `.trellis/spec/trellis-plus/architecture.md`
- `.trellis/spec/trellis-plus/configuration-storage.md`
- `.trellis/spec/trellis-plus/index.md`
- `.trellis/spec/trellis-plus/validation.md`
- `.trellis/tasks/10-04-telegram-bot/check.jsonl`
- `.trellis/tasks/10-04-telegram-bot/commit-plan.md`
- `.trellis/tasks/10-04-telegram-bot/design.md`
- `.trellis/tasks/10-04-telegram-bot/implement.jsonl`
- `.trellis/tasks/10-04-telegram-bot/implement.md`
- `.trellis/tasks/10-04-telegram-bot/live-validation.md`
- `.trellis/tasks/10-04-telegram-bot/prd.md`
- `.trellis/tasks/10-04-telegram-bot/research/feature-routing.md`
- `.trellis/tasks/10-04-telegram-bot/research/repository-fit.md`
- `.trellis/tasks/10-04-telegram-bot/research/telegram-library.md`
- `.trellis/tasks/10-04-telegram-bot/task.json`
- `.trellis/tasks/10-04-telegram-bot/validation.md`
- `config/features/help/config.toml.example`
- `config/features/music/config.toml.example`
- `config/features/news/config.toml.example`
- `config/features/ping/config.toml.example`
- `config/official/readme.md`
- `config/telegram/features/help/config.toml.example`
- `config/telegram/features/music/config.toml.example`
- `config/telegram/features/news/config.toml.example`
- `config/telegram/features/ping/config.toml.example`
- `deploy.sh`
- `deploy/Dockerfile`
- `deploy/compose.yaml`
- `deploy/engines.sh`
- `deploy/onebot.sh`
- `docs/application-template.md`
- `docs/operations.md`
- `preview.sh`
- `pyproject.toml`
- `readme.md`
- `src/kisara/application/services/__init__.py`
- `src/kisara/application/services/daily_news.py`
- `src/kisara/application/services/news_push.py`
- `src/kisara/application/services/public.py`
- `src/kisara/bot/adapters/onebot_v11.py`
- `src/kisara/bot/adapters/telegram.py`
- `src/kisara/bot/commands/help.py`
- `src/kisara/bot/contracts.py`
- `src/kisara/bot/dispatcher.py`
- `src/kisara/bot/features.py`
- `src/kisara/bot/main.py`
- `src/kisara/config/feature_files.py`
- `src/kisara/config/settings.py`
- `src/kisara/infrastructure/persistence/telegram_news.py`
- `start.sh`
- `tests/integration/test_telegram_protocol.py`
- `tests/unit/test_dispatcher.py`
- `tests/unit/test_engine_deployment.py`
- `tests/unit/test_news_push.py`
- `tests/unit/test_telegram_adapter.py`
- `tests/unit/test_telegram_news.py`
- `tests/unit/test_telegram_settings.py`

## Commit body

```text
Add Telegram as another Kisara entry point for online checks, help, news,
scheduled news and music, with explicit platform-aware routing and switches.
Keep SDK operations behind adapters, authorize before business effects, and
isolate Telegram credentials/configuration/state in Compose profiles.

Persist delivery claims before sending; distinguish confirmed receipts, known
rejections and uncertain outcomes. Own bounded polling and background lifecycle,
including revoked tokens, partial initialization and safe error diagnostics.

Add targeted engine operations and document .env recreation versus TOML restart.
Validation: 311 tests passed, including existing QQ regressions, real pinned-SDK
fake-peer lifecycle/protocol cases and deployment recording tests. Placeholder
Compose validation passed for OneBot, Telegram, combined and official profiles;
Bash syntax and whitespace checks passed. No lint/type toolchain is configured.
Real Telegram accounts, group permissions, network and music provider acceptance
remain pending; no online services or deployment data were changed.

Co-authored-by: OpenAI Codex <codex@openai.com>
```

## Other dirty files

None. Existing private credentials, runtime data, personal agent configuration,
and development caches are excluded by Git ignore rules and are not candidates.

## Delivery boundary

Real account acceptance is human-required; see [live-validation.md](live-validation.md).
User confirmation must acknowledge the documented pending live checks before
any work commit. A commit does not authorize deployment or pushing.
Normal task archive/journal bookkeeping follows the approved delivery workflow
after the work commit and its acceptance requirements are satisfied.
