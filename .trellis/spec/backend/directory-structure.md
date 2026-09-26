# Directory Structure

## Runtime boundaries

The source package is `src/kisara/`; `python -m kisara` enters `bot/main.py`.
There is no web frontend or HTTP routing framework.

| Path under `src/kisara/` | Ownership |
| --- | --- |
| `bot/contracts.py` | Normalized events, dispatch results, outgoing payloads, adapter protocol |
| `bot/dispatcher.py` | Allowlists, bounded duplicate tracking, aliases, command routing |
| `bot/commands/` | Simple command parsing/output such as ping, roll, help, eat |
| `bot/adapters/` | OneBot/official parsing, lifecycle, API requests, replies |
| `bot/main.py` | Startup configuration and dependency assembly |
| `bot/console.py` | Offline interactive console |
| `application/services/` | Dice, food, chat, tarot, public providers, news, export, setu behavior |
| `config/` | Typed startup settings and feature-file validation |
| `infrastructure/integrations/` | Bounded external HTTP reads |
| `infrastructure/persistence/` | SQLite state and confirmed media file storage |
| `resources/` | Packaged data with provenance/license notices |
| `utils/` | Reusable plain-text and atomic file-publication helpers |

`domain/`, `shared/`, `bot/events/`, and `infrastructure/logging/` currently
contain package scaffolding rather than independent behavior. Do not introduce
abstractions solely to populate them.

## Feature wiring

Follow the existing explicit service → command/dispatcher → startup assembly
pattern. `bot/commands/roll.py` uses `application/services/dice.py`; its
validated entrypoint is routed in `bot/dispatcher.py`. `DailyNews` is created
in `bot/main.py` and injected into the dispatcher and scheduled delivery
callback. There is no automatic plugin discovery.

Concrete assembly example from `bot/main.py`:

```python
public_services = PublicServices(
    saucenao_key=settings.saucenao_key,
    music_api_url=settings.music_api_url,
    tianapi_key=settings.tianapi_key,
)
```

Protocol-specific workflows use narrow gateways: see `SetuGateway` in
`application/services/setu.py` and `ExportImgGateway` in
`application/services/export_img.py`. Shared feature code does not import the
optional `botpy` SDK; only the selected adapter is loaded at startup.

## Supporting files

Feature examples live in `config/features/<feature>/config.toml.example`;
private `config.toml` files and `.env` stay ignored. New package data must be
included in `pyproject.toml` and carry provenance where applicable. Unit tests
live in `tests/unit/`, OneBot protocol simulations in `tests/integration/`.

Feature contracts belong in the implementation module's opening docstring and
`application/services/__init__.py`. Update explicit aliases and
`bot/commands/help.py` when adding commands. Use `docs/application-template.md`
for feature planning, `docs/operations.md` for runtime instructions, and
`docs/legacy-migration.md` for historical behavior. Keep `readme.md` concise.

## Naming and common mistakes

Use existing lowercase snake_case modules and PascalCase classes. Import
utilities from concrete modules such as `kisara.utils.files`.
Avoid an unwired service, platform calls in generic utilities, or a second
configuration path. A stateless command does not need a store, new runtime
volume, or speculative domain layer. See the detailed
[architecture contracts](../trellis-plus/architecture.md).
