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
The 2026-10-12 approved follow-up selects all COMPOSE_PROFILES bots, rebuilds
selected application images explicitly and displays platform log names.

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
omitting the target uses effective COMPOSE_PROFILES, defaulting to onebot only
when unset. Omitted preview action means start. Every application preview,
including Official-only, uses the Compose image path. Up means detached
build/recreate; down means targeted stop with data
retained. Down-all explicitly selects whole-project shutdown.

## 3. Contracts

No-arg/root help shows usage without dotenv or Docker effects. Offline console
and tests clear inherited HAKO_SERVICE, use hako, and never load account secrets.
Test arguments pass unchanged to pytest; pyproject testpaths supplies the full
default. Do not prepend all tests when an explicit file is requested.

Preview's owning parser gives an explicit target precedence over defaults,
including invalid defaults. Otherwise use COMPOSE_PROFILES with inherited
same-key environment precedence over dotenv, including explicit empty values.
KISARA_ENGINE selects the application's runtime engine, never preview profiles.
Reject empty/unknown/duplicate profiles and conflicting onebot/onebot-dev.
Do not rewrite .env. Preserve readiness, local API staging,
fingerprint behavior, credential checks and selected-container cleanup.

The update sequence is preview down, preview build, then preview. Down removes
only selected owned containers, retaining login/state/cache/media and volumes.
Build explicitly rebuilds each selected application image from current Docker
context even when its tag exists; normal Docker caching remains valid. Build
never starts services. Start uses the prepared tag, loads current runtime
settings at creation and retains engine-only config binds. Missing resources
follow existing preparation/offline rules; do not force upgrades of auxiliary
images, base images or pinned packages.

Ready `preview status` shows the existing summary, then follows the last 80
lines and new logs from selected owned application bots, without `--verbose`.
Display napcat/kisara/kisara-dev as onebot, telegram as telegram and official
as official in both follow hints and `platform | log` prefixes. Keep both
OneBot streams and use distinct actual service identifiers for FIFO/readers,
ownership and cleanup. Redact credentials on each line before display
and avoid unbounded raw log storage. Do not follow auxiliary services on successful status.
Status preserves user/chat/account IDs, bot names and ordinary numbers; captured
failure/verbose diagnostics retain identifier redaction.
Ctrl+C/TERM exits 130/143 and reaps only this command's readers; containers and
data remain intact. Reader/sanitizer failures are explicit nonzero errors with
no raw fallback. Auxiliary-only status ends after its summary; absent/unready
status keeps existing nonzero reporting and bounded failure diagnostics.

Keep existing hako.scope=preview.sh labels and filters. Selected Official down
can clean up the legacy same-repository/scope hako.service=bot container while
retaining storage, after inspecting its runtime engine as official; start/build
must reject that legacy conflict. An unknown/non-Official bot identity is not
eligible for this cleanup. Never adopt
foreign containers. The canonical executable name is not a reason to orphan owned
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
| No target, conflicting KISARA_ENGINE | Effective COMPOSE_PROFILES selects all listed services |
| No target, profiles unset / empty / invalid | onebot default / explicit error / explicit error |
| down then build then start, existing image tags | Data retained; each selected bot image rebuilt; start uses tags and current settings |
| Official-only | Compose build/start with official extra and existing config/state mounts |
| Legacy owned Official hako container | Selected down can remove it; start/build refuse duplicate instance |
| Preview status/stop | No automatic start/build/preparation |
| Ready preview status with bot | Summary, last 80 lines, then continuous redacted logs |
| Mixed ready preview bots | Concurrent platform labels; NapCat and app both onebot with separate readers |
| Ctrl+C/TERM during status | Exit 130/143; readers reaped, containers/data retained |
| Status reader/sanitizer failure | Explicit nonzero error, no raw fallback, readers reaped |
| Existing labeled preview | New command recognizes ownership and preserves data |
| Stopped non-preview deployment container | Refuse takeover; explicit selected-container removal needed for a separately authorized conversion |
| Backend failure | Propagate nonzero status |
| Changed source/configuration | Explicit down/build/start uses current source and runtime settings |

## 5. Good, base and bad cases

Good: kisara.sh test tests/unit/test_config_roots.py -q stays focused and offline;
preview start telegram overrides an inherited OneBot selection.
COMPOSE_PROFILES=onebot,telegram,official starts every listed bot regardless of
KISARA_ENGINE. Base: bare help does nothing to services and unset profiles
default to onebot.
Ready preview status keeps displaying new safe bot logs until Ctrl+C.
Bad: load .env for tests, change persistent preview labels, or give root scripts
separate Docker lifecycle implementations.

## 6. Tests required

Fake backends prove routes, unknown/help/no-effect paths, literal
arguments with spaces/metacharacters, offline isolation and child exit status.
Lifecycle fixtures execute canonical preview commands to prove target
precedence, single/mixed engine selection, status/stop readiness, old ownership
and local API staging. Assert changed source/settings enter selected builds and
new creation after down, build never starts, start avoids duplicate builds and
persistent data survives. Check Official-only image build and legacy/foreign
conflict boundaries. Run focused suites then full kisara.sh test regression;
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
Wrong: KISARA_ENGINE silently narrows COMPOSE_PROFILES, skip explicit builds
because a tag exists, or use onebot as the FIFO identity for two streams.
Correct: select profiles once, rebuild selected application tags on build, and
map distinct service identities only at log presentation.
