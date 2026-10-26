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
The 2026-10-13 approved lifecycle task unifies ordinary and preview management,
retains down only, and removes bespoke fingerprint/reuse/rollback policy.
On 2026-10-22 the user approved live logs during preview startup, attached
viewing after readiness, and warning-plus-follow for unready existing bot groups.

## 2. Signatures

```text
./kisara.sh [--help]
./kisara.sh console
./kisara.sh test [pytest arguments...]
./kisara.sh preview [start|up|down|status|build] [target] [--verbose]
./kisara.sh up [engine-list]
./kisara.sh down|restart|logs|ps|status|pull [engine-list]
./kisara.sh down-all
```

Preview targets are supported engines or comma-separated Compose profiles;
omitting the target uses effective COMPOSE_PROFILES, defaulting to onebot only
when unset. Omitted preview action means start. Every application preview,
including Official-only, uses the Compose image path. Up means detached
build/recreate; down stops and removes selected objects with data retained.
Stop is removed, including preview/engines/onebot aliases. Down-all explicitly
selects whole-project removal after repository preflight.

The pure sourced deploy/lifecycle.sh API uses REPO_ROOT, COMPOSE_FILE,
COMPOSE_PROJECT_NAME and lifecycle_docker_command[] supplied by its caller:

```text
lifecycle_find service                     # stdout candidate ID(s), read-only
lifecycle_owned id service                 # 0 only for verified repository identity
lifecycle_targets                          # services[] -> lifecycle_services[]
lifecycle_preflight service...             # fill lifecycle_ids[service], or fail
lifecycle_remove service                   # stop/rm verified ID, no volume deletion
lifecycle_switch                           # remove verified opposing QQ / old Official
lifecycle_project_preflight                # fill IDs for all verified project objects
```

Callers declare associative lifecycle_ids before preflight. Sourcing performs
no runtime work or trap/option changes. Nonzero identity errors prevent effects;
removal is idempotent for absent objects, including auto-removed old Official.

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
Do not rewrite .env. Preserve readiness, local API staging and credential checks.
One shared deployment-layer identity/preflight manages both entry modes.

Compose candidates require exact project/service and repository provenance:
the canonical deployment working_dir and an exact base compose.yaml entry in
generated project.config_files. Paths with spaces are literal; names/substrings
never prove ownership. Existing exact hako.repo/scope=preview.sh/service labels
remain recognizable when source labels are absent. Contradictory explicit repo
or source labels reject rather than using another permissive fallback. Unknown,
foreign or duplicate candidates fail before modifying a valid selected peer.
Recheck identity before removal/log readers; down-all preflights every project
object. New Compose creation relies on generated source labels, without custom
preview-exclusive ownership/config/attempt labels.

The update sequence may use preview build then preview, with optional down.
Down removes selected repo-owned ordinary or preview containers, retaining
login/state/cache/media and volumes. Absent objects are a successful no-op.
Build explicitly rebuilds each selected application image from current Docker
context even when its tag exists; normal Docker caching remains valid. Build
never starts/stops/removes services and is allowed with running/partial groups.
Start reconciles selected auxiliaries normally, then force-recreates only selected
applications with no-deps to reload same-path TOML/current environment. Preview
uses prepared tags; ordinary up retains application builds. Keep engine-only
binds and local Bot API health-before-Telegram ordering. Missing resources
follow existing preparation/offline rules; do not force upgrades of auxiliary
images, base images or pinned packages.

Delete configuration fingerprint, existing-group build, incomplete/reuse and
competing-mode refusals. Explicit startup replaces the verified opposing QQ
application; build/status do not switch modes. QQ down removes both application
modes and NapCat; unselected Telegram/Official remain. Startup may interrupt
selected applications; unchanged auxiliaries are not forced to recreate.

Failed startup returns nonzero and retains objects for inspection/direct retry.
Preview captures bounded redacted diagnostics; ordinary deployment preserves
its existing foreground Compose output. No attempt-label or custom container rollback;
temporary logs/readers still clean up. Status never reconciles or repairs missing,
stopped, partial or uninstrumented services and never emits a false ready banner.

