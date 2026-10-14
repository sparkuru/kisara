# Journal - kisara (Part 1)

> AI development session journal
> Started: 2026-09-26

---


## Session 1: Complete Trellis bootstrap guidelines
<!-- trellis-session: v=2 fp=2ebee66c66bd2bd0 -->

**Date**: 2026-09-27
**Task**: Complete Trellis bootstrap guidelines
**Branch**: `keiyaku-no-kisu`

### Summary

Completed source-backed backend guidelines and shared Trellis initialization; reviewed docs, provenance, framework hashes, context manifests, and whitespace; archived the existing bootstrap task.

### Main Changes

- Filled five backend guideline documents and their index; synchronized project-owned delivery policy.
- Tracked reviewed shared initialization files and verbatim upstream license/provenance while excluding personal configuration and runtime state.

### Git Commits

| Hash | Message |
|------|---------|
| `86fd274` | docs(trellis): initialize workflow and backend guidelines |

### Testing

- [OK] Documentation/source review passed; 35 relative links and all backend placeholder checks passed.
- [OK] Task context validation passed; 33 framework hashes and exact installed license bytes matched; staged whitespace check passed.
- [OK] Application and live QQ tests were not applicable to the documentation-only scope; human-not-needed.

### Status

[OK] **Completed**

### Next Steps

- No active task remains. Future product work requires user-selected scope.


## Session 2: Daily news private QQ schedule and mainline integration
<!-- trellis-session: v=2 fp=6b4fc3b9e427333c -->

**Date**: 2026-09-27
**Task**: Daily news private QQ schedule and mainline integration
**Branch**: `feat/daily-news-private-push`

### Summary

Added scheduled personal QQ news delivery sharing group push_time; preserved and committed all user edits and prepared local mainline integration.

### Main Changes

- Added push_users authorization, private-only scheduling, additive durable private delivery state, configuration and operations documentation.
- Included user-edited ignore rules and CJK font configuration guidance, preserving all inspected dirty files.

### Git Commits

| Hash | Message |
|------|---------|
| `cce8c9d` | feat(news): add scheduled private QQ push |

### Testing

- [OK] Focused Docker suite: 82 passed; full dev.sh --all: 129 passed on Python 3.12.14; independent review found no defects.
- [OK] News example TOML parsing, git diff --check and task context validation passed.

### Status

[OK] **Completed**

### Next Steps

- Real QQ live acceptance remains separately deferred; integrate the completed feature branch into keiyaku-no-kisu by local fast-forward.


## Session 3: Manual daily news cache clearing
<!-- trellis-session: v=2 fp=a084f8a85570cd56 -->

**Date**: 2026-09-27
**Task**: Manual daily news cache clearing
**Branch**: `keiyaku-no-kisu`

### Summary

Added the 清除新闻缓存 trigger to clear current-day PNG and HTML caches with authorization, locking, safe error handling, and fresh fetching on the next request; reviewed and archived the task.

### Main Changes

- Added service clearing, shared command routing, enabled-feature help, regression tests, operations documentation, and storage contract.

### Git Commits

| Hash | Message |
|------|---------|
| `e989caf` | feat(news): add manual current-day cache clearing |

### Testing

- [OK] 46 focused tests passed via hako; isolated full suite passed 155 tests on Python 3.12.14.
- [OK] Initial root full suite: 152 passed and 3 existing settings tests failed due to local feature config affecting cwd-relative loading; private configuration unchanged.
- [OK] git diff --check passed; no configured lint/type-check; no live QQ validation or deployment.

### Status

[OK] **Completed**


## Session 4: Forwarded video count investigation
<!-- trellis-session: v=2 fp=29bb6f56663f4bd4 -->

**Date**: 2026-09-28
**Task**: Forwarded video count investigation
**Branch**: `keiyaku-no-kisu`

### Summary

Confirmed the preview counts all 12 videos in the nested forward; self-forwarding exposed no new videos. No product code change.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Read-only OneBot get_msg/get_forward_msg probes compared original and self-forwarded messages.
- [OK] Checked archive metadata and the configured 100 MiB per-file limit.

### Status

[OK] **Completed**


## Session 5: Setu quoted results and size units
<!-- trellis-session: v=2 fp=5a50b3a96644f4cb -->

**Date**: 2026-09-28
**Task**: Setu quoted results and size units
**Branch**: `keiyaku-no-kisu`

