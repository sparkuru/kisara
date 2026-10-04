# Evidence

- Template has 43 assignments. Current private .env has no duplicate keys;
  no private values or credential-presence details are recorded here.
- deploy/compose.yaml maps Telegram/Official access into runtime KISARA_*;
  OneBot/development use legacy deployment names. Storage is independent.
- deploy/engines.sh and deploy/onebot.sh export legacy setu GID host defaults;
  new ownership names must account for those exports.
- start.sh/preview.sh follow profiles absent an explicit shell KISARA_ENGINE.
  They do not source dotenv. Official preview invokes hako, which passes the
  environment file to its bot service, requiring direct Settings aliases.
- Settings.from_environment and CSV/bool/percent/required/group helpers read
  environment. Namespace resolution must preserve explicit TOML precedence
  and must not modify global environment.
- Existing deployment tests use a fake Docker executable for scoped lifecycle;
  interpolation additionally needs synthetic Compose validation.
- hako/dev.sh own development checks; no configured lint/type tool exists.
  Offline checks and workers must not load the user's private environment.
