# Proposed commit and completion plan

The user reported the result satisfactory and explicitly authorized committing
the current directory including all other dirty files. Reinspection identified
user changes to `.gitignore` and font guidance in the news example; both are
included without reverting them. Ignored runtime/private files remain excluded.
The user also requested preserving all changes on the original mainline branch
`keiyaku-no-kisu`; both branches still share the same starting commit, so the
feature commits will be integrated there by a local fast-forward merge.

Work commit completed: `cce8c9d` on `feat/daily-news-private-push`; all 18
inspected product/spec/test files, including the additional user changes, are
committed. Archive/journal bookkeeping and the mainline fast-forward follow.

## 1. Work commit

Subject: `feat(news): add scheduled private QQ push`

Exact body:

```text
Add opt-in personal QQ recipients to the existing OneBot daily-news schedule.
Private recipients share push_time with groups, use the global user allowlist,
and work without enabling group functionality. Explicit push_users TOML values
override the comma-separated environment fallback, including an empty list.

Keep the deployed group completion schema and APIs unchanged and add a separate
private completion table in the existing state database. Preserve common content
generation, confirmed-success checkpoints, retry and connected-session cleanup.
Document schedule integration, configuration, operations and executable specs.
Include the user's additional ignore-rule and news font-configuration guidance
changes as explicitly requested.

Validation: focused Docker suite 82 passed; full ./dev.sh --all suite 129 passed
on Python 3.12.14; git diff --check and task context validation passed.
Real QQ reachability and live private-image receipt have not been verified.
Remote unknown outcomes retain the existing possible-duplicate limitation.

Co-authored-by: OpenAI Codex <codex@openai.com>
```

Explicit candidate files:

- `.env.example`
- `.gitignore` (user-authorized additional dirty changes)
- `.trellis/spec/backend/database-guidelines.md`
- `.trellis/spec/trellis-plus/configuration-storage.md`
- `config/features/news/config.toml.example`
- `deploy/compose.yaml`
- `docs/application-template.md`
- `docs/operations.md`
- `src/kisara/application/services/daily_news.py`
- `src/kisara/bot/adapters/onebot_v11.py`
- `src/kisara/bot/main.py`
- `src/kisara/config/feature_files.py`
- `src/kisara/config/settings.py`
- `src/kisara/infrastructure/persistence/news_delivery.py`
- `tests/integration/test_onebot_protocol.py`
- `tests/unit/test_news_delivery.py`
- `tests/unit/test_news_push.py` (new)
- `tests/unit/test_settings.py`

The template's D schedule section was requested and written earlier in this
same conversation; it is recognized, authorized work and is included along
with this task's news updates. Additional user-edited ignore rules and font
guidance were explicitly authorized after the final review. No other
unrecognized dirty product file was found.
Actual `.env`, feature `config.toml`, runtime media/databases and personal
platform settings are excluded.

## 2. Task archive and session journal

After the work commit, use the normal Trellis finish workflow to archive
`daily-news-private-push` and record the session journal. The scripts create
separate bookkeeping commits; task planning/context/review evidence belongs
in that archive, not in the product work commit. Preserve the approved order:
work commit, archive commit, journal commit. Afterward return to
`keiyaku-no-kisu` and fast-forward merge the feature branch, retaining all
committed user and feature changes. No pushing or deployment.

## Review gate

Implementation and automated checks passed. Independent full-scope review found
no product/spec defects and made no changes; exact coverage is in `review.md`.
Human review classification is **human-required for real QQ delivery acceptance**;
simulated protocol tests cannot establish account reachability. Request explicit
confirmation to commit the implementation with that live acceptance deferred.
The user has now authorized committing all inspected dirty files and integrating
the results into the original mainline; no additional confirmation is needed.
The manual procedure is in `docs/operations.md`; no real QQ send or runtime
configuration change is part of this commit plan.