Preview start opens the existing sanitized last80/live bot stream as soon as
selected containers are started/collected, while bounded readiness checks run.
Print the existing ready summary only after true readiness, then keep following.
Ready `preview status` prints the summary and follows the same stream without
`--verbose`. Unready status warns and follows the existing owned selected bots
without a ready banner or automatic service changes; readiness alone must not
select a finite diagnostic dump instead of viewing.
Display napcat/kisara/kisara-dev as onebot, telegram as telegram and official
as official in both follow hints and `platform | log` prefixes. Keep both
OneBot streams and use distinct actual service identifiers for FIFO/readers,
ownership and cleanup. Redact credentials on each line before display
and avoid unbounded raw log storage. Match QR block symbols as complete symbols
(for example, `/▀|▄|█/d`), not a multibyte bracket class: under `LC_ALL=C` or
`POSIX`, `/[▀▄█]/d` also matches bytes in ordinary Chinese text and silently
drops receive/send lines. Preserve non-QR UTF-8 log lines in both byte and UTF-8
locales. Do not follow Music or local Bot API streams; include the owned NapCat gateway.
Both views preserve user/chat/account IDs, bot names and ordinary numbers; captured
failure/verbose diagnostics retain identifier redaction.
Ctrl+C/TERM exits 130/143 and reaps only this command's readers; containers and
data remain intact. Reader/sanitizer failures are explicit nonzero errors with
no raw fallback. Auxiliary-only status is finite, with a ready summary or actual
failure diagnostics. Missing/foreign groups still fail explicitly. Real stream
EOF ends viewing; no automatic reader reconnect is introduced. Reader setup
must run in the parent shell so cleanup owns all PIDs. Check reader failures
during startup readiness as well as during attached viewing; do not print ready
after a sanitizer/reader failure. INT/TERM while viewing skips the redundant bulk
diagnostic dump; genuine startup timeout/failure keeps bounded diagnostics,
including auxiliary information. Require mkfifo for start and status.

Recognize existing hako.scope=preview.sh identities. Selected Official down
can clean up the legacy same-repository/scope hako.service=bot container while
retaining storage, after inspecting its runtime engine as official; startup can
remove it before creating the Compose app, while build leaves it untouched.
Handle its auto-remove-on-stop without failing an absent subsequent rm.
An unknown/non-Official bot identity is not
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
| Legacy owned Official hako container | Verified down/start can remove it; build leaves it intact |
| Preview status/down | No automatic start/build/preparation |
| Removed stop command | Explicit input error, no forwarding or Docker mutation |
| Existing running group on build | Images rebuilt; container IDs/settings unchanged |
| Partial/stopped/config-changed group on start | Reconcile directly; fresh application startup |
| Failed startup | Nonzero, retained containers/logs, direct retry supported |
| Ready preview status with bot | Summary, last 80 lines, then continuous redacted logs |
| Bare/start preview while bots remain unready | Immediate safe bot logs during bounded checks; real summary after readiness, then continued following |
| Unready status with owned selected bots | Warning and continuous safe logs, no ready banner or runtime mutation |
| Mixed ready preview bots | Concurrent platform labels; NapCat and app both onebot with separate readers |
| Ctrl+C/TERM during start/status viewing | Exit 130/143; readers reaped, containers/data retained; no redundant diagnostic dump |
| Status reader/sanitizer failure | Explicit nonzero error, no raw fallback, readers reaped |
| Reader/sanitizer failure during startup readiness | Prompt nonzero failure and cleanup; no ready banner or masked timeout |
| Existing labeled preview | New command recognizes ownership and preserves data |
| Stopped ordinary same-repo container | Either entry can down/recreate; no manual rm/label changes |
| Foreign same-project/service collision | Refuse before effects, even when names match |
| Explicit QQ mode change | Verified opposing app removed; other platforms/data retained |
| Backend failure | Propagate nonzero status |
| Changed source/configuration | Build/start uses current source/settings without fingerprint refusal |

