# Backend Development Guidelines

Kisara is a Python QQ bot with explicitly selected OneBot 11 or official
adapters. These guidelines describe the current source and tests. Shared
delivery and feature policies live in [Trellis Plus](../trellis-plus/index.md).
Write documentation and implementation module docstrings in English.

## Guidelines Index

| Guide | Read when |
| --- | --- |
| [Directory Structure](directory-structure.md) | Adding or moving features, adapters, resources, or utilities |
| [Database Guidelines](database-guidelines.md) | Changing SQLite state, idempotency, or recovery |
| [Error Handling](error-handling.md) | Changing validation, providers, dispatch results, or adapter failures |
| [Quality Guidelines](quality-guidelines.md) | Before implementation and quality review |
| [Logging Guidelines](logging-guidelines.md) | Changing diagnostics or exception logging |

## Pre-Development Checklist

Read the active task's PRD and any design/implementation artifacts, this index,
[quality guidance](quality-guidelines.md), and the relevant topic above.
Load [architecture](../trellis-plus/architecture.md) and
[configuration/storage](../trellis-plus/configuration-storage.md) when the
change touches those contracts. Use the
[thinking guides](../guides/index.md) for reuse or cross-layer changes.
Register relevant detail files in task context manifests; an index link alone
does not inject its referenced documents.

## Quality Check

Follow [quality-guidelines.md](quality-guidelines.md) and the shared
[validation profile](../trellis-plus/validation.md). Check source claims and
relative links for documentation changes. Use the existing Docker wrapper and
focused suites for code changes, and broader tests for cross-layer changes.
Record actual commands/results and the human review classification before the
[delivery steps](../trellis-plus/workflow.md).
