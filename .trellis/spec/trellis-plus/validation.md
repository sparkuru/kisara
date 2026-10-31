# Validation and Docker Development Profile

- ownership: project-shared
- source: project-authored
- evidence: `pyproject.toml`, `hako`, `kisara.sh`, `tests/`, `docs/operations.md`

## Before development

Reuse executable `hako` and its `python:3.12-slim` runtime. The repository is
mounted at `/app` with the host UID/GID; container HOME, user packages, and pip
cache live in ignored `.devhome/`. One-off tool commands do not load `.env`;
credential-loading mode is explicitly `HAKO_SERVICE=bot`. Do not enable it for
offline checks. One-off commands publish no host ports.

If the wrapper is missing or unusable for a changed toolchain, apply
`dev-it-in-docker` at the bootstrap/before-dev checkpoint. Preserve this
project's service separation: kisara.sh console/test are offline; preview and
up/down manage online services through the existing engines backend. Hako stays
the development executor, not another lifecycle. Old root scripts are removed.
See [CLI contracts](cli-entrypoints.md).

Codex adaptation uses narrow `./hako` or `./kisara.sh test` prefix approval
when supported. It does not grant raw Docker access or replace managed
permissions. No `.codex/rules/default.rules`, hook, sandbox relaxation, or
second policy copy is installed by this setup. If the surface cannot approve
the wrapper, report the missing execution permission and preserve the boundary.
This follows the maintained `dev-it-in-docker` Codex procedure where the
Trellis Plus bootstrap reference's static rules-file suggestion differs.

## Commands and applicability

Run commands from the repository root. If development dependencies are absent:

```bash
./hako python -m pip install --user -e ".[dev]"
```

Use `.[dev,official]` only when official SDK work requires it.
Use `.[dev,telegram]` for Telegram adapter work; the Telegram extra requires
Python 3.10+ while the existing wrapper runs 3.12.

| Change | Automated checks |
| --- | --- |
| Documentation/spec only | Relative links and source claims; `git diff --check`; check new untracked files explicitly |
| Local commands/console | `./kisara.sh test tests/unit/test_offline_commands.py` or focused `./hako python -m pytest tests/unit/test_offline_commands.py` |
| Configuration | `./hako python -m pytest tests/unit/test_settings.py` |
| Canonical CLI and engine/preview routes | `./kisara.sh test tests/unit/test_kisara_cli.py tests/unit/test_engine_deployment.py tests/unit/test_preview_lifecycle.py` |
| Routing | `./hako python -m pytest tests/unit/test_dispatcher.py` |
| Setu state/media behavior | `./hako python -m pytest tests/unit/test_setu.py` |
| News/cache/delivery | `./hako python -m pytest tests/unit/test_daily_news.py tests/unit/test_news_delivery.py` |
| Utility contracts | `./hako python -m pytest tests/unit/test_utils.py` plus consuming feature tests |
| OneBot adapter/protocol | `./hako python -m pytest tests/unit/test_onebot_adapter.py tests/integration/test_onebot_protocol.py` |
| Telegram adapter/scheduler/protocol | `./hako python -m pytest tests/unit/test_telegram_adapter.py tests/unit/test_telegram_news.py tests/integration/test_telegram_protocol.py` |
| TgSetu archive/config/local server | `./hako python -m pytest tests/unit/test_tgsetu.py tests/unit/test_tgsetu_config.py tests/unit/test_tgsetu_files.py tests/unit/test_telegram_settings.py tests/unit/test_telegram_bot_api_deployment.py` plus Telegram adapter/protocol and deployment/preview suites |
| Cross-layer, adapter, schema, or deployment changes | Relevant focused checks followed by `./kisara.sh test` |

Additional feature suites live in `tests/unit/`; choose the matching existing
suite. Mock external providers and simulate OneBot protocol interactions for
repeatable checks without QQ credentials. No CI workflow, configured linter,
formatter, or type-check command was found; do not claim those gates passed
or silently add a new toolchain. The manifest declares Python >=3.8 while the
wrapper exercises Python 3.12; that runtime alone is not compatibility proof
for every declared Python version.

