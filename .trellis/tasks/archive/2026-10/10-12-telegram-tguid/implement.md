# Implementation and verification plan

## Phase gate

- [x] Task creation approved.
- [x] User chose dotenv lists and retained the group master switch.
- [x] PRD converged; design specifies configuration/routing/native boundaries.
- [x] Present final planning summary and obtain a subsequent explicit approval.
- [x] Validate curated implement/check context and run task.py start only after
  that approval. No implementation dispatch while planning.

Approval evidence: user “开始”, 2026-10-12. Both manifests validated with nine
real entries; task start succeeded and the Trellis implement role was dispatched.
No source commit, archive, live account operation or deployment is authorized.

The existing four-file product draft predates the task-recording response and
is untested. Review it as a draft, replace its hardcoded Telegram permission,
and correct its unconditional group/public help wording. It is not a completed
implementation or a reviewed reference implementation.

## Execution

1. Dispatch the available Trellis implement role with this task path and curated
   context. Prefer native context injection, require explicit child-side reads
   if injection is incomplete. Own only the source/config/test/operational-doc
   files listed in design.md; preserve unrelated changes. Main owns task records,
   specs, private dotenv maintenance, commit decisions and wrap-up.
2. Add independent selected-engine public-feature parsing/defaults and strict
   canonical ordinary-feature validation. Wire startup and both OneBot Compose
   profiles plus Telegram/official. Do not widen credential/environment sharing.
3. Replace the command-specific allow exception with exact registered-feature
   authorization. Preserve group master switch, normal allow rules, enablement,
   duplicate suppression and per-feature constraints. Review all QQ fallback
   branches so a public feature cannot trigger a different feature.
4. Keep native Setu/export/TgSetu/push gates strict. If quote preparation needs
   shared command authorization, inject a pure callback specifically there;
   do not consume deduplication or authorize native workflows through it.
5. Finish the `/tguid` handler/help and existing module/operations documentation.
6. Add focused behavioral checks: sender UID versus chat/quote ID, unlisted
   private users, group on/off, aliases, other-bot targeting, unknown/prefix
   commands, disabled/missing handlers, bad arguments, duplicates, cross-chat
   IDs, engine isolation, configuration defaults/explicit empty/error inputs,
   no provider/history/native side effects on rejection and OneBot fallback.
7. Main updates applicable project-owned code specs with actual signatures,
   matrix, good/bad cases and test points; reconcile old all-command-allow claims.
8. Main appends only missing private dotenv keys, if the file exists, using the
   established grammar and no value disclosure. Check a scratch fixture for
   custom/empty values, comments, line endings, duplicate keys and idempotence;
   ambiguity prevents changing that file, not the source implementation.

## Focused checks

```bash
./hako python -m pytest tests/unit/test_settings.py tests/unit/test_telegram_settings.py tests/unit/test_dispatcher.py tests/unit/test_telegram_adapter.py tests/unit/test_onebot_adapter.py tests/unit/test_engine_deployment.py tests/integration/test_telegram_protocol.py tests/integration/test_onebot_protocol.py -q
```

Use the existing Docker wrapper with no bot/credential mode. Run additional
existing native-flow suites if their boundaries change. The project has no
configured linter/type-checker; do not add one or report unrun checks.

## Independent review and final gate

- Dispatch the available Trellis check role after implementation with actual
  changed paths and this task's manifest. Require review of allow bypass scope,
  no fallback side effects, native/history boundaries and configuration isolation.
- Review child evidence, fix scoped defects, then run the required cross-layer
  gate `./kisara.sh test -q` and `git diff --check`.
- Record exact commands/results, changed files, any unavailable dependencies or
  checks, and the concrete human-review classification in task validation.
- Do not deploy, restart services, use live accounts, commit, archive, alter
  another task or push without the appropriate existing authorization.

## Risk and rollback checkpoints

Validate settings and routing before broad checks. Never fix a failure by
weakening allowlists, skipping native tests or changing feature enablement.
Unknown-scope changes return to the main session rather than widen the task.
Explicit empty public configuration restores strict global permission for that
engine. All private data, native state and stored jobs remain untouched.

## Completed checks

Implementation, independent review, spec synchronization and safe missing-key
dotenv maintenance are complete. Focused implement 444 passed/1 skipped, final
changed-router 111 passed, independent public gate 85 passed, and final complete
Docker suite 997 passed/1 skipped/3 existing warnings. See `validation.md` for
commands, evidence, actual scope and remaining uncommitted/undeployed state.

## Preview follow-up plan

The user chose to extend this task and selected COMPOSE_PROFILES-based startup.
The user approved the final follow-up summary with “可用”; the task is active
for preview implementation. Prior public-feature gates cover that earlier scope.

1. Completed: final summary approved with “可用”, manifests validated, and task
   reactivated for the approved preview implementation.
2. Dispatch Trellis implement with ownership of preview-runtime.sh,
   preview-console.sh, necessary existing forwarding helpers, affected lifecycle/
   CLI/deployment tests and operations docs. Preserve all existing task/public
   code edits. Main owns specs/task/mainline/journal and any user-owned dotenv.
3. Centralize no-target selection on effective COMPOSE_PROFILES; remove the
   KISARA_ENGINE single-engine override and retain explicit target precedence.
4. Make the existing image-based Compose preparation/start path apply to every
   bot, including Official-only; keep hako for offline checks. Add only the
   evidenced old owned Official-hako cleanup/conflict boundary, never foreign
   deployment adoption/removal. Preserve storage/ownership/readiness/local API.
5. Ensure default down/build/start consistently selects the same profile list,
   explicitly rebuilds existing selected application tags using current source
   input, and recreates with current settings. No implicit start in build/status/
   down; no unnecessary dependency/base/auxiliary upgrade or global no-cache flag.
6. Map log display prefixes and follow hints to onebot/telegram/official while
   keeping unique internal stream identities and all existing content/redaction.
7. Add meaningful fake-Docker lifecycle tests for selection conflicts, all-bot
   updates, source/settings freshness, image rebuild/use, Official-only behavior,
   legacy/foreign conflict, aliases, platform log names, stream failures, signals
   and persistent-data preservation. Test credential values remain undisclosed.
8. Run Bash syntax checks on changed shell files and available ShellCheck/shfmt
   without installing a competing toolchain. Run focused tests via existing hako:

   ```bash
   ./hako python -m pytest tests/unit/test_preview_lifecycle.py tests/unit/test_kisara_cli.py tests/unit/test_engine_deployment.py tests/unit/test_hako_deployment.py tests/unit/test_preview_readiness.py -q
   ```

9. Dispatch independent Trellis check for the whole combined changed scope,
   including earlier public permissions, then run `./kisara.sh test -q` after
   scoped fixes. Main updates code specs, acceptance/results and journal without
   committing/archiving automatically. Actual account/service operation remains
   outside this implementation approval.

Preview follow-up implementation and full-scope independent review are complete.
The focused five-suite gate passed 237 tests/1 missing-Git skip; independent
combined regressions passed 140 tests. Shell syntax and diff checks passed;
ShellCheck/shfmt are unavailable. No forwarder change was needed. Synthetic
fixtures cover the reviewed lifecycle contract; actual image/live account
verification remains separately scoped. The fresh full regression gate passed
1024 tests/1 missing-Git skip/3 existing PTB warnings in 315.57s. Implementation,
independent review and spec synchronization are complete; no commit/deployment
or archive was performed.

Subsequent delivery: the user's “提交” authorized local commits. Reviewed code,
tests, operations and specs were committed as 7da12cd; bookkeeping follows
separately. No code changes or additional runtime operation accompanied delivery.
