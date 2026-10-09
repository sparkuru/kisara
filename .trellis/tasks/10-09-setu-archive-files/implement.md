# Implementation plan

Status: implementation approved on 2026-10-09 following final planning review.

## Ordered work

- [x] Record approved archive-only `_timestamp.ext` collision policy and finalize coverage/path examples. Existing images/media keep their hash/repeated-save rules.
- [x] Inspect existing OneBot file metadata/resolver paths and cover provided locations/get_file cache/get_file URL shapes through simulated protocol tests. No live payload is claimed; existing interfaces suffice.
- [x] Run requirement convergence and lossless PRD convergence; validate curated manifests.
- [x] Present final planning summary, receive implementation approval, then run `task.py start`.
- [x] Dispatch `trellis-implement` with active task/context. Load backend and Python guidelines before Python edits.
- [x] Add archive-specific placement in `src/kisara/infrastructure/persistence/setu_files.py`; append `_timestamp` only for archive name conflicts, preserving full extensions. Preserve caps/source checks and all existing non-archive hash/repeated-save behavior; prevent archive collision/concurrent overwrites.
- [x] Correct the live-evidenced NapCat file identifier/deadline contract. Prefer explicit `file_id` for files, preserve basename, and add operation-specific bounded `get_file` response wait plus privacy-safe diagnostics. Retain ordinary media behavior and short chat deadlines.
- [x] Preserve usable retry selection after long file failures across the original confirmation deadline; keep short/unstarted/image-only deadlines unchanged.
- [x] Implement user-approved quoted ordinary-file entry using the existing state flow. Global/feature authorization precedes all lookup/handling; only quoted-source attachments are collected. Generalize prompts/guidance and module/config/operations docs; no setu help entry existed to change. Focused service/protocol tests passed 221.
- [x] Add archive behavioral tests in `tests/unit/test_setu.py` and relevant adapter/protocol coverage.
- [x] Update English module documentation and relevant example/operations/spec contracts. Keep private config untouched.
- [x] Re-run full-scope `trellis-check` after resolver/retry and ordinary-file entry changes. That historical checkpoint passed493tests; the newest live cache/state defects require the follow-up review below.
- [x] Prepare live QQ acceptance and classify deployed command acceptance as human-required. Scope any subsequently authorized service rebuild to OneBot; native ordinary-file bytes passed the later isolated verification.

## Validation commands after implementation

Latest live defect iteration:

- [x] Confirm actual states: both reported file batches expired with no saved
  items; retained source IDs did not mean completion.
- [x] Add atomic renewed-source state handling and truthfully distinct replies;
  preserve original partial checkpoints and budgets.
- [x] Confirm successful native ordinary-file response and precise mounted
  NapCat/temp path. Add file-only direct-child allowance and restrictive tests.
- [x] Check actual read access before declaring success: native0600 file unreadable
  by the OneBotUID. Add bounded native chunk fallback and full protocol validation.
- [x] Validate actual109092709bytes through revised adapter/saver under botUID10001
  into a temporary directory; independently compare original cache SHA-256,
  original basename and0640. Remove temporary validation copy.
- [x] Run combined focused suites:303passed in13.59seconds after15 lifecycle
  regressions and both cancelled-worker future cleanup corrections.
- [x] Finish latest full-scope review/full-suite gates after stream additions:
  575passed in18.28seconds,3existingPTBwarnings; diff/manifests passed and no
  code defect remained.
- [ ] Apply latest image externally and verify real quoted-source result/DB
  checkpoints; no agent deployment or account sends authorized/performed.

```bash
./hako python -m pytest tests/unit/test_setu.py tests/unit/test_setu_config.py
./hako python -m pytest tests/unit/test_onebot_adapter.py tests/integration/test_onebot_protocol.py
```

Run `./dev.sh --all` for adapter/cross-layer changes. Use the existing Docker wrapper without bot credentials for offline checks. Focused combined suite passed 150 tests after implementation; full-scope review/results are recorded in `validation.md` when complete.

Cover supported suffixes/both modes; uppercase/compound names; Chinese/spaces; mixed/nested forwards; confirm/direct save; matching name/content; archive-only timestamp collisions, including occupied timestamp candidates; missing/unsafe names; bytes; source/size rejection; partial retries; and unchanged non-archive hash/repeated-save behavior. Verify archive publication cannot replace different content under concurrent saves.

Planning checks:

```bash
python3 .trellis/scripts/task.py validate .trellis/tasks/10-09-setu-archive-files
git diff --check
```

Inspect new files explicitly since `git diff --check` excludes untracked contents; verify referenced source/spec paths.

## Prepared live acceptance

In an authorized private OneBot chat, quote a merged forward containing a small archive with known original filename and bytes using `/setu`. Verify prompt file count and no premature save. Quote the prompt with 保存; verify result quote/count/directory and saved basename/digest. Exercise direct save and a second conflicting archive for the approved policy as needed. Record sanitized outcomes without account IDs, signed URLs, tokens, or unrelated chat messages.

Current OneBot is ordinary `kisara`, not `kisara-dev`; live acceptance needs an approved image rebuild after code checks. Do not restart all profiles or infer Telegram support.

## Save-start notice follow-up

- [x] Add one claimed-save start notice with pending-kind counts and current
  command quote before resolution/transfer; no prompt/result-ID change.
- [x] Update normal/direct/retry protocol tests for the extra send and ordering,
  including notice-send failure and inactive/authorization/expiry suppression.
- [x] Re-run four focused suites:308passed in15.04seconds.
- [x] Finish full-scope review/full suite:580passed in19.71seconds with3existing
  Telegram warnings; diff/manifests passed. Specs/evidence refreshed, no
  behavioral findings. Actual updated-runtime start/result receipt remains
  pending alongside the existing human acceptance gate.

## Risk and rollback points

Review original-name provenance, archive-only naming, collision/concurrent publication, resolver boundaries, and checkpoint/result correctness. No schema or deployment changes currently planned. Preserve previous archive files and batch metadata. Any approved deployment/rollback targets OneBot code and service image.
