# 定时新闻可配置重试间隔

## Goal

将定时新闻抓取及可安全重试的发送失败间隔设为可配置秒数，默认60秒，保留去重和Telegram限流/不确定结果保护。

## Background

On 2026-10-26 the user reported a scheduled OneBot news fetch failing in TLS
handshake. Read-only checks confirmed the historical handshake error but found
current host/container requests healthy, including three successful calls using
the application's HttpReader. Both explicit and transparent local proxy paths
participate; historical local-versus-upstream attribution remains unknown.
The user requested automatic retry after about 60 seconds, then explicitly
required the seconds to be configurable.

Current OneBot scheduler sleeps 900 seconds for pending work
(`bot/adapters/onebot_v11.py:_run_daily_news`). Telegram already journals retryable
generation/rejection failures for 900 seconds (`application/services/news_push.py`).
This is a retry-policy/configuration change, not another preview repair.

## Requirements

- R1: Scheduled news retries generation failures and existing safely retryable
  delivery failures using a positive integer seconds setting, default 60.
- R2: Each supported scheduled-news engine has independent configuration:
  `news.push_retry_seconds` in its feature TOML; explicit TOML wins over selected
  engine `ONEBOT_NEWS_PUSH_RETRY_SECONDS` / `TELEGRAM_NEWS_PUSH_RETRY_SECONDS`,
  then generic runtime `KISARA_NEWS_PUSH_RETRY_SECONDS`, then default60. Preserve
  existing namespace isolation and OneBot legacy deployment fallback.
- R3: Reject invalid configured values at startup, including zero, negative,
  boolean, fractional and malformed/empty values. Do not busy-loop or silently
  replace explicit invalid settings with a default.
- R4: Preserve independent target checkpoints and skip confirmed sends; retain
  Telegram permanent-rejection and uncertain-send protections. A longer server
  retry-after still wins. Retry delay starts after the failed operation finishes;
  waiting is cancellable. Only today's scheduled work is retried.
- R5: Synchronize examples, Compose wiring, operational documentation and
  implementation docstrings. No new generic HTTP retry policy or manual-news
  retry behavior.

## Acceptance Criteria

- [x] AC1 (R1): A failed generation is followed by a successful scheduled retry
  at the default60 or a non-default configured interval, without sending early.
- [x] AC2 (R2-R3): Tests cover defaults, TOML/env precedence, engine isolation,
  invalid values and Compose propagation for ordinary/development OneBot and Telegram.
- [x] AC3 (R4): Confirmed targets are not replayed; Telegram longer retry-after,
  permanent/uncertain states, cancellation and day boundaries remain correct.
- [x] AC4 (R5): Examples/docs show how to configure seconds and required runtime
  rollout. Focused and full offline regression pass with exact evidence recorded.

## Scope and constraints

Change settings/feature-key loading, the existing two schedulers and adapter
injection, safe config examples, Compose mapping, operations docs, tests and
project-owned specs/task records. Reuse existing validation and scheduling
mechanisms; do not add a new scheduler, dependency, database schema or retry flag.
Do not alter HTTP timeouts, proxy/TLS policy, manual news, recipient permissions,
live service/account state, private configuration values or unrelated pending
preview/Telegram startup changes. No commit/archive/push is authorized.

## Authorization

The user's request to add60-second automatic retry and subsequent explicit
configurability requirement authorize implementing this bounded change. Technical
defaults and boundaries above follow existing feature configuration/delivery
contracts. Implementation and tests proceed without another process confirmation.

## Validation status

Implementation is complete. Selected new regressions failed23/passed8 before
production changes and passed31 afterward; the eight already-passing cases
were existing safe rejection of unsupported TOML keys. Focused
news/settings/deployment/OneBot+Telegram protocol checks passed386 tests with
one existing missing-Git skip in20.97 seconds. Examples, operations guidance and
project-owned config contract are synchronized. Independent source review found
no actionable defect; full `./kisara.sh test -q` passed1179 tests with one
existing skip and three existing PTB warnings in560.36 seconds, exit0. Both
eight-entry context manifests validate; the configuration spec's per-file
injection truncation warning was handled by direct repository reads. Main
independently parsed both news TOML examples and resolved task-relative links.
See
[implementation evidence](implementation-evidence.md) for exact commands and
the isolated-fixture boundary, and [independent review](check-evidence.md) for
the full gate and scope checks. Human review is optional for this source
contract; actual deployed-provider recovery was not exercised. Live deployment,
private config edits, commit/archive/push remain undone.
