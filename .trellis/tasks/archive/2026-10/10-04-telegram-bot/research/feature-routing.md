# Feature routing and Compose selection evidence

## Existing seams

- bot/dispatcher.py provides authorization and bounded deduplication. Its _route
  and _route_public branches are existing routing behavior to preserve while
  introducing explicit registered handlers.
- bot/commands/help.py assembles help separately from route matching. Effective
  feature metadata can make Telegram help and routing agree without changing
  existing QQ feature availability.
- config/feature_files.py currently accepts enabled for chat/tarot but not
  news/music. New flags need compatible defaults and per-engine effective values.
- bot/main.py assembles existing services. Telegram needs only its five feature
  families and must not initialize unused QQ-only workflows.
- PublicServices.music already returns a song title, artist, link, and optional
  QQ music ID. Reuse it; other PublicServices methods remain existing QQ services.
- OneBotV11Adapter._run_daily_news owns the existing QQ scheduler. New enablement
  can gate its runner while retaining timing/retry/completion behavior.
- Current Compose hardcodes OneBot bot services; only music uses a profile.
  Official/Telegram profile services and unified entrypoint routing are needed.
- deploy/onebot.sh and preview.sh currently assume QQ-oriented lifecycle commands.
  Selection and targeted actions require explicit compatibility checks.

## Native Compose mechanism

Verified official sources on 2026-10-04:

- [Profiles](https://docs.docker.com/compose/how-tos/profiles/): assigned services
  start with selected profiles; unprofiled services start by default. Explicit
  service targeting can start a service without its profile.
- [COMPOSE_PROFILES](https://docs.docker.com/compose/how-tos/environment-variables/envvars/):
  comma-separated profiles may be selected in .env.

Use COMPOSE_PROFILES=onebot,telegram for deployment selection and a single
KISARA_ENGINE value inside each bot process. Keep credentials mapped explicitly
per service instead of injecting the whole environment file.

Selection controls startup, not automatic shutdown of already-running services.
Document targeted stop/restart and whole-stack behavior. Preserve the existing
QQ project/service/volume/login identities; keep Telegram state separate.
Optional music access stays internal without forcing inactive bot engines.

## Registry and switches

Use static feature definitions for command matching/aliases/help, handlers,
switches, and supported platform adaptation. Preserve authorization/deduplication
before effects. Telegram's registry contains ping/help/news/news_push/music.
Existing QQ commands/workflows retain their semantics and platform eligibility.

Use compatible feature TOML flags and preserve older defaults. Manual news and
scheduled push are independently enabled; disabled push creates no loop. Help
reflects the current effective registry. Future native Telegram handlers reuse
eligibility rules without becoming fabricated text commands.

## Checks

Validate QQ compatibility with the existing full suite, Telegram inventory with
fake SDK tests, profile combinations with placeholder/fake Compose invocations,
inactive-engine credential isolation, and target-specific lifecycle operations.
Do not use planning checks to start/stop live services or render real credentials.
