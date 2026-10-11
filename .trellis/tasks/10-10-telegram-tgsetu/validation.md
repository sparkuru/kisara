# Implementation and validation — 2026-10-11

The user's final-plan approval authorized implementation/checking. Work is on
`feat/telegram-tgsetu`, uncommitted. No real account operation, live deployment,
endpoint switch, task archive or other-task mutation was performed.

## Delivered behavior

- Telegram-only optional `/tgsetu on/off/status/retry`, private/global/feature
  authorization, persistent activation and durable independently checkpointed
  file jobs. Telegram `/setu` remains unavailable; OneBot behavior is preserved.
- SDK media normalization, UTF-16 hashtag parsing, one selected PhotoSize,
  shared initial album caption, frozen ordinals and late-member acceptance.
  Results distinguish logical units and actual received messages/files.
- Flat caption/original-document naming, compound extensions, bounded UTF-8
  names, complete-file no-replace publication and stable content conflict
  disambiguators. Partial success survives failure/retry/restart.
- Local getFile plus confined no-symlink chunk copy; known/actual byte caps,
  owned bounded workers and joined cancellation. Publication intent precedes
  linking; restart verifies bytes before repeating retrieval.
- Internal pinned official Bot API image, same-path RO cache for bot, matched
  UID 10001, staged startup/restart and preview integration. API ID/hash stay
  server-only, including the `hako` runtime wrapper.
- Bounded paced/coalesced in-memory notifications. Lost notices do not undo
  durable archive truth; the queue itself is not replayed across restart.

## Automated checks

| Command/check | Result |
| --- | --- |
| `./hako python -m pytest tests/unit/test_tgsetu_config.py tests/unit/test_tgsetu.py tests/unit/test_tgsetu_files.py` | 67 passed after final saturated-worker naming-window fix |
| Adapter/settings/dispatcher/protocol focused checks | 197 passed before final symlink regression; 3 existing PTB warnings |
| Reviewer adapter/protocol checks | 85 passed including in-cache file/directory symlink regressions; same warnings |
| Deployment/preview/server helper focused checks | 104 passed before final staged-restart failure case; that engine suite separately 38 passed |
| Reviewer readiness + hako fixture checks | 9 passed |
| Initial `./dev.sh --all -q` | 778 passed / 1 failed / 3 warnings; old readiness factory rejected new constructor keywords, fixed without weakening readiness assertion |
| Full suite before final naming-window regression | 784 passed, 3 existing PTB warnings, 145.97 seconds |
| Final `./dev.sh --all -q` | 786 passed, 3 existing PTB RetryAfter deprecation warnings, 155.15 seconds |
| Independent quiet/max-window regression checks | 5 passed, 24 deselected |
| Bash syntax: hako, engines.sh, preview-runtime.sh, server entrypoint/probe | Passed |
| Sanitized Compose `config --quiet` | Passed; no real rendered configuration printed |
| `git diff --check`, new-file trailing whitespace | Passed |
| Task manifest validation | Both curated 15-entry manifests passed without truncation warnings |
| Local Markdown targets | 11 documentation/task files checked; no missing targets |

The >20 MB test is a local byte fixture, not a Telegram download. Its traced
peak Python copy memory is below 2 MiB. Tests also cover per-unit caps,
concurrent same-name distinct bytes, same-content reuse across timestamps,
partial retries, cancellation, late captions/members, max grouping deadline,
foreign identity scope and seven-day metadata retention without archive deletion.

No configured linter/type checker exists. Host ShellCheck/shfmt are unavailable;
their passes are not claimed. Docker Python 3.12 tests do not prove all declared
Python runtime versions.

## Official image verification

Build and offline smoke passed. Build used a minimal temporary context containing
only the server Dockerfile and its two scripts, with no repository credentials.
Pinned source: Bot API commit `e3e9dd8e5b3d7ab8537cd5a10dc31d5ffa8f82d1`,
TDLib submodule `bc9c263e2bfee06aaab41e82db51a103376030bc`. Original licenses
and TDLib README are retained in the built image and inventoried in third_party.

