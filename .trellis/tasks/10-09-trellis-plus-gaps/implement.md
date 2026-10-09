# Implementation and verification

1. Curate shared index/workflow/validation/configuration and backend quality in
   both manifests. Append index/workflow to setu manifests without duplicates.
2. Main session writes complete principles, incremental config, loading,
   prospective attribution, mainline and exact notice/source provenance.
3. Implement agent repairs preview CLI and existing runtime paths, pinned
   preparation, runtime facts/rendering, endpoint resolution and bounded safe
   readiness/diagnostics. It owns scripts, .env.example, constraints and tests.
4. Main reconciles validation.md and docs/operations.md with the implementation.
5. Check agent reviews integrated change, runs appropriate checks, and fixes safe
   local issues. Main rereads checklist and records full after-state/limitations.
6. End with reviewed uncommitted files; do not stage/commit/archive/deploy.

## Checks

- bash -n changed shell; installed shellcheck/shfmt when available.
- ./hako python -m pytest tests/unit/test_engine_deployment.py <preview tests> -q
- Focused relevant checks, then ./dev.sh --all for deployment cross-layer risk.
- Temporary fixtures: missing image/dependency/both, prepared resources, healthy
  reuse, unhealthy/changed/incomplete group, failed build/install/recheck,
  invalid config, context/host/current/old CLI/remote, watch/readiness failure,
  bounded log timeout/failure/ownership/secret masking, no prepare from readonly
  or stop commands, retained storage and only newly created resource cleanup.
- Link/source/manifest/notice checks, template hashes, git diff --check and
  explicit final path/diff review.

## Authorization

Reuse the user's approval of the concrete audit plan followed by '创建任务，按已批准
方案推进' for the same scope. No repeated implementation confirmation is needed.
Docker tests may need narrow sandbox escalation; real preview startup/downloads,
UUPM/update/live calls and archival are not included.