### Summary

Quoted setu results now target each triggering user command; setu transfer caps use K/M/G strings and the private config is updated.

### Main Changes

- Preserved direct partial-failure retry selection while quoting normal, direct, and retry results.
- Converted setu caps to 1024-based K/M/G syntax; rejected old integers and malformed values.
- Isolated settings tests from private feature files and recorded the setu contracts in specs.

### Git Commits

| Hash | Message |
|------|---------|
| `0cd7419` | feat(setu): quote save results and parse size limits |

### Testing

- [OK] ./dev.sh --all: 191 passed; git diff --check passed; task context validation passed.

### Status

[OK] **Completed**

### Next Steps

- Preview Kisara and NapCat containers were stopped; live QQ rendering awaits a preview restart and user check.


## Session 6: Restore daily news with labeled fallback
<!-- trellis-session: v=2 fp=0442dc6c1a2d612f -->

**Date**: 2026-10-04
**Task**: Restore daily news with labeled fallback
**Branch**: `keiyaku-no-kisu`

### Summary

Restore /news during upstream publication delays with a prominent yesterday warning, immutable inline PNGs and no fallback cache; preserve once-per-day scheduled completion.

### Main Changes

- Separate the known source notice from 15 validated actual headlines; retain warning in image and text for both engines.
- Refetch every fallback request, discard fallback HTML cache, and resume normal dated caching after publication without changing prior result bytes.
- Preserve authorization, aliases, strict dates/headlines and existing scheduled group/private checkpoints; update operations, feature docs, and storage spec.

### Git Commits

| Hash | Message |
|------|---------|
| `0db32e3` | fix(news): deliver labeled fallback during publication delays |

### Testing

- [OK] Focused news/push/delivery/dispatcher suites: 78 passed; full offline Docker suite: 215 passed; git diff --check and context manifests passed.
- [OK] Rendered and visually inspected actual source HTML as a 960x5648 PNG; verified notice, path=None and no dated HTML/PNG publication.

### Status

[OK] **Completed**

### Next Steps

- No deployment or push performed; rebuild/restart through the normal deployment path when desired.


## Session 7: Telegram entry point and engine routing
<!-- trellis-session: v=2 fp=13e7c200e2983b94 -->

**Date**: 2026-10-04
**Task**: Telegram entry point and engine routing
**Branch**: `feat/telegram-bot`

### Summary

Implemented Telegram ping/help/news/scheduled news/music, static feature routing and switches, isolated Compose engines and targeted lifecycle operations. Full regression: 311 passed; SDK lifecycle/protocol, journal recovery and deployment selection verified. User approved work commit with real account/network/music-provider acceptance pending. No online services operated or remote push performed.

### Git Commits

| Hash | Message |
|------|---------|
| `1152184` | feat(bot): add Telegram entry point and engine-aware routing |

### Status

[OK] **Completed**


## Session 8: Engine configuration and Telegram message summaries
<!-- trellis-session: v=2 fp=0a8d397a7b2eacd2 -->

**Date**: 2026-10-04
**Task**: Engine configuration and Telegram message summaries
**Branch**: `feat/telegram-bot`

### Summary

Namespaced engine dotenv inputs with legacy compatibility; migrated local configuration and enabled redacted Telegram receive/send logs.

### Main Changes

- Added per-engine configuration namespaces, presence-based legacy fallback, and TOML override compatibility.
- Added opt-in Telegram message summaries with token redaction before message chunking.
- Migrated private configuration and restarted only Telegram; QQ containers remained unchanged.

### Git Commits

| Hash | Message |
|------|---------|
| `d89fdbe` | feat(config): namespace engines and add Telegram message logs |

### Testing

- [OK] 355 offline tests passed; synthetic Compose matrices, Bash syntax, and diff checks passed. Three existing PTB deprecation warnings remain.

### Status

[OK] **Completed**


## Session 9: Setu archive saving and progress notices
<!-- trellis-session: v=2 fp=189598bd99da1f5f -->

**Date**: 2026-10-09
**Task**: Setu archive saving and progress notices
**Branch**: `feat/setu-archive-files`

### Summary

Implemented and committed quoted archive saving, native file streaming, renewed-source retry and start notices; deployed acceptance remains pending.

### Main Changes

- Preserve archive names with archive-only collision timestamps; support quoted ordinary files and canonical bounded native streaming.
- Retain failed batch checkpoints across renewed source actions and announce pending-kind counts before transfer.

