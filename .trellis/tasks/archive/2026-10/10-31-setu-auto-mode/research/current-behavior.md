# Current Setu entry and reuse evidence

Source line anchors below describe the inspected pre-change baseline
`b1dbc95`; implementation shifts those line numbers.

## Routing

`src/kisara/bot/adapters/onebot_v11.py:255` runs exports before Setu. The Setu
branch applies global and feature authorization, optionally resolves the
quoted source for recognized manual start words, and then invokes
`Setu.handle`. An incoming forward already has normalized forward segments;
automatic handling should not synthesize a manual text command or depend on
retrieving a quoted message.

## Service

`src/kisara/application/services/setu.py:114` recognizes exact manual start
words and configured direct confirmation words. `/setu on` and `/setu off`
are not currently recognized. `handle` at line 124 requires both a start word
and a prepared quoted source before extracting attachments and preparing a
batch. Ordinary unsolicited forwards currently fall through.

The existing extraction walks nested forwards under node/depth limits.
The direct branch calls the existing source-claim transaction and `_save`;
this provides the needed save feedback without introducing another downloader.
`_save` at line 291 sends pending-kind counts before lookup/transfer and keeps
the existing batch result/checkpoint/retry machinery. Automatic mode should
select the incoming source message ID as its quote target.

## State

`src/kisara/infrastructure/persistence/setu.py:13` owns `setu.sqlite3`. It
persists batch state and seen source IDs, with transactional claims in
`prepare_source`. Preserve this source identity and successful-item metadata.
There is no activation table or process-local activation set today. The user
selected memory-only activation with restart resetting it to off. Use service
memory keyed by instance and user; leave stored batches and schema unchanged.
Adapter reconnect reuses the existing service, so reconnect does not imply a
process restart or a reset of this setting.

`src/kisara/bot/adapters/onebot_v11.py:223` serializes events within a
conversation. Keep this ordering: `/setu off` affects later handled forwards
and does not cancel the preceding save. A parallel background queue or
out-of-band command path is unnecessary for the requested behavior.

## Existing regression coverage

- `tests/unit/test_setu.py` covers quoted confirmation/direct saving, source
  deduplication, expiry, partial retry, notices, source restrictions and layouts.
- `tests/integration/test_onebot_protocol.py:536` covers manual source words
  through simulated OneBot peers; subsequent cases cover direct/normal notice
  quotes, native file transfer and authorization rejection.
- `docs/operations.md:492` describes existing source/file entry and save notices.
- `docs/application-template.md:90` lists the existing Setu feature contract.
- `.trellis/spec/trellis-plus/architecture.md` and `setu-storage.md` currently
  state that unsolicited forwards do not auto-save. Update those statements to
  distinguish default-off/manual behavior from explicitly enabled automatic mode.

## Validation boundary

This is planning/source inspection only. No application tests or live QQ
operations have run for this task. Expected execution validation is focused
Setu service and OneBot protocol suites through `./hako`, followed by the
project's full suite because this changes native message routing. Restart scope
is now resolved; final planning review/approval is still pending before task
activation or implementation dispatch.
