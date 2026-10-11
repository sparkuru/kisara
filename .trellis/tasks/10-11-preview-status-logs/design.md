# Preview status continuous bot logs

## Boundary and flow

The canonical dispatcher remains unchanged. After selected-owned preview
readiness and summary succeed, the preview runtime follows Docker logs for
the selected application bot IDs. Start with `--tail 80`, then follow new lines
without a total runtime timeout. Auxiliary-only selection has no bot stream.
Absent/unready status retains existing bounded diagnostics and nonzero exit.

The relevant bot services are `kisara`, `kisara-dev`, `telegram`, `official`
and standalone official `bot`. Verify existing ownership before each reader
starts; never follow by broad Compose project selection. Mixed selections need
concurrent readers with service labels on emitted lines.

## Streaming privacy and lifecycle

Refactor or reuse the existing sanitizer so every line is fully sanitized
before output, including configured secret replacement and current pattern
filters. Preserve the captured preparation/failure-diagnostic contract.
Streaming must flush promptly without waiting for end-of-file; scratch and
memory use must be bounded independently of cumulative history. Do not add
a new sanitizer dependency or expose raw fallback/error output.

Track only this invocation's reader/helper processes. On INT/TERM, stream
failure or sanitizer failure, stop and reap these processes before existing
temporary-workspace cleanup. Do not stop containers or signal unrelated
processes. Ctrl+C returns 130; TERM returns 143. Log stream failures are
explicit nonzero errors. Status following observes logs only; it does not
continuously re-evaluate readiness or restart readers/containers.

## Compatibility and rollback

Ready `preview status` now stays attached; this is the user-requested behavior.
`preview start`, failure diagnostics, target precedence, historical ownership
labels and service lifecycle remain intact. Existing finite fixtures can finish
their streams naturally; sustained fixtures must signal and await the command.
Preserve preexisting edits in all overlapping files. Revert only changes recorded
by this task if rollback is needed; do not restore whole files from Git.
