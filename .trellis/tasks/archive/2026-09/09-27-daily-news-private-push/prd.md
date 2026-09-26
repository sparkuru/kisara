# Daily news private scheduled push

## Goal

Allow the OneBot bot to deliver the daily-news image automatically to configured
personal QQ recipients, while preserving existing scheduled group deliveries.
The user requested personal QQ-number targeting and approved creating this task.

## Confirmed background

- News currently accepts `push_groups` and a single UTC+8 `push_time` (default
  10:30); group targets require enabled groups and the global group allowlist
  (`src/kisara/config/settings.py:149`).
- Startup and the connected-session scheduler are currently enabled only for
  nonempty group targets (`src/kisara/bot/main.py:138`,
  `src/kisara/bot/adapters/onebot_v11.py:130`).
- The scheduler generates content once for pending targets, sends through
  OneBot, records confirmed successes and rechecks pending deliveries after
  15 minutes. Late startup catches up today's delivery only
  (`src/kisara/bot/adapters/onebot_v11.py:468`).
- The database currently keys delivery by `(day, group_id)`; legacy group
  records must retain their meaning when personal targets are added
  (`src/kisara/infrastructure/persistence/news_delivery.py:18`).
- Private OneBot sending already exists via `send_private_msg` with `user_id`
  (`src/kisara/bot/adapters/onebot_v11.py:418`).
- The documentation change in `docs/application-template.md` predates this
  feature task and must be preserved.

## Requirements

- R1: Configure one or more personal QQ numbers as news push recipients.
  Use `push_users` in the news feature TOML, with an empty default. Empty
  personal recipients disable private push without disabling group push.
  Accept canonical positive decimal QQ numbers as strings, remove duplicate
  targets, and follow the existing TOML-over-environment configuration policy.
- R2: Personal push works when group functionality and group subscriptions are
  disabled. Personal recipients must belong to `KISARA_ALLOWED_USERS`;
  scheduled push remains OneBot-only.
- R3: Deliver the same dated news text and image used by existing group push.
  Personal and group recipients share the existing `push_time` (UTC+8, default
  10:30), as explicitly agreed by the user.
- R4: Track personal and group delivery independently, including when the QQ
  user number equals a group number. Retain existing successful group records.
- R5: Preserve current confirmed-success recording, 15-minute retry, today's
  late catch-up, and connection-bound lifecycle for private deliveries too.
  Local completion records do not establish strict exactly-once delivery when
  a remote outcome is unknown.
- R6: Document configuration, permissions, time, retry, state and operating
  steps, and verify configuration, persistence and OneBot behavior with
  automated tests.

## Acceptance criteria

- AC1 (R1–R3): An allowed personal QQ recipient configured without group targets
  receives the daily news through `send_private_msg`, with the expected
  `user_id`, text and image, after the configured due time.
- AC2 (R2): Reject disallowed personal recipients and scheduled private push on
  the official engine before runtime; reject malformed personal QQ numbers;
  empty private targets remain inert. Explicit TOML values take precedence
  over `KISARA_NEWS_PUSH_USERS`, including an explicit empty list.
- AC3 (R4): Group and private targets sharing the same numeric ID can each
  receive news. Reopening state preserves both kinds of confirmed completion.
  Existing group completion records still suppress those completed sends.
- AC4 (R5): Before the due time no send occurs; late startup sends today's news;
  a failed recipient does not stop others and can retry without resending
  recorded successes. Disconnect cancels the scheduler; reconnect does not
  create overlapping schedulers.
- AC5 (R6): Configuration example and feature documentation match actual
  behavior. Focused and required broader automated checks pass; live QQ
  acceptance remains a separately identified check.

## Out of scope

- Official-platform private push, a generic scheduler framework, per-user
  self-subscription commands, independent private/user-specific send times,
  historical news backfill, and changes to news content/rendering.
- Sending live QQ messages, changing private runtime configuration, or
  deploying the feature as part of implementation validation.
