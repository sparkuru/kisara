# Implementation plan

## Ordered checklist

1. [x] Before source edits, refresh the registered Trellis specs and preserve
   the existing parent-task/worktree changes. Keep the OneBot research record
   in the child task; do not add bridge code.
2. [x] Preserve the architecture decision: the local server is a transport
   backend for Kisara's native Telegram adapter, while OneBot remains a
   separate protocol boundary. Do not trade semantic correctness for fewer
   processes, and do not add a hidden Telegram-OneBot translation layer.
3. [x] Inspect the existing local-only tests and add only the missing focused
   regression at the real boundary: disabled/enabled effective TgSetu config,
   local endpoint/API ID-hash validation, or lifecycle ordering. Do not add a
   cloud download path or weaken the current local media contract.
4. [x] Keep the existing `telegram-bot-api` Dockerfile, entrypoint, probe,
   Compose profile, named cache volume, same-path read-only mount and UID
   ownership intact. If a test exposes a defect in those already-approved
   assets, fix only that defect and update its focused test.
5. [x] Update the existing operator documentation if needed so the selected
   deployment clearly states: BotFather token remains required; API ID/hash are
   local-server-only; local API still reaches Telegram; OneBot bridges are a
   separate option; and the one-time cloud `logOut` cutover is not automatic.
6. [x] Run offline focused checks for TgSetu, Telegram settings/adapter,
   dispatcher, protocol, local Bot API deployment and engine lifecycle. Run
   the complete `./kisara.sh test` gate because the change crosses feature,
   adapter, configuration and deployment layers.
7. [x] Validate task manifests, Markdown links/source claims, `git diff --check`
   and the diff for credential-bearing files. Do not print rendered Compose
   configuration or values from `.env`.
8. [ ] Before live mutation, require the operator's private `.env` to contain
   valid API ID/hash. Back up the ignored TgSetu TOML to owner-only `/tmp`,
   record only a checksum, and verify the current Telegram/state/archive
   ownership. Do not alter the Bot token or persistent volumes.
9. [ ] Perform the controlled migration: stop the cloud token owner, execute
   the guarded one-time cloud `logOut`, enable local mode and the authorized
   TgSetu TOML, then run `./kisara.sh up telegram`. The lifecycle must start
   and health-check `telegram-bot-api` before recreating Telegram; no second
   poller or OneBot bridge is started.
10. [ ] Verify the selected container's endpoint/configuration through safe
   metadata and bounded redacted logs. Have the authorized private user send
   `/help` and `/tgsetu on`; confirm `/tgsetu` is listed and the generic
   unavailable response is gone. Do not claim media retrieval success from a
   command-only smoke check.
11. [ ] If cutover or smoke verification fails, restore the exact ignored TOML
    backup and use the scoped lifecycle rollback while retaining state/cache/
    archive. Account-level cloud rollback is manual and subject to Telegram's
    documented post-logout interval; do not automate or bypass it.

## Validation commands

Focused offline gate:

```text
./hako python -m pytest \
  tests/unit/test_tgsetu.py \
  tests/unit/test_tgsetu_config.py \
  tests/unit/test_tgsetu_files.py \
  tests/unit/test_telegram_settings.py \
  tests/unit/test_telegram_adapter.py \
  tests/unit/test_dispatcher.py \
  tests/unit/test_telegram_bot_api_deployment.py \
  tests/unit/test_engine_deployment.py \
  tests/integration/test_telegram_protocol.py -q
```

Canonical gate and task validation:

```text
python3 ./.trellis/scripts/task.py validate .trellis/tasks/10-14-telegram-tgsetu-command-availability
./kisara.sh test
```

Documentation/task checks:

```text
git diff --check
```

Live lifecycle, only after the final planning approval and private credential
preflight:

```text
./kisara.sh status telegram
./kisara.sh up telegram
./kisara.sh status telegram
```

`TELEGRAM_LOCAL_MODE=true` automatically selects the internal
`telegram-local` Compose profile. Do not pass `telegram-bot-api` as a public
engine selection, expose its port, or run a separate `getUpdates` client.

## Verification record

Completed offline on 2026-10-14:

- Focused Telegram/TgSetu/deployment gate: `311 passed, 1 skipped`.
- Full project gate: `1068 passed, 1 skipped, 3 existing PTB warnings`.
- Task manifest validation and `git diff --check`: passed.
- Added regression coverage for an explicitly disabled TgSetu TOML and
  documented the token/API ID/hash and OneBot boundary in `docs/operations.md`.
- No production source, cloud fallback, OneBot bridge, `.env` value, live
  service, Bot API `logOut`, or persistent volume was changed.

Live steps 8–11 remain pending. A redacted private-environment preflight found
that `TELEGRAM_API_ID` is not a valid numeric value and
`TELEGRAM_API_HASH` is absent. Do not enable the ignored TgSetu TOML or perform
the one-time cloud logout until those credentials and the local endpoint are
corrected.

## Pause status

Paused at the user's request on 2026-10-22 because the required Telegram API
application could not be obtained from `my.telegram.org`. The offline
implementation, tests, documentation and research remain preserved. Resume
only after an explicit user request and a fresh private-credential preflight;
until then, do not enable the live TOML, switch endpoints, call cloud `logOut`,
restart Telegram, or add further Telegram implementation.

## Risk and rollback points

- `src/kisara/bot/main.py` and `src/kisara/config/settings.py`: startup config
  and endpoint validation. Roll back if ordinary command assembly or the local
  endpoint changes unexpectedly.
- `src/kisara/bot/adapters/telegram.py`: Bot API root/cache path and lifecycle.
  Do not replace the local cache path with a cloud temporary file.
- `deploy/engines.sh` and `deploy/compose.yaml`: local service ordering and
  ownership. Verify only Telegram/local API objects are selected; OneBot and
  unrelated services must remain untouched.
- Ignored `config/telegram/features/tgsetu/config.toml` and `.env`: private
  live inputs. Keep exact rollback copies, never stage them, and never include
  their values in task logs.
- Cloud `logOut`: account-level migration boundary. It is one-shot and may
  impose a temporary cloud re-login restriction; failure stops the cutover and
  does not authorize destructive cleanup.
- OneBot bridge candidates: research-only in this task. Installing one would
  create a competing Bot API owner and expand the feature/engine boundary.
