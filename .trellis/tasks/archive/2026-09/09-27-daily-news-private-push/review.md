# Final implementation review

Independent `trellis-check` review found no product or spec defects and made no
edits. The implementer and main session verified the approved feature, and the
reviewer independently inspected all tracked changes and the new untracked
`tests/unit/test_news_push.py`. The earlier template schedule section is preserved.

## Acceptance evidence

| Criteria | Evidence |
| --- | --- |
| AC1 | `test_news_push.py` tests real main factory/adapter assembly for private-only subscriptions; protocol test verifies correlated private text/image request with numeric `user_id` |
| AC2 | `test_settings.py` tests canonical QQ-number rejection, TOML/env precedence and explicit empty override, deduplication, allowlist/engine gating and independent group permissions; protocol test checks no task when both target lists are empty |
| AC3 | `test_news_delivery.py` tests same-number group/user isolation, repeated private completion, reopening and an actual pre-feature database without loss or group schema changes |
| AC4 | `test_news_push.py` covers due boundary, late today's catch-up, one content factory per iteration, group/private isolated failures, 900-second retry, provider recovery and reopened-state suppression; protocol sessions test cancellation before confirmation, reconnect retry and subsequent suppression |
| AC5 | Example, `.env.example`, both Compose services, operations, service docstring, template and database/configuration specs match implementation; focused and full regression suites passed |

## Checks performed

- Focused Docker tests: 82 passed in 1.07s.
- Full `./dev.sh --all`: 129 passed in 3.24s.
- Python runtime: 3.12.14; this is not proof for every declared Python version.
- `git diff --check`: passed, checked by implementer, main and independent reviewer.
- Context validation: both manifests passed with 11 real entries each.
- Local documentation links/source/example paths: checked by independent reviewer.
- Application lint/type checking: not configured, not run.

The reviewer reused the successful test evidence because no changes justified
repeating it. No live QQ send, private configuration change or service operation
was performed.

## Human review and remaining live acceptance

Classification: **human-required for real QQ delivery acceptance**. Automated
implementation review passes. Live delivery was explicitly outside implementation
validation and remains deferred; commit confirmation must acknowledge this limit.

The runnable manual procedure is in `docs/operations.md`: add an allowed,
reachable QQ recipient to news `push_users`, choose a shared UTC+8 time a few
minutes ahead, restart through the normal deployment path, verify dated-image
receipt, restart on the same day and verify no duplicate. Restore the intended
schedule afterward; observe existing group push too when configured.

Unknown remote results or a crash/local checkpoint failure after a successful
send can still result in duplicate delivery under existing retry behavior. This
is documented and the implementation does not claim strict exactly-once delivery.

## Commit readiness

All product dirty paths are recognized work from this conversation. The user
approved committing the complete working directory, including their additional
`.gitignore` changes and news-example font documentation. These additional
changes are documentation/ignore rules, with no product-code changes since the
129-test run. Main inspected the extra diff and checked its font claims against
the renderer and existing Compose config mount. The user also requested local
integration into the original `keiyaku-no-kisu` mainline. The exact work commit,
archive/journal bookkeeping and fast-forward plan are in `commit-plan.md`.
