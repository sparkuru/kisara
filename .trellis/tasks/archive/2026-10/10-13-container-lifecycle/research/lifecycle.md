# Research: repository container lifecycle

- Query: Find the smallest shared ownership boundary and remove ordinary/preview lifecycle conflicts without damaging data, foreign containers, readiness or status isolation.
- Scope: internal source and isolated test fixtures; no daemon operations, private dotenv reads or external research.
- Date: 2026-10-13

## Findings

### Current cause and affected files

- `deploy/engines.sh:32` wraps ordinary Compose commands with the configured project and this repository's absolute `deploy/compose.yaml`; `:115` performs up/build, `:125` stops the opposing OneBot application, `:137` maps both stop/down to Compose stop. Ordinary lifecycle has no repository ownership preflight.
- `deploy/preview-runtime.sh:307` discovers by Compose project/service, but `:316` requires exact `hako.repo|preview.sh|service`. `:362` therefore rejects the ordinary deployment found through the same project/service query, including an exited container. This is a permission-policy mismatch, not an active lock file.
- `deploy/preview-runtime.sh:329` also rejects legacy Official, competing OneBot modes, changed fingerprints and incomplete groups. `:753` refuses build whenever any selected group exists. `:758` skips startup reconciliation for an existing group; `:548` and `:554` use `--no-recreate` when it does start.
- `kisara.sh:98` already routes public up to detached deployment; root changes should be limited to usage if command semantics change. Shared behavior belongs in the existing engines/helper layer.
- `hako:122` accepts detached preview bot mode only with its established labels; `:140` emits repo/scope/service. No hako implementation change is necessary to recognize an old runtime.
- `deploy/onebot.sh:54` and `:121` retain a separate legacy lifecycle implementation, used explicitly by deployment tests. If left in scope, it must use the shared ownership rule before effects; alternatively explicitly document it as outside the canonical entrypoint change. Do not silently weaken the advertised “either entry” safety boundary by overlooking this executable.

### Minimal common ownership boundary

Discovery and authorization are separate. Discover candidates using exact effective Compose project and service; inspect every selected candidate before any build/start/stop/remove effect. A project/service match alone is insufficient because another checkout can deliberately use the same project name.

Existing identity cases:

1. Ordinary Compose: base `deploy/compose.yaml:1` through `:244` declares no custom ownership labels. The prospective common authorization must inspect Compose-generated `com.docker.compose.project`, `com.docker.compose.service`, `com.docker.compose.project.working_dir` and `com.docker.compose.project.config_files`, requiring this repository's deployment working directory and base compose file. Exact field parsing must preserve paths with spaces and reject other checkout/base-file identities. A matching name or substring is insufficient.
2. Current preview Compose: `deploy/preview-runtime.sh:288` emits `hako.repo`, stable `hako.scope=preview.sh`, actual `hako.service`, config and attempt. Accept the established exact repo/scope/service identity, while rejecting contradictory Compose source labels when those are present. Never let a conflicting explicit repo label fall back to permissive Compose identity.
3. Evidenced old Official hako: `preview_find bot` at `:309` filters exact repo/scope/service. `preview_legacy_official` at `:323` additionally inspects only whether `KISARA_ENGINE=official` exists. This narrow branch can allow stop/down and explicit start migration; unrelated hako/manual bots are ineligible. Its lack of Compose labels is expected.

The prior task's `validation.md:114` records exited `kisara-telegram-1` without preview ownership. Its recorded prose does not include full working_dir/config_files values; the parent session has separately established those read-only facts. This research makes no new daemon claims.

A viable small sourced helper can own candidate enumeration, exact ownership inspection and selected preflight for both entrypaths. It should accept/use the already effective Docker argv rather than rediscover endpoint or log secrets. Keep Compose configuration/image generation, credential validation, readiness and console behavior in their existing owners. Reuse common selection and validation instead of a new lifecycle state machine or force flag.

For whole-project `down-all`, preflight the actual project's containers before invoking project-wide Compose down; selected-only validation cannot protect a foreign colliding service elsewhere in the project. Likewise inspect the opposing OneBot application before stopping it. Unknown/foreign candidates must cause failure before any selected container has already been changed.

### Gates removable through explicit Compose reconciliation

