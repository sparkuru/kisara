# Setu automatic archive mode

## Goal

Allow an authorized OneBot private-chat user to enable `/setu on`, send
successive merged forwards, and have each saved automatically until
`/setu off`, without repeating a quoted save command for every source.

## Source request

The user explicitly requested task creation on 2026-10-31 and specified:

> /setu on；则后续发送的所有合并消息。全都自动引用并说明正在保存 xxx（即正常流程）、
> 即，这个主动模式下，自动处理用户发来的内容，直到 /setu off 为止。
> 原本的 引用并说明保存 的逻辑不受影响

## Background and confirmed facts

Source anchors in this section refer to the inspected baseline `b1dbc95`.

- Setu currently handles only authorized OneBot private chats. Both global
  and feature allowlists apply before native lookup or saving:
  `src/kisara/bot/adapters/onebot_v11.py:264` and
  `src/kisara/application/services/setu.py:119`.
- Manual source commands quote a merged forward or ordinary file. The normal
  command asks for a quoted confirmation; configured direct confirmation words
  skip that question: `src/kisara/application/services/setu.py:124`.
- Each claimed save already sends a quoted `正在保存以上 …` notice counting
  unfinished attachments before transfer, followed by the archive result:
  `src/kisara/application/services/setu.py:291`.
- Existing batches and per-item checkpoints are durable in `setu.sqlite3`:
  `src/kisara/infrastructure/persistence/setu.py:13`. There is currently no
  Setu activation setting. Technical evidence is recorded in
  [research/current-behavior.md](research/current-behavior.md).

## Requirements

- **R1 — Explicit activation:** `/setu on` enables automatic handling for the
  sender in that bot instance; `/setu off` disables it. Reply with the resulting
  mode. A user without an activation starts with automatic handling off.
  Repeating either command is harmless. One user's choice must not affect
  another user or instance. The user explicitly selected restart resetting
  activation to off. Activation lasts in process memory only; a transport
  reconnect within that process does not reset it.
- **R2 — Automatic merged forwards:** While enabled, each newly received merged
  forward starts its own archive attempt without a source quote or additional
  confirmation. Extract its supported attachments, including nested forwards,
  under the existing limits. Empty or unsupported sources must not produce a
  false saving/completion claim.
- **R3 — Existing save feedback:** Quote the incoming merged-forward message
  with the existing pending-attachment counts and `正在保存以上 …` notice before
  transfer. Report the actual save outcome afterward. Preserve the current
  best-effort notice behavior and failed-item retry selection.
- **R4 — Manual compatibility:** With automatic mode on or off, preserve manual
  quoted-source confirmation, direct save, pending prompt selection, source
  deduplication, expiry, saved checkpoints, and retry behavior. `/setu off`
  stops automatic acceptance of later forwards; it does not discard an already
  accepted batch or disable explicit manual saving.
- **R5 — Existing boundaries:** Retain OneBot/private/global/feature permissions
  before extraction, state changes, lookups, or media effects. Preserve export
  priority and ordinary command routing. Automatic acceptance is limited to
  merged forwards; ordinary images, videos, audio, text and standalone files
  retain existing behavior.
- **R6 — Documentation:** Explain activation, deactivation, scope, restart
  behavior and manual compatibility in existing feature documentation and
  applicable shared specs.

## Acceptance criteria

- [x] **AC1 / R1:** Authorized `/setu on` and `/setu off` return clear status;
  repeated commands remain usable; a fresh user defaults to off.
- [x] **AC2 / R1, R5:** Activation is isolated between users and instances.
  Unauthorized and group events do not activate, expand or save anything.
- [x] **AC3 / R2, R3:** After enabling, two successive merged forwards each
  save without another command/confirmation, with distinct source quotes and
  accurate pending counts. A mixed/nested forward follows existing limits.
- [x] **AC4 / R3, R4:** Duplicate delivery does not repeat a completed save;
  partial failure preserves successful files and the existing retry route.
  Notice-send failure does not strand an accepted save.
- [x] **AC5 / R4:** After disabling, later unsolicited merged forwards do not
  archive automatically. Existing quoted normal/direct save and confirmation
  flows still work in either mode, including already pending batches.
- [x] **AC6 / R5:** Standalone media/files and unrelated commands do not acquire
  new automatic-save behavior; export priority is preserved.
- [x] **AC7 / R1:** Recreating the service over the same stored batches starts
  with automatic mode off while preserving saved files/checkpoints. Reconnecting
  the transport with the same service retains the in-memory activation.
- [x] **AC8 / R6:** Existing operational docs, feature docstrings and applicable
  specs agree with the implemented behavior; focused service/protocol checks
  and the required broader suite have recorded results.

## Out of scope

Telegram `/tgsetu`, official-adapter support, group automatic archiving,
standalone-media automatic archiving, new file placement/download policies,
historical media migration, dependency upgrades, live service operation,
deployment, commits and push are not part of this task-creation request.

## Key decisions

The user chose “重启关闭吧” on 2026-10-31 after discussing memory-only and
durable activation. No new SQLite activation state, configuration setting or
dependency is needed. Existing archive batch persistence remains unchanged.
There are no remaining blocking product questions.

## Planning status

The user approved the final planning summary with “开始” on 2026-10-31.
[Design](design.md), [execution plan](implement.md), research and both context
manifests are prepared and validated. Implementation and offline checking are
authorized; live operations and delivery actions remain outside this approval.

Implementation, independent review and scoped automated acceptance are complete.
[Validation evidence](validation.md) records the 276-pass focused gate, the full
run's 1342 passes/7 skips and one unrelated preview cleanup failure, and its
successful isolated retry. The full run is not claimed wholly green.

On 2026-10-31 the user reported “验收通过；可以提交”, accepting the delivered
behavior and authorizing local commit plus normal task wrap-up. This supersedes
the initial commit/archive exclusion for this task only. Live operations,
deployment and push remain outside scope.
