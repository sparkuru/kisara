# Execution plan

1. Obtain approval of the revised final summary, then activate this task.
2. Load curated policy plus shell/Python skills as applicable. Record the
   preexisting diff before changing overlapping files. Implement in the existing
   preview runtime and console helpers; add focused lifecycle regression cases.
3. Verify selected ownership, recent plus delayed new output, mixed concurrent
   readers, secret suppression before stream completion, auxiliary-only selection,
   stream/sanitizer errors and cleanup after INT/TERM. Recording fixtures must
   prove containers/data survive and no lifecycle mutations occur.
4. Run Bash syntax checks and ShellCheck/shfmt when available. Run focused
   preview/CLI suites through `./kisara.sh test`, then full regression required
   by the command-entry policy. Record actual commands/results.
5. Independently check the implementation and tests using the Trellis check
   role; fix concrete findings and rerun affected checks.
6. Update existing preview help, `docs/operations.md` and applicable shared
   preview policy. Use a bounded observer for a read-only real `preview status`
   smoke check, interrupting only this invocation and confirming the current bot
   continues running. Do not recreate containers or perform account operations.
7. Record evidence and remaining limits, inspect the task-specific final diff,
   and report completion. After completion, the user separately approved the
   combined 105-path work commit with Telegram/configuration/command prerequisites;
   workspace journals, push and archive remain excluded.

## Expected files and rollback points

- `deploy/preview-runtime.sh`: actual status behavior, redaction and reader cleanup.
- `deploy/preview-console.sh`: status help text.
- `tests/unit/test_preview_lifecycle.py`: behavioral streaming and signal fixtures.
- Existing operations/shared preview policy: documented changed status contract.

No new permanent helper is required by this plan. If a helper proves necessary,
justify it within the existing boundary before proceeding. All these source/docs
surfaces may have user-owned uncommitted edits; preserve those edits throughout.