### Git Commits

| Hash | Message |
|------|---------|
| `c3e2f324e3a4a780702cc5c84b3deb670f48d807` | feat(setu): save archive files and announce save progress |

### Testing

- [OK] 308 focused and 580 full-suite tests passed; whitespace and 14/12 task manifests passed.
- [OK] Real 109092709-byte native temporary copy matched original cache SHA-256 under the bot UID.

### Status

[OK] **Completed**

### Next Steps

- Apply the new OneBot image and verify actual start/final replies plus SQLite completion; keep the task in_progress until live acceptance.


## Session 10: Complete and archive Trellis Plus gap remediation
<!-- trellis-session: v=2 fp=9c59db483154db8f -->

**Date**: 2026-10-09
**Task**: Complete and archive Trellis Plus gap remediation
**Branch**: `chore/trellis-plus-gaps`

### Summary

Repaired 22 prospective GAPs; user approved archival after review. Archive fc0d64f uses exact task scope and one Codex trailer. Final self-check: 45 PASS, 1 historical GAP, 6 UNKNOWN, 5 N/A.

### Main Changes

- Completed shared loading/development/archive policy, source-aware mainline, exact notices and preview lifecycle/readiness/diagnostics.
- Preserved private dotenv values, protected Trellis files, live services and Setu pending acceptance.

### Git Commits

| Hash | Message |
|------|---------|
| `6f8f043910e444cf1f2e18a0d5c26ef0668044f7` | feat(preview): complete Trellis Plus gap remediation |

### Testing

- [OK] 643 full-suite tests passed in Docker; 3 existing PTB warnings. Bash syntax and whitespace checks passed.

### Status

[OK] **Completed**

### Next Steps

- Guided read-only Pulse; real preview cold-start/account/device and update/Setu-loading checks need separate authorization or evidence.


## Session 11: Telegram tgsetu implementation and offline verification
<!-- trellis-session: v=2 fp=685aed27b0697cce -->

**Date**: 2026-10-11
**Task**: Telegram tgsetu implementation and offline verification
**Branch**: `feat/telegram-tgsetu`

### Summary

Implemented the approved feature on feat/telegram-tgsetu; work is uncommitted. Final offline suite and official server image checks passed; real account/deployment acceptance remains separate.

### Main Changes

- Native on/off activation, durable per-file archive/retry/recovery, caption/album naming and local Bot API deployment preparation.
- Independent review fixed cache symlink aliasing, logical-count wording, readiness fixtures and saturated-worker album deadlines.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Final ./dev.sh --all -q: 786 passed, 3 existing PTB warnings; shell syntax, manifests, diff and documentation checks passed.
- [OK] Official Bot API 10.3 image build and network-none version/library/license plus synthetic UID10001 read-only-cache smoke passed.

### Status

[OK] **Completed**

### Next Steps

- Review concrete task validation and prepared live acceptance; no live deployment, account switch, commit or archive was performed.


## Session 12: Unify selected-engine configuration roots
<!-- trellis-session: v=2 fp=989ac249df143ab7 -->

**Date**: 2026-10-11
**Task**: Unify selected-engine configuration roots
**Branch**: `feat/telegram-tgsetu`

### Summary

Implemented user-approved config/<engine>/features follow-up, preserving prior TgSetu work. Canonical root is consistent across Compose/hako/direct execution; work remains uncommitted and undeployed.

### Main Changes

- Explicit root injection for ordinary/dedicated/group settings; same-path isolated Compose mounts, shared fonts and moved OneBot examples.
- Copied existing private chat/news/setu bytes and modes without overwrite, retained old ignored backups, broadened all-engine private-file ignores.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Independent focused gate 202 passed/1 Git-dependent skip; host synthetic Git checks covered private/examples, sanitized real Compose checked all roots/fonts.
- [OK] Final ./dev.sh --all -q: 825 passed, 1 separately verified Git-dependent skip, 3 existing PTB warnings; manifests/diff/local links clean.

### Status

[OK] **Completed**

### Next Steps

- Activate via targeted container recreation when authorized; existing broad preview fingerprint behavior documented; real account acceptance/commit/archive remain unperformed.


## Session 13: 统一 kisara.sh 命令入口
<!-- trellis-session: v=2 fp=c56dc0c98fbeaa28 -->

