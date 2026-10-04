# Design

## Public deployment schema

Keep dotenv format: deployment/shared music infrastructure first, then OneBot
with NapCat, Telegram, and Official. Engine-owned deployment KISARA_<suffix>
fields become ONEBOT_<suffix>, including documented watch/ownership settings.
Transport ONEBOT_* and NAPCAT_* fields remain unchanged. Official credentials
become OFFICIAL_APP_ID/OFFICIAL_APP_SECRET. Keep existing Telegram names.
Expose only supported basic switches; advanced feature configuration stays in
engine-local TOML. KISARA_ENGINE is an explicit direct-runtime/preview option,
documented separately without assigning it in the default Compose template.

## Resolution

Compose resolves engine-specific deployment inputs into existing runtime
fields. OneBot retains legacy KISARA_* fallback; Official credentials retain
AppID/AppSecret fallback. Other services never inherit OneBot deployment
permissions. New names win by presence, including empty strings; use unset-only
fallback for new names. Keep existing runtime validation and defaults.

Direct Settings loading resolves only the selected engine's namespace before
parsing. Preserve generic runtime names and existing SDK aliases. Prefer a
pure environment mapping passed to parsing helpers, without mutating global
os.environ. Explicit TOML values still win. Do not change preview topology.

Ownership helpers must honor new OneBot names without exported legacy host
defaults masking dotenv values. Preserve host UID/GID defaults and scoped
lifecycle behavior. No competing wrappers or configuration framework.

## Private migration

Main session alone rereads the latest .env and captures effective Compose
environments privately. Create an owner-only backup in a private temporary
directory, rename assignment keys while retaining right-hand-side syntax,
preserve already-existing new keys over aliases and preserve custom inputs.
Render using template order/comments and atomically replace at mode 0600.
Compare effective engine settings and private assignment preservation before
and after; restore backup on a mismatch. Never use .env.2 as migration input.

## Boundaries

Change template, Compose, relevant helpers, Settings, focused tests, operating
docs and specs. Business services, adapters, QQ login/state storage and running
containers are outside this change. Migration happens after implementation
review; workers receive no private dotenv. Live account reachability is a
separate operational action, not needed to prove a configuration rename.

## Approved Telegram logging extension

The later user request approves receive/send summaries resembling NapCat.
Use `TELEGRAM_MESSAGE_LOG_ENABLED=false` in the public template and Compose
default, plus an appended `Settings.telegram_message_log_enabled: bool = False`
field. Resolve/validate this Telegram-only switch only for Telegram. Main adds
`TELEGRAM_MESSAGE_LOG_ENABLED=true` to the latest private environment after
checking, preserving all existing values, then updates only the running
Telegram preview service. Existing QQ containers must not be recreated.

Keep logging inside the Telegram adapter. Received summaries include allowed
user ID, chat ID, conversation kind and single-line message preview. Use the
existing Settings access sets solely to decide whether log details may be
disclosed; do not alter handler invocation, routing, dedup or SDK behavior.
After confirmed text/document sends, log destination and bounded content or
caption plus document metadata; never log attachment bytes. Ordinary allowed
messages that produce no reply may have an explicit no-reply processing line.
Startup readiness must be emitted only after polling and application start.

Bound previews at 120 display characters after redacting the configured bot
token and token-bearing Bot API URL fragments. Escape control characters and
newlines before logging so one message cannot create extra log lines or terminal
control sequences. Use lazy logger arguments and retain SDK logger suppression.
This opt-in exception does not enable raw events, SDK request URLs, arbitrary
credential diagnostics or logs from unauthorized/unsupported messages.

Affected additional public files are Telegram adapter, Settings, dotenv
template/Compose, focused Telegram/configuration tests and operating docs;
main owns logging/configuration specs and local switch/deployment. Synthetic
tests prove receive/send and failure/redaction behavior; main checks only
bounded live readiness and QQ container identity, not private message contents.
