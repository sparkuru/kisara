# Engine-owned configuration roots

## 1. Scope and trigger

All entrypoints must load the selected engine's configuration from the same
repository-relative directory. This covers ordinary features, dedicated archive
loaders, group JSON, Compose, hako and direct execution. User approval on
2026-10-11 replaces the old Compose-only root remapping.

## 2. Signatures

- `engine_config_root(engine: str) -> Path`: `config/<engine>` for onebot,
  telegram or official; rejects unsupported engines with ConfigurationError.
- `Settings.config_root -> Path`: derived from the instance's engine, including
  directly constructed Settings fixtures.
- `load_feature(name: str, config_root: Path) -> Mapping[str, Any]`: explicit
  selected root, no implicit per-feature engine/environment lookup.
- `_read_group_overrides(allowed_groups, config_root, environment)` uses that
  root for its default JSON. Setu/TgSetu main assembly uses Settings.config_root.

## 3. Contracts

`KISARA_ENGINE` defaults to onebot. Namespaced environment inputs retain their
existing mapping/precedence. Ordinary TOML lives at
`config/<engine>/features/<feature>/config.toml`; missing files retain normal
env/code fallback. Dedicated archive missing files disable their feature.
Explicit TOML values override matching env fallbacks, including false/empty.
Default group JSON is `<root>/groups.json`; explicit GROUP_CONFIG_PATH retains
its literal path. Group TOML overrides JSON. Authorization is unchanged.

Compose mounts only the selected engine directory read-only at the identical
`/app/config/<engine>` path. Both OneBot profiles use config/onebot. Shared
config/fonts stays read-only at /app/config/fonts. State/login/archive/cache
identities and credential boundaries stay intact. Hako already mounts the
repository at /app; direct execution must start from the repository root with
its runtime environment supplied. No extra config-root env option is required.

Versioned OneBot examples live under config/onebot. Actual feature config.toml
and groups.json files in every engine root are ignored; examples stay trackable.
Legacy root private files remain ignored migration backups, never a shared
fallback. One-time local migration preserves bytes/modes and originals, skips
equal existing targets, and refuses differing targets before copying any file.
Never log config contents or create a permanent updater for this migration.

Changed mount layout needs targeted container recreation, not restart. Once
deployed, ordinary TOML edits still need only a restart. No automatic service
operation or account migration occurs during code checks.

Existing preview fingerprints still hash all configuration TOML/JSON for
conservative reuse detection. Unrelated/backup config edits may invalidate
reuse; this does not change selected-engine feature loading. This follow-up
does not redefine fingerprint inputs or external explicit-path detection.

## 4. Validation and error matrix

| Input/state | Result |
| --- | --- |
| Unsupported engine | ConfigurationError, no config/SDK effects |
| Selected valid TOML, conflicting other-engine/legacy files | Selected values only |
| Selected file missing | Feature-specific fallback/disabled behavior, no other-root search |
| Selected malformed/unknown-key file | ConfigurationError, no fallback hiding error |
| Default groups JSON | Selected root only; Telegram ignores QQ group overrides |
| Explicit group path | Literal requested path and existing validation remain |
| Global/feature allowlist mismatch | Existing startup/policy denial remains |
| Migration target exists with different bytes/link | Stop without overwrite; path-only report |
| New private TOML/group JSON | Ignored by Git; example remains trackable |

## 5. Good, base and bad cases

Good: Telegram has music enabled and OneBot disabled in their own files; all
entrypoints yield the corresponding value. Base: a missing selected ordinary
file uses its existing env/default; TgSetu stays off when missing. Bad: read
config/features as a shared fallback or rely on Compose to hide loader errors.

## 6. Tests required

Use distinct sentinel configs for all engines and a misleading legacy root.
Assert selected values, env priority, missing/invalid selected behavior, direct
Settings root, group JSON default/explicit path, and archive main injection.
Verify all four Compose bot binds exclude other-engine roots and preserve
fonts/state/cache. Hako uses the same /app working repository. Git check-ignore
fixtures cover private and example paths; when Git is absent inside the Docker
test image, explicitly run the synthetic Git fixture separately and record it.
Migration scratch fixtures cover bytes/modes, repeated runs, equal/conflicting
targets, retained originals and links. Run focused then full Docker regression.

## 7. Wrong versus correct

Wrong: hardcode config/features in loaders, remap Telegram into it only in
Compose, and let direct execution consume OneBot's private configuration.
Correct: select config/telegram at startup, pass it to every loader, and mount
that same directory at /app/config/telegram for Telegram.