**Date**: 2026-10-11
**Task**: 统一 kisara.sh 命令入口
**Branch**: `feat/telegram-tgsetu`

### Summary

完成用户批准的 CLI 入口收敛并独立复核；源代码仍未提交，任务因既有真实账号验收保持 in_progress。

### Main Changes

- 新增 kisara.sh，console/test 走 hako，preview/up/down 等走 deploy/engines.sh；旧四脚本保留临时转发及 start 选择菜单。
- 预览显式目标优先于环境选择，保持旧归属标签、就绪、定向清理和本地 API 分阶段启动；更新操作文档、规格及任务主线记录。

### Git Commits

(No commits - planning session)

### Testing

- [OK] ./kisara.sh test -q: 907 passed, 1 Git-dependent skip previously verified on host, 3 existing PTB warnings; independent focused gate 191 passed/1 skip.
- [OK] 新入口帮助及真实离线控制台 /quit 通过；Bash 语法、可执行权限、差异空白、新文件空白、22 份 Markdown 目标及 19-entry manifests 通过。ShellCheck/shfmt 未安装。

### Status

[OK] **Completed**

### Next Steps

- 实际服务部署和 Telegram 账号验收仍待单独操作范围；未执行服务/账号操作、提交或归档，保留 Setu 独立任务。


## Session 14: 删除旧脚本并完成 OneBot 预览转换
<!-- trellis-session: v=2 fp=e2dcec4b67aaaeb5 -->

**Date**: 2026-10-11
**Task**: 删除旧脚本并完成 OneBot 预览转换
**Branch**: `feat/telegram-tgsetu`

### Summary

用户批准删除四个旧入口，并单独授权移除已停止的 QQ 部署容器后按 kisara.sh preview 启动；实际发现并修复 NapCat 缺少 Node 和 HTTP 根路径重定向的探针误判。源代码仍未提交，TgSetu/Setu 受控账号验收继续保持待验收。

### Main Changes

- 删除 deploy.sh/dev.sh/start.sh/preview.sh；迁移真实 canonical 测试和当前指导，保留历史验证及 preview.sh 存储归属标签。
- NapCat 用既有 Python 标准库检查 /webui/ HTTP2xx 与 TCP3001并解析监听器；无代理/重定向/正文输出，保留其他引擎探针和所有权/回滚。
- 按授权移除两停止 QQ 容器且无删除卷标志，启动 OneBot 预览，确认原登录/配置/state 存储保留且 config/onebot 挂载生效；原 Telegram 容器未动。

### Git Commits

(No commits - planning session)

### Testing

- [OK] 最终 ./kisara.sh test -q:893 passed,1 Git-dependent skip previously host-verified,3 existing PTB warnings,176.59s；真实 HTTP/TCP/重定向/代理/隐私、无 Node 和远程 Docker 回归通过独立复核。
- [OK] 真实 ./kisara.sh preview 与 preview status 均返回 System is ready；20-entry manifests/23 Markdown targets/Bash syntax/diff checks passed。ShellCheck/shfmt 未安装。

### Status

[OK] **Completed**

### Next Steps

- 保留用户要求运行的 QQ 预览；控制功能回执/Telegram TgSetu 账号检验、Telegram 激活及提交归档需其各自范围；保留 Setu 独立任务。


## Session 15: Continuous preview bot logs and combined work commit
<!-- trellis-session: v=2 fp=6ad226d33c0129a0 -->

**Date**: 2026-10-11
**Task**: Continuous preview bot logs and combined work commit
**Branch**: `feat/telegram-tgsetu`

### Summary

Implemented continuous selected-bot preview logs with per-line redaction and interrupt cleanup; user approved combined Telegram/configuration/CLI work commit. Task archival and push remain unperformed.

### Main Changes

- Preview status follows the last 80 lines and new selected owned bot logs; Ctrl+C ends viewing only, with all invocation readers reaped.
- Combined work commit includes Telegram archiving/local API preparation, engine roots, canonical kisara.sh and NapCat probe corrections; prior session journals are retained.

### Git Commits

| Hash | Message |
|------|---------|
| `2782454` | feat: add Telegram archive tooling and continuous preview logs |

### Testing

- [OK] Full Docker suite: 913 passed, 1 skipped, 3 existing PTB warnings; independent 20-case streaming gate passed.
- [OK] Real 12-second preview status/interrupt smoke passed; Kisara/NapCat identity, running state, start time and PID were unchanged.

