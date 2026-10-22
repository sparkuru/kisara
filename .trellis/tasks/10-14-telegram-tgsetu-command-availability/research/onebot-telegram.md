# OneBot and Telegram integration research

Date: 2026-10-14

## Question

是否有主流 OneBot 实现直接接入 Telegram Bot，以及它们是否等同于官方
`telegram-bot-api` 或 NapCat。

## Evidence

The [official OneBot ecosystem](https://onebot.dev/ecosystem) defines an
"OneBot implementation" as a program that connects to a bot platform and
provides a OneBot-compatible interface. Under the OneBot 11 / 10 / CQHTTP
implementation list it includes Telegram entries:

- [`Hoshinonyaruko/Gensokyo-telegram`](https://github.com/hoshinonyaruko/gensokyo-telegram)
  is a Go Telegram Bot implementation. Its documented transport options are
  Telegram HTTP polling or webhook, with a OneBot v11 reverse WebSocket for
  clients such as NoneBot2, Koishi, TRSS and ZeroBot.
- [`Echomirix/Tele-KiraLink`](https://github.com/Echomirix/Tele-KiraLink) is a
  Java Telegram Bot API implementation. Its README documents OneBot v11
  compatibility, forward WebSocket, HTTP/reverse HTTP and partial QQ-shaped
  group APIs/events.

The official local server is a different layer:

- [`tdlib/telegram-bot-api`](https://github.com/tdlib/telegram-bot-api) is an
  HTTP server implementation of Telegram's Bot API. It does not expose
  OneBot v11/v12 events or actions.
- NapCat is a QQ/NTQQ-side OneBot 11 implementation, not a Telegram adapter;
  its [repository](https://github.com/NapNeko/NapCatQQ) describes it as a
  protocol-side framework based on NTQQ.

As an additional, newer example, [`DnullP/tgonebot`](https://github.com/DnullP/tgonebot)
documents Telegram Bot API to OneBot 12, both as a standalone service and an
embeddable Go module. It is useful evidence that the bridge pattern also exists
for OneBot 12, but it is not needed for this task's OneBot 11/native Telegram
decision.

## Compatibility conclusion

There are two distinct deployment shapes:

| Shape | Telegram owner | Outbound interface | Fits current fix? |
| --- | --- | --- | --- |
| Kisara native Telegram | Kisara `telegram` + local `telegram-bot-api` | Telegram Bot API through internal HTTP | Yes |
| Telegram-OneBot bridge | Gensokyo/Tele-KiraLink/tgonebot | OneBot HTTP/WebSocket to a framework | No, separate task |

The two shapes must not run as competing update owners for the same Bot. A
bridge would also move Telegram events into Kisara's OneBot engine, while the
current `/tgsetu` feature is registered as Telegram-only and its media/cache
contract belongs to the native Telegram adapter. Combining them in this repair
would require a new engine/feature boundary, not just changing an endpoint.

## Decision for this task

Use the native Telegram shape: Kisara talks only to the internal local Bot API
server, and the local server talks to Telegram. Do not add a Telegram-OneBot
bridge, change the OneBot adapter, or claim that the local Bot API speaks
OneBot. If Telegram messages must later be consumed through OneBot, create a
separate task that selects and evaluates one bridge, defines Telegram-to-QQ
semantic mappings, and handles single-owner Bot update migration.

This decision is based on semantic and ownership correctness, not effort or
cost. A bridge remains a valid future architecture if OneBot plugin/client
compatibility becomes a product requirement; it is not the correct hidden
transport for the current Telegram-native TgSetu contract.
