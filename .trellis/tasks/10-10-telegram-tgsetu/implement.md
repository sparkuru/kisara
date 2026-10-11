# Approved implementation plan

The user approved the latest final planning summary on 2026-10-11. Flat individual-file atomic publication, on/off automatic saving and attachment original-stem + description + tags naming are required. Task activation and feature branch are established; implement/check now, without live deployment or commit/archive.

## Sequence

Latest approved revision: delete the four old root scripts, migrate executable
fixtures/callers to kisara.sh and retain real canonical selection/lifecycle
coverage. Update current guidance; retain stored preview labels and historical
evidence. The user separately approved removing stopped QQ containers and
starting the effective bare-command OneBot preview; record its actual outcome
and preserve mounted data/Telegram. See latest [boundary](research/unified-entrypoint.md).

Latest revision completed and independently reviewed: four old scripts absent,
canonical fixture migration and bounded Python NapCat probe at /webui/ verified.
Final full gate893 passed /1 Git-dependent skip /3 existing PTB warnings.
Authorized real OneBot start/status returned ready and retains original mounted
login/data/state plus isolated config/onebot. Telegram remains unchanged.
No controlled feature/account completion or commit/archive claim follows.

Previous approved follow-up: implement kisara.sh offline/online dispatch, retain
temporary old-script forwarding, extend preview target selection in its owning
parser, update active help/docs/specs and verify focused/full regression per
[CLI boundary](research/unified-entrypoint.md).

CLI follow-up completed and independently reviewed. Canonical full regression:
`./kisara.sh test -q` — 907 passed, 1 Git-dependent skip, 3 existing PTB warnings.
Pure help and real offline console /quit smoke passed. Compatibility forwarding,
explicit preview targets and old ownership labels are covered by focused and
full fixtures. No actual service operation, commit or archive was performed.

Approved follow-up: unify selected-engine roots, migrate OneBot examples/private
files safely, align Compose/direct/hako reads, broaden private-file ignores,
update docs/specs and rerun focused/full checks per
[configuration boundary](research/config-root-unification.md).

Follow-up completed and independently reviewed: final full Docker gate
825 passed / 1 Git-dependent skip / 3 existing PTB warnings. The skip's
synthetic Git check ran separately on the host. Actual private chat/news/setu
copies preserve bytes/modes and retain ignored originals. Deployment is
unexecuted; the changed mounts require targeted recreation to activate.

1. Completed: final summary approval, task activation, feature branch and integration boundary. Update the plan before proceeding if new evidence materially changes approved behavior.
2. Load backend database/error/logging/quality and shared routing/storage/validation policies, plus Python/shell skills as applicable; curate context manifests.
3. Add TgSetu config/example, native registry/help/enablement and main wiring. Preserve OneBot and optional SDK imports.
4. Implement authorized media/caption normalization, on/off activation, durable per-file queue, logical-unit metadata/deduplication, frozen names, late arrivals and caps. Do not add finish/confirmation or a separate quoted-save workflow.
5. Implement filename policy and flat no-replace individual-file publication, durable per-file claims/checkpoints/reconciliation, owned transfer workers and unfinished-file retry. Preserve successful siblings on partial failure.
6. Configure local ExtBot endpoints/cache root; pin/build official server, Compose internal service/shared cache/separate archive and non-root permissions. Update existing deployment/preview entrypoints consistently. Do not operate live services.
7. Add focused config/naming/state/SDK tests for authorization-before-effects, on/off acceptance and already accepted work, targeting, disabled feature, activation/restart, UTF-16, photo variants, mixed album media, attachment suffixes, collision, late arrival, oversize, cancellation and publish-before-DB restart.
8. Run focused checks then broad suite; update existing operations/application docs and shared feature/storage specs, not README.
9. Prepare concrete account acceptance and controlled endpoint migration/rollback; inspect scope/diff before delivery.

## Planned validation

- `./hako python -m pytest tests/unit/test_tgsetu_config.py tests/unit/test_tgsetu.py tests/unit/test_tgsetu_files.py` after creating those suites.
- `./hako python -m pytest tests/unit/test_telegram_adapter.py tests/unit/test_telegram_settings.py tests/integration/test_telegram_protocol.py tests/unit/test_dispatcher.py tests/unit/test_engine_deployment.py`.
- `./hako python -m pytest tests/unit/test_setu.py tests/unit/test_setu_config.py tests/integration/test_onebot_protocol.py` for retained OneBot behavior.
- `./kisara.sh test` after focused cross-layer checks.
- `git diff --check`, relevant shell syntax/ShellCheck/shfmt if scripts change; sanitized Compose fixtures without rendered credentials.
- Controlled >20 MB fixture for chunk-copy memory bounds and local-path checks; separate live forward/large-file/restart acceptance.

Product tests were not run during planning because no product code changed.

## Execution result

Steps 2–8 are implemented and independently reviewed. Final full Docker suite:
786 passed, 3 existing PTB warnings. The source-pinned official Bot API 10.3
image built successfully and passed network-none binary/library/license and
synthetic shared-UID/read-only-cache checks. See [validation](validation.md).
Step 9 is prepared in [live-validation](live-validation.md) and operations docs;
actual account/deployment acceptance is unexecuted. Work remains uncommitted and
the task remains in_progress; no archive or other-task operation was performed.

## Risks and rollback

Preserve existing Setu state/media and its separate task. SQLite/filesystem recovery must reconcile publication. Validate local cache mount path/read permissions and disk retention. Preserve the custom ExtBot's polling readiness/fatal-error/client-cleanup behavior. No deployment/logOut occurs without its explicit operation scope; keep persistent volumes for endpoint rollback.
