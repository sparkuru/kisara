# Quality Guidelines

## Current development contract

`pyproject.toml` declares Python >=3.8, a setuptools `src/` package, and pytest
as the development dependency. The existing `./hako` wrapper runs Python 3.12
in Docker, mounts source, and keeps packages/caches in ignored `.devhome/`.
Use the wrapper for application development checks; offline checks do not load
`.env`. Trellis's own documented host Python commands manage workflow records.

No application linter, formatter, static type checker, or CI workflow is
configured. Do not claim these passed or introduce a new toolchain as an
incidental fix. Testing in Python 3.12 alone does not prove the entire declared
Python support range.

Source uses snake_case functions/modules, PascalCase classes, typed public
signatures, standard dataclasses, and English docstrings. Follow nearby
implementation and tests; load the available Python or shell coding skill for
changes in that language.

## Required patterns

Authorize before services, history lookup, downloading, sending, or recall.
Use normalized `MessageEvent` / `OutgoingMessage` contracts for shared routing,
explicit startup injection, and concrete utility imports. Keep configuration
validation at startup and feature side effects in the owning service/adapter.
Retain existing per-feature state and retry rules; do not weaken checks to make
validation pass. Preserve private files and unrelated work.

See [directory ownership](directory-structure.md),
[error boundaries](error-handling.md), and
[feature contracts](../trellis-plus/architecture.md).

## Test style and commands

Tests use pytest functions with direct behavioral assertions, `tmp_path` for
storage, normalized events for routing, injected/fake dependencies for external
providers, and simulated WebSocket peers for OneBot protocol behavior.
Example from `tests/unit/test_news_delivery.py`:

```python
first = NewsDeliveryStore(str(tmp_path))
assert not first.was_sent("2026-09-23", "group-1")
first.mark_sent("2026-09-23", "group-1")
restarted = NewsDeliveryStore(str(tmp_path))
assert restarted.was_sent("2026-09-23", "group-1")
assert not restarted.was_sent("2026-09-23", "group-2")
```

| Changed surface | Check |
| --- | --- |
| Documentation/specs | Resolve relative links/source paths; inspect new file contents; `git diff --check` |
| Offline commands | `./dev.sh --test` |
| Routing | `./hako python -m pytest tests/unit/test_dispatcher.py` |
| Configuration | `./hako python -m pytest tests/unit/test_settings.py` |
| Durable media workflow | `./hako python -m pytest tests/unit/test_setu.py` |
| SQLite news state | `./hako python -m pytest tests/unit/test_news_delivery.py` |
| Utilities | `./hako python -m pytest tests/unit/test_utils.py` plus consuming feature tests |
| Adapter/cross-layer/schema/deployment | Relevant focused suites, then `./dev.sh --all` |

The shared [validation profile](../trellis-plus/validation.md) lists additional
feature checks. Regression tests should fail when the changed behavior is
removed. Verify authorization rejection, duplicate suppression, failure paths,
and recovery when relevant; do not assert only internal implementation details.
Documentation-only changes do not need new application tests or live services.

## Review and delivery

Check that service, route, help, configuration example, storage mapping,
implementation docstring, and tests agree where relevant. Review source claims,
imports, packaged resources/provenance, staged paths, and privacy boundaries.
Reject speculative abstractions, automatic enabling of group features,
unbounded network reads, raw protocol payloads in shared utilities, and broad
host cleanup.

Record actual validation and any missing coverage. Classify the concrete human
review need using the shared policy; docs/mechanical changes normally qualify
as `human-not-needed`. Respect the user's existing commit authorization and
follow [delivery policy](../trellis-plus/workflow.md) for work commits, task
archive, and journal recording.
