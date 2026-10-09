# Validation and Docker Development Profile

- ownership: project-shared
- source: project-authored
- evidence: `pyproject.toml`, `hako`, `dev.sh`, `tests/`, `docs/operations.md`

## Before development

Reuse executable `hako` and its `python:3.12-slim` runtime. The repository is
mounted at `/app` with the host UID/GID; container HOME, user packages, and pip
cache live in ignored `.devhome/`. One-off tool commands do not load `.env`;
credential-loading mode is explicitly `HAKO_SERVICE=bot`. Do not enable it for
offline checks. One-off commands publish no host ports.

If the wrapper is missing or unusable for a changed toolchain, apply
`dev-it-in-docker` at the bootstrap/before-dev checkpoint. Preserve this
project's existing service separation: `dev.sh` is the offline console/test
entrypoint; `preview.sh` and `deploy.sh` manage online services. `dev.sh` has no
`down` subcommand. Do not replace the established entrypoints with a generic
service template.

Codex adaptation uses the current session's narrow `./hako` prefix approval
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
| Local commands/console | `./dev.sh --test` or focused `./hako python -m pytest tests/unit/test_offline_commands.py` |
| Configuration | `./hako python -m pytest tests/unit/test_settings.py` |
| Routing | `./hako python -m pytest tests/unit/test_dispatcher.py` |
| Setu state/media behavior | `./hako python -m pytest tests/unit/test_setu.py` |
| News/cache/delivery | `./hako python -m pytest tests/unit/test_daily_news.py tests/unit/test_news_delivery.py` |
| Utility contracts | `./hako python -m pytest tests/unit/test_utils.py` plus consuming feature tests |
| OneBot adapter/protocol | `./hako python -m pytest tests/unit/test_onebot_adapter.py tests/integration/test_onebot_protocol.py` |
| Telegram adapter/scheduler/protocol | `./hako python -m pytest tests/unit/test_telegram_adapter.py tests/unit/test_telegram_news.py tests/integration/test_telegram_protocol.py` |
| Cross-layer, adapter, schema, or deployment changes | Relevant focused checks followed by `./dev.sh --all` |

Additional feature suites live in `tests/unit/`; choose the matching existing
suite. Mock external providers and simulate OneBot protocol interactions for
repeatable checks without QQ credentials. No CI workflow, configured linter,
formatter, or type-check command was found; do not claim those gates passed
or silently add a new toolchain. The manifest declares Python >=3.8 while the
wrapper exercises Python 3.12; that runtime alone is not compatibility proof
for every declared Python version.

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

The user-approved 2026-10-09 remediation keeps `preview.sh` thin, dispatching
preview operations through `deploy/engines.sh` and project-owned sourced helpers
`deploy/dotenv.sh`, `deploy/preview-console.sh`, `deploy/preview-runtime.sh`.
Ordinary deployment operations retain their explicit targeted service APIs;
`dev.sh` remains the offline console/test entry, not another online runtime.

### First setup and commands

Host requirements: Bash 4.4+, Docker with a reachable daemon, Compose plugin or
legacy docker-compose, timeout, sha256sum, sed, awk, sort, find, mktemp, cat and id.
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
./preview.sh                 # same as start; prepare missing resources only
./preview.sh start --verbose # captured redacted details after each step
./preview.sh status          # state/readiness only; no preparation/start
./preview.sh build           # explicit preparation/rebuild; stop an existing group first
./preview.sh stop            # preview-owned containers only, storage retained
./preview.sh down            # data-preserving stop alias
./preview.sh --help          # no dotenv loading or Docker operations
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
| HAKO_IMAGE | python:3.12-slim; Official wrapper runtime, must satisfy Python 3.12 preview requirements |

When no owned group exists, prepare a missing configured image, check selected
dependency versions/import entries, install the missing pinned runtime closure,
repeat that check, then create the service group. Prepare containers publish no
ports and receive no runtime credential environment; a mounted source tree can
still expose .env as a file, so this is not secret-file isolation. Use
`deploy/preview-constraints-py312.txt` and `preview-deps.py`: exact observed Python
3.12 distribution versions, selected engine closure and no-deps pip installation.
No package manager, SDK extras or build backend is added just for preview.
Constraints are not hash verification or a lock for all declared Python versions.

Inspect existing ownership/configuration before preparation. A healthy matching
group is reused; incomplete/unhealthy/config-changed groups require explicit
data-preserving recovery. Configuration fingerprints include service inputs and
relevant manifests/config files; dependency/image/source changes can require
explicit stop/build/start. Dependency entry checks cannot establish every future
branch/lockfile/ABI or account capability; do not treat them as feature acceptance.
Build/status/stop/down/help do not implicitly start services. Offline/no-install
constraints take precedence; failures name the unavailable resource and supported
explicit preparation instead of silently falling back to host execution.
Start rejects missing/example OneBot access tokens before any Docker operation.
Stop/down do not require host-address discovery; unavailable browser candidates
must never prevent data-preserving teardown of owned containers.

### Readiness and console contract

Use bounded real-service probes and the preview-only adapter readiness marker
where a gateway has no inbound listener. The marker is atomic container-local
state tied to the current application PID/start identity/engine, invalidated on
disconnect, fatal failure and shutdown. Reject old markers, dead processes and
watcher-only survival. Without preview opt-in this instrumentation does not write
state or change application/auth/protocol behavior.
Telegram readiness starts only after a successful poll while the application is
running; application startup cannot overwrite an earlier polling failure.

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

Progress/help/errors go to stderr; details appear only on terminal failure or
explicit verbose, after redaction. Semantic colors use the destination TTY and
respect NO_COLOR/TERM=dumb; URL text stays plain. Ready status uses the same
summary; an unready status returns actual failure/state with no ready banner.

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
On terminal startup failure, verify repository/scope/service ownership before
reading only a bounded recent log tail (80 lines, 5-second timeout), then redact
injected secrets, private account/access identifiers, authenticated URLs and bearer
tokens before output. Failed reading/redaction never emits raw fallback logs,
blocks cleanup or replaces the original status. Inspect diagnostics before
removing only newly created owned resources; do not remove reused/unrelated
containers or persistent storage, and never reset incompatible data automatically.

For lifecycle changes run focused deployment/preview fixtures and project checks,
covering missing/prepared resources, reuse/abnormal existing group, failed build/
install/recheck, invalid config, endpoint precedence/capabilities/remote, watcher
failure, safe-log timeout/failure/ownership, output/address scopes and stop/data
preservation. Record actual commands/results in the task; stub evidence is not
real Docker or cold-start evidence. Real isolated first-use/build/install/start,
HTTP/protocol readiness, reuse/stop, default empty persistent-storage creation and
retention, ignored/untracked data, uncached/network and real-device checks need
their own execution authority and separate results. Do not exercise this profile
against private dotenv/live bot instances to close a documentation or fixture gap.

## Initialization evidence

On 2026-09-26, `./hako python --version` passed with Python 3.12.14 after
session-scoped wrapper escalation for the Docker socket. Both `hako` and
`dev.sh` were executable; `.devhome` was already ignored. This records wrapper
readiness only. No application test run or live-account acceptance is claimed
for this documentation-only initialization. Browser validation is not applicable.