For QQ login PNG work, also execute the injected reader in the actual cached
NapCat image: its Python3.10 timestamp parser differs from hako Python3.12.
Use synthetic PNG data and nine-digit Docker RFC3339 timestamps in an isolated
offline, read-only container with no account mounts. A real-image geometry
probe or successful decoder check does not exercise the timestamp reader.

For future Python/shell changes, load the available `code-python` or
`code-shellscript` skill respectively. Shell validation should match the actual
interpreter; run syntax checks and ShellCheck/shfmt when available and relevant.
Deployment checks must not print rendered secret-bearing Compose configuration.

## Human-only validation and submit-ready gate

Before a proposed commit/archive, compare changed acceptance criteria, the
diff, and executed checks. Record one classification:

- `human-not-needed`: documentation/mechanical changes or focused tests fully
  cover the changed behavior and no meaningful judgment remains.
- `human-optional`: checks passed; a narrow, low-risk user check may add signal.
  State explicitly whether proceeding depends on the reply.
- `human-required`: a material check could not run or acceptance needs an
  actual QQ account, private credentials/provider, hardware, or product
  decision; also evaluate authorization, security, schema migration, deletion,
  deployment, and permissions changes before committing.

Respect explicit existing user authorization. When human input is required,
finish runnable preparation first and request only the concrete remaining
decision/check before committing. Report implementation, command/results,
exact user steps, expected outcome, and useful pass/fail or sanitized logs.
Do not ask for a generic smoke test.

Live QQ acceptance can require authorized private `/ping`, rejection of
unauthorized senders/groups, idle-time recovery, separate Kisara/NapCat restart,
temporary disconnect recovery without duplicate replies, login-expiry handling,
and a log privacy check. Feature-specific sending/recall/attachment behavior
and configured external provider availability also need live evidence when
changed. Do not start or stop live services to validate a docs-only setup.
Synthetic protocol tests do not establish real account capability or sustained
service reliability.

Telegram acceptance needs allowed private/group command delivery, another bot's
addressing ignored, denied users/groups without effects, document readability and
caption attribution, a reachable configured music provider, and allowed private/
group scheduled delivery. Verify confirmed sends survive restart without replay
and targeted Telegram lifecycle operations leave other engines running. Use the
task's prepared live-validation steps; do not inject production send failures
when deterministic state/protocol tests establish the recovery contract.

## Preview lifecycle profile

The 2026-10-11 user-approved interface routes kisara.sh preview through
`deploy/engines.sh` and project-owned sourced helpers
`deploy/dotenv.sh`, `deploy/lifecycle.sh`, `deploy/preview-console.sh`,
`deploy/preview-runtime.sh`. The 2026-10-13 approved follow-up shares repository
identity/preflight/removal between ordinary deployment and preview; onebot.sh
forwards scoped operations to engines. Console/test remain offline. Existing
hako.scope=preview.sh identities remain recognizable; new Compose objects use
generated repository source labels, without preview-exclusive/config/attempt
labels. Public stop aliases are removed; down stops/removes objects, keeping data.

### First setup and commands

Host requirements: Bash 4.4+, Docker with a reachable daemon, Compose plugin or
legacy docker-compose, timeout, sed, mktemp, mkfifo, flock, stty, cat and id.
Local wildcard publishing additionally requires ip. No host application Python
or global SDK/browser installation is required. Python probes/install helpers
run in the existing Python 3.12 images/wrapper.

From the repository root, only when .env is absent, run
`cp .env.example .env`, then edit the selected engine's actual credentials and
access list. OneBot needs ONEBOT_ACCESS_TOKEN/ONEBOT_ALLOWED_USERS and appropriate
NAPCAT_WEBUI_TOKEN plus initial NapCat login. Telegram needs TELEGRAM_BOT_TOKEN
and TELEGRAM_ALLOWED_USERS. Official needs OFFICIAL_APP_ID/SECRET and its access
list. Feature TOML retains its established engine-specific path and precedence.
Never copy the example over an existing private file.

```bash
./kisara.sh preview                 # prepare missing resources, refresh selected apps
./kisara.sh preview start --verbose # captured redacted details after each step
./kisara.sh preview status          # readiness, then continuous redacted bot logs
./kisara.sh preview build           # explicit rebuild; running containers unchanged
./kisara.sh preview down            # selected repository objects removed; data retained
./kisara.sh preview --help          # no dotenv loading or Docker operations
```

