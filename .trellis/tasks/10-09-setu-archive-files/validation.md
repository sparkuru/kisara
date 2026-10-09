# Validation and current acceptance state

## Current result

Latest live failures exposed two additional application gaps: retained seen IDs
hid expired failed work, and ordinary native downloads used an unapproved
NapCat/temp path with owner-only permissions. Corrected state transitions,
precise file-only cache handling and bounded native chunk fallback are implemented.
The latest user follow-up adds one pending-kind save-start notice after the
durable claim and before resolution/transfer. Start/result ordering, normal/
direct/retry counts and notice-send failure are covered; final review passed.

Current automated checkpoint:

| Check | Result |
| --- | --- |
| Focused setu/config/adapter/protocol suites | 308 passed,15.04seconds |
| Final full-scope review, ./dev.sh --all | 580 passed,19.71seconds; no behavioral findings |
| Existing warnings | 3 Telegram SDK retry_after deprecation warnings |
| Whitespace check | git diff --check passed |
| Task manifests |14implement /12check entries, no size warnings |
| Lint/type checker | Not configured; not claimed |

## Current behavioral coverage

- Original safe archive basenames, compound/case-sensitive extensions and bytes
  in both layouts; archive-only timestamp conflicts, same-content reuse and
  non-overwriting concurrent publication; unchanged image/generic-file placement.
- Actual dual-field NapCat identifiers, dedicated bounded file deadlines and
  safe action/retcode diagnostics; caps before native transfer.
- Fresh explicit source commands restore expired failed work atomically without
  a second batch, retain completed paths/inodes/date/byte budget and refresh only
  matching unresolved identifiers/URLs. Old confirmations remain expired.
- Distinct direct replies for active saves, completed work, changed source and
  pruned metadata. Overlapping source actions only save once.
- Exact direct-child NapCat/temp file exception with symlink/root/private sibling,
  nested path and non-file/missing-kind rejection.
- Owner-only native files use existing authenticated WS chunk transport, with
  bounded metadata/chunks, order/base64/actual sizes and completion totals before
  spool-to-saver publication. Both layouts, normal/direct and forward/file
  protocol matrices exercise the full fallback.
- Partial-stream timeout, disconnect, rejection, malformed replies, spool write
  failure and cancellation retire their correlation callbacks; later chat
  requests still complete. Retry retains earlier successful file inodes. A
  cancelled disk copier cleans its incoming file, releases the transfer slot
  and emits no unobserved future error, both when cancellation precedes and
  follows the worker's failed completion callback.
- Global/feature/private gates, quoted-source provenance, no unsolicited saving,
  no download before consent and separate image-export priority remain effective.
- Save-start notices quote the triggering command and precede resolver/copy/final
  result, count unfinished categories only and omit zeros. They retain the normal
  prompt and direct failure-result selectors; progress replies cannot select a
  retry. A failed notice send logs no private details and saving still completes
  with accurate success/failure counts. No-pending/rejected actions emit no notice.

## Live complete-byte evidence

The reported ordinary file now has a successful native download. A real read
under OneBotUID10001 failed because native file mode0600 belongs to1000; no
chmod/chown/config/mount change was made. Revised adapter/saver loaded into an
isolated diagnostic process under the same UID transferred all109092709bytes
through download_file_stream, saved exact original basename with mode0640 in
a private temporary directory, and matched the independently read original
cache SHA-256. Spool and temporary output were cleaned.

See research/live-cache-and-expired-retry.md for sanitized source/probe details.
No production archive/checkpoint was modified, no agent QQsend or restart/build
occurred. Native download and full byte persistence capability passed; a deployed
quoted command/result and SQLite completion checkpoint remain pending.
The new start-notice receipt also requires the updated runtime image; simulated
protocol tests establish its ordering and reply shape without live account sends.

Human classification: human-required for deployed command acceptance.
The user has already rebuilt the ordinary-file entry externally; the running
image still lacks the newest state/cache/stream corrections. Apply only the
OneBot image, then quote the exact ordinary-file message again with 直接保存;
expect1saved/0failed, original basename, saved checkpoint and duplicate source
suppression. live-validation.md contains the scoped rebuild and checks.
The earlier private forwarded resource still has its separate native120s failure.

## Executed commands

```bash
./hako python -m pytest tests/unit/test_setu.py tests/unit/test_setu_config.py tests/unit/test_onebot_adapter.py tests/integration/test_onebot_protocol.py -q
./dev.sh --all
python3 .trellis/scripts/task.py validate .trellis/tasks/10-09-setu-archive-files
git diff --check
```

Docker tests do not load bot credentials. Narrow diagnostic Docker execs used
only existing target connection credentials internally and the one reported
source; no sensitive values are printed. Python3.12-only testing does not prove
every declared Python version.

## Historical checkpoints

Initial archive storage:150focused/422full. Canonical-ID/deadline/retry fixes:
181focused/454full. Approved ordinary-file entry:221focused/493full, three
existing Telegram SDK retry_after deprecation warnings. These earlier passes
did not establish the actual new native path/permissions or expired-source
behavior and are superseded by the latest review.

Prior independent review bounded wrapper exception contents and outer-trace
privacy; archive recognition mutation sensitivity failed its exact-name
hash-layout assertion as expected without mutating shared source. Specs are
below32768byte injection limits and context includes the latest native evidence.
The user explicitly authorized committing the reviewed implementation after
the final start-notice report on2026-10-09. commit-plan.md records that scope;
this does not claim the pending deployed acceptance passed. Keep the task
in_progress and record the work commit in the session journal without archival.
