# Telegram and engine-routing implementation plan

Status: implementation, independent review, and approved work commit complete
on `feat/telegram-bot` (`1152184`). Live account setup/acceptance remains pending.

## Delivery shape and ordering

Keep one integrated Telegram-entrypoint task with ordered, verifiable milestones.
Feature contracts and profile-controlled deployment support the same end-to-end
release; they are not separate requested releases. Feature registration precedes
Telegram routing/scheduling integration, while deployment precedes live checks.

## Activation gate

Review the converged PRD/design/plan and nonempty context manifests. Present the
final scope/acceptance/technical decisions to the user. Only subsequent approval
of that summary permits task.py start. Do not treat prior scope answers as approval
of an earlier, materially different implementation plan.

## Milestones after approval

1. Registry, feature settings, and shared outputs
   - Load before-dev, Python/shell guidelines, and relevant specs.
   - Add explicit feature registration, switch/adaptation checks, and derived help.
   - Preserve existing dispatcher permissions/deduplication and QQ-only handlers,
     aliases, workflow ordering, fallbacks, and current configuration defaults.
   - Add compatible enabled flags and independent manual-news/push switches.
   - Add neutral news bytes/attachments while preserving OneBot output.
   - Reuse PublicServices.music without deleting other providers or data.
   - Verify disabled/unsupported features cause no provider/business effects.

2. Telegram adapter and scheduled feature
   - Add pinned optional dependency and selected-engine startup validation.
   - Normalize authorized private/group events, targeted commands, and chat-scoped
     identifiers. Keep original native reply context.
   - Implement checks/help/news/music through the effective router inventory.
   - Send readable captioned news PNG documents and music text/links.
   - Own bounded polling, synchronous-service execution, scheduler cancellation,
     and sanitized error handling.
   - Implement Telegram delivery claims/completion/known-failure/uncertain states,
     30-day retention, today-only catch-up, fallback completion, and restart checks.
   - Gate the existing QQ scheduler compatibly rather than rewrite its behavior.

3. Compose and entrypoints
   - Add profile-controlled OneBot/Telegram/official services and .env selection.
   - Preserve existing QQ project/service/state/login identity and defaults.
   - Use explicit per-container credentials and independent Telegram config/state.
   - Wire optional internal music infrastructure without forcing inactive bots.
   - Adapt start/deploy/preview routing for selected engines and targeted actions.
   - Check inactive-engine validation, conflicting QQ owners, independent stop/
     rebuild, and placeholder Compose selection. No live service changes here.

4. Integration, documentation, and review
   - Update delivered feature docstrings, operations, architecture/configuration
     specs, and applicable application template sections.
   - Document commands, switches/defaults, platform capabilities, credentials,
     subscriptions, restart/apply behavior, and migration/rollback.
   - Run focused checks and the full existing regression suite.
   - Dispatch Trellis check, resolve findings, and prepare exact live checks.
   - Follow established delivery authorization/workflow for commit/archive/journal.

## Agent protocol

After activation, use trellis-implement and trellis-check per the active Codex
workflow. Main session owns coordination, clarification, specs, integration,
commits, and finishing. Prompts start with Active task:
.trellis/tasks/10-04-telegram-bot. Native context injection is preferred; child-side
loading supplies missing context. Assign ownership and preserve others' edits.
Ordered implementation/review avoids conflicts in shared settings/contracts/router/
Compose files.

## Validation commands

    ./hako python -m pip install --user -e ".[dev,telegram]"
    ./hako python -m pytest tests/unit/test_settings.py tests/unit/test_dispatcher.py tests/unit/test_offline_commands.py
    ./hako python -m pytest tests/unit/test_daily_news.py tests/unit/test_news_delivery.py tests/unit/test_news_push.py
    ./hako python -m pytest tests/unit/test_public_services.py
    ./hako python -m pytest tests/unit/test_onebot_adapter.py tests/integration/test_onebot_protocol.py
    ./hako python -m pytest tests/unit/test_telegram_adapter.py tests/unit/test_telegram_news.py tests/integration/test_telegram_protocol.py
    ./dev.sh --all
    git diff --check

New Telegram suite names are planned outputs, not existing or executed checks.
Add meaningful registry/switch and deployment selection tests as appropriate.
Run interpreter syntax checks and available ShellCheck/shfmt for changed shell.
No incidental Python lint/type-check toolchain is required.

The full existing suite includes QQ chat/tarot/offline/setu/export/recall behavior;
do not retire it or weaken assertions to accommodate the Telegram inventory.
Validate existing package/resource references and runtime mounts remain usable.

Required Telegram cases: allowed/denied users/groups; own/other bot addressing;
equal message IDs across chats; switch/alias/help consistency; provider missing/
failure behavior; immutable warned news bytes; private/group scheduled targets;
claim/success/known failure/unknown outcome; failed completion writes; interrupted
shutdown/restart; retention/catch-up; secret-free SDK errors.

Required deployment cases: OneBot-only, Telegram-only, combined, official path;
inactive credentials/dependencies; unchanged QQ volume identity; minimal credential
mapping; targeted lifecycle isolation; explicit whole-stack behavior.

## Live preparation and rollback

Prepare authorized /ping, /help, /news, /music private/group checks, denied users,
explicit group addressing, configured provider behavior, and a near-term schedule
for allowed private/group recipients. Restart the selected bot and verify confirmed
scheduled sends do not replay. Verify existing QQ features/state while Telegram
runs and after targeted Telegram operations.

Real accounts/provider/network permissions remain human-required when unavailable.
Complete runnable preparation before asking for concrete live validation or
deployment authorization. Offline tests do not prove real account behavior.

Rollback restores prior code/images/Compose while preserving volumes/account state.
No source/resource cleanup or runtime-data deletion is part of these milestones.