### Status

[OK] **Completed**

### Next Steps

- Retain requested running QQ preview. Telegram controlled account/deployment acceptance and task archival require their own scope; no push performed.


## Session 16: Review existing tasks and consolidate local branches
<!-- trellis-session: v=2 fp=d4a396212bedc0f5 -->

**Date**: 2026-10-11
**Task**: Review existing tasks and consolidate local branches
**Branch**: `keiyaku-no-kisu`

### Summary

Reviewed all three active tasks without creating a task. Archived completed preview-status-logs as 47ea1cc; kept Setu and Telegram in progress for missing account acceptance. Fast-forwarded all local work into keiyaku-no-kisu and deleted both fully merged source branches.

### Main Changes

- Updated mainline archive links, task work-commit provenance and pending acceptance notes; only keiyaku-no-kisu remains locally.

### Git Commits

| Hash | Message |
|------|---------|
| `e333af8` | chore: record task review and local branch integration |
| `2782454` | feat: add Telegram archive tooling and continuous preview logs |

### Testing

- [OK] Fresh Docker preview streaming gate: 20 passed, 89 deselected, 78.03 seconds; Bash syntax and merge-range whitespace passed.
- [OK] Mainline links, all 10 completed archive records, 2 pending active records, single archive attribution and retention of both deleted branch tips verified.

### Status

[OK] **Completed**

### Next Steps

- Complete the separately prepared Setu and Telegram account acceptance before archiving those tasks; no live account/service operation or push performed in this cleanup.


## Session 17: Accept and archive Setu archive attachments
<!-- trellis-session: v=2 fp=0673d4bcbff8f8a1 -->

**Date**: 2026-10-11
**Task**: Accept and archive Setu archive attachments
**Branch**: `keiyaku-no-kisu`

### Summary

User confirmed setu-archive-files passed acceptance. Recorded the user-reported live result, marked the existing task completed and archived it as 10feef1; updated mainline paths and acceptance state. Telegram remains the sole active task.

### Main Changes

- Preserved historical automated/native-transfer evidence and diagnostics; no new task, account/service operation or push.

### Git Commits

| Hash | Message |
|------|---------|
| `c3e2f32` | feat(setu): save archive files and announce save progress |

### Testing

- [OK] Record-only closure; existing 308 focused/580 full passes retained, no new application test run.

### Status

[OK] **Completed**

### Next Steps

- Telegram task still requires its separately prepared account/deployment acceptance.


## Session 18: Public command features and Telegram UID
<!-- trellis-session: v=2 fp=bee727ff54d5bce2 -->

**Date**: 2026-10-12
**Task**: Public command features and Telegram UID
**Branch**: `keiyaku-no-kisu`

### Summary

Implemented independent dotenv public features with group switch retained and self-ID lookup; independent review and full offline Docker gate passed. No deployment or commit.

### Main Changes

- Added TELEGRAM_PUBLIC_FEATURE, ONEBOT_PUBLIC_FEATURE and OFFICIAL_PUBLIC_FEATURE; safely appended only missing private dotenv keys.
- Wired exact ordinary-feature authorization and Telegram /tguid, retaining native/admin gates and fixing disabled QQ fallback plus recall metadata.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Full ./kisara.sh test -q: 997 passed, 1 missing-Git skip, 3 existing PTB warnings; independent public gate 85 passed.
- [OK] Dotenv scratch cases 7 passed; git diff --check and task contexts passed.

### Status

[OK] **Completed**

### Next Steps

- User may choose targeted deployment or separately authorize commit/archive; task remains in_progress with checked uncommitted changes.


## Session 19: Preview profile selection, rebuild and platform logs
<!-- trellis-session: v=2 fp=b5df754e37f7d1ae -->

**Date**: 2026-10-13
**Task**: Preview profile selection, rebuild and platform logs
**Branch**: `keiyaku-no-kisu`

### Summary

Extended the existing public-feature task after user approval. Unified profile-based preview and Official Compose images, platform log labels, preserved ownership/storage and completed combined regression.

### Main Changes

