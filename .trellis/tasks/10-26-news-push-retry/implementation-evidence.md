# Scheduled-news configurable retry implementation

## Context and boundary

The native hook supplied curated task context but truncated the visible output.
Read the saved `/tmp/hook_outputs/01a175c4-0ff8-7f22-ad92-46fbce52aea8/dcce174f-20be-4b51-b260-749eb3fd9d25.txt`
and explicitly loaded task artifacts, manifests and relevant repository specs.
The configuration/storage spec grew beyond the native per-file cap during main
session updates; the new scheduled-news section was read directly from the
repository. Applicable Python coding guidance was loaded. Preexisting dirty
preview and Telegram startup-recovery work was preserved.

## Changes

- Append `Settings.news_push_retry_seconds = 60`, keeping positional constructor
  compatibility. News TOML accepts `push_retry_seconds`; lazy explicit TOML wins
  over selected-engine env, generic runtime env and default. Invalid zero,
  negative, boolean, fractional, empty and non-numeric inputs fail startup.
- OneBot's existing connected-session loop uses the configured interval in place
  of900 seconds. It keeps durable confirmed-target suppression, retained data,
  today-only scheduling and cancellation semantics. Generation-error diagnostics
  now name the retry delay.
- Telegram's existing scheduler accepts a trailing optional `retry_seconds`
  argument, injected by the adapter. Generation/known-rejection deadlines start
  after failure completion, with longer server retry-after preserved. Polling
  sleeps `min(30, retry_seconds)`, supporting short intervals without a new task
  or scheduler. Confirmed/permanent/uncertain states and journal schema remain
  unchanged. Existing persisted retry deadlines are not rewritten.
- Compose wires ordinary/development OneBot and Telegram independently. Both
  OneBot fallback levels use unset-only interpolation so explicit empty values
  reach startup validation. Telegram deployment does not inherit generic OneBot
  settings. Update both TOML examples, `.env.example`, existing operations
  guidance and feature implementation docstrings.

No HTTP timeout/proxy/TLS changes, automatic manual-news retry, dependency,
schema change, private dotenv rewrite, live service/account operation,
commit/archive/push or README edit occurred.

## Regression evidence

Before production changes:

```sh
./kisara.sh test tests/unit/test_news_retry_settings.py tests/unit/test_news_push.py tests/unit/test_telegram_news.py -k 'news_retry or failed_factory or generation_retry or rejection_retry or short_retry' -q
```

Result: **23 failed, 8 passed, 20 deselected in0.47s**. Failure categories:
missing settings/schema/constructor support; invalid environment not rejected;
old900-second delay rather than60; no custom interval; no post-failure deadline
or short-poll contract. Eight existing unsupported-key rejection cases already
failed safely and passed the invalid-input tests before implementation.

After production changes, the same command passed **31 tests,20 deselected
in0.43s**. These tests include slow generation/send failure followed by no early
retry and eventual success, default/custom timing, server wait precedence,
short-poll cancellation and configuration precedence/type rejection.

Added further coverage after that before/after comparison:

- Six invalid generic runtime values cannot silently revive the default.
-27 actual Compose interpolation combinations cover three services, absent/
  empty/custom selected variables and absent/empty/custom legacy values, with
  other-engine sentinels proving isolation.
- Real Telegram adapter lifecycle injects default/custom retry settings into
  its scheduler and cancels that scheduler before SDK cleanup.
- Existing news expectations now use60 seconds while still checking mixed-target
  partial retry, recorded-success suppression and next-day waits.

Focused integration command:

```sh
./kisara.sh test tests/unit/test_news_retry_settings.py tests/unit/test_news_push.py tests/unit/test_telegram_news.py tests/unit/test_settings.py tests/unit/test_telegram_settings.py tests/unit/test_engine_deployment.py tests/integration/test_telegram_protocol.py tests/integration/test_onebot_protocol.py -q
```

Result: **386 passed,1 skipped in20.97s**, exit0. The skip remains the existing
missing Git executable in the development image. Checks run in the existing
Python3.12 Docker wrapper with synthetic configuration/providers/protocol peers,
not live dotenv/accounts. Initial sandboxed wrapper access returned126 due to
Docker socket denial; narrow wrapper escalation succeeded. No automatic
approval-review rejection occurred.

`git diff --check` passed. The repository has no configured application linter
or type checker; no new toolchain was installed. Independent full regression
and final review belong to the main-session checker, not this evidence report.

## Rollout and limits

Production containers were not rebuilt or restarted, so current live instances
still use their existing image/configuration. The source change requires
targeted image rebuild/recreation. Later feature-TOML changes need a targeted
restart; environment changes need recreation. Telegram polling adds ordinary
polling/event-loop latency and never permits retry before the deadline. OneBot's
existing uncertain-send/checkpoint duplicate limitation is unchanged. Synthetic
tests do not establish provider uptime or real account delivery.
