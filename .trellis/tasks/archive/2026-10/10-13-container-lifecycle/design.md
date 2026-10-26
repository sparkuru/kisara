# Repository-owned container lifecycle

## Boundary and behavior gap

Ordinary deploy and preview select the same Compose project/services but use
different ownership and recovery rules. Fix this at deploy/engines.sh and its
sourced helpers. Do not add another command runner, user force option, persistent
state cache or lifecycle lock. Keep kisara.sh as the public entry and hako as the
offline executor. The existing deploy/onebot.sh becomes a thin scoped forwarding
entry instead of keeping a third lifecycle implementation.

One coherent task owns lookup, preflight, down, startup/switching and tests.
Independent child deliverables would split the same ownership contract.

## Commands and selection

- ./kisara.sh preview [start|up|down|status|build] [profiles] [--verbose]
- ./kisara.sh up|down|restart|logs|ps|status|pull [profiles]
- ./kisara.sh down-all
- Existing onebot.sh up/start/dev/deploy/down/logs/ps/status/pull keep their scoped intent by
  forwarding into engines.sh. Remove stop aliases throughout these online APIs.

Down stops and removes only the selected repository-owned container objects;
never delete volumes, binds, login/state/cache/media or other platforms.
Down with an absent selected service is successful. OneBot selection denotes
the shared QQ group: down covers its two application modes and NapCat while
retaining Telegram/Official. Startup removes the verified opposing QQ application
before starting the requested mode. Build/status do not switch QQ modes.

Effective COMPOSE_PROFILES, unset-only onebot default, literal dotenv parsing,
same-key environment presence and explicit-target precedence remain. Invalid
profiles/duplicate modes fail before effects. Preserve existing foreground versus
detached intent. Ordinary QQ logs/ps/status keep the former OneBot diagnostic
scope across both verified application modes, excluding the legacy hako bot from
Compose queries; startup/restart still target the requested mode. Preserve
local Docker/legacy Compose compatibility.

## Shared ownership and preflight

Add one small pure sourced deploy lifecycle helper used by engines and preview:
candidate lookup, source identity inspection, selected/project-wide preflight,
scoped removal and verified opposing-mode handling. Use the caller's effective
Docker argv; do not rediscover endpoints or read credential values.

For Compose candidates, require exact effective project and actual service.
Ordinary identity additionally requires the canonical repository deployment
working directory and an exact base COMPOSE_FILE entry in generated
com.docker.compose.project.config_files. Parse fields literally, including paths
with spaces; never authorize by a basename, substring or container name.

Retain exact existing hako.repo/scope=preview.sh/service ownership for current
previews, including those without generated origin evidence. If origin labels or
explicit repo labels contradict this checkout, reject rather than falling back.
Missing/unverifiable identity fails actionably; no generic checkout-relocation
adoption or manually relabeling a foreign object.

The evidenced old hako.service=bot Official preview remains a narrow case:
exact repo/scope/service and an inspect check for KISARA_ENGINE=official. Selected
down or startup can remove it with data retained; build leaves it untouched.
Handle auto-remove-on-stop by checking exact ID existence before subsequent rm.
Do not expand this to arbitrary detached hako/manual runtimes.

Inspect all affected candidates before any mutation, including the opposing QQ
mode and all project objects for explicit down-all. Recheck ownership at removal
and before log readers. Foreign/malformed/contradictory/duplicate candidates fail
before modifying a valid peer. Read-only status/log/ps cannot expose foreign logs.

## Build and startup

Delete preview fingerprint/config refusal, complete-group/reuse refusal,
build-existing refusal and --no-recreate startup. New Compose creation relies
on standard generated source identity, removing bespoke hako.config/attempt and
preview-exclusive identity-label generation. Existing stored repo/scope/service
labels remain recognizable until ordinary recreation replaces the objects; no
manual label update or renamed legacy scope. NapCat/music need no preview-only
override labels, so ordinary/preview entry does not itself alter their desired
configuration. Real image/env/config changes can still recreate auxiliaries.

Build explicitly rebuilds selected app image tags with current context, even
with running/stopped/partial selected containers. It never stops/removes/starts
them, switches modes or migrates legacy runtimes. Missing auxiliaries and offline
mode follow established preparation rules; no upgrades or global no-cache.

Startup applies desired state through Compose. Stage selected auxiliaries first
using normal up --no-build reconciliation. Local Bot API must be healthy before
Telegram starts. Then recreate only selected application bots with
up --force-recreate --no-deps so startup-only same-path TOML is reloaded. Preview
uses prepared image tags; ordinary up retains its explicit application build.
The helper may factor stages, but does not introduce a generic orchestration
framework. No --remove-orphans, --renew-anon-volumes or volume removal flags.

This intentionally restarts selected applications on explicit startup, while
unchanged NapCat/API/music remain. No zero-downtime or transactional rollback
claim. Docker's official up reference confirms image/config recreation preserves
mounted volumes and documents --force-recreate/--no-deps:
https://docs.docker.com/reference/cli/docker/compose/up/

## Failure, readiness and logs

Follow normal Compose diagnostic behavior: failed startup leaves selected
created/recreated containers available for inspection, returns a nonzero status
and preview emits bounded credential-redacted diagnostics. Ordinary deployment
preserves its existing foreground Compose output; no new output-capture framework
or claim of sanitizing all build/foreground output is introduced. The next start reconciles or
recreates applications directly; down is explicit removal. Remove the custom
attempt-label/container rollback path instead of adding ID snapshot state.

Keep temporary-log cleanup and status-reader cleanup. Ctrl+C/TERM during status
only reaps invocation readers, never containers. Ordinary foreground Compose
signal semantics remain its own existing behavior.

Startup waits within the configured readiness deadline after actual staging,
without a reuse shortcut. Status checks selected existence/readiness immediately,
reports partial/stopped/uninstrumented groups honestly and never repairs them.
An ordinary outbound runtime lacking preview readiness instrumentation is not
advertised ready solely from its running state; explicit preview start creates
the instrumented application through the common lifecycle.

Keep summary facts, platform log labels, both OneBot streams, tail80, incremental
redaction, explicit stream failures and reader-only signal exit codes.

## Files and checks

Implementation: kisara.sh usage/routing, deploy/engines.sh, existing preview
helpers, scoped onebot forwarder and a single shared helper. Update existing
preview/CLI/engine/local API fixtures and docs/operations.md. Main updates
cli-entrypoints/validation/engine-config specs and task/mainline/journal.

Use one improved stateful fake Docker: real source labels, distinct stable IDs,
ordinary base-only versus preview overrides, image/config reconciliation,
application force recreation and reused auxiliaries. Do not duplicate another
complete Docker model or assert freshness solely from fabricated snapshots.

Cover ordinary-preview-ordinary roundtrip, exited ordinary Telegram down, build
with running containers, fresh environment/TOML, partial groups, QQ switching,
foreign collisions/contradictions/duplicates, down-all scope and failure retry.
Retain every log/redaction/signal/offline/local API/data-preservation assertion.
Fixtures prove arguments and lifecycle model, not private live account readiness.

No actual bot operation or private config rewrite accompanies code validation.
Rollback source only after review; persistent data and original work stay intact.