First preparation may download images and pinned packages and take several
minutes; readiness also depends on actual account/login/network prerequisites.
If login prevents readiness, use the explicit initial-login/retry guidance from
script diagnostics/help; no failed group is advertised ready. Startup never
runs tests. No live account message delivery is established by runtime readiness.

### Configuration and preparation

Primary inputs are root .env plus inherited environment overrides by presence,
including explicit empty values. The dotenv loader accepts KEY=value and quoted
single-line literal values/comments; it does not execute shell or interpolate
shell expressions, and rejects duplicates/unsupported syntax/control-variable
names. Do not rely on shell expansion to generate credentials or Docker inputs.
NAPCAT_UID/GID file inputs remain effective; host defaults use separate fallback
names rather than exporting over user inputs. Application TOML still wins over
engine runtime environment according to configuration-storage.md.

Optional consumed keys in .env.example:

| Key | Purpose/default |
| --- | --- |
| KISARA_PREVIEW_OFFLINE | false; true forbids automatic pull/build/install |
| KISARA_PREVIEW_TIMEOUT | positive seconds, default 90, bounds group readiness |
| KISARA_PREVIEW_IMAGE_PREFIX | empty derives the Compose project's preview image namespace |
| KISARA_PREVIEW_HOST_ADDRESSES | empty; explicit daemon-host address CSV when remote wildcard publishing requires it |

No-target preview actions share effective COMPOSE_PROFILES selection, defaulting
to onebot only when unset. Same-key inherited environment overrides dotenv;
explicit targets override that default list. KISARA_ENGINE is not a preview
selector. Every bot, including Official-only, uses its Compose-built image.
HAKO_IMAGE remains an offline development-wrapper input.

On startup, prepare a missing configured image, check selected
dependency versions/import entries, install the missing pinned runtime closure,
repeat that check, then reconcile the service group. Prepare containers publish no
ports and receive no runtime credential environment. Use
`deploy/preview-constraints-py312.txt` and `preview-deps.py`: exact observed Python
3.12 distribution versions, selected engine closure and no-deps pip installation.
No package manager, SDK extras or build backend is added just for preview.
Constraints are not hash verification or a lock for all declared Python versions.

Preflight all affected repository identities before effects. Accept ordinary
or preview objects only with exact source identity; reject foreign/contradictory/
duplicate candidates. Explicit startup reconciles partial/stopped groups and
recreates selected apps to reload environment and same-path TOML. Auxiliary
services use ordinary Compose reconciliation; local Bot API is ready before
Telegram. No fingerprint/reuse/incomplete-group gate. Retain read-only QQ
logs/ps/status across both verified application modes;
exclude legacy hako identities from Compose service queries. Startup/restart
remain selected-mode operations. Dependency entry checks cannot establish every future
branch/lockfile/ABI or account capability; do not treat them as feature acceptance.
Build/status/down/help do not implicitly start services. Offline/no-install
constraints take precedence; failures name the unavailable resource and supported
explicit preparation instead of silently falling back to host execution.
Start rejects missing/example OneBot access tokens before any Docker operation.
Down does not require host-address discovery; unavailable browser candidates
must never prevent data-preserving teardown of owned containers.

For a code/settings update, down optionally removes selected repo objects; build
explicitly rebuilds all selected application image tags using current source
and manifests, including already-existing tags; the next start uses those tags
with current runtime settings and engine config binds. Retain all persistent
storage and normal Docker cache behavior. Build works with existing containers
without starting/stopping/removing them. Auxiliary images follow missing-resource
rules. Legacy Official hako.service=bot ownership remains recognizable after
runtime-engine verification: down/start can remove it, build leaves it intact.
Ordinary/preview conversion uses the shared lifecycle, no manual Docker rm/labels.
Explicit QQ startup switches its verified opposing app; QQ down covers both modes
and NapCat, retaining other engines. Whole-project down-all preflights every
project object before scoped removal, retaining networks and all persistent data.

### Readiness and console contract

Use bounded real-service probes and the preview-only adapter readiness marker
where a gateway has no inbound listener. The marker is atomic container-local
state tied to the current application PID/start identity/engine, invalidated on
disconnect, fatal failure and shutdown. Reject old markers, dead processes and
watcher-only survival. Without preview opt-in this instrumentation does not write
state or change application/auth/protocol behavior.
Telegram readiness starts only after a successful poll while the application is
running; application startup cannot overwrite an earlier polling failure.