- Image: `kisara-tgsetu-bot-api-smoke:10.3`,
  `sha256:d9a05f837f0cc7b91691417e7c275529cb268003ac3233b01e84d880b8ac73dd`.
- Network-none `--version`: Bot API 10.3; `--help` succeeded. Runtime `ldd`
  resolved all libraries; configured image user is `10001:10001`.
- Retained server/TDLib licenses and TDLib README are readable. Both original
  license files hash to
  `c9bff75738922193e67fa726fa225535870d2aa1059f91452c411736284ad566`.
- A synthetic labeled Docker volume seeded by the actual server image's UID
  10001 contains an owner-only 0600 fixture. A separate Python container with
  UID 10001 and the identical read-only mount reads the fixture; writing fails
  with EROFS. This proves the synthetic ownership/mount boundary, not an actual
  Bot API download or the deployed bot's account behavior.
- All smoke containers used `--rm` and network none. The exact owned fixture
  volume and minimal temporary build context were removed. The smoke image and
  build cache remain available. No server/account/SDK getFile operation ran.

Reproducible version/metadata checks (executed, no credentials):

```bash
docker run --rm --network none kisara-tgsetu-bot-api-smoke:10.3 --version
docker run --rm --network none kisara-tgsetu-bot-api-smoke:10.3 --help
docker image inspect --format '{{.Id}} {{.Config.User}}' kisara-tgsetu-bot-api-smoke:10.3
```

## Review and remaining acceptance

A separate Trellis reviewer loaded task/artifacts/specs and checked cross-layer
authorization, SDK isolation, naming, caps, cancellation, publication/recovery,
retry and deployment. It fixed the cache-path alias gap, clarified counts and
updated the readiness test stub. During final source review, the root session
found that busy transfer workers could extend the initial naming window. The
authorized active acceptance path now freezes due plans before enqueueing with
the same captured time, with no intervening await. Quiet/max tests block every
worker and verify late lower-ID caption/ordinal behavior before and after
release; both failed before the fix and passed afterward. Independent review
confirmed the fix. No remaining concrete code defect was reported.

[Prepared account acceptance](live-validation.md) covers real client forwards,
mixed albums, >20 MB retrieval, actual shared-volume permissions, off/denied
inputs, retry and restart. Account migration, Telegram network delivery and
Compose deployment remain unexecuted; offline tests do not prove them. Keep the
task in_progress pending that separate acceptance and any later commit/archive
scope. Preserve the existing Setu task and its pending live acceptance.

## Approved configuration-root follow-up — 2026-10-11

The user approved the recommended `config/<engine>/features` layout and
consistent Compose/hako/direct reads. [Follow-up boundary](research/config-root-unification.md)
records scope and acceptance; [engine code-spec](../../spec/trellis-plus/engine-config.md)
records signatures and migration rules.

Implemented explicit selected-root ordinary/dedicated/group loading, same-path
engine-only Compose mounts plus shared fonts, 10 versioned OneBot example moves,
all-engine private-file ignores, and synchronized current docs/module contracts.
No new environment root override or universal feature allowlist was added.

- Runtime focused suite: 168 passed.
- Independent configuration/deployment/wrapper review: 202 passed, 1 skipped.
  Git is absent in the Docker test image; independent host temporary Git
  fixtures verified 8 private paths ignored and 6 example paths trackable.
- Synthetic real Compose JSON verified all four bot engine-only roots and
  shared fonts. Other state/cache/archive/login mounts are unchanged.
- Private migration scratch checks passed: exact custom bytes and modes,
  groups JSON, equal-target/repeat no-op, conflicting target preflight refusal,
  retained originals, source/target link rejection.
- Actual local copy: chat/news/setu config.toml into config/onebot/features;
  contents and modes verified, old ignored files retained. No value was printed.
  Existing Telegram tgsetu config.toml is now correctly ignored too.
- Final `./dev.sh --all -q`: 825 passed, 1 skipped, 3 existing PTB warnings,
  133.11 seconds. The Git-dependent skip was separately verified on the host.
- Manifest validation: both 17-entry contexts fit without truncation warnings.
- Final local Markdown check: 13 documentation/task files, no missing targets;
  `git diff --check` and new-file trailing whitespace passed.

