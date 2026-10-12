# Validation and delivery state — 2026-10-12

## Public-feature delivered behavior

- Independent `.env` inputs `TELEGRAM_PUBLIC_FEATURE`, `ONEBOT_PUBLIC_FEATURE`,
  and `OFFICIAL_PUBLIC_FEATURE`, with canonical ordinary registry names.
  Telegram unset default is `tguid`; OneBot/official unset defaults are empty.
  Explicit empty overrides defaults/internal fallback. Other namespaces do not
  configure the selected engine. Both OneBot Compose services are wired.
- Registered public ordinary commands bypass sender/group allowlists, while
  groups always require the existing master switch. Enablement, platform support,
  arguments and feature-owned rules remain effective. Unknown/noncanonical,
  unsupported/native/scheduled public entries fail startup validation.
- Telegram `/tguid` returns the sender's numeric ID using the existing source
  chat/quote reply path. Another bot's addressed command is ignored; arguments
  get usage guidance. Lookup grants no access and needs no service or storage.
- Public access cannot enter ordinary-text/unknown/unassembled QQ fallback.
  Public `ping` arguments get usage guidance; explicit disabled QQ features stop
  before fallback for every caller. Previously authorized enabled legacy ping
  fallback is retained.
- OneBot quote preparation receives a pure exact command authorizer, without
  consuming dispatch duplicate tracking. Native Setu/export/TgSetu and scheduled
  recipients retain strict access. Recall metadata matches its OneBot-only,
  dispatcher-owned handler without a false PublicServices dependency; quote/admin
  checks and configured disablement remain.
- Existing operations/help/ownership documentation and project code specs agree.
  Public Telegram replies do not expand opt-in allowlist-bound conversation logs.

## Public-feature automated evidence

| Gate | Actual result |
| --- | --- |
| Implement focused routing/settings/adapters/deployment/push/protocol suites | 444 passed, 1 skipped, 3 existing PTB warnings |
| Final changed-router/OneBot/push gate | 111 passed |
| Independent public/recall/startup review gate | 85 passed, 281 deselected, 0.78s |
| Final `./kisara.sh test -q` | **997 passed, 1 skipped, 3 warnings**, 258.33s |
| `git diff --check` | Passed |
| Both task context manifests | 10 valid spec entries each |
| Spec/mainline Markdown targets | 56 local file targets resolved |
| Private dotenv maintenance | 7 scratch cases passed; only three missing public-feature keys appended |

Focused implement command:

```bash
./hako python -m pytest tests/unit/test_settings.py tests/unit/test_telegram_settings.py tests/unit/test_dispatcher.py tests/unit/test_telegram_adapter.py tests/unit/test_onebot_adapter.py tests/unit/test_engine_deployment.py tests/unit/test_news_push.py tests/integration/test_telegram_protocol.py tests/integration/test_onebot_protocol.py -q
./hako python -m pytest tests/unit/test_dispatcher.py tests/unit/test_onebot_adapter.py tests/unit/test_news_push.py -q
```

Independent check command:

```bash
./hako python -m pytest tests/unit/test_dispatcher.py tests/unit/test_settings.py tests/unit/test_telegram_settings.py tests/unit/test_onebot_adapter.py tests/unit/test_engine_deployment.py tests/integration/test_onebot_protocol.py tests/integration/test_telegram_protocol.py -q -k 'public or recall or startup_injects'
```

The skip is the unchanged isolated Git-ignore fixture because the Docker image
does not contain Git. The three warnings are the existing PTB `retry_after`
timedelta deprecation. No configured application linter/type-checker exists;
those tools were not installed or claimed as passed. All application checks ran
in the existing offline Docker wrapper without loading credential environment.

The first focused attempt found two incorrect new protocol assertions expecting
quoted text segments where the existing OneBot sender emits a plain string.
Corrected assertions passed in the subsequent focused and full gates. No
production send failure or provider/account traffic was injected.

## Private dotenv preservation

