# Research: NapCat file resolver and live save timeout

- Query: Explain a private forwarded archive save failure roughly ten seconds after direct confirmation, using the running NapCat implementation.
- Scope: internal; installed dependency source plus repository boundaries
- Date: 2026-10-09

## Findings

### Source inspected and versions

| File | Description |
| --- | --- |
| Running `kisara-napcat-1:/app/napcat/napcat.mjs` | Installed executable bundle; embedded `Vu` version is **4.18.28** at line 8388. |
| `src/kisara/bot/adapters/onebot_v11.py` | Resolver and correlated OneBot request timeout. |
| `src/kisara/application/services/setu.py` | Media metadata extraction, pre-save limits and failure boundary. |
| `src/kisara/infrastructure/persistence/setu_files.py` | HTTPS fetch and approved local QQ cache checks. |

No external documentation was needed. Container reads were limited to source and package metadata. No private content, signed URLs, account IDs, credentials or actual filenames are recorded here.

### File segment and identifier contract

Installed `napcat.mjs:72883-72934` converts an ordinary file element into:

```json
{"type":"file","data":{"file":"<original basename>","file_id":"<QQ file UUID>","file_size":"<size>","url":"<optional URL>"}}
```

The converter registers both `fileUuid` and `fileName` as cache keys with the same decoded value `{peer, msgId, elementId, fileUUID}` (`napcat.mjs:72900`). URL generation is optional: it requires packet functionality and enabled URL conversion, and failure yields a segment without `url` (`72901-72934`). The converter's inline URL lookup uses a 1500ms packet timeout (`72906`). The generic cache is an in-memory map of up to 5000 keys, with 24-hour sliding TTL; it can evict entries and does not survive restart (`71555-71633`). The strings are lookup keys, not independently decodable portable IDs. Re-reading the forward registers the aliases again.

Current application extraction selects `data.file` before `data.file_id` and persists only the selected string as `file` (`setu.py:180-188`). Consequently it usually stores the basename rather than the opaque UUID. This does work when the basename alias still maps to the intended element, but can collide if later conversion registers another file with the same name. Both aliases being registered means basename selection alone is **not evidence that this particular failure is an invalid identifier**.

### `get_file` downloads the whole file before replying

`napcat.mjs:75519-75589` defines the shared handler for `get_file`:

1. Payload accepts optional `file` and `file_id`; `file` takes precedence via `e.file ||= e.file_id || ""`.
2. Decoded message/element key: await `FileApi.downloadMedia(...)`; only then fetch element metadata and return `{file: <local path>, url: <local path>, file_size, file_name}` for ordinary file elements. URL conversion after download is special-cased for images/videos, not generic archives (`75535-75553`).
3. Decoded model key: await `downloadFileForModelId`; return both `file` and `url` equal to the local path (`75555-75569`).
4. Unrecognized key: search the QQ file assistant and, if found, await `downloadFileById`, then return local path plus metadata (`75570-75585`).
5. No match throws `file not found`.

`downloadMedia` waits for the kernel's `onRichMediaDownloadComplete` and has a default **120-second** timeout (`9444-9475`). The shared get_file call passes empty cache/file paths, so its initial existing-file shortcut does not receive a known path from this caller. Model download likewise has a default **120-second** timeout (`9396-9411`). File-assistant fallback computes a size-aware timeout using `min(baseTimeout + size / 1024 / speedKBps * 1000, maxTimeout)` (`41413-41419`, `75573`), whose schema defaults are 10 seconds base, 256 KiB/s and 30-minute maximum (`41399-41404`). For 109092709 bytes that formula is approximately 426 seconds; this is the fallback branch estimate, not proof that it was the branch used live.

Current `media_location` chooses `get_file` for file-kind attachments and sends the same stored string in both parameters (`onebot_v11.py:426-450`). `_request` uses a global **10-second** timeout (`onebot_v11.py:26`, `541-555`). After expiry it removes the echo future (`557-558`); late NapCat completion cannot retroactively complete that failed save. It does not cancel NapCat's kernel download.

Main-session sanitized state observation: the latest failed attachment is a `.7z`, approximately **104 MiB**, with no URL and `OneBotError`; failure arrived roughly ten seconds after confirmation. Together with source behavior, a transfer being cut off by the adapter's 10-second wait is a strong explanation. The persisted error records only the exception class, so it does not prove timeout versus a protocol error with matching timing.