Independent review found no source blocker. Preview fingerprints retain their
preexisting conservative hash of all TOML/JSON, so unrelated config edits can
invalidate preview reuse while application loading stays engine-specific.
No fingerprint-policy redesign was included. Changed Compose mounts require
targeted recreation before real runtime acceptance; restart alone retains old
mounts. No service/account operation, commit or archive was performed.

## Approved command-entry follow-up — 2026-10-11

The user approved `./kisara.sh`, `hako`, and `deploy/engines.sh` as the public
entry, development executor and online lifecycle owner respectively.
[CLI boundary](research/unified-entrypoint.md) and
[executable contract](../../spec/trellis-plus/cli-entrypoints.md) record scope.

Implemented pure root help, offline console/test dispatch, detached up and
targeted lifecycle commands. Pytest arguments pass literally without adding the
entire suite to focused requests. Preview accepts explicit validated targets
ahead of env/dotenv selection without rewriting .env. Single official preview
retains owned hako; mixed profiles retain Compose. Existing preview labels,
readiness, local API staging, fingerprint and cleanup behavior are preserved.
Old deploy/dev/start/preview files temporarily forward, with start retaining
its engine-selection UI. Current operational docs/specs use the canonical entry.

- CLI/deployment/offline focused gate: 103 passed, 1 Git-dependent skip.
- Preview focused gate: 81 passed; two final added edge cases also passed.
- Final CLI gate after explicit-empty dev argument correction: 58 passed.
- Independent CLI/deployment/preview/readiness/hako gate: 191 passed, 1 skipped.
  Its collection preceded final supplementary cases; the full gate below
  verifies the final frozen source, including those cases.
- Final `./kisara.sh test -q`: **907 passed, 1 skipped, 3 existing PTB warnings**,
  165.25 seconds. Git is absent in the Docker image; the unchanged private-ignore
  fixture was separately verified on the host during configuration-root checks.
- Real `./kisara.sh console` with /quit: startup and zero-status exit passed.
  Root/help and preview/help passed without Docker or dotenv operations.
- Bash syntax for the canonical/compatibility/helper scripts, executable modes,
  `git diff --check`, and new CLI-file whitespace passed. ShellCheck/shfmt are
  unavailable; no application lint/type-check command is configured.
- Both context manifests validate with 19 entries and no truncation warnings.
- Local Markdown targets: 22 current documentation/spec/task files passed.

Independent review found and resolved the dev explicit-empty argument boundary
and a bare-help command in deployment docs. No outstanding source finding.
Online lifecycle tests use isolated fake Docker; actual service/account
operations, deployment, commits and archival remain unperformed. Keep this task
in_progress for the previously prepared live account acceptance.

## Approved script retirement — 2026-10-11

The user explicitly approved deleting deploy.sh, dev.sh, start.sh and preview.sh.
All four are absent; executable fixtures and callers use kisara.sh. Removed
24 obsolete compatibility cases and one wrapper-specific selection case;
five new real canonical selection cases retain engine/profile/dotenv/default
coverage. A canonical status test keeps recognizing stored preview.sh ownership
labels from a repository path containing spaces. Production runtime code was
unchanged during retirement. Current .env.example/docs/specs use the new entry;
the original design has an explicit current-entry correction, with historical
decision/executed-check records preserved.

- Focused CLI/engine/preview gate: 163 passed, 1 Git-dependent skip, 149.89 s.
- Independent five-suite gate: 172 passed, 1 skipped, 152.72 s; no findings.
- Retirement full `./kisara.sh test -q`: 887 passed, 1 skipped,
  3 existing PTB warnings, 175.29 s.
- Retained Bash syntax, modified Python module parsing and diff checks passed.
  These gates precede the subsequently discovered actual NapCat probe defect.

## Separately approved OneBot preview conversion and discovered probe defect

The user selected removing stopped QQ deployment containers and starting the
canonical preview, preserving mounted data and leaving Telegram unchanged.
Safe selection inspection showed effective KISARA_ENGINE=onebot even though
COMPOSE_PROFILES includes onebot,telegram. Stopped-state/project/service/mount
checks preceded removal of exactly kisara-napcat-1 and kisara-kisara-1, using
docker rm without force or volume-removal flags. All mounted login/config/state
storage was retained. The existing stopped Telegram container was untouched.