The one-off temporary helper reused `deploy/dotenv.sh`'s data grammar in an
isolated subprocess and emitted no configuration values. It verified absence
(no partial file creation), custom/empty values, quotes/comments/CRLF bytes,
mode preservation, repeated no-op, duplicate/invalid rejection and symlink refusal
in temporary fixtures before modifying the named existing private `.env`.
Actual added keys are the three public-feature inputs above; original bytes and
mode were retained. The helper lives only under `/tmp`, not in repository source.

## Review and limitations

Independent Trellis check found no functional blocker. It corrected stale
operations/group comments and the OneBot strict-helper docstring; main qualified
three configuration-spec claims and recorded the public exception separately.
Native injection was available but displayed output was truncated, so agents
explicitly reread task artifacts and complete relevant manifest specs. The
configuration/storage file remains below its 32768-byte per-file limit.

Classification: **human-optional**. Approved access rules are exercised with the
real pinned Telegram SDK and synthetic Bot API peers plus OneBot protocol peers.
Actual account delivery is not established, and implementation/check completion
does not depend on a user reply. A later deployed private `/tguid` should return
that sender's numeric ID; group lookup should respond only with the group master
switch enabled. No deployment or live account operation occurred.

Existing OneBot quote preparation can repeat a history lookup before dispatch
rejects a duplicate. This limitation predates public policy and remains; feature
handlers/replies still follow the existing dispatch duplicate cache. No new
history cache, schema or delivery guarantee was introduced.

## Remaining delivery state

Public-feature and approved preview implementation/automated checking are
complete, including the fresh combined full gate recorded below.
The user subsequently authorized local commits with “提交”; the work commit is
`7da12cd14a523b56e4491349c40cfb949d0ef3a7` on `keiyaku-no-kisu`.
The task stays `in_progress` pending separate archival. No archive, branch
operation or push was performed.
The task helper warned that this task's recorded branch equals its base branch;
resolve branch/accepted commit evidence before any future archival, not by
silencing archive validation. Other task acceptance and running services are
unchanged. Dotenv/image changes require a targeted recreation such as
`./kisara.sh up telegram` if the user subsequently chooses deployment.

## Read-only runtime diagnosis

After the user reported no `/tguid` reply, scoped Docker reads confirmed the
existing `kisara-telegram-1` container (`4f1b8e7fb9d2`) is exited with code 0.
Its finish time is `2026-10-10T16:57:05Z` and it has no preview ownership label.
Copying only its feature registry source to a temporary file confirmed that
this old image contains neither `tguid` nor `tgsetu` registration. Thus there is
no active local Telegram poller in that deployment, and starting the unchanged
old image alone would not load this feature. Its existing deployment entry
`./kisara.sh up telegram` can rebuild/recreate it if separately authorized.
Preview requires its own ownership and cannot directly adopt that container.
No logs/configuration values, Bot API requests, account messages, image build,
container start/stop or live service changes were performed in this diagnosis.

## Approved preview follow-up — 2026-10-13

The user chose this existing task, COMPOSE_PROFILES-based selection and the
uniform Official image path, then approved the final summary with “可用”.

- No-target down/build/start/status share effective COMPOSE_PROFILES, with
  inherited same-key presence precedence and unset-only onebot default.
  Explicit targets win; KISARA_ENGINE no longer selects preview profiles.
- All selected application bots, including Official-only, use Compose images.
  Explicit build rebuilds existing tags from current source/manifests without
  starting services; subsequent start uses those tags and current settings.
  Existing config binds, pinned dependency checks, auxiliary preparation,
  local Bot API staging and persistent data remain intact.
- Persisted preview labels retain hako.scope=preview.sh. Selected Official down
  can remove a legacy hako.service=bot instance only after exact ownership and
  actual runtime engine verification. Start/build/status refuse that conflict.
  Unknown/foreign containers are not adopted or removed.
- Log prefixes and follow hints use onebot/telegram/official. Both NapCat and
  OneBot application streams remain, with distinct service FIFO/reader identities.
  History80, incremental credential redaction, readiness and signal cleanup
  remain; Ctrl+C/TERM only end viewing.

