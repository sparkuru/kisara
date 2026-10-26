# Independent scheduled-news retry review

## Context and scope

Read the saved native hook output at
`/tmp/hook_outputs/01a175c9-2ee6-7200-9591-4f62b898023f/2ff171d4-8d8b-428b-9d73-a9fba2f09a35.txt`.
The visible hook/tool output was truncated, and configuration-storage.md exceeds
the native 32768-byte per-file cap. Read the complete repository configuration
spec directly, plus the other manifest guidance, PRD/design/implementation plan,
mainline task status, Python coding guidance and implementer's evidence report.
Both eight-entry manifests validate; their per-file warning is resolved for this
review by the direct file read, not by claiming complete native injection.

Reviewed this task's settings/feature-key loading, existing OneBot and Telegram
schedulers, adapter injection, synthetic deployment interpolation tests, news and
configuration regressions, both public TOML examples, `.env.example`, operations
guidance and project-owned configuration contract. The working tree also holds
earlier preview and Telegram startup-recovery edits; those were preserved and
not attributed to this task's implementation.

## Findings fixed

None. No production or test correction was needed during independent review.

## Findings not fixed

No actionable defect found in the scoped changes.

Confirmed the new settings field and scheduler optional argument are appended,
preserving positional calls. Explicit TOML is chosen before parsing lower-priority
environment input; boolean/fractional/nonpositive/malformed/empty values fail
startup. Selected namespace resolution copies rather than mutates environment.
Compose preserves explicit empty input through both OneBot fallback levels and
keeps Telegram independent. Tests execute the actual expressions with synthetic
values instead of asserting only the new key's presence.

Both existing schedulers consume the setting. OneBot retains its connected-session
loop and confirmed-target checkpoints. Telegram measures new deadlines after
generation/rejection completion, respects longer server retry-after, and bounds
polling by the retry interval. Confirmed/permanent/uncertain/claimed transitions,
cancel cleanup, current-day checks and existing persisted deadlines are retained.
No HTTP retry, manual-news change, new scheduler, dependency or schema was added.
Documentation correctly requires application image rebuild/recreation before
deployed instances can use this source change; private configuration/live bots
were not changed by this review.

## Verification

- Lint: no configured application linter in pyproject.toml; not run or claimed
  as passed. No toolchain was installed.
- TypeCheck: no configured command; not run or claimed as passed.
- `git diff --check`: passed.
- New untracked test and task artifact whitespace checks: passed, including
  direct `git diff --no-index --check` against each file.
- `python3 .trellis/scripts/task.py validate .trellis/tasks/10-26-news-push-retry`:
  both eight-entry manifests passed, with the explicitly handled per-file size
  warning above.
- Implementer's focused gate inspected in `implementation-evidence.md`:
  **386 passed, 1 existing skip in 20.97s**. Initial targeted comparison was
  **23 failed/8 passed** before and **31 passed** afterward. These numbers are
  inspected implementer evidence, not independently rerun here.
- Independent full `./kisara.sh test -q`: **1179 passed, 1 skipped, 3 warnings
  in 560.36s**, exit 0. The skip remains the development image's unavailable Git
  executable case; the warnings are existing PTB `retry_after` timedelta
  deprecation notices. Production and tests remained unchanged throughout this
  full run; no supplemental source/test gate was needed.

The full gate uses the existing Python 3.12 offline Docker wrapper with synthetic
configuration, fake providers and protocol peers. Narrow wrapper escalation was
requested because the Docker socket restriction was already established in the
main session. No private dotenv/provider/account operation, live service mutation,
commit, archive or push was performed by this reviewer.

## Human review classification

Classify as **human-optional** for the source behavior: deterministic tests and
the full regression passed for configuration and timing/state transitions. No
reply is required to establish code readiness. A deployed
runtime/provider observation may add operational evidence but is not required to
establish this offline code contract. Live deployment remains unperformed and
requires its own authorized lifecycle action. OneBot's preexisting uncertain-send
and failed-checkpoint duplicate limitation remains; no exactly-once guarantee is
introduced.
