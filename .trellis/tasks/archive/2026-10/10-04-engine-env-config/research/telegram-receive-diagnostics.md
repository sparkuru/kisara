# Research: Telegram receive diagnostics

- Query: Why can Telegram messages produce replies without received-message log lines?
- Scope: internal; read-only public source, tests, and specs. No private configuration, container inspection, external API calls, or product edits.
- Date: 2026-10-04

## Findings

### Files found

- `src/kisara/bot/adapters/telegram.py`: SDK polling ownership, update normalization, callbacks, replies, and safe error logging.
- `src/kisara/bot/main.py`: standard INFO logging, dispatcher assembly, startup and outer failure handling.
- `src/kisara/bot/dispatcher.py`: silent authorization/dedup outcomes and Telegram command routing.
- `tests/unit/test_telegram_adapter.py`: normalization, access filtering, ordinary-text silence, and token-safe error logs.
- `tests/integration/test_telegram_protocol.py`: synthetic Bot API peer exercises real SDK polling through routing and replies.
- `.trellis/spec/backend/logging-guidelines.md`: logging privacy and suppression contract.

### Receipt is currently unlogged

- `main.py:58` configures INFO logging; `main.py:171` logs the engine starting **before** calling `adapter.start()`. That startup line alone does not prove polling readiness.
- `telegram.py:29` suppresses `telegram`, `httpx`, and `httpcore` loggers, including registered child loggers, by disabling propagation and attaching null handlers. This is intentional: Bot API URLs contain the token. Do not re-enable SDK HTTP logs to diagnose receipt.
- `telegram.py:175` installs a text-message callback excluding edited messages. `telegram.py:178` initializes the SDK, starts polling, starts application processing, and assigns internal `status = "running"` at line 183. No readiness log is emitted there.
- `telegram.py:256` normalizes the update, returns silently if unsupported, runs the handler in an executor, and sends a reply when the handler returns output. It logs **only exceptions** at line 265. Successful receipt and send have no INFO/DEBUG log call.
- `main.py:151` passes `dispatcher.dispatch_payload`, which converts structured dispatch results into output or `None` (`dispatcher.py:94`). It does not expose authorization or route reasons to the adapter, and neither dispatcher method logs received messages.
- Consequently a successful private `/ping` reply can coexist with only the engine-startup line in container logs. This is normal for the current implementation, not evidence that the update was missed.

### Normal filters and silent outcomes

- `telegram.py:42`: ignore absent ordinary messages, `sender_chat` (including anonymous senders), forum topic messages, bot senders, missing/non-text content, channel posts, and commands addressed to another bot. `/news_clear` is normalized to `/news-clear`.
- `dispatcher.py:113`: unauthorized senders/conversations and duplicate messages produce `None` through `dispatch_payload`, without external action or logs.
- `dispatcher.py:309`: sender ID must be allowed; groups also require enablement and an allowed group ID. Ordinary group messages require the group's trigger policy (`dispatcher.py:320`).
- `dispatcher.py:135`: ordinary Telegram text returns no reply. Telegram is command-driven; unknown slash commands and disabled features receive safe help-oriented replies after authorization.
- `tests/unit/test_telegram_adapter.py:57` verifies allowed `/ping` replies, chat-scoped deduplication, and rejected sender/group silence. Line 77 explicitly verifies ordinary `hello` is silent; lines 79–80 verify `/start` aliases help. `tests/integration/test_telegram_protocol.py:67` verifies real SDK polling against an offline peer, not a live account.

### Operational interpretation and recommendation

The main session separately reports that the user's private `/ping` receives a normal reply, with a running Telegram container, zero restarts, and no warnings/errors. This research did not independently inspect live state. The reply is stronger operational evidence than a startup log: the poller, text callback, authorization, ping routing, and outbound send all completed for that message. No transport/network remediation is indicated by that evidence.

Explain that successful inbound messages currently have no log entry. If receipt visibility is requested later, add bounded application-owned metadata such as `Telegram text update received` and a safe lifecycle readiness line. Preserve the existing suppression and avoid message bodies, raw events, token-bearing URLs, and unnecessary user/chat identifiers. Route outcomes would require an explicit bounded contract because the current adapter receives output only, not a `DispatchResult`.

For reference only, if a future `/ping` fails: safe existing errors are `Telegram polling failed (<exception class>)` (`telegram.py:245`), invalid-token stop (`telegram.py:230`), callback processing failure (`telegram.py:252`), command/send failure (`telegram.py:264`), and bounded outer startup/ownership failure (`main.py:177`). Conflict and invalid-token failures stop ownership; routine SDK/network logs remain suppressed. Avoid launching a second `getUpdates` consumer merely to probe receipt.

### Related specs and external references

- `.trellis/spec/backend/logging-guidelines.md`: SDK token exposure requires suppression; tokens, raw events, message bodies, `.env`, and full private URLs must stay out of logs.
- `.trellis/spec/backend/error-handling.md`: unauthorized/duplicate events are unhandled; adapter boundaries report unexpected failures without fabricating success.
- `.trellis/spec/trellis-plus/configuration-storage.md`: separate Telegram configuration/state and scoped lifecycle controls.
- `.trellis/workflow.md`: research is persisted to the active task; no implementation or verification manifests loaded for this role.
- No external sources were needed: the question is answered by the current implementation and existing tests. SDK code paths were not audited beyond the adapter and test contracts.

## Caveats / Not Found

- No receive, reply-success, or polling-ready application log is present in the inspected Telegram adapter.
- This finding concerns current logging behavior; it is not proof of historical receipt for an arbitrary message.
- No tests were run and no runtime or private configuration was read. The reported live `/ping` outcome came from the coordinating main session.