Changed implementation paths are deploy/preview-runtime.sh,
deploy/preview-console.sh, tests/unit/test_preview_lifecycle.py and
docs/operations.md. Main synchronized .env.example comments and project-owned
CLI/validation/configuration specs. No forwarding change was necessary.

Focused command:

```bash
./hako python -m pytest tests/unit/test_preview_lifecycle.py tests/unit/test_kisara_cli.py tests/unit/test_engine_deployment.py tests/unit/test_hako_deployment.py tests/unit/test_preview_readiness.py -q
```

Result: **237 passed, 1 skipped in 293.33s**. The skip remains the existing
missing-Git Docker fixture. Changed shell helpers pass bash -n; ShellCheck and
shfmt are unavailable, and no application lint/type-check configuration exists.
git diff --check and both eleven-entry task manifests pass validation. Each
manifest references 121588 spec bytes, maximum single file 32576 bytes; 58 local
Markdown targets resolve. Context injection can exceed its total with artifacts,
so workers explicitly read the relevant complete files as fallback.

Synthetic Docker fixtures cover all-bot/Official-only down/build/start with
existing tags, changed source/manifest and permissions, no implicit build start
or duplicate startup build, retained data, explicit/default/invalid selection,
legacy/foreign boundaries and all fifteen existing signal/log-follow cases.
Snapshots establish build input/argv and creation settings, not actual image
contents, account delivery or private-environment readiness. Main separately
verified existing Compose build contexts, engine extras, Dockerfile COPY inputs
and exclusion of private dotenv from its context. No actual bot image build or
live service/account operation was performed.

Independent final whole-scope Trellis review found no additional defect or spec
drift. Its combined regression gate passed **140 tests, 362 deselected in
146.63s**; Bash syntax also passed for deploy/engines.sh. Exact command:

```bash
./hako python -m pytest tests/unit/test_preview_lifecycle.py tests/unit/test_dispatcher.py tests/unit/test_settings.py tests/unit/test_telegram_settings.py tests/unit/test_onebot_adapter.py tests/unit/test_engine_deployment.py tests/integration/test_onebot_protocol.py tests/integration/test_telegram_protocol.py -q -k 'refreshes_all_selected or refuses_legacy or removes_only_verified or preserves_foreign_and_unverified or without_target_uses_profiles or invalid_profiles or explicit_target_overrides or status_follows_selected or status_stream or status_redaction or public or recall or startup_injects'
```

Classification remains **human-optional** for separately authorized real
image/deployment/account verification; offline implementation completion does
not depend on a user reply. The new full `./kisara.sh test -q` gate passed
**1024 tests, 1 skipped, 3 existing PTB warnings in 315.57s**. The skip remains
the Docker image's missing Git CLI; the warnings remain RetryAfter timedelta
deprecations. Earlier 997-pass evidence covers only the public-feature scope;
this 1024-pass result covers the final combined implementation. No application
code changed after the earlier public gate, and no code fixes followed preview
review. Those checks preceded the delivery commit below; no deployment, archive
or push occurred.

## Local delivery and follow-up diagnosis — 2026-10-13

The user requested “提交”. Committed the reviewed 26 code/test/docs/spec paths as
`7da12cd14a523b56e4491349c40cfb949d0ef3a7`:
`feat(bot): add public commands and refresh preview workflow`.
Task/mainline/journal records follow separately. Private dotenv and runtime data
are excluded. No source changed since the final 1024-pass gate; staged whitespace
checks passed. Archival, deployment, service migration and push remain excluded.

The user then reported preview stop telegram refusing ownership. A fresh scoped
Docker ps read confirmed the same `kisara-telegram-1` (`4f1b8e7fb9d2`) is still
exited, now reported 47 hours ago. The preview source rejects non-preview-owned
containers before mutation; the ordinary targeted stop/down path uses Compose
stop and retains container objects. No service was changed. The user highlighted
the redundant lifecycle guards; consolidating ordinary/preview lifecycle is a
proposed follow-up, not implemented or included in this work commit.