The main session subsequently inspected the exact failed forward structurally: the file segment contains only `file`, `file_id`, and string `file_size`; `file` is a 33-character basename, while `file_id` is a distinct 69-character opaque key. It has no `url` or separate `name`. This confirms that extraction lost the explicitly provided canonical ID.

### Download destination and timeout controls

The get_file payload schema exposes only `file` and `file_id` (`napcat.mjs:75519-75522`); the handler does not consume a caller-provided download timeout. Extending the bot's wait does not change NapCat's native 120-second cached-element transfer timeout. This API has no observed timeout knob to pass from the bot.

The cached-element call passes an empty `filePath` into the kernel download request (`75536`, `9444-9475`) and returns the kernel completion event's `filePath`. It does not choose NapCat's own temporary directory. There is no JavaScript-level guarantee that this target's returned path will satisfy the mounted QQ cache allowlist. A cache-cleaning action separately recognizes `core.dataPath/<account>/nt_qq/nt_data/File` (`78853`), but that is neither a download destination contract nor proof of this runtime's returned directory shape. Its separate cleaning of NapCat temporary files also does not imply get_file uses that directory.

Merged-forward conversion gets message elements through native `getMultiMsg`, or a packet fallback, then runs the ordinary file converter (`73172-73194`, `73548-73558`). No special forwarded-file destination path is selected by that converter. Actual successful kernel response and mount visibility must be validated separately, without broadening source path allowlists in anticipation.

### Direct private-file URL is not a drop-in safe alternative

Installed `get_private_file_url` (`napcat.mjs:78392-78414`) has a schema requiring only `file_id`, despite its example including `user_id`. It:

- decodes that key through the same cache;
- requires cached `fileUUID` and `msgId`;
- fetches the original message and uses the first mapped file element's `file10MMd5`;
- calls the private packet URL operation and returns `{url: <download URL>}` without downloading the payload;
- throws `real fileUUID not found!` when prerequisites are missing.

The private URL packet implementation **constructs `http://`**, including a returned server/port (`napcat.mjs:32608-32610`). The group operation constructs HTTPS (`32604-32607`). Current saver accepts only HTTPS or approved local paths, and rejects any other scheme (`setu_files.py:136-145`). Switching to this private URL action alone therefore conflicts with the existing safe fetch contract. Whether any specific returned server supports equivalent HTTPS has not been probed and must not be assumed.

### Boundaries relevant to a correction

- Keep correlation timeouts for short chat APIs independent of potentially long file transfer waits.
- Preserve canonical `file_id` separately from the original basename; choosing UUID avoids basename cache overwrite and gives the private URL API its expected field. It still depends on NapCat's alias registration and current cache lifetime.
- Preserve pre-transfer size checks (`setu.py:280-285`), safe source checks, bounded copying and no raw response logging.
- A returned local path must still pass configured root and `nt_qq*/nt_data/{Video,Pic,Audio,File,Record}` checks (`setu_files.py:145-155`). No live file response/path was observed in this research.
- The repository Compose mounts the same host `data/napcat/QQ` read/write into NapCat and read-only into OneBot at `/app/.config/QQ` (`deploy/compose.yaml`). This makes paths in that specific tree available; it does not mount `/app/napcat/cache` or an arbitrary QQ file-assistant output location.

## Related specs

- `.trellis/spec/backend/error-handling.md`: OneBot failures remain protocol-boundary failures; setu preserves failed items for retry.
- `.trellis/spec/backend/logging-guidelines.md`: bounded diagnostics; no raw events, private URLs or chained secret-bearing errors in logs.
- `.trellis/spec/backend/index.md`: relevant layer index.

## Caveats / Not Found

- No `get_file`, private URL, media download, send, service restart or configuration mutation was invoked by this researcher.
- The main session owns exact failed-batch/forward structural inspection. Its sanitized attachment metadata is cited above; private chat content was not independently inspected here.
- Installed package.json reports a placeholder version, so embedded executable bundle version 4.18.28 is the useful observed runtime source version; Docker image tag is `latest`, not a reproducible dependency pin.
- Actual NapCat transfer status, exact OneBot retcode and returned local path remain unverified. Source and elapsed time establish the contract mismatch, not complete proof of the individual live failure.
- Larger request timeout cannot alone fix unavailable/expired cache identifiers, packet failure, kernel download failure or a cache path outside the approved mount.
