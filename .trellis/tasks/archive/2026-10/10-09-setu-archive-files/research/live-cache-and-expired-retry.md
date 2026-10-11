# Live cache path, permissions, and expired failed sources

Date:2026-10-09. Scope: reported two file saves only. No account IDs, actual
basenames, opaque resolver keys, tokens, signed URLs or unrelated chat content
are recorded.

## Sanitized observed state

The user externally recreated OneBot and NapCat at05:36:30UTC and reported
13:36/13:37CST results. Read-only SQLite inspection showed the older forward
file and newest ordinary-file batch both expired, each with1item and0saved.
Their stored errors were OneBotError and SetuFileError respectively. A seen
source key therefore did not establish completed work. The previous direct
lookup queried only unexpired awaiting state and conflated missing/expired,
in-progress and completed batches in one reply.

## Successful ordinary native download

Targeted get_msg re-registered only the quoted ordinary file's canonical ID;
get_file returned statusok, retcode0, with an existing109092709byte file inside
the existing mountedQQroot. Its exact structural layout is
`local_media_root/NapCat/temp/<original basename>` (direct child). The previous
`nt_qq*/nt_data/{File,Pic,Video,Audio,Record}` check rejected it.

Initial full-copy validation immediately identified the next actual boundary:
file0600, ownerUID/GID1000; OneBotUID/GID10001, supplementarygroups1000/10001.
An actual one-byte open by the bot UID failed with PermissionError(errno13).
No chmod, chown, user/config/mount change was performed.

## Existing native stream contract

Installed NapCat4.18.28 supports download_file_stream over existing authenticated
WebSocket. Source anchors in `/app/napcat/napcat.mjs`:

-793xx–79534:q2.resolveDownload uses the same canonical native lookup; its
  streamFileChunks reads native bytes and emits indexed base64 file_chunk.
-79535–79580:download_file_stream exposes file/file_id/chunk_size, emits
  file_info, then chunks, then response/file_complete with actual totals.
-40406:stream/response enum values;40485–40496:websocketHandle keeps echo.
-6438x–6440x:WS transport wraps each stream packet with the same echo.

This does not fix an upstream unavailable forwarded file: it still uses the
same native resolver. It does solve the separate permissions boundary once the
ordinary native transfer succeeds, without exposing arbitrary paths to the bot.

## Real complete-byte validation

An isolated exec inside the existing OneBot container loaded exact revised
adapter and saver source into temporary in-memory namespaces. The actual
UID10001 used get_msg/get_file, reproduced the owner-only read rejection, then
used canonical download_file_stream with64KiB chunks and existing capped wait.
A private spool and temporary output directory were used; no new source path
exception or permission change was needed for the internal BinaryIO.

Results:

- Native stream succeeded; complete saved size109092709bytes.
- Saved original basename exactly and mode0640.
- Saved file SHA-256 matched the saver result.
- A separate read of the one original cache file under its ownerUID1000 produced
  the same SHA-256, establishing independent complete-byte equality.
- Temporary output copy and spool were closed/removed.
- Production archive, SQLite state and service process were not modified;
  no QQ sends, rebuild/restart, config changes or commits occurred.

This establishes native transfer and corrected byte persistence capability.
It does not establish the externally deployed command result or completion
checkpoint. Those require applying the new image and a fresh quoted-source
command. The earlier private-forward native timeout remains a distinct limit.