## 5. Good, base and bad cases

Good: kisara.sh test tests/unit/test_config_roots.py -q stays focused and offline;
preview start telegram overrides an inherited OneBot selection.
COMPOSE_PROFILES=onebot,telegram,official starts every listed bot regardless of
KISARA_ENGINE. Base: bare help does nothing to services and unset profiles
default to onebot.
Bare preview displays safe bot logs before readiness and remains attached after
its summary. Status of an unready owned bot warns and still displays fresh logs.
Bad: load .env for tests, guess ownership from names, or give root scripts
separate Docker lifecycle implementations. Existing onebot.sh forwards scoped
commands through engines instead of keeping another lifecycle implementation.
Ordinary QQ logs/ps/status inspect the verified logical group, including both
kisara and kisara-dev, so the OneBot forwarding entry can diagnose its active
mode. Exclude the legacy hako bot identity from Compose queries. Startup and
restart continue to use the requested application mode.

## 6. Tests required

Fake backends prove routes, unknown/help/no-effect paths, literal
arguments with spaces/metacharacters, offline isolation and child exit status.
Lifecycle fixtures execute canonical preview commands to prove target
precedence, single/mixed engine selection, status/down readiness, old ownership
and local API staging. Assert changed source/settings enter selected builds and
fresh app creation, build never mutates runtime, start avoids duplicate builds and
persistent data survives. Check Official-only image build and legacy/foreign
conflict boundaries. Stateful fake Docker models distinct IDs, generated source
labels, base-only/override Compose paths, desired image/config reconciliation,
app-only forced recreation and reused auxiliaries. Verify ordinary-preview-
ordinary roundtrip, foreign contradictions/duplicates/whole-project preflight,
failure retention/direct retry, absent down and QQ mode switching. Do not fake
ownership by assigning every object a project/service based on its dictionary
key. Run focused suites then full kisara.sh test regression;
cover delayed lines before EOF, redaction while attached, selected mixed bots,
stream failures and parent-only INT/TERM cleanup without lifecycle mutations;
also cover unready startup output before interrupt, readiness transition and
continued viewing, unready-status following, stream failure during readiness,
and cancellation without a bulk diagnostic dump. Preserve genuine timeout and
auxiliary diagnostic coverage;
include repeated delayed Chinese/mixed UTF-8 lines under C, POSIX and UTF-8
locales, with ASCII sentinels and actual QR symbols to distinguish dropped lines
from a stopped reader;
syntax-check changed Bash and use ShellCheck/shfmt only when available.

## 7. Wrong versus correct

Wrong: restore removed root scripts, create another runtime manager, or require
preview-only tags to remove a stopped ordinary same-repo container.
Correct: canonical entry calls hako/engines directly; retired files remain
absent; common source identity handles both modes and existing tags remain
recognizable without a manual migration.
Wrong: capture an unlimited raw follow stream and redact only after EOF, or
stop bot containers when an operator closes status. Correct: emit sanitized
lines promptly and clean up only invocation-owned readers.
Wrong: KISARA_ENGINE silently narrows COMPOSE_PROFILES, skip explicit builds
because a tag exists, or use onebot as the FIFO identity for two streams.
Correct: select profiles once, rebuild selected application tags on build, and
map distinct service identities only at log presentation.
Wrong: reuse a config fingerprint/attempt label to block updates or delete failed
startup containers automatically. Correct: explicit Compose startup applies
desired state, reports real readiness failures and retains objects for diagnosis.
Wrong: treat any visible log text or an application polling-ready INFO message
as proof that continuous preview following was reached. Correct: distinguish
`Recent bounded diagnostics` from `Following ... logs`, observe actual exit
status, and reproduce ready, starting and unready command states before closing
a streaming defect. A ready-only or finite-log fixture cannot prove startup
output visibility or sustained following.
