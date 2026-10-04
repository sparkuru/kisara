# Engine environment configuration

## Goal

Make deployment environment configuration clearly belong to independent OneBot,
Telegram and Official engines, and migrate the latest local `.env` without
losing credentials or changing configured QQ behavior.

## Background

The template labels OneBot access settings as common. Compose already uses
explicit isolated Telegram/Official mappings, while OneBot consumes legacy
deployment `KISARA_*` names (`deploy/compose.yaml`). Settings and Official hako
preview also consume the environment directly (`src/kisara/config/settings.py`,
`preview.sh`, `hako`), so Compose-only aliases are insufficient. The user has
filled Telegram credentials, its allowlist, and the onebot,telegram profile
selection in the current `.env`; `.env.2` is redacted historical input.

## Requirements

1. Group the template into deployment/shared services, OneBot/NapCat, Telegram,
   and Official. Engine-owned inputs use `ONEBOT_*`, `TELEGRAM_*`, `OFFICIAL_*`.
   Keep `NAPCAT_*` and genuinely shared infrastructure settings.
2. Move OneBot access, instance, basic switches, news/music and documented
   development settings to its namespace; use `OFFICIAL_APP_ID` and
   `OFFICIAL_APP_SECRET` for Official credentials. Retain Telegram names.
3. Map names to existing per-process runtime fields in Compose and support
   new names in direct settings/preview. Preserve targeted lifecycle, service
   identities, mounts, login data, state and feature behavior.
4. Legacy names remain compatible when the corresponding new name is absent.
   New explicit empty values and false win. Preserve TOML precedence and
   engine-local configuration paths; document runtime versus deployment names.
5. Main session alone backs up and atomically migrates the latest `.env`,
   preserving value syntax, existing new keys, custom settings and mode 0600.
   Compare effective OneBot/Telegram configuration privately before/after.
6. Do not print credentials, put private files in worker prompts/artifacts or
   commits, or source dotenv as code. The original configuration migration did
   not change services; the approved logging extension permits a targeted
   Telegram preview update after checks, leaving QQ running unchanged.
7. The user subsequently approved NapCat-like Telegram receive/send summaries:
   INFO logs with conversation kind, chat/user IDs and bounded single-line
   text previews. Add an explicit Telegram-only boolean switch, off by default
   for new deployments and enabled in this user's local environment. This
   authorized opt-in is a narrow exception to the default no-message-body log
   policy. Keep SDK HTTP logs suppressed and mask credentials before bounding
   or escaping previews. Log content only for allowed senders/conversations;
   unsupported and denied messages must not disclose their content or identity.
   Emit send success only after confirmed SDK success and cover document/news
   sends without logging media bytes. Add bounded polling-ready lifecycle log.

## Acceptance criteria

- Each template setting has a clear owner; COMPOSE_PROFILES controls engines.
- New names and legacy fallbacks work in Compose and direct settings loading.
- Tests cover explicit empty/false precedence, allowlist/credential isolation
  and unchanged TOML precedence; synthetic Compose interpolation is checked.
- All latest private credential/access/profile values survive migration.
  No values from redacted `.env.2` overwrite current configuration.
- Focused and prescribed full checks pass, with unavailable gates stated
  accurately; secret-bearing Compose rendering is never printed.
- Opt-in logs show received allowed messages and confirmed text/document sends;
  disabled logs, denied/unsupported messages, failures, multiline/control input,
  long previews and token-bearing content have focused regression coverage.
- Targeted Telegram preview update applies the switch/code; QQ container IDs
  and start times remain unchanged. Do not send live diagnostic messages.

## Out of scope

Registration, live diagnostic messages, QQ deployment/restarts, feature removal,
multiple instances per engine, remote pushes or automatic commits.
