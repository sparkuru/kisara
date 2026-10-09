# Design

## Ownership

The main session owns shared specs, notices, mainline, context and final evidence.
A Trellis implement agent owns the existing preview/deployment/wrapper paths and
focused behavior tests; a separate check agent reviews the integrated result.
Write only project-authored ordinary code/shared data, never protected templates.

## Lifecycle

Keep preview.sh thin and reuse deploy/engines.sh and deploy/onebot.sh. Shared
project-authored shell helpers may consolidate configuration, renderer and safe
diagnostics; do not create a parallel service runtime. Preserve deploy/start APIs,
engine isolation and Official's existing configuration path/hako semantics.
Help never loads .env or invokes Docker.

The preview operation parses/validates configuration and tools, resolves Docker
endpoint, discovers needed host candidates, and inspects all existing selected
instances before preparation. Reuse healthy identical instances; report explicit
recovery for changed/unhealthy/incomplete ones. Prepare missing image/dependency
entries with the established image/wrapper; selected extras use pinned Python
3.12 constraints drawn from retained distribution metadata. Do not claim stale
lockfile or all-Python-version correctness from entry checks alone.

Create services detached only after preparation succeeds. Use bounded readiness
for each actual contract: NapCat UI/protocol, OneBot gateway, Telegram polling,
Official gateway and optional music HTTP. A current process/startup marker is
not sufficient when a watcher is alive after application failure. Do not invent
an inbound service for outbound-only bots; document actual absence of listeners.

Where no real probe can observe adapter initialization, opt-in preview-only
readiness instrumentation may write atomic container-local /tmp status tied to
the actual application PID and engine. The implement agent additionally owns
onebot_v11.py/telegram.py/official.py and a small readiness helper/tests for
this narrow requirement. Start unready and invalidate on disconnect, fatal
failure and shutdown; reject stale/dead PID and live-watcher/failed-child states.
Without preview opt-in it performs no writes and changes no protocol, auth,
business behavior, persistent state or public application endpoint.

## Configuration and console

Treat dotenv as data; environment wins by presence, including empty. Separate
host defaults from NAPCAT_UID/GID inputs so file values remain effective. Resolve
DOCKER_CONTEXT before DOCKER_HOST; with neither inspect current context using
supported operations. Local Unix socket supports caller-host discovery; remote
endpoints require explicit host addresses or authorized discovery. Wildcard host
publishing enumerates all eligible addresses from ip -br a.

After all required readiness checks, emit one stdout summary using nonempty
sections in order: System is ready., Open, Local only (preview host), Listeners,
Published, Internal only, Notes. Fill only actual protocol/port/route/scope facts,
group URLs by service and distinguish candidates from cross-device proof.
Progress/help/errors are stderr, TTY/NO_COLOR aware. Capture preparation output
in owner-only temporary logs; show redacted details on failure/verbose only.
Before failure cleanup validate repo/scope/service ownership, fetch bounded recent
logs with timeout, mask injected secrets/private IDs/auth URLs/bearer tokens.
Log/redaction failure never leaks raw text or replaces original failure; cleanup
touches only resources made by this attempt and never persistent data.

## Policy and continuity

Reuse equivalent architecture/storage/validation/workflow docs. Add a focused
development-principles detail and exact manual read/context commands; register
explicit detail paths in manifests, without modifying runtime loaders or AGENTS.
Prospective archive route is task.py archive --no-commit, verify successful state,
inspect explicit source/destination/bookkeeping paths, then one prepared commit.
Retry inspects state/history first; no historical rewrite or empty attribution.

Mainline defaults guided and separates remediation from pending setu live
acceptance. Old design milestones are reference/proposed/superseded; no serial
product authority is inferred. Recover legacy-LICENSE.txt exactly from 497fd9a,
record blob and removal at 109cb82, and preserve existing tarot/Trellis notices.

## Validation and rollback

Use temporary fake Docker/address/application fixtures for branches and focused
deployment regressions. Project tests use hako; syntax and installed lint/format
tools check shell. No actual preview against private .env or live containers.
Cold-start/storage/socket/remote/account validation remains UNKNOWN unless
separately authorized. Inspect links, manifests, notice bytes, template hashes
and diff. Rollback is limited reviewed task-file reverts, never worktree reset
or data deletion.
