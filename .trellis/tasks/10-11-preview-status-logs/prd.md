# Show current bot logs in preview status

## Goal

Make `./kisara.sh preview status` show readiness and the selected current bot's
recent logs, then continuously follow new logs until the operator interrupts it.

## Background

- The user explicitly requested task creation and adding logs to preview status.
- On final-summary review, the user clarified: “不用退出；直接持续”. This
  supersedes the proposed finite snapshot and requires continuous log following.
- `kisara.sh:73` forwards preview operations to the existing lifecycle backend.
- `deploy/preview-runtime.sh:688` currently shows a summary for ready status;
  failure diagnostics are already available through `preview_diagnostics` at
  line 419, using ownership verification, an 80-line tail and a 5-second timeout.
- `preview_redact` at `deploy/preview-runtime.sh:16` provides existing secret,
  identifier and authenticated-URL sanitization.
- Preview source, tests and operational documentation already have unrelated
  uncommitted changes. Preserve them and keep this task's additions identifiable.

## Requirements

- R1: After the existing readiness summary, show clearly labeled bot logs and
  continuously follow new lines without requiring `--verbose`.
- R2: Show the last 80 lines for each selected, owned bot container: OneBot
  `kisara`/`kisara-dev`, Telegram `telegram`, official `official`/standalone `bot`.
  Successful status does not need auxiliary NapCat, music or local Bot API logs.
- R3: Apply the existing redaction contract before each emitted log line. Do not
  buffer output until the stream closes or store an ever-growing raw log file.
  Failed reads/redaction show an actionable message with no raw fallback.
- R4: Ctrl+C ends only this command's log readers, leaves bot containers/data
  intact and returns the conventional interrupt status. Preserve absent/unready
  nonzero reporting and existing bounded failure diagnostics. Stream failures
  must be reported explicitly and terminate with nonzero status.
- R5: Respect explicit engine targets, effective default selection and ownership.
  Status must never prepare, build, install, start, stop or remove services.
- R6: Update existing preview help, operational usage and relevant policy to
  describe continuous following; validate through controlled streaming recording
  fixtures and a read-only current-preview smoke check where permitted.

## Acceptance Criteria

- [x] AC1 (R1–R2): Ready status prints readiness, recent logs and subsequent new
  lines without `--verbose`, remains running between lines and respects default
  and explicit bot selections.
- [x] AC2 (R2, R5): Mixed bot selections show each selected bot with a label;
  auxiliary-only status makes no bot-log request, and unrelated containers are
  never queried for logs.
- [x] AC3 (R3–R4): Stream/read/redaction failures produce a useful message and
  nonzero exit, disclose no raw secret and leave no orphaned log readers.
- [x] AC6 (R3–R5): Ctrl+C promptly exits with interrupt status; selected bot
  containers and persistent data remain intact, all owned readers are reaped,
  and memory/scratch usage does not grow with accumulated log history.
- [x] AC4 (R4–R5): Absent/unready status remains nonzero; recording fixtures prove
  there are no lifecycle mutations and existing failure diagnostics still work.
- [x] AC5 (R6): Existing help/docs/policy match the verified behavior; relevant
  shell checks and focused preview/CLI tests pass, with exact evidence recorded.

## Out of Scope

- New preview subcommands/options, configurable tail size, persistent log
  storage, bot logging changes, ongoing health monitoring and new dependencies.
- Service recreation, deployment, credentials/account operations, changes to
  unrelated ongoing tasks and archive. Work commit was separately authorized
  after implementation; see the delivery decision below.

## Planning Status

Continuous streaming introduces redaction and signal/process lifecycle work;
`design.md` and `implement.md` accompany this revised PRD. The user approved
the revised final summary on 2026-10-11 with “可以”; the task is in progress.
Implementation, independent review, focused and full regression and the real
read-only preview smoke have passed. See `validation.md` for commands/results;
The user subsequently authorized a combined work commit containing this task
and the implemented Telegram/configuration/canonical-command prerequisites:
105 explicitly reviewed paths, excluding workspace journals. No push or archive
is authorized; keep both task records in progress.
