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

## Initialization evidence

On 2026-09-26, `./hako python --version` passed with Python 3.12.14 after
session-scoped wrapper escalation for the Docker socket. Both `hako` and
`dev.sh` were executable; `.devhome` was already ignored. This records wrapper
readiness only. No application test run or live-account acceptance is claimed
for this documentation-only initialization. Browser validation is not applicable.