Two bounded starts passed configuration/image/start stages but failed NapCat
readiness. The owned-attempt cleanup removed their new QQ containers and kept
data. Read-only runtime facts establish a probe defect: node/nodejs are absent;
python3/curl/bash/awk exist; WebUI is enabled on port6099, IPv4 HTTP / and /webui
both return200 and TCP3001 connects. The application WebSocket had connected.
Thus login/reset/timeout expansion is not the evidenced correction. See
[probe research](research/preview-napcat-readiness.md). Temporary bounded logs
were removed; no private response body or credential was retained in records.

The bounded stdlib correction and actual start/status results below are
separate from the retirement gates above.

## NapCat correction and actual readiness result

Implemented bounded direct Python stdlib HTTP+TCP probes and /proc listener
reuse for NapCat through python3 -c, leaving Music Node and all bot PID/marker
checks unchanged. Compressed IPv6 mapping/scope remains correct. The generic
failure hint now distinguishes WebUI/socket readiness from login preparation.

An intermediate correction gate passed 891 tests but failed one remote-host
mock case: fake Docker assumed exec was argv0, ignoring --host prefix. The
fixture now indexes arguments relative to exec; production Docker invocation
was already correct. Fourteen focused helper/dispatch/remote/fallback cases
passed after this correction. This intermediate gate is not the final result.

Actual direct HTTP inspection then resolved another compatibility detail:
NapCat Python is3.10.12; / and /webui respond301, /webui/ and /webui/index.html
respond200. Earlier urllib200 reports followed redirects. The final direct
probe requests /webui/, preserving strict2xx, proxy isolation and TCP3001.
The real helper fixture models root301+canonical200 and rejects former GET /.

- Final readiness helper suite: 12 passed, 3.22 s. Success, HTTP503/TCP failure,
  all-proxy isolation, response/output privacy, exact source CLI and root301
  regression run through real local HTTP/TCP fixtures.
- Independent affected helper/dispatch/listener checks: 9 passed,
  91 deselected; final route-specific review: 5 passed, 7 deselected, 2.73 s.
- Bash syntax and diff checks passed; no independent source findings remain.
- Final frozen-source `./kisara.sh test -q`: **893 passed, 1 skipped,
  3 existing PTB warnings**, 176.59 s. The Git-dependent skip's unchanged fixture
  was separately verified on the host earlier in this task.
- Both 20-entry context manifests and 23 current Markdown file targets passed;
  no truncated contexts. ShellCheck/shfmt remain unavailable.
- The final user-authorized `./kisara.sh preview` attempt returned0 and
  `System is ready.` after the canonical-path fix became available to its next
  bounded probe. No readiness bypass or login/config reset was used.
- Separate actual `./kisara.sh preview status`: returned0, `System is ready.`;
  required NapCat HTTP6099/TCP3001 and current OneBot process marker passed.
  Published WebUI:127.0.0.1:6099; both listeners bind[::] in container namespace.
  Host HTTP browser URL is http://127.0.0.1:6099/ (local redirect to /webui/).
- Actual container/mount metadata confirms both new QQ objects own
  hako.scope=preview.sh, retain original QQ/config bind paths and the same
  kisara_kisara_state volume, and activate isolated config/onebot plus shared
  fonts. Telegram retains the exact original container ID and stopped status.
  Temporary captured startup logs were removed after recording safe facts.

This proves the scoped startup/status and preserved ownership/storage boundary,
not controlled feature delivery, sustained reliability, cross-device access,
Telegram /tgsetu retrieval or the separate pending Setu account acceptance.
The QQ preview remains running as the user requested; commit/archive unperformed.

## Combined work commit authorization

After completing preview-status-logs, the user approved the explicitly reviewed
105-path combined work commit covering this implemented task, engine configuration
roots, canonical command/probe changes and continuous preview logs. Final combined
worktree regression: 913 passed, 1 skipped, 3 existing PTB warnings. Workspace
journals, push and archive are excluded; this authorization does not perform or
complete the separately prepared Telegram account/deployment acceptance.
