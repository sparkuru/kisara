# Telegram library and integration research

Scope note: initial investigation. The latest user decision retains only ping,
help, news, scheduled news, and music, with a shared deployment .env selecting
Compose engines. The broad command/config/deployment suggestions below are
historical proposals, not current requirements. Current scope is in the PRD,
design, and feature-routing.md. PTB/API facts remain relevant evidence.

Checked on 2026-10-04. Technical choices below are design proposals; task
remains in planning and the implementation has not been authorized.

## Selected library proposal

Use `python-telegram-bot==22.8` as a Telegram-only optional dependency. It
wraps Telegram's official HTTP Bot API, provides asynchronous sending, update
handlers, polling, and application lifecycle hooks. Its native handlers also
leave a route for future Telegram-specific callback/button interactions without
requiring them to fit shared text-message routing.

Primary sources:

- [PTB 22.8 introduction](https://docs.python-telegram-bot.org/en/v22.8/):
  asynchronous Python interface, Python 3.10+ support, native support for Bot
  API 10.0, and extension options for newer API methods.
- [Application lifecycle](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.application.html):
  polling lifecycle and post-init/post-stop/post-shutdown hooks.
- [ApplicationBuilder](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.applicationbuilder.html):
  updates are processed sequentially unless concurrency is enabled. Queue,
  concurrency, and connection-pool settings require deliberate bounds.
- [Error types](https://docs.python-telegram-bot.org/en/v22.8/telegram.error.html):
  explicit errors for rejected requests, denied access, rate limiting, and
  network/timeout failures.
- [Bot methods](https://docs.python-telegram-bot.org/en/v22.8/telegram.bot.html):
  native text, photo, and document sending.

PTB is a community-maintained wrapper, not a Telegram-maintained Python SDK.
Use ordinary supported Bot API methods for the first release; do not imply
that the selected wrapper automatically covers every newer Telegram feature.

The current Docker image uses Python 3.12 and is compatible with PTB's declared
Python range. Keep existing base-package support and OneBot/official dependency
behavior intact. Installing the Telegram extra requires Python 3.10+; report
that explicitly instead of silently selecting an obsolete library on Python 3.8.

## Shared command inventory proposal

Reuse existing command business behavior for ping/help, eat/roll, chat/tarot,
wallpaper, Blue Archive guides, love notes, music search, news, and news-cache
clearing. Translate Telegram command addressing at the adapter boundary and
provide engine-aware help. Music can use the existing service's text/link
response; QQ's native music-card representation is not a Telegram requirement.

Telegram group privacy and command addressing must be documented and checked
against actual account behavior. Keep SDK types out of shared services.

## Source-search constraint

`PublicServices.source_search(image_url, similarity)` sends an input URL to
SauceNAO. Telegram's [getFile](https://core.telegram.org/bots/api#getfile)
download URL embeds the bot token. Never pass that URL to another provider,
return it to users, or log it. Proper support needs authorization before file
lookup/download, bounded download, and an upload-capable provider integration.

Recommend deferring `/source` to that dedicated media-input work. This is a
product scope decision awaiting the user, not an implied feature omission.

## Configuration and lifecycle direction

Use a Telegram-specific environment file and feature-configuration root, a
separate Compose project/file, and an independent persistent state volume.
Do not mount QQ credentials, NapCat login state, or the QQ feature directory
into the Telegram container. Optional tarot art can be shared read-only.

Current `feature_files.load_feature` resolves fixed `config/features` paths,
and group overrides have a legacy `config/groups.json` fallback. A configurable
configuration root must preserve those existing defaults for QQ and apply
consistently to feature loading, group overrides, and any explicitly scoped
workflow paths. A Telegram configuration example must not require editing
QQ's deployed configuration.

Use long polling initially. No public inbound endpoint is necessary. Proxy/
network reachability to Telegram still needs actual deployment validation;
the current evidence does not establish the user's network path.

## News and media direction

`DailyNewsResult` already preserves either published image files or immutable
fallback PNG bytes. Add a neutral image representation/helper while preserving
`onebot_image()` for existing QQ callers. Fallback warnings must remain visible
in both text and PNG; never publish yesterday's fallback into today's fresh
cache. Telegram receives local PNG bytes/files by upload, not by publishing
local files to a public web server.

Photo/document limits require deterministic representation handling; avoid
retrying an unknown remote send as another representation. Confirmed scheduled
delivery needs separate Telegram state and explicit treatment of known rejection
versus unknown network/send outcomes. Preserve existing QQ tables and scheduling
semantics rather than changing its deployed storage as an incidental refactor.

Disable credential-bearing HTTP request logging and log only sanitized error
categories. PTB/HTTP client exception text and URL strings can expose the token;
tests should check emitted logs with synthetic token-bearing failures.
