# Execution plan

1. Review artifacts and configuration/validation/language guidelines; search
   all legacy variable consumers before changing mappings.
2. Implement grouped template, unset-only Compose aliases and necessary
   ownership-helper changes preserving current defaults.
3. Resolve selected-engine names in direct Settings loading without global
   mutation, retaining runtime aliases and TOML precedence.
4. Update operating docs and meaningful configuration/deployment tests.
5. Run focused tests, shell syntax and available shell tools; verify synthetic
   Compose interpolation without private credentials.
6. Dispatch full-scope Trellis check/fix and run prescribed full checks.
7. Main updates configuration specs, rereads/backups/migrates .env, checks exact
   private value retention and effective engines, and inspects final diff.
8. Report restart instructions; no services or commits change automatically.

## Validation

- ./hako python -m pytest tests/unit/test_settings.py tests/unit/test_telegram_settings.py tests/unit/test_engine_deployment.py
- ./dev.sh --all
- bash -n on changed shell scripts; relevant available ShellCheck/shfmt checks.
- Compose config --quiet and captured JSON with synthetic inputs/all profiles.
- Private effective-environment comparison across local migration.
- git diff --check and changed/untracked/ignored-file inspection.

No configured application lint or type-check command exists; report accurately.

## Approved follow-up: Telegram summaries

1. Implement explicit Telegram-only opt-in switch, bounded/redacted one-line
   receive/send summaries and polling-ready log. Preserve routing and SDK
   suppression. Update examples/Compose/docs and meaningful focused tests.
2. Independently check/fix and run focused plus full offline test suite;
   privately render synthetic switch mappings, inspect privacy boundaries.
3. Main records the opt-in logging exception in specs, backs up the latest
   private dotenv and enables only the new switch without changing other values.
4. Main recreates only Telegram after passing checks, privately captures runtime
   logs, confirms ready state and unchanged QQ container IDs/start times.
   No live diagnostic messages or private payloads are printed.
