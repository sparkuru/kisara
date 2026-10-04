# Telegram live acceptance

Status: preparation only; no live services or accounts were changed by this task.
Automated SDK/protocol checks do not establish account or network capability.

## Setup after deployment authorization

Use an existing Telegram bot token privately. Select Telegram alone or alongside
OneBot through the documented Compose profiles. Configure one allowed private
user and one allowed group, including that group's permitted invoking user.
For private scheduled delivery, the user must first start the bot. Configure a
reachable music provider when music search is expected to return a result.
Keep credentials and full rendered Compose configuration out of shared logs.

## Commands and access

1. From the allowed private user, send `/start`, `/ping`, `/help`, `/news`, and
   `/music <known title>`. Expect onboarding help, an online response, only the
   enabled Telegram features, a readable PNG document with source/date caption,
   and the title/artist/public music link. Starting the bot must not subscribe it.
   Run `/news_clear` and request `/news` again to check engine-local cache maintenance.
2. From a user outside the allowlist, repeat `/news` and `/music`. Expect silence
   and no provider invocation. Repeat in a group outside the group allowlist.
3. In the allowed group, send `/ping@<this bot username>` and `/news@<this bot
   username>`. Expect a response associated with that command. A command addressed
   to another bot and ordinary chat must stay silent.
4. Disable music and manual news in Telegram's feature TOML configuration,
   restart only Telegram, and repeat their commands and aliases. Expect unavailable
   guidance, no business/provider effects, and their omission from `/help`.
   Re-enable them and restart Telegram before the next check.
5. During a real publication delay, `/news` must identify the previous edition
   and the delay in caption/image. After today's publication, a subsequent manual
   request must retrieve today's edition rather than reuse a dated fallback.

## Scheduled delivery and isolation

For TOML changes use `./deploy.sh restart telegram`. For `.env` changes use
`./deploy.sh up telegram` to recreate the container; restart retains its old
environment. These are live operations to run only after deployment authorization.

1. Set a near-term UTC+8 push time and explicit allowed private/group recipients.
   Restart only Telegram. Expect one captioned news PNG document per recipient.
2. Restart Telegram after confirmed delivery. Expect no replay of that day's
   confirmed sends. Keep manual `/news` available for retrieval.
3. Disable push while retaining manual news; restart Telegram. Expect manual
   news to work and no scheduled sends. Enable push while disabling manual news
   for the reciprocal check. Restore the desired settings afterward.
4. For denied sending permissions or a bot-blocking recipient, expect a safe
   diagnostic and the documented known-failure behavior. Unknown send results
   must stay uncertain without automatic resend; use the persisted-state tests
   for deterministic fault injection rather than deliberately interrupting a
   production send.
5. While Telegram is running, verify the currently used QQ commands and stored
   state. Stop/restart/rebuild Telegram using targeted commands; QQ and NapCat
   must remain running with the same login/state. Ordinary stops retain volumes.

## Evidence

Record only pass/fail, command category, date, and sanitized error category.
Do not copy tokens, message bodies, private payloads, login QR codes, or provider
URLs into task artifacts. Real account/provider/network validation remains open
until these checks have actually run.
