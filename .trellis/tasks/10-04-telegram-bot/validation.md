# Validation evidence

Branch: `feat/telegram-bot`. Status: implementation and independent review complete;
live acceptance pending. User approved the reviewed work commit with these
pending checks. No deployment or real account operations performed.

## Executed checks

- Main independently ran final `./dev.sh --all`: **311 passed**, 3 PTB retry-after
  deprecation warnings, 7.59 seconds, Python 3.12.14 / pytest 8.4.2, no skips.
- Check agent's final full gate: **311 passed**, 7.26 seconds.
- Actual pinned PTB request/protocol peer tests: **6 passed**, including revoked
  token logs/cleanup, partial initialization, saturated 128-item queue, and
  scheduler shutdown ordering.
- Recording deployment tests: **19 passed**.
- Check agent's focused routing/startup/offline suite: **70 passed**.
- Final focused OneBot/news-push and Telegram journal checks: **21 passed**.
- Implement agent verified actual Docker Compose v5.5.0 `config --quiet` and
  `config --services` with a temporary placeholder environment for OneBot-only,
  Telegram-only, combined, and official selections. No service operations ran.
- Bash syntax and `git diff --check` passed. New-file whitespace was inspected.
- Context manifest validation passed: 12 entries each in implement/check.

ShellCheck/shfmt are unavailable. The repository configures no application lint
or static type-check tool; no such check is claimed. Python 3.12 testing does
not prove every declared base-package Python version. Telegram extra needs 3.10+.

## Acceptance mapping

| Criteria | Evidence |
| --- | --- |
| AC1, AC5, AC6, AC8 | Telegram settings/adapter/protocol and registry/native-gate tests |
| AC2 | News bytes/fallback regression and captioned-document protocol tests |
| AC3 | Durable claims, receipt/restart, known/uncertain failure, cancellation, failed checkpoint, retention and date-rollover tests |
| AC4 | Recording wrapper tests and actual placeholder Compose profile validation |
| AC7 | Complete existing regression suite retained and passed |

## Human validation

Classification: **human-required** for real Telegram account/network/provider
acceptance. The code is ready for review; actual account delivery and deployment
have not been established by offline tests. Follow [live-validation.md](live-validation.md)
for exact private/group commands, denied access, near-term push, restart and
targeted lifecycle checks. Credentials remain private; no production failures
need to be injected. Commit/deployment decisions remain in the main session.

## Independent review

Full-scope Trellis check passed with no remaining code blockers. Fixed partial
SDK initialization cleanup, safe dotenv selection whitespace/comments, native
`/news_clear` adaptation, and QQ absent-service fallback. All fixes have focused
regressions and the final full gate. Docs distinguish TOML restart from container
environment recreation. Source/spec/whitespace and shell syntax checks passed.
