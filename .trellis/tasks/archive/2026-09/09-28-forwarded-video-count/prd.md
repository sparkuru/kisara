# Investigate truncated forwarded videos in preview

## Goal

Verify whether the current preview undercounts videos in one nested merged forward, compare direct and self-forwarded copies, and record any handling limits.

## Background

- On 2026-09-28, the active preview consisted of `kisara-kisara-1` and `kisara-napcat-1`; NapCat reported version 4.18.28.
- Two recent setu batches for the affected source recorded 12 `video` segments, 1 `image` segment, and 0 unsupported nodes. The bot's prompt showed the same counts.
- The active `max_nodes` is 500 and `max_depth` is 5; the source defaults match. There is no 13-item configuration cap.
- A read-only local OneBot `get_msg` and `get_forward_msg` probe returned 7 outer nodes. At depth 1, the inline nodes contain 9 `video`, 1 `image`, 1 `text`, and 3 more `forward` segments. At depth 2, they contain 3 `video`, 3 `text`, and 32 `json` segments; no further `forward` segments appear. The JSON segments are QQ bubble shop cards with `club.vip.qq.com` links, not media attachments.
- All 10 nested forward IDs were tested separately through `get_forward_msg` and returned `failed` (retcode 1200) with no messages. A sample nested ID also failed through `get_msg`. The inline content is the only content exposed by these tested OneBot calls.
- At the user's request, the original user-sent private forward was sent once to the bot's own QQ account using NapCat `forward_friend_single_msg`; the API returned `ok` (retcode 0). The resulting self-chat message is a `com.tencent.multimsg` JSON card. Its resource ID returns 7 top-level nodes through `get_forward_msg`, but every node has an empty `message` and `raw_message`; querying by its message ID or `uniseq` fails with retcode 1200. The original forward still returns the same 12 videos and 1 image after the test.
- The user then manually forwarded one inner message to the bot's own QQ account. The new self-chat `forward` is readable as a top-level message and contains 3 videos. All 3 `file` identifiers match videos already present at depth 2 of the original forward; their URLs differ after forwarding. This experiment did not expose any additional video.
- In the original forward's returned order, the 7 outer branches contain 1, 1, 2, 3, 1, 1, and 3 videos respectively (12 total). The newly forwarded 3 videos match the original depth-2 branch.
- Kisara's extraction code in `src/kisara/application/services/setu.py:160` traverses the embedded nodes; `src/kisara/bot/adapters/onebot_v11.py:404` returns NapCat's `data.messages` unchanged.
- The user confirmed that the QQ client count is correct and the apparent undercount was a misread. There is no missing video in the tested message.
- The two recent batches expired without confirmed saving. All 12 video entries have HTTPS URLs, but 4 report a size above the active 100 MiB per-file limit. Video metadata availability does not prove every file can be downloaded and saved.

## Requirements

- Compare the QQ client count with the original OneBot response and a self-forwarded copy.
- Distinguish parsed video entries from successful media transfer and report configuration limits accurately.
- Keep private message contents, identifiers, and media URLs out of logs and task artifacts.

## Acceptance Criteria

- [x] The QQ client count and the OneBot count are compared for the same forwarded message; the user confirmed the count was correct.
- [x] The original and self-forwarded messages are compared by structural API probes and anonymous file-identifier matches.
- [x] No product code change is needed because no extraction defect was reproduced.
- [x] The preview services and user media remain intact; one requested self-forward message was sent to the bot's own chat.

## Out of Scope

- Saving QQ bubble shop cards as video files.
- Changing global media size limits or broadly raising forward node limits without evidence.

## Resolution

The original incoming forward exposes all 12 videos through OneBot. Forwarding it to the bot's own account did not reveal more media; the API-created self-forward exposes empty nodes, while the manually forwarded inner message exposes 3 videos already counted in the original. No code fix is required for the count. Actual archiving remains subject to the configured file-size limit and source availability.
