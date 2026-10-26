# Readiness/log-viewing execution plan

1. Load revised PRD/design and curated CLI/validation/shell/Python contracts.
   Prior locale/ready-stream results remain scoped historical evidence.
2. Add regressions for prompt logs while bare preview remains unready,
   transition to truthful ready summary, unready-status following, and INT/TERM
   without a post-interrupt diagnostic dump.
3. Split reader setup/wait without losing parent PID ownership. Integrate setup
   before startup readiness and after status readiness inspection; add shared
   nonblocking failure checking while waiting. Add start mkfifo prerequisite.
4. Preserve bounded startup failure/auxiliary diagnostics, real marker readiness,
   no-effect status, credential-safe FIFOs, multi-engine labels and retained
   data. Test sanitizer/reader failure during startup and cleanup on signals.
5. Update preview help/operations docs and project-owned CLI/validation contracts
   for approved attached-start and unready-status behavior. Do not change README,
   SDK/application readiness rules or live runtime.
6. Run focused CLI/engine/preview/readiness suites through existing hako/test
   wrapper, plus Bash syntax and available shell tools. Dispatch independent
   Trellis check and required full regression after focused success.
7. Record why first completion missed the actual path and new before/after
   evidence; main reviews final diff and waits for commit authorization.

Expected files: deploy/preview-runtime.sh, deploy/preview-console.sh,
tests/unit/test_preview_lifecycle.py, relevant CLI fixtures if help assertions
change, docs/operations.md, project-owned CLI/validation specs and task records.
No live start/rebuild/restart, account message, dotenv-value inspection, commit
or archive. Revised final planning approval is required before implementation.
