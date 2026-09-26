# Bootstrap Project Guidelines

## Goal

Complete the existing Trellis initialization so future agents have practical,
source-backed Kisara backend guidance. The user requested completion and local
commits on 2026-09-26 and explicitly chose to resume this task without creating
a new one.

## Requirements

- Document the current directory structure, SQLite persistence, error handling,
  logging, and quality conventions in `.trellis/spec/backend/`.
- Include concrete source/test paths and short examples rather than template
  placeholders. Keep documentation in English.
- Keep the project-owned Trellis Plus policies consistent with the completed
  backend guidelines and the current delivery authorization.
- Preserve generated runtime behavior and personal platform configuration.
- Track the initialized shared workflow with exact upstream license text and
  provenance; exclude local identity, session pointers, caches, and credentials.
- Verify documentation, commit the completed work, archive this task, and
  record the session using Trellis's existing bookkeeping commands.

## Acceptance Criteria

- [x] All five backend guideline files describe existing source patterns.
- [x] Guidelines include real examples and an accurate navigation index.
- [x] Documentation links and referenced paths resolve; no scaffold placeholders
  remain in backend guidance.
- [x] Upstream provenance and license text are recorded without changing the
  application's licensing or inventing a copyright notice.
- [x] Quality review passes and its scope/results are recorded.
- [ ] Work commits precede task archive and journal commits.

## Constraints

This is documentation and workflow initialization only. It does not change bot
code, schemas, deployment, live services, dependencies, or private configuration.
Application tests are not required for a documentation-only change; use the
checks in `.trellis/spec/trellis-plus/validation.md`.