| Current gate | Proposed smaller behavior | Preserved constraint |
| --- | --- | --- |
| Preview-only ownership at `:362` | Shared repository ownership for either entry | Foreign candidates rejected before effects |
| Fingerprint mismatch at `:363` | Delete bespoke gate and allow explicit start reconciliation | Current environment/image desired state; real startup errors remain errors |
| Incomplete group at `:372` | Explicit start creates missing/stopped services | Status never repairs or treats a partial group as success |
| Build-existing at `:753` | Build images while existing containers stay untouched | Build does not start, stop, migrate legacy runtime or switch QQ mode |
| Reuse skip at `:758` | Explicit start always invokes Compose up | Status/help retain no preparation or lifecycle effects |
| `--no-recreate` at `:548`, `:554` | Allow Compose to apply desired images/config | Do not use project-wide remove-orphans or stop unselected bots |
| Opposing OneBot refusal at `:345` | Preflight repository-owned counterpart, then stop it on explicit startup | Only requested application runs against shared QQ state; no build/status switching |
| Legacy Official start/build refusal at `:339` | Build leaves old runtime untouched; selected explicit start stops verified legacy runtime before Compose creation | No duplicate Official poller; data retained |

`preview_fingerprint` at `:253` also makes teardown/status depend on manifests and all config files, and hashes unrelated engine/profile/environment inputs. Removing it avoids those accidental stop/status prerequisites. Missing actual build inputs still need honest Compose/build errors. Do not keep the fingerprint solely to preserve `test_missing_fingerprint_input_blocks_preparation`'s implementation assertion.

Two important reconciliation details require a deliberate design choice:

- `preview_override:288-292` writes random per-invocation `hako.attempt`. Once recreation is permitted, that label itself changes Compose desired configuration every start, forcing recreation even when settings/images are unchanged. Remove attempt from desired-state configuration and snapshot IDs before/after for cleanup, or explicitly choose/document unconditional startup recreation. Keeping a random label while claiming normal Compose reuse is incorrect.
- Compose's desired state can represent environment, image and mount-definition changes; same-path bind-mounted TOML contents are not a Compose configuration change. Startup's exact fresh-TOML guarantee therefore needs application restart/recreation if the process reads TOML only at startup. This is a limitation of merely removing `--no-recreate`, not a reason to restore a refusal fingerprint. An application-only explicit recreation can keep NapCat/local API on normal reconciliation; unconditional full recreation would also restart QQ gateway/API on every start. The parent owns the policy choice.

### Cleanup/readiness that must remain

- `preview_cleanup:512-533` captures partial startup IDs, emits bounded redacted diagnostics, and removes only resources created by the failed invocation, never volumes. Without attempt labels use a pre-start ID snapshot and exact ownership recheck; unchanged preexisting IDs must survive. Recreated predecessor resources cannot be restored by deleting their replacements. Decide explicitly whether a replacement for a preexisting service stays available for diagnostics instead of being removed; fixtures must prove whichever policy is approved.
- `preview_wait:475-495` currently returns immediately for reused groups. Remove reuse-dependent timeout behavior when startup has actually reconciled/restarted services; keep status immediately reporting not ready and the configured startup deadline.
- `preview_start_group:543-552` stages the local Bot API and waits before creating Telegram; preserve this even on partial groups and mode conversion. Fail before bot startup when API is unavailable.
- `preview_summary:583-586` and `preview_follow_logs:104` index every selected service. Status must explicitly reject missing selected IDs before readiness/summary/logs; otherwise an empty group can pass the wait loop and cause nounset or falsely ready output after incomplete-group gating is removed.
- `preview_follow_logs:109` rechecks ownership before readers and uses per-service pipes. Keep platform presentation, both OneBot streams, redaction, exit 130/143, and reader-only cleanup. Do not require preview-only labels to view a repository-owned ordinary runtime, but ordinary outbound bots lack preview markers; status readiness semantics for them need an honest unready/instrumentation distinction until explicit preview start reconciles them.

### Stop/down operational choices

Policy resolved by user while this research was running: keep only `down`, defined as selected-container stop + removal with persistent data retained. Remove public `stop`, with no compatibility alias, from root, preview and engines. The conventional alternatives below are historical tradeoff evidence, not the implementation plan.

Current inconsistency: ordinary stop/down retain container objects (`engines.sh:137`), while preview down aliases stop (`preview-runtime.sh:703`) and both stop plus remove (`:738-744`). Both retain bind data/named volumes; neither performs volume deletion.

Conventional consistent semantics would mean:

