# Approved follow-up: one configuration root per engine

On 2026-10-11 the user requested “按照你的建议，处理第 2 点问题”, approving
the proposed engine-directory/entrypoint unification. This extends this active
task's implementation/check scope. It does not authorize live service operations,
endpoint migration, commits or archival. Preserve all existing TgSetu changes.

## Behavior gap

Feature loaders read `config/features` relative to cwd. Compose remaps
Telegram/Official roots there; hako/direct runs use the repository root instead.
OneBot keeps the old unsuffixed layout. New engine-private TOML is not covered
by the current root-only gitignore pattern.

## Implementation contract

- Canonical root: `config/<engine>` for onebot, telegram and official. A small
  explicit resolver belongs to config; select the root at startup and pass it
  to loaders. No implicit per-feature env reads or shared legacy fallback.
- Ordinary features: `<root>/features/<feature>/config.toml`. Main assembly's
  Setu/TgSetu use that same root. Default group JSON: `<root>/groups.json`.
  Explicit GROUP_CONFIG_PATH keeps its literal path and precedence. Preserve
  missing-file rules, TOML/env/default priority and all authorization policies.
- Settings exposes its root consistently even when constructed directly (a
  derived property is sufficient). `load_feature` takes an explicit Path root.
  No new environment root override or config framework is needed.
- Compose mounts only `config/<engine>` at `/app/config/<engine>` for that bot.
  Preserve shared `config/fonts` at `/app/config/fonts` for existing font paths;
  state/archive/cache mounts stay unchanged. Hako's existing /app repository
  mount plus the application resolver selects the same files automatically.
- Move versioned OneBot feature and group examples to config/onebot. Keep
  Telegram/Official directories. Ignore actual feature TOML/group JSON for all
  engine directories, retaining trackable examples and old private-file ignores.
- Root will perform a one-time byte-preserving no-overwrite copy of existing
  private root OneBot config to the new root after fixture checks. Retain the
  ignored originals as migration backups; never load them as a shared fallback.
  Report collisions by path only. No permanent updater or secret-value output.

## Ownership

- Runtime implementer: feature_files/settings/main, configuration fixtures and
  main integration tests, service module docstrings for changed paths.
- Deployment implementer: Compose, tracked examples/readme, gitignore, env
  example comments and affected deployment/preview/wrapper fixtures.
- Root: task/spec/docs/validation/mainline records and local private copy.
- Reviewer: cross-layer checks and necessary scoped mechanical fixes.

Workers share this workspace: preserve others' changes, coordinate interfaces,
and do not spawn nested agents.

## Acceptance

Conflicting sentinel configs for all three engines must yield only the selected
engine's values. Legacy root files must not alter Telegram/Official or hide an
invalid selected file. Verify missing/invalid TOML, env precedence, dedicated
archive loading and default/explicit group JSON. Compose paths must match the
resolver and keep other-engine configs/credentials isolated. Check-ignore
fixtures prove private files ignored and examples trackable. Migration fixtures
cover custom bytes/modes, equal/unequal existing targets, repeat runs and retained
originals. Run focused then full Docker tests, shell syntax, sanitized Compose,
diff/whitespace and local documentation-link checks.
