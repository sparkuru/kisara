# Approved follow-up: unified kisara.sh entrypoint

On 2026-10-11 the user approved the proposed consolidated command interface,
naming `./kisara.sh`, `hako`, and `deploy/engines.sh`. Preserve earlier TgSetu
and config-root changes. Scope is implementation/checking, not service/account
operations, deployment, commits or archival.

## Gap and public contract

Four top-level user scripts duplicate entry decisions and have ambiguous names.
Add one documented public dispatcher; retain their previously proposed temporary
compatibility forwarding interfaces. Internal responsibilities stay separate:
hako runs ephemeral development commands, engines owns online lifecycle, and
existing preview helpers own readiness/labels/cleanup.

- `./kisara.sh` and `--help`: show help, do not load .env or invoke Docker.
- `console`: offline `hako python -m kisara.bot.console`; reject surplus args.
- `test [pytest args...]`: offline `hako python -m pytest` with forwarded argv;
  pyproject testpaths defaults to the full tests directory. Explicit test paths
  must stay focused, not also prepend the entire suite.
- `preview [start|stop|down|status|build] [engine-or-profile-list] [--verbose]`:
  defaults start and delegates `engines.sh preview`. Extend preview's own parser
  to accept an explicit target that wins over inherited env/dotenv without
  mutating the dotenv file. Omitted target preserves existing engine/profile
  selection. Existing single official preview remains the owned hako path;
  mixed profile selection retains Compose semantics.
- `up [engine-list]`: detached build/recreate, maps to engines `deploy`.
- `down|stop|restart|logs|ps|status|pull [engine-list]`: existing targeted
  backend actions; `down-all` remains explicit whole-project shutdown.
- CLI parsing/help/errors use existing Bash/semantic terminal conventions,
  quote argv, support cwd/path spaces and propagate child exit statuses.
- Offline console/tests clear HAKO_SERVICE even when inherited bot mode is set,
  never load .env or send credentials to test/console containers.

## Compatibility and preserved boundaries

Deploy wrapper retains default/up/start/action conventions through kisara.sh.
Dev wrapper retains no-arg console, --test focused offline-command suite, --all
full-suite behavior. Preview wrapper forwards to kisara.sh preview. Start
retains explicit/env/profile/default/interactive engine selection as necessary
compatibility glue and calls kisara.sh preview start. Do not create another
service orchestration path, lifecycle implementation or permanent alias registry.

Keep existing `hako.scope=preview.sh` labels and cleanup filters so new commands
can still inspect/stop already owned previews. Preserve readiness/fingerprint,
cache/state/network/authorization/targeted-stop/local-API staging behavior.
Update user-facing runtime guidance/help to kisara.sh; do not rename stored
ownership identities. No README edits (human-owned); current operations/specs
and hako usage comments receive canonical commands. Historical task/archive
records remain historical.

## Ownership and validation

- CLI implementer: new kisara.sh; compatibility deploy/dev/start/preview scripts;
  hako usage comments; new CLI routing tests and affected engine-deployment
  fixture setup. No production preview helper edits.
- Preview implementer: preview-runtime/console parser and user guidance;
  preview-lifecycle fixtures/tests covering public kisara.sh routes.
- Root: task/spec/docs/mainline/session and final full regression.
- Reviewer: independent cross-layer checks and necessary scoped local fixes.

Workers share a workspace; preserve earlier work, coordinate argv contract and
fixture ownership, do not spawn nested agents. First run focused fake backend
tests, then full Docker regression. Verify help/invalid inputs no operations,
full/focused pytest arguments and offline isolation, explicit target precedence,
old aliases, status/stop no startup, local API staging, ownership labels,
literal argv and exit status. Syntax-check changed Bash; lint/format tools only
when available, no new toolchain or live accounts/services.

## Latest approved revision: retire compatibility scripts

The user now explicitly approves deleting the four root deploy.sh, dev.sh,
start.sh and preview.sh files. This supersedes their temporary forwarding/UI
contracts above. Keep kisara.sh, hako and deploy/engines.sh; do not add aliases
or another interactive selection interface. Migrate executable test fixtures
and callers to the canonical entry, remove obsolete forwarding/menu tests,
and retain equivalent backend targeting/credential/selection coverage where
the canonical interface provides it. Existing preview ownership labels are
stored runtime identities and remain preview.sh even after file deletion.
Update current docs/specs/.env.example and task state; retain historical
executed validation records and prior decision history.

Boundary: delete exactly those four versioned root scripts; edit the three
CLI/deployment/preview unit suites for fixtures/callers, current guidance and
task records. No engine lifecycle redesign, service takeover, automatic stop,
container recreation, account operation, commit or archive is authorized.
The separately reported non-preview NapCat conflict is investigated read-only;
the ownership check remains enforced. Focused tests and a final canonical full
gate must pass with the scripts absent.

## Subsequent operational approval: OneBot preview conversion

After reporting the non-preview NapCat conflict, the user selected removing
the stopped QQ deployment containers and starting the canonical preview while
retaining mounted data and leaving Telegram alone. Read-only selection checks
show KISARA_ENGINE=onebot and configured profiles onebot,telegram: the effective
bare preview target is onebot. This authorizes conversion/startup for exactly
the QQ group. It supersedes the no-service-operation boundary for that specific
operation only; Telegram account/deployment acceptance and commit/archive stay
outside scope. Container removal must verify stopped state and project/service
labels first, use no force/volume-removal flag, and retain bind paths/state
volumes. Record actual startup/readiness outcome separately from mock tests.

## Runtime-discovered readiness correction

Two bounded startup attempts failed and cleaned only their new QQ containers.
The immediate defect is NapCat readiness and listener inspection executing
node, which is absent from the actual image. Read-only inspection confirms
python3/curl/bash/awk available, WebUI enabled on port6099/host::, IPv4 HTTP
root and /webui both 200, and TCP3001 available; the app WebSocket had connected.
This does not require new login, data reset or weakening readiness.

Smallest fix: extend the existing dependency-free preview-probe.py with a
bounded NapCat HTTP+TCP predicate and reuse its /proc listener decoder; execute
that helper through python3 -c in NapCat, keeping music's existing Node path.
Local HTTP must bypass inherited proxies. Preserve bot PID/marker checks,
required sockets, actual mappings, ownership/cleanup and secret-free results.
Accept the helper's compressed IPv6 listener forms in summary classification.
Files: preview-probe.py, preview-runtime.sh, readiness/lifecycle unit suites;
root owns docs/spec/records. Add meaningful real-helper fixtures for successful
HTTP+TCP, HTTP/TCP failure, proxies, listener addresses, and canonical dispatch
without Node. Independent review, focused/full tests and actual restart/status
must follow. No image dependency installation or broad runtime redesign.

Final direct-response evidence: container Python is 3.10.12; HTTPConnection
returns301 for / and /webui, and200 for /webui/ and /webui/index.html. The earlier
urllib200 observations followed redirects. Use the canonical /webui/ path in
the direct stdlib predicate; keep strict2xx, local proxy bypass and TCP3001.
Add a real regression with root301 and /webui/200. Existing browser root URLs
remain valid through browser redirects; no broad summary-path change is needed.
