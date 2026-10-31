# Setu automatic mode design

## Change boundary

The behavior gap is repeated manual source selection for successive merged
forwards. Add activation and incoming-forward selection to the owning Setu
service, reusing extraction, batch claims and saving. Do not add a parallel
adapter workflow, download strategy, queue, database or configuration flag.

Expected product changes are `src/kisara/application/services/setu.py`, its
unit tests, the existing OneBot protocol tests, `docs/operations.md`, and
`docs/application-template.md`. Update the relevant architecture/Setu specs
after verification. Adapter changes are unnecessary unless protocol tests expose
a concrete routing gap; investigate and document that gap before widening scope.

## Activation lifetime

Own an initially empty set of `(instance_id, sender_id)` pairs in `Setu`.
Recognize exact `/setu on` and `/setu off` after the existing authorization
gate, using the service's existing whitespace/case normalization. On adds the
key; off discards it. Both return the resulting mode, including the restart
reset behavior where useful. Repeated commands are idempotent.

The existing service survives a WebSocket reconnect; its activation remains.
A newly constructed service has no activation, including when it reuses the
same state directory. No setting is written to SQLite, TOML or environment.

## Processing flow

1. Preserve adapter export priority, global authorization and feature/private
   authorization before any Setu side effect.
2. Handle the two exact activation commands in the service. Keep the existing
   manual quoted-source and confirmation semantics authoritative.
3. For a received merged forward from an enabled user, use the incoming
   message ID as the batch source. Collect supported attachments through the
   existing bounded `_extract` path. A source quote is not required.
4. Reuse `add_setu` and transactional `prepare_source(..., direct=True)` to
   claim saving. Reuse the existing action/status handling; avoid duplicating
   batch preparation or feeding fabricated commands back through `handle`.
   A small local helper for common source processing is acceptable if manual
   behavior remains covered by the existing regression suite.
5. Invoke the existing `_save(..., command_id=event.message_id, direct=True)`.
   This quotes the received source for both the start notice and final result
   and preserves result-based failed-item retry. The informational notice must
   never become the confirmation selector.

Automatic selection uses current-message forwards only. It does not broaden
standalone media acceptance or resolve arbitrary quoted history. Empty sources
report no savable attachments; unsupported expansion must not claim successful
transfer. Preserve existing failure/status behavior for unsupported items.

## Ordering, duplicate delivery and recovery

Retain existing per-conversation event ordering. A preceding accepted save can
finish before `/setu off` is handled; later forwards see the disabled setting.
Do not introduce cancellation or purge pending batches on off.

Keep existing durable source deduplication, atomic batch claims and item
checkpoints. Duplicate source delivery must not trigger another completed save.
Partial failure uses the existing direct-result confirmation retry. A process
restart resets automatic activation only; existing stored-batch recovery and
manual retry remain available. Do not automatically resume all failed or
interrupted saves merely because automatic mode had been active previously.

## Compatibility, rollout and rollback

No schema, dependency, permission, file naming, path, mount or configuration
changes are required. Default-off behavior remains manual. Update existing
feature documentation rather than adding another user guide. There is no
frontend or Telegram work.

Offline protocol fixtures establish routing/quote behavior, not live QQ account
delivery. Do not restart live services for this planning or implementation task.
Source rollback removes the mode entry and in-memory state without a data
migration; existing saved files and batch checkpoints remain valid.
