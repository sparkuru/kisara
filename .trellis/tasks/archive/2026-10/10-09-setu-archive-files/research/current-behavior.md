# Current runtime and source evidence

Inspected 2026-10-09 during planning. Read-only evidence; no live transfer acceptance, service restart, or private-config change.

## Runtime

`kisara-kisara-1`, `kisara-telegram-1`, and `kisara-napcat-1` were running, each with restart count 0, started 2026-10-04. No project dev bot observed. Account connectivity was not exercised.

Allowlisted config query inside OneBot: enabled=true; save_mode=date_original; save_root=/app/setu; max_file_bytes=2G; max_batch_bytes=10G; local_media_root=/app/.config/QQ. Credentials/user IDs excluded.

## Source anchors (pre-implementation baseline `473267b`)

| Source | Evidence |
| --- | --- |
| `src/kisara/application/services/setu.py:51` | Generic file collection already exists. |
| `src/kisara/application/services/setu.py:97` | OneBot/private/user gates precede collection. |
| `src/kisara/application/services/setu.py:176` | Collection stores file metadata; no archive-specific filter. |
| `src/kisara/application/services/setu.py:233` | Generic file count already shown. |
| `src/kisara/application/services/setu.py:266` | Checkpoints and retries preserve completed files. |
| `src/kisara/bot/adapters/onebot_v11.py:426` | Supplied URL or get_file resolution; response URL/file consumed. |
| `src/kisara/infrastructure/persistence/setu_files.py:32` | Date mode uses sanitized names. |
| `src/kisara/infrastructure/persistence/setu_files.py:42` | Hash mode renames and keeps only final suffix. |
| `src/kisara/infrastructure/persistence/setu_files.py:98` | Same placement applies to all attachments. |
| `src/kisara/infrastructure/persistence/setu_files.py:102` | Matching hashes reuse files; different contents use numbered names. Existence check then os.replace is not a concurrency guarantee. |
| `src/kisara/infrastructure/persistence/setu_files.py:114` | Bounded approved URL/cache copying; local File directory allowed. |
| `src/kisara/infrastructure/persistence/setu_files.py:167` | Lossy sanitization/truncation/fallback names do not guarantee exact original archive names. |
| `tests/unit/test_setu.py:88` | Nested-forward placement tests cover image/video in both modes. |

## Conclusions and limits

This task extends generic file support with explicit archive coverage and naming rules. No specific current archive transfer failure was reproduced. Resolver changes require actual payload evidence; source protections remain intact.

User decision after initial research: different-content archive name conflicts use `original_timestamp.ext` in the same directory; preserve compound extensions. The user explicitly restricted stamp handling to the new archive feature, keeping existing image/media hash naming and repeated-save behavior. The earlier proposed collision subdirectory was not selected.
