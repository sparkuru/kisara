# Primary SDK/API and repository research

Researched 2026-10-10. Read documentation and pinned SDK source; no credentials, Telegram history, real downloads or running-service operations.

## Repository evidence

- `pyproject.toml:19`: PTB 22.8.
- `src/kisara/bot/main.py:65`: existing Setu applies only to OneBot.
- `src/kisara/bot/adapters/telegram.py:47`, `:221`: text normalization/filter; `:134`, `:216`: custom prebuilt ExtBot.
- `src/kisara/bot/dispatcher.py:81` and `src/kisara/bot/features.py:25`: native auth and explicit feature inventory.
- `src/kisara/infrastructure/persistence/setu_files.py:88`, `:166`, `:245`: temporary/bounded copy/hash and archive lock/no-replace publication; generic path uses check then replace.
- `src/kisara/application/services/setu.py:291`, `src/kisara/infrastructure/persistence/setu.py:180`: individual checkpoints/partial-success retry, not message-wide atomic commit.
- `deploy/compose.yaml:148`, `:177`: Telegram config/state isolated, no archive/cache mounts.
- `.trellis/tasks/10-09-setu-archive-files/prd.md`: prior task excludes Telegram. Preserve it.

## Primary sources and conclusions

1. [Pinned SDK Message source](https://raw.githubusercontent.com/python-telegram-bot/python-telegram-bot/v22.8/src/telegram/_message.py): media_group_id, photo resolution variants, caption/entities and replies. No original client selection ID/count or group completion field.
2. [PTB official album design patterns](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Frequently-requested-design-patterns#how-do-i-deal-with-a-media-group): one API message per album item; timer or explicit finish collection. Timer may miss late media; explicit finish is an application boundary.
3. [Bot API Message/Update/MessageOrigin](https://core.telegram.org/bots/api#message): incoming forwarded origin is not a selection-batch identity; original IDs are not uniformly available. Inference from documented schemas: report received counts, not original selected totals. No documented general getMessage/getMediaGroup/history retrieval to enumerate missing siblings in this stack.
4. [Caption parser source](https://raw.githubusercontent.com/python-telegram-bot/python-telegram-bot/v22.8/src/telegram/_message.py) and [MessageEntity](https://docs.python-telegram-bot.org/en/v22.8/telegram.messageentity.html): parse_caption_entities/parse_caption_entity handle UTF-16; direct Python slicing by API offsets breaks non-BMP text.
5. [Cloud getFile](https://core.telegram.org/bots/api#getfile): 20 MB download bound; incoming filename/MIME must be retained because getFile may not preserve them. file_unique_id cannot retrieve bytes.
6. [Official local-server usage](https://github.com/tdlib/telegram-bot-api#usage): API ID/hash plus --local; unrestricted API download size and absolute file paths. [Migration](https://github.com/tdlib/telegram-bot-api#moving-a-bot-to-a-local-server) requires cloud logOut; [logOut](https://core.telegram.org/bots/api#logout) constrains cloud return for 10 minutes. User confirmed local server in first version.
7. [Pinned File implementation](https://raw.githubusercontent.com/python-telegram-bot/python-telegram-bot/v22.8/src/telegram/_files/file.py), lines 184–203: synchronous local copy, remote retrieve-to-bytes then write. download_to_drive is not bounded-memory network streaming. Use SDK getFile plus validated cache-path chunk copy in an owned worker.
8. [File documentation](https://docs.python-telegram-bot.org/en/v22.8/telegram.file.html#telegram.File.download_to_drive) and [ApplicationBuilder](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.applicationbuilder.html): custom paths/local mode/endpoints; adapt configuration to this repository's prebuilt ExtBot.

## PikPak interaction reference (user follow-up, 2026-10-10)

- [Official PikPak help](https://mypikpak.com/en-US/help) describes account linking followed by forwarding media to the bot for automatic saving. Its documented normal flow does not require an explicit finish/confirmation command for each submission.
- [Official PikPak bot integration document](https://github.com/pikcloud/pikpak-open/blob/main/telegram-bot.md) describes forwarding and magnet deep links. The inspected public documents do not establish its production SDK, queue architecture, album aggregation, content deduplication or large-file transport. Do not claim PikPak uses PTB/local Bot API/MTProto as an observed fact.
- A feasible design for this project, not a verified PikPak implementation: an authorized submitted media message creates a durable per-file job, acknowledges acceptance, retrieves bytes via the chosen local Bot API, publishes complete bytes independently, and reports saved/failed status. No original multi-select count is required to enqueue each received file. Album metadata can be grouped for naming/notifications without waiting for a complete user selection batch; delayed members remain independent jobs.
- With D3 (individual-file atomicity), an explicit finish is needed only if the product requires a closed collection summary and confirmation; it is not a prerequisite for safe per-file processing. D4 was approved by the user's “可以”: `/tgsetu on` enables automatic media-to-save for the authorized private user and `/tgsetu off` stops new acceptance, with no finish or per-submission confirmation. Activation persistence and late-caption naming are operating proposals to include in final review.

## Current decisions and limits

Confirmed: Telegram command, caption/tag expectation, attachment own name, logical-message independence, first-version local server/large files, flat individual-file atomic publication (user selected A on 2026-10-10), and PikPak-style on/off automatic saving (subsequent “可以”). Successful siblings remain saved and retry processes unfinished files only.

The user subsequently selected attachment naming A: original stem + caption title + tags + full original extension. This closes D5's attachment product choice. Shared-caption windows, immutable ordinals/fallbacks and activation/restart behavior are explicit operating defaults in the final-review design, not claims about PikPak internals. Implementation still requires subsequent approval of the latest final summary.

Not verified: real forwarded album delivery/captions, local-server version/image/cache permissions, real >20 MB retrieval and original photo bytes. SDK/source evidence does not replace live account acceptance.
