# Research: Native forwarded-file resolver limits

- Query: Explain canonical-ID get_file failure after 120 seconds and immediate private URL prerequisite failure; identify source-backed alternatives.
- Scope: internal; installed NapCat executable source and sanitized main-session observations
- Date: 2026-10-09

## Findings

### Evidence after the initial timeout hypothesis

The main session performed live probes with the freshly converted canonical ID. Sanitized observations:

- `get_file`: `retcode=1200` after **120.01 seconds**, without any path or URL.
- `get_private_file_url`: `retcode=1200` immediately; response safely classified against the fixed source literal `real fileUUID not found!`.
- Target file segment has a distinct 69-character opaque `file_id`, a 33-character basename ending `.7z`, size 109092709 bytes, and no URL.

These observations refine [the initial source investigation](napcat-file-resolver-live-failure.md): a 10-second bot timeout was a real mismatch, but extending it and preferring the canonical identifier **did not make this native forwarded-file download succeed**. The native 120-second download path is now the failing boundary.

### Files and source paths

All dependency citations below refer to running `kisara-napcat-1:/app/napcat/napcat.mjs`, embedded version 4.18.28 (`8388`).

| Lines | Description |
| --- | --- |
| `73172-73194` | Multi-forward converter chooses native getMultiMsg, falling back to packet FetchForwardMsg. |
| `73548-73558` | Native inner-message parse attaches parentMsgPeer and parentMsgIdList. |
| `72883-72934` | Ordinary file segment construction and identifier alias registration. |
| `71615-71627` | Cached decoded file representation. |
| `75519-75589` | get_file shared payload and full-download handler. |
| `9444-9475` | Native downloadRichMedia call and completion matching. |
| `78392-78414` | Private URL action native-message/MD5 prerequisites. |
| `77751-77773` | Group URL action uses group_id and cached UUID directly. |
| `32604-32610` | Group URL constructs HTTPS; private URL constructs HTTP. |
| `75912-76028` | get_forward_msg schema and native history/protocol lookup. |
| `73562-73609` | Ordinary OneBot message response metadata. |
| `32434-32448`, `32639-32707` | Packet forward fallback converter does not parse file elements. |
| `79485-79513` | Stream download resolver reuses the same native download. |

### Cached ID representation loses the multi-forward ancestry

The file converter registers both the UUID and basename with decoded value `{peer, msgId, elementId, fileUUID}` (`72900`, `71623`). The peer is taken from the inner raw message's own `chatType/peerUid`, not its attached `parentMsgPeer`. Neither `parentMsgPeer` nor `parentMsgIdList` is stored in the file cache.

Native `getMultiMsg` uses the parent peer and parent/current message IDs (`73548-73554`). Its returned inner records are parsed with parent fields attached (`73556-73558`). In contrast, `get_file` later calls `downloadMedia` using only the cached inner record's own peer, msgId and elementId (`75536`). `downloadRichMedia` request passes no multi-forward parent identity (`9444-9475`). Its completion matcher requires both msgElementId and msgId to match that cached element, and waits 120 seconds.

This is an evidence-backed **ancestry loss in the resolver contract**, and a possible explanation for forwarded elements being unavailable to ordinary kernel download/message lookup. It is not proof that this kernel needs parent IDs for this particular record; kernel native implementation was not inspected and no completed path was observed.

The observed 69-character string cannot be decoded by shape or length alone. The implementation looks it up in a process-local map; it is not a serialized object carrying its own native fields. Re-conversion registers it again.

### Immediate private URL failure has multiple precise prerequisites

`get_private_file_url` first requires decoded `fileUUID` and `msgId`. It then retrieves `getMsgsByMsgId(decoded.peer, [decoded.msgId])` and obtains:

```javascript
r.msgList[0]?.elements.map(s => s.fileElement?.file10MMd5)[0]
```

It examines only the first message and first element, rather than finding the element matching the cached elementId. If the original message is absent, its first element is text, or its first file element lacks MD5, this becomes falsy and throws the same fixed `real fileUUID not found!` literal (`78404-78413`). Cache absence or empty cached UUID/msgId also gives the same literal.

The main live response proves failure **before packet URL generation**. It does not distinguish cache prerequisites from native lookup/first-element MD5 failure. Fresh conversion in the same process makes restart-only cache loss less plausible, but not mathematically impossible (the cache can be overwritten/evicted). A node containing a file segment does not imply normal getMsgsByMsgId can retrieve the inner message.

### Avoid incorrectly attributing this to packet-generated synthetic message IDs

Packet `FetchForwardMsg` does create a fixed synthetic msgId (`32677-32678`), which would be problematic for ordinary native message retrieval. However its packet-to-raw converter recognizes only text, mentions, reply, video and picture (`32434-32448`); it does **not** invoke the file parser, despite file support in the opposite conversion direction. Accordingly an observed ordinary file segment points toward native `getMultiMsg` output, not that packet fallback. Synthetic fallback msgId is not an established cause for this case.

### Exposed options and alternatives

- `get_forward_msg` schema exposes only `message_id`/`id` (`75912-75915`). It returns parsed OneBot nodes. There is no exposed option in this handler to return raw native file fields, parent identifiers, file10MMd5 or change file resolver behavior. `get_msg` also returns parsed OneBot messages (`74547-74609`); `raw_message` is rendered CQ text, not raw native element metadata.
- `get_file` exposes only optional `file`/`file_id`, with no timeout or filePath parameter (`75519-75522`). Passing arbitrary timeout metadata is not consumed by its handler.
- `download_file_stream` and related stream actions use the same cached-element downloadMedia path (`79485-79513`) and cannot bypass this native 120-second failure.
- `download_file` accepts an already known URL/base64, then stores into NapCat's temporary directory (`75826-75865`). It does not resolve the forwarded UUID and its output is outside the established mounted-media source contract. It is not a proven safe workaround.
- **Conditional group-origin fallback:** `get_group_file_url` requires `group_id` and canonical cached file_id, decodes fileUUID and directly calls the packet group URL operation without native message/MD5 lookup or full download (`77751-77773`). That operation constructs HTTPS (`32604-32607`). It is applicable only if the inner node establishes the actual group source; the outer private chat does not establish inner origin. Its returned URL still needs the existing approved HTTPS host and redirect checks.
- **Private-origin case:** no exposed, proven API was found taking raw UUID plus MD5 or resolving the file from complete multi-forward ancestry. A correction in NapCat (preserving enough native forward metadata and resolving MD5 from the actual converted element) may be required. Changing HTTP or filesystem allowlists is not justified by these failures.

## Related specs

- `.trellis/spec/backend/error-handling.md`: partial-save retry and bounded protocol failure reporting.
- `.trellis/spec/backend/logging-guidelines.md`: structural diagnostics rather than raw private payloads/URLs.
- `.trellis/spec/backend/index.md`: backend contracts.

## Caveats / Not Found

- Researcher performed no live API action, download, send, restart or configuration write. Probe observations above were supplied by the main session.
- No returned local path or URL exists from the probes, so source mount compatibility remains unverified.
- Whether the inner node is group-origin, private-origin, or has text before its file requires sanitized structural inspection by the main session.
- No available source proves that longer waits alone will resolve the native kernel timeout, or that changing QQ/NapCat versions would fix it. No such change was attempted.