- No-target preview uses COMPOSE_PROFILES; down/build/start rebuilds every selected application image using current inputs and creates with current settings.
- Official-only preview uses Compose; legacy owned hako cleanup verifies runtime engine. Platform log hints/prefixes retain distinct OneBot stream readers.
- Preserved prior public-feature and /tguid edits; synchronized task/mainline/specs and operations without deployment, commit or archive.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Focused preview gate: 237 passed, 1 existing missing-Git skip in 293.33s.
- [OK] Independent combined review: 140 passed, 362 deselected in 146.63s; no additional findings.
- [OK] Full ./kisara.sh test -q: 1024 passed, 1 existing missing-Git skip, 3 existing PTB warnings in 315.57s. Bash syntax and diff checks passed; ShellCheck/shfmt unavailable.

### Status

[OK] **Completed**

### Next Steps

- Retain uncommitted changes and current task; real image/deployment/account verification and delivery remain separately authorized.


## Session 20: Commit public commands and preview workflow
<!-- trellis-session: v=2 fp=a90a63110778142a -->

**Date**: 2026-10-13
**Task**: Commit public commands and preview workflow
**Branch**: `keiyaku-no-kisu`

### Summary

User authorized local delivery. Committed validated code/test/docs/spec changes, updated task/mainline, and diagnosed the ordinary Telegram ownership refusal without service operations.

### Main Changes

- Work commit 7da12cd contains 26 reviewed code/test/docs/spec paths for public features, tguid and preview behavior.
- Retained task and archive boundaries; ordinary/preview lifecycle simplification is proposed after user feedback, not implemented.

### Git Commits

| Hash | Message |
|------|---------|
| `7da12cd14a523b56e4491349c40cfb949d0ef3a7` | feat(bot): add public commands and refresh preview workflow |

### Testing

- [OK] Existing final full suite: 1024 passed, 1 missing-Git skip, 3 existing PTB warnings; no source change since that gate. Staged diff checks passed.
- [OK] Fresh scoped Docker ps confirms the existing Telegram deployment is stopped; no live lifecycle mutations.

### Status

[OK] **Completed**

### Next Steps

- Resolve user-selected lifecycle simplification or deployment follow-up separately; no push or archive performed.


## Session 21: Unified ordinary and preview container lifecycle
<!-- trellis-session: v=2 fp=5f01e5b2ccdf6f30 -->

**Date**: 2026-10-13
**Task**: Unified ordinary and preview container lifecycle
**Branch**: `feat/container-lifecycle`

### Summary

Approved down-only task implemented and independently checked; final full offline regression passed. Code remains uncommitted; no live bot or private dotenv operations.

### Main Changes

- Shared exact repository identity/preflight/down helper; ordinary-preview roundtrip, QQ switching and scoped OneBot forwarding.
- Removed fingerprint/reuse/partial/build-existing and automatic rollback gates; selected application startup refreshes configuration while auxiliaries reconcile normally.
- Synced task artifacts, mainline, operations and executable code specs; retained both QQ modes in read-only diagnostics and captured preview switch output.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Independent core/log subset: 70 passed, 163 deselected in 237.94s.
- [OK] Final ./kisara.sh test -q: 1067 passed, 1 existing missing-Git skip, 3 existing PTB warnings in 500.97s.
- [OK] Six-shell Bash syntax and whitespace checks passed; ShellCheck/shfmt unavailable, application lint/type-check unconfigured.

### Status

[OK] **Completed**

### Next Steps

- Uncommitted code is ready for review; task stays in_progress. Real deployment/account checks, commit/archive/push require separately scoped authorization.


## Session 22: Commit unified container lifecycle
<!-- trellis-session: v=2 fp=4f67372d0402ba28 -->

**Date**: 2026-10-14
**Task**: Commit unified container lifecycle
**Branch**: `feat/container-lifecycle`

### Summary

User authorized local delivery with 提交. Committed validated lifecycle code/tests/docs/specs and recorded the task work hash; no new implementation, archive, push or live operation.

### Main Changes

- Work commit 6af84c6 unifies ordinary/preview management and down-only behavior; task and mainline now record committed delivery.

### Git Commits

| Hash | Message |
|------|---------|
| `6af84c646c07c069d8f35f77308e509b401b29ee` | fix(deploy): unify container lifecycle |

### Testing

- [OK] Previously completed final full gate: 1067 passed, 1 existing skip, 3 existing PTB warnings; independent subset 70 passed.
- [OK] Commit-time Bash syntax and staged whitespace checks passed; full suite not repeated for unchanged code.

### Status

[OK] **Completed**

### Next Steps

- Retain the active task without archive; no push, merge or deployment performed.
