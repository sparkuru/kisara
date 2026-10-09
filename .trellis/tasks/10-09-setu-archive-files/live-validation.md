# Prepared live QQ acceptance

Status: native ordinary-file download and complete-byte saving now passed in an
isolated temporary validation, including the bot UID's owner-only source
condition. See research/live-cache-and-expired-retry.md. Deployed command/result
and completion checkpoint acceptance remains pending. No agent-issued account
messages, preview rebuilds or service restarts were performed.

## Target and deployment preparation

The inspected runtime uses the ordinary OneBot `kisara` service, alongside running
NapCat and Telegram. Settings remain enabled,date_original,/app/setu,2G per-file
and10G batch caps. The user recreated OneBot/NapCat at05:36:30UTC with the
ordinary-file entry. The latest expired-source/cache/stream corrections are
not deployed. Existing mounts/config/state/archive mappings remain effective.

After implementation/check completion and deployment authorization, rebuild only the OneBot service:

```bash
docker compose --env-file .env --project-name kisara -f deploy/compose.yaml --profile onebot up --build --detach --no-deps kisara
```

This command is prepared, not run. Do not run an all-profile restart or reset volumes. Verify the new OneBot container is running and that NapCat/Telegram container IDs/start times remain unchanged. The rebuild needs access to the configured image/package sources; report an actual build failure without changing network/security policy.

## Archive acceptance

Before repeating the exact reported private forward, note that canonical
get_file already failed inside NapCat at120s and no private URL was available.
Do not assume a Kisara rebuild alone repairs this resource. First resolve the
native source. The user approved an ordinary quoted-file entry; validate it
separately rather than claiming that the failing forward was repaired.

### User-approved ordinary-file entry

For the exact latest failed ordinary-file source, rebuilding only OneBot and
quoting that same file message again with 直接保存 should resume its expired
unfinished batch. The file need not be resent. Expect one 正在保存以上 1 个文件。
notice before transfer, then1saved/0failed, its original
basename in the date directory, a saved checkpoint and no duplicate batch/file
on repeating the completed source, with no new progress notice for that completed
source. Native stream is used if its cache is still
0600; no chmod is needed. The older forwarded source has a separate native
download failure and is not proven repaired by these application corrections.

1. After authorized targeted deployment, send a small archive as an ordinary
   file message directly in an existing authorized private chat (not a merged
   forward). Sending alone must not prompt or save.
2. Quote that file with `/setu`, check a one-file prompt and no save/progress before
   confirmation, then quote the prompt with 保存. Verify the pending-kind start
   notice precedes transfer and final result, with both quoting that command.
   Verify result quote target,
   saved basename, bytes/digest, and returned local cache path approval.
3. Repeat with 直接保存 on another ordinary file, and with two different-content
   archives sharing a name to check the timestamp variant.
4. A repeated completed source or confirmation must not create another file.
   Plain image/video/text quotes and unauthorized sessions must remain without
   new Setu effects. Existing image export retains its separate priority.
5. Test the originally reported approximately104MiB archive as an ordinary
   file only after the small source succeeds. If get_file still fails or returns
   an unapproved/unmounted path, capture safe action/retcode/category and keep
   live acceptance failed; do not relax guards to force a success.

### Existing merged-forward entry

1. Use an existing authorized private OneBot chat. Prepare two small archives with the same original name, e.g. `资料 示例.tar.gz`, and different known content/digests. No new allowlist entry is needed.
2. Send the first archive inside a merged forward, optionally alongside an image/video. Quote the forward with `/setu`.
3. Confirm the prompt includes the file in its file count and quotes the merged forward. Before confirmation, the archive must not be present under the save root.
4. Quote the prompt with 保存 before its timeout. The result must quote that command, report successful file/item counts and the save directory, and preserve `资料 示例.tar.gz` with exactly matching bytes/digest.
5. Send the different-content archive in another merged forward with the same basename. Quote with 直接保存. Its result must arrive without an intervening prompt, and the saved file must be `资料 示例_<timestamp>.tar.gz` in the same date directory. The first archive must retain its bytes and filename.
6. Repeat a completed confirmation/direct-source command. No extra file or replacement may occur. Save matching archive content from another forward and confirm an existing original or timestamp variant is reused.
7. In the same flow, include a repeated ordinary image. Its saved paths/count/bytes must follow the existing selected media placement, without the new archive `_timestamp` suffix behavior.

Synthetic validation covers both placement modes and source/size/name failures. This live case uses the current selected mode; do not change private config merely to repeat the synthetic matrix. If a real file fails location resolution, capture only the minimal sanitized segment/response fields needed to establish original-name/location behavior; never dump private messages or signed URLs.

## Evidence to record

- OneBot image/service version and targeted deployment result.
- Archive original and saved basenames, byte counts and digests.
- Sanitized prompt/result counts and whether quote targets were correct.
- Same-name/different-content timestamp collision result and repeated-save behavior.
- NapCat/Telegram remained running with unchanged container IDs/start times.

Do not record account IDs, tokens, private config, source URLs, QR codes, or unrelated chat logs. No deliberate production fault injection is necessary.