NapCat readiness and listener inspection execute the dependency-free
`deploy/preview-probe.py` source through container `python3 -c`. The actual
NapCat image has python3 but no node; Music retains its Node probe. NapCat
requires HTTP 2xx at `/webui/` on container loopback6099 and a successful TCP3001 connect,
each bounded inside the existing Docker-exec timeout. Use direct HTTPConnection
so inherited proxies cannot redirect local probes, and emit no response body.
Reuse the existing /proc decoder for IPv4/IPv6 sockets and exclude Docker DNS;
compressed wildcard/loopback IPv6 must keep correct mapping/scope classification.
Real local HTTP/TCP tests and a fake NapCat that rejects Node cover this runtime
capability assumption, including root301 with canonical WebUI200. Do not infer
ready solely from a running container or
transport socket, reset login data, or add another image/toolchain.

After all required service readiness checks, one stdout summary begins
`System is ready.` and emits nonempty sections in this order: Open, Local only
(preview host), Listeners, Published, Internal only, Notes. Group browser entries
as `<entry> (<service>):` followed by one complete URL per line, no bullets or
trailing annotations; deduplicate each entry. Use actual schemes/ports/routes and
inspect mappings/listeners rather than assuming Docker publishing establishes
an active service. No wildcard, container IP or Compose name is advertised as a
host-accessible URL; internal probes/destinations stay Internal only. Outbound-only
Official/Telegram have no inbound listeners: omit empty endpoint sections, confirm
their actual readiness and state that absence in Notes; never invent a listener
to satisfy the reference renderer's generic minimum-listener guard.

Progress/help/errors go to stderr; captured preparation details appear only on
terminal failure or explicit verbose, after redaction. Start and status also
follow bot logs without verbose. Start attaches readers after container startup
and before bounded readiness waiting; it emits the real summary after readiness
and remains attached. Semantic colors use the destination TTY and respect
NO_COLOR/TERM=dumb; URL text stays plain. Ready status uses the same summary;
unready status warns and follows existing owned selected bots with no ready
banner or service mutation. Missing/foreign groups retain explicit failure;
auxiliary-only groups remain finite with truthful success/failure reporting.