- stop: stop selected verified repository-owned runtime objects; keep objects for inspection/restart.
- down: stop and remove only selected verified objects; preserve all named volumes, binds, login, state and unselected services. Prefer scoped stop + rm without volume flags (or ID-based equivalents) over project-wide down. A targeted Compose down form varies by Compose capability; existing project supports legacy fallback.
- Existing `preview stop` followed by start no longer relies on removal, because normal start reconciliation handles stopped objects. Existing docs that promise removal through stop must change.
- Old Official hako was created with `docker run --rm` (`hako:129`): stop can automatically remove it. Document/cover this narrow runtime fact rather than inventing an object-retention compatibility mechanism. Down removal must handle absence after auto-remove honestly and idempotently.

Keeping current aliases would reduce naming change but require choosing the same behavior for both entries: either preview stop retains objects (changes existing preview tests) or ordinary stop removes objects (changes ordinary users' expectation). The user's later down-only choice supersedes both alternatives.

For the resolved down-only policy, internal `docker stop` / `compose stop` remain valid implementation operations; public parser/help/recovery strings must distinguish those from commands users can invoke. Root dispatch (`kisara.sh:74`), engines action matching (`engines.sh:137`), preview parser/normalization (`preview-runtime.sh:693`, `:703`), preview-console help, CLI routing tests and operation docs all currently expose stop. `deploy/onebot.sh:121` accepts down/stop independently: remove its stop alias or make the retained helper forward its approved operations to canonical engines so it cannot bypass shared preflight. Preserve its explicit QQ targeting, detached deploy and foreground dev behavior; avoid turning this into another parallel lifecycle refactor.

### Application recreation and auxiliary staging

The parent proposes explicit application recreation on startup to ensure mounted TOML is reloaded; this fits the source layout without fingerprints. `deploy/compose.yaml:79-80` and `:147-148` give OneBot applications a NapCat dependency. Telegram (`:172-212`) and Official (`:214-244`) have no declared depends_on; Telegram Local API is staged by script instead.

Treat `napcat`, `music` and `telegram-bot-api` as selected auxiliaries: reconcile their desired current mode/config/image through normal Compose up first, preserving Local API readiness before Telegram. Then create/recreate only selected `kisara`, `kisara-dev`, `telegram`, `official` applications with `--force-recreate --no-deps` after their selected prerequisites have actually started. Separating app argv from auxiliaries is essential: adding force-recreate to the existing combined `services` list would recreate NapCat as an explicitly selected service regardless of dependency flags. `--no-deps` makes the application stage's dependency behavior explicit and avoids re-starting/reconciling NapCat there; it cannot replace the auxiliary stage because OneBot needs NapCat active.

The local source proves why prerequisites must be staged and which service lists need splitting; it does not prove installed Compose-version flag behavior. Fixtures should assert auxiliary normal-up first, bounded local API readiness before app creation, application-only force-recreate/no-deps, fresh TOML-triggered application startup without fingerprint gating, and no rebuilding or restarting auxiliaries merely due to per-invocation random labels. If preview stages Local API once then also includes it in a broad auxiliary up, avoid redundant staged up or probes while retaining actual ordering.

Application force recreation is a user-requested explicit startup mutation. Status/build/down must not inherit it. Once force recreation is an explicit contract, application PID/ID changes on every start are expected, while unchanged auxiliary IDs remain stable; roundtrip mode switching should also reset preview readiness environment to ordinary desired config naturally.

Build while running changes image tags only. Running containers should retain their current image/settings until explicit up/start. Startup reconciliation may cause a selected service interruption; safe switching does not promise transactional rollback or zero downtime. Removing volumes, networking needed by unselected bots, QQ login paths or cache files is outside either semantics.

### Test fixtures and minimum meaningful coverage

`tests/unit/test_preview_lifecycle.py` is the strongest existing shared fixture but needs real behavior modeled:

- `FAKE_DOCKER:50-60` always overwrites selected containers on up, ignoring `--no-recreate`, existing ID, Compose diff and restarted objects. Add stable object IDs and desired image/config comparisons so unchanged up/restart and changed-image/config recreation are distinguishable. Model partial UP_FAIL creation with real IDs, then prove cleanup preserves preexisting IDs/unselected bots.
- `:67-70` fabricates every object's Compose project/service from state dictionary key, including legacy hako. Store real labels instead, honor every supplied filter, and model ordinary generated working_dir/config_files plus configured custom project. Add foreign same-project/service with another directory, matching basename/substrings, contradictory hako.repo, absent/malformed origin, duplicate candidates, spaces and multiple config files.
- `:53` assumes every Compose up has a second override file. Ordinary -> preview -> ordinary testing must parse the base-only and base+override forms. `:54` parses only custom labels; actual source labels must be generated for both forms. Add scoped Compose stop/rm/restart/ps/down handling; currently Compose branch exits without changing lifecycle state (`:61`).
- `:87-93` FOLLOW_FOREIGN fault injection assumes exactly three ownership fields. Adapt to the common identity format while retaining the before-reader recheck regression.
- `test_abnormal_existing_group_is_never_repaired:295` must split into foreign fail-before-effects, healthy/changed/partial explicit reconciliation and real unhealthy timeout cleanup.
- `test_build_prepares_without_start_and_refuses_live_group:437` must become build-existing-no-lifecycle-mutation, preserving the container snapshot, and then start applying the built image.
- Existing primary tests `:243`, local API `:604`, alias `:926` assert no up/probes on second start. Replace that assertion with desired unchanged object IDs/no unnecessary build or pull and permitted Compose up; retain data and readiness meaning.
- `test_local_api_source_change_requires_explicit_stop:638` and `:826` assert bespoke fingerprint behavior. Replace with local API explicit build/start application and fresh source/config behavior, without hashing unrelated inputs.
- `legacy_official:847`, legacy refusal `:855`, down `:866` and foreign/unverified `:888` can be extended for build-no-mutation and selected startup migration, retaining exact legacy boundaries.
- Streaming tests `:986`, `:1078`, `:1092` already cover reader ownership/redaction/signals; preserve them with common identity and prove status has no up/build/stop/rm effects for ordinary/partial/stopped groups.

`tests/unit/test_engine_deployment.py:17-43` is record-only and inspect always prints health, so it cannot currently validate new ownership or ordinary mutation. Reuse/extend the stateful lifecycle fixture for roundtrip conversion rather than copying a second full fake Docker. Keep its focused command-argument/mount/credential tests, updating copied helper inputs and fake inspection output only where necessary.

`tests/unit/test_kisara_cli.py:18-43` is inert root routing, appropriate to leave mostly unchanged. Update usage assertions for stop/down; no reason to change literal argv/offline behavior. `tests/unit/test_hako_deployment.py:16` proves credential isolation and binds; retain it if hako stays unchanged.

### Related specs and targeted updates

- `.trellis/spec/trellis-plus/cli-entrypoints.md:18-23`, `:39-47`, `:66-75`, `:108-113`: replace contradictory ordinary/preview down, fingerprint, exclusive preview ownership, legacy refusal and stopped ordinary refusal contracts with approved common identity/reconciliation/stop-down behavior.
- `.trellis/spec/trellis-plus/validation.md:135-140`, `:185-205`, `:294-305`: replace stop-before-build, matching-only reuse, incomplete/config-changed refusal and non-preview conversion rules; retain redaction/readiness/offline/data/fixtures-vs-real evidence requirements.
- `.trellis/spec/trellis-plus/development-principles.md:38-44` supports using existing execution paths and removing superseded prototype policy rather than adding a compatibility state machine.
- `docs/operations.md` is the existing operational home; update current command meanings and the simpler ordinary/preview switching examples there, not a new migration document or README expansion.

### External references and version evidence supplied by parent

The parent independently checked the official [Docker Compose up reference](https://docs.docker.com/reference/cli/docker/compose/up/) and reported that configuration/image changes recreate containers preserving mounted volumes, and both `--force-recreate` and `--no-deps` are documented. The parent also performed a version-only check yielding Compose v5.5.0, without a daemon lifecycle operation. Those checks support the planned staged auxiliary/application startup; this researcher did not independently browse or invoke Docker. Legacy Compose remains a supported code fallback and needs fixture coverage rather than assuming the local version covers it.

## Caveats / Not Found

- No live container operation or rendered Compose configuration was performed. This report is source/fixture evidence; real Docker reconciliation and private-account readiness remain separately authorized verification.
- Compose origin-label availability across plugin and legacy versions has not been checked against installed binaries or external docs. Reject unidentified origin rather than guessing; use the known exact preview label identity for evidenced already-owned previews.
- Same-repository ownership describes local lifecycle authority, not proof of account delivery or application feature health.
- A copied/renamed checkout changes repository-path identity; broad relocation adoption is not established by this task and must not be introduced as a generic compatibility fallback.
