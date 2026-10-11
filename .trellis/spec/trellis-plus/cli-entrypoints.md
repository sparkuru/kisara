# Canonical kisara.sh command entrypoint

## 1. Scope and trigger

User approval on 2026-10-11 names kisara.sh as the documented command entry,
hako as the development executor, and deploy/engines.sh as online lifecycle
owner. Root scripts delegate; preview remains implemented by existing helpers.
The user subsequently approved deleting deploy.sh, dev.sh, start.sh and
preview.sh; only kisara.sh is the public entry, with no forwarding aliases/menu.
This consolidation does not authorize a deployment or account operation.
The 2026-10-11 preview-status-logs task additionally authorizes readiness followed
by continuous redacted logs from the selected current bots, stopped by Ctrl+C.

## 2. Signatures

```text
./kisara.sh [--help]
./kisara.sh console
./kisara.sh test [pytest arguments...]
./kisara.sh preview [start|stop|down|status|build] [target] [--verbose]
./kisara.sh up [engine-list]
./kisara.sh down|stop|restart|logs|ps|status|pull [engine-list]
./kisara.sh down-all
```

Preview targets are supported engines or comma-separated Compose profiles;
omitting the target retains configured/default selection. Omitted preview
action means start. Explicit
single official preview keeps its existing owned-hako path; mixed profiles use
Compose. Up means detached build/recreate; down means targeted stop with data
retained. Down-all explicitly selects whole-project shutdown.

## 3. Contracts

No-arg/root help shows usage without dotenv or Docker effects. Offline console
and tests clear inherited HAKO_SERVICE, use hako, and never load account secrets.
Test arguments pass unchanged to pytest; pyproject testpaths supplies the full
default. Do not prepend all tests when an explicit file is requested.

Preview's owning parser determines explicit target precedence over inherited
KISARA_ENGINE/COMPOSE_PROFILES and dotenv. With no target, original selection
rules remain. Do not rewrite .env. Preserve readiness, local API staging,
fingerprint behavior, credential checks and selected-container cleanup.

Ready `preview status` shows the existing summary, then follows the last 80
lines and new logs from selected owned application bots, without `--verbose`.
Use service labels for mixed bots, redact credentials on each line before display
and avoid unbounded raw log storage. Do not follow auxiliary services on successful status.
Status preserves user/chat/account IDs, bot names and ordinary numbers; captured
failure/verbose diagnostics retain identifier redaction.
Ctrl+C/TERM exits 130/143 and reaps only this command's readers; containers and
data remain intact. Reader/sanitizer failures are explicit nonzero errors with
no raw fallback. Auxiliary-only status ends after its summary; absent/unready
status keeps existing nonzero reporting and bounded failure diagnostics.

Keep existing hako.scope=preview.sh labels and filters, including official hako
previews. The canonical executable name is not a reason to orphan owned
containers. Runtime help/recovery examples use kisara.sh; historical ownership
and validation records retain their actual names.

The four former root scripts are removed. All executable fixtures/callers use
kisara.sh directly; selection uses explicit arguments or existing environment
rules. Do not restore forwarding aliases or interactive selection glue. Hako
stays available for arbitrary development commands and dependency installation.

Use quoted literal argv, resolve scripts from their own location, preserve
child exit status, and keep errors/help on stderr. Semantic colors honor
NO_COLOR and non-TTY output. No broad aliases, alternative runtime or new CLI
dependency is introduced.

## 4. Validation and error matrix

| Input/state | Required result |
| --- | --- |
| Root/noargs/help | Usage, no config/Docker invocation |
| Invalid command/arity/target | Error before backend operations |
| Offline command with inherited bot mode | No dotenv/credential loading |
| Test with file path/options | Exact focused pytest argv |
| Explicit preview target conflicts with env | Argument target wins; file unchanged |
| Preview status/stop | No automatic start/build/preparation |
| Ready preview status with bot | Summary, last 80 lines, then continuous redacted logs |
| Mixed ready preview bots | Concurrent streams labeled by selected owned service |
| Ctrl+C/TERM during status | Exit 130/143; readers reaped, containers/data retained |
| Status reader/sanitizer failure | Explicit nonzero error, no raw fallback, readers reaped |
| Existing labeled preview | New command recognizes ownership and preserves data |
| Stopped non-preview deployment container | Refuse takeover; explicit selected-container removal needed for a separately authorized conversion |
| Backend failure | Propagate nonzero status |
| Changed source/configuration mounts | Existing targeted recreation rules remain |

## 5. Good, base and bad cases

Good: kisara.sh test tests/unit/test_config_roots.py -q stays focused and offline;
preview start telegram overrides an inherited OneBot selection. Base: bare help
does nothing to services and preview start without a target retains env choice.
Ready preview status keeps displaying new safe bot logs until Ctrl+C.
Bad: load .env for tests, change persistent preview labels, or give root scripts
separate Docker lifecycle implementations.

## 6. Tests required

Fake backends prove routes, unknown/help/no-effect paths, literal
arguments with spaces/metacharacters, offline isolation and child exit status.
Lifecycle fixtures execute canonical preview commands to prove target
precedence, single/mixed engine selection, status/stop readiness, old ownership
and local API staging. Run focused suites then full kisara.sh test regression;
cover delayed lines before EOF, redaction while attached, selected mixed bots,
stream failures and parent-only INT/TERM cleanup without lifecycle mutations;
syntax-check changed Bash and use ShellCheck/shfmt only when available.

## 7. Wrong versus correct

Wrong: restore removed wrapper scripts, make kisara.sh depend on them, or rename
ownership tags while a preview remains deployed.
Correct: canonical entry calls hako/engines directly; retired files remain
absent and preview's established ownership identity stays stable.
Wrong: capture an unlimited raw follow stream and redact only after EOF, or
stop bot containers when an operator closes status. Correct: emit sanitized
lines promptly and clean up only invocation-owned readers.
