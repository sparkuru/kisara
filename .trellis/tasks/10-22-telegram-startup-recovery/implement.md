# Telegram startup recovery execution plan

1. Read PRD/design, full curated specs, Python conventions and existing adapter
   startup, partial-init cleanup, polling ownership and readiness tests.
2. Add focused failing protocol fixtures for one-time getMe/init and
   deleteWebhook/bootstrap transport failures. Record the original behavior
   separately from the unproven historical incident cause.
3. Implement the smallest adapter-owned bounded recovery and classified safe
   diagnostics. Expected code boundary: bot/adapters/telegram.py, bot/main.py if
   necessary, unit/test_telegram_settings.py and integration/test_telegram_protocol.py;
   adjust existing unit/test_telegram_adapter.py only for directly affected
   ownership/error coverage. Preserve others' edits and avoid unrelated refactors.
4. Verify exactly three total attempts, successful recovery, nonretryable
   exception subclasses, request/poller cleanup, stop during backoff, no false
   readiness and absence of synthetic secrets in logs.
5. Run focused existing suites through the offline Docker wrapper:
   ./kisara.sh test tests/unit/test_telegram_adapter.py tests/unit/test_telegram_settings.py
   tests/integration/test_telegram_protocol.py tests/unit/test_preview_readiness.py -q
6. Dispatch independent Trellis check; run the required full ./kisara.sh test -q
   after focused success. Record exact commands, outcomes and real-runtime limits.
7. Main updates applicable project-owned error/logging/readiness contracts and
   task/mainline evidence, reviews full diff, then requests commit approval.

No live Telegram API call, service restart, dotenv read or account cutover is
needed for fixture reproduction. No implementation before final plan approval.