During startup and after status's readiness report, follow the last 80 lines and subsequent new lines
from selected owned application bots (`kisara`, `kisara-dev`, `telegram`,
`official`) and the selected OneBot group's `napcat` gateway,
which owns QQ receive/send logs. Verify ownership before reading, label mixed
output using `platform | log`, and omit Music/local Bot API streams. Map
napcat/kisara/kisara-dev to onebot, telegram to telegram and official to official
in both prefixes and follow hints. Preserve unique service IDs for FIFOs/readers
so both OneBot streams survive their shared display label.
Start/status viewing retains receive/reply/no-reply message previews already emitted by the bot,
and shows user/chat/account IDs, bot names and ordinary numbers, while still
redacting credentials. Account and access-list configuration values are not
credentials in these live streams. Captured diagnostics retain identifier
redaction. The Telegram adapter's message-summary opt-in remains required;
neither start nor status enables application logging.
QQ login PNG display is the explicit interactive authentication exception in
[the CLI contract](cli-entrypoints.md#8-qq-login-png-in-attached-logs), shared
by preview and ordinary attached QQ logs. Validate saved-PNG event ordering,
whole-block geometry and independently decoded output, replacement/deduplication,
bounded recent-snapshot/live overlap, completed-login stale-PNG suppression,
terminal fallback, fixed-path/ownership bounds and image-helper cancellation.
Do not treat a decoded fixture as real QQ authorization. No status watcher,
WebUI login session, extra QR command or encoder dependency is required.
Terminal-control redaction also needs real non-C collation coverage:
en_US/zh_CN when installed, alongside C/POSIX/C.UTF-8. Unsupported-locale
fallback to C is not a pass for those cases. Verify internal byte-locale
scoping, unchanged caller locale, ANSI-interleaved credential replacement,
Chinese preservation and direct sanitizer PID tracking under the
[logging contract](../backend/logging-guidelines.md#terminal-control-redaction-locale).
Failure diagnostics continue suppressing incoming/reply/no-reply message lines.
Auxiliary-only selection returns after the summary. Redact each line before
display, flush promptly, and keep memory/scratch bounded independently of log history. Never
wait for the stream to end to release safe output or emit raw fallback errors.
INT/TERM stops and reaps only this invocation's readers/helpers, returns 130/143
and leaves containers/data intact. Reader or sanitizer failures must be explicit,
nonzero and reap other owned readers. Following has no total runtime timeout;
after startup it does not continuously check readiness or restart services/readers.
Real reader EOF ends viewing. Reader setup must execute in the parent shell so
the invocation owns every helper PID; startup readiness checks must also detect
reader/sanitizer failure promptly and before printing a ready summary. INT/TERM
during active viewing must not append a redundant bounded diagnostic dump.
Genuine startup timeout/failure, including auxiliary failure information, keeps
the existing bounded diagnostics and nonzero result.

Resolve effective Docker endpoint first: explicit DOCKER_CONTEXT precedes
DOCKER_HOST, host-only uses that endpoint, otherwise inspect current context with
a supported CLI operation. Distinguish unavailable CLI capabilities from invalid
user configuration. Local Unix socket allows local-host discovery; remote targets
require authorized host discovery or explicit daemon-host addresses, never guessed
caller addresses. Do not introduce an SSH execution route as implicit authority.

For every start/ready status with effective wildcard host publishing, enumerate
all eligible UP/UNKNOWN interface addresses from `ip -br a` on the publishing
host, including secondary/bridge/VPN addresses, strip CIDR and deduplicate in
order. IPv4 publishing establishes only IPv4 candidates; IPv6 needs an actual
IPv6 mapping, brackets literals and excludes link-local zone-dependent addresses.
Specific binds advertise that bound address; loopback URLs go Local only. Missing
ip/discovery fails actionably; no eligible address omits Open and records the
limitation. Every entry repeats the eligible candidate list. These candidates
do not establish cross-device reachability. Preserve loopback/SSH-tunnel/internal
defaults, firewall and host interfaces.

### Diagnostics, cleanup and evidence

Detailed preparation output lives in owner-only /tmp logs, cleaned on exit.
On terminal startup failure, verify common repository/source identity before
reading only a bounded recent log tail (80 lines, 5-second timeout), then redact
injected secrets, private account/access identifiers, authenticated URLs and bearer
tokens before output. Failed reading/redaction never emits raw fallback logs,
blocks temporary/reader cleanup or replaces the original status. Retain selected
created/recreated containers for diagnosis and direct startup retry. Remove the
custom attempt-label/automatic container rollback path. Down is explicit object
removal; never delete foreign containers, persistent storage or incompatible data.

For lifecycle changes run focused deployment/preview fixtures and project checks,
covering missing/prepared resources, ordinary-preview-ordinary reconciliation,
partial/stopped groups, failed build/
install/recheck, invalid config, endpoint precedence/capabilities/remote, watcher
failure, safe-log timeout/failure/ownership, output/address scopes and down/data
preservation. Start/status streaming fixtures must prove delayed lines arrive before
EOF, target/ownership isolation, concurrent labeled bots, sanitization before
emission, bounded scratch, reader/sanitizer failures and cleanup on parent-only
INT/TERM without container mutations. Cover startup logs before readiness and
interrupt, transition to the truthful summary and continued viewing, unready
status with live readers, and reader failure during readiness. INT/TERM viewing
must not release a bulk diagnostic dump; preserve genuine startup timeout and
auxiliary-failure diagnostics. Record actual commands/results in the task; stub evidence is not
real Docker or cold-start evidence. Real isolated first-use/build/install/start,
HTTP/protocol readiness, reconciliation/down, default empty persistent-storage creation and
retention, ignored/untracked data, uncached/network and real-device checks need
their own execution authority and separate results. Do not exercise this profile
against private dotenv/live bot instances to close a documentation or fixture gap.

## Initialization evidence

On 2026-09-26, `./hako python --version` passed with Python 3.12.14 after
session-scoped wrapper escalation for the Docker socket. Both `hako` and
`dev.sh` were executable; `.devhome` was already ignored. This records wrapper
readiness only. No application test run or live-account acceptance is claimed
for this documentation-only initialization. Browser validation is not applicable.
