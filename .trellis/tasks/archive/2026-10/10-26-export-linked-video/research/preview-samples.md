# Preview message evidence

Inspected on 2026-10-26 through the running OneBot preview using read-only
`get_friend_msg_history` (20 recent messages per configured allowed private
conversation, at most five conversations) and a targeted `get_msg` for the
identified mini-program card. No send, download, restart or configuration write
was performed. Credentials stayed inside the existing container environment;
only message kinds, selected public links and card schema fields were emitted.
Account IDs, unrelated messages and raw card metadata are intentionally omitted.

## Observed inputs

1. A message containing one `json` segment. The segment's `data.data` is a JSON
   string describing `app = com.tencent.miniapp_01`, with `meta.detail_1`:
   - `title`: 哔哩哔哩
   - `appid`: 1109937557
   - `url`: a scheme-less `m.q.qq.com/a/s/...` mini-program launch address
   - `qqdocurl`: `https://b23.tv/wHhO5iP`
2. A message containing one `text` segment with this public video URL:
   `https://www.bilibili.com/video/BV1drnJ6BE86/`

These samples establish actual input formats, not successful download, short-link
resolution, authenticated access, video quality or native QQ video delivery.
At initial inspection the relationship between the two source videos had not
been verified. Subsequent bounded short-link resolution established that the
card points to a different video, `BV1rcpL6TEwK`; see [validation](../validation.md).

## Implications for planning

- Prefer the card's `qqdocurl` as the Bilibili share target; do not mistake its
  QQ mini-program `url` or thumbnail `preview` for the video address.
- Decode the `json` segment payload structurally before extracting fields.
  Regex over the serialized outer segments did not find the escaped URL.
- Cover both text URLs and the real card schema with sanitized fixtures.
- Existing image handling consumes generic export phrases before other routing:
  `src/kisara/application/services/export_img.py:37`,
  `src/kisara/application/services/export_img.py:45`, and
  `src/kisara/bot/adapters/onebot_v11.py:249`.
- Reuse the conversation ownership boundary at
  `src/kisara/bot/adapters/onebot_v11.py:317` before interpreting the source.
- The observed examples are OneBot/QQ messages. They do not establish requested
  Telegram or official QQ support.

## Subsequent planning decisions

The user approved Bilibili-only first-iteration scope and supplied an env file
for authorized session use. [Provider research](bilibili-provider.md) records
the follow-up login/format probes. [Design](../design.md) owns the proposed
downloader/runtime choices; this input-shape evidence alone does not establish
successful end-to-end export.
