# Application 功能开发模版

本文件供后续 agent 和开发者在 Kisara 中增加或修改功能时参考。内容以当前代码为准；`design.md` 描述的目标不自动视为已实现。新增功能前，先按下文确定入口、能力边界、配置来源和数据归属，再选择对应模版。当前没有自动发现功能的插件机制，命令与依赖需要显式接入。

## 使用约定

引用本模版时，请 agent 先把用户需求填入文末的“功能规格”，再给出**需求 → 代码位置 → 配置 → 状态/数据库 → 验证**对应表。实现完成后，逐项报告实际改动和验证结果；未涉及的项写“无”和原因。需求没有明确的数据保存、群聊权限或平台行为时，不要自行把功能扩大到这些范围。若模版与当前代码冲突，以当前代码和用户明确要求为准，并指出差异。

本模版提供可检查的实现约束，不能单靠一次引用保证 agent 理解或执行正确。验收应以代码差异、配置示例和针对性测试为证据。

### 功能说明的归属

每个功能的用户可见用途、触发命令与参数、适用引擎和会话、配置文件与关键字段、处理流程、持久化路径及失败/重试行为，写在对应 `src/kisara/application/services/<feature>.py` **文件开头的模块 docstring**。改功能时同步改这段说明，并以代码核对，不能只改帮助文本或模版。一个模块承载多个功能时（如 `public.py`），在同一开头 docstring 逐项说明；纯命令或适配器操作没有独立 service 时，写在实际实现模块的开头 docstring，并在 `application/services/__init__.py` 标出归属。Python docstring 保持英文，命令别名可用英文描述并指向分发器的完整列表。

`readme.md` 只保留项目简介、开发模版入口、版权与来源指引；功能细节不再放回 README。启动、部署与排障步骤放在 `docs/operations.md`，历史迁移记录放在 `docs/legacy-migration.md`。新增功能如改变运行步骤，应同步更新操作文档；不能把运行手册堆进 service docstring。

给后续 agent 的引用方式：

```text
请按 docs/application-template.md 实现以下需求：<需求>。
先填写功能规格和“需求 → 代码位置 → 配置 → 状态/数据库 → 验证”对应表，
再实现并运行相关测试。交付时逐项回填实际文件、配置优先级、存储路径、
数据库结构或无需数据库的原因，以及未验证的运行条件。
```

## 当前结构与处理路径

| 层 | 当前职责 | 主要位置 |
| --- | --- | --- |
| 启动与组装 | 读取配置、构造服务和分发器、选择协议适配器 | `src/kisara/__main__.py`、`src/kisara/bot/main.py` |
| 协议契约 | 定义 `MessageEvent`、`MessageSegment`、`DispatchResult`、`OutgoingMessage` | `src/kisara/bot/contracts.py` |
| 适配器 | 将平台消息归一化，发送文本、图片、音乐或执行平台操作 | `src/kisara/bot/adapters/onebot_v11.py`、`official.py` |
| 路由 | 用户和群组授权、消息去重、旧命令别名、参数校验、普通命令分发 | `src/kisara/bot/dispatcher.py` |
| 命令包装 | 简单命令的参数和输出格式 | `src/kisara/bot/commands/` |
| 应用服务 | 功能行为与编排 | `src/kisara/application/services/` |
| 通用工具 | 跨功能复用的文本处理和文件发布等小型纯工具 | `src/kisara/utils/` |
| 外部依赖 | HTTP 请求、SQLite 状态、文件保存 | `src/kisara/infrastructure/integrations/`、`persistence/` |
| 配置 | 全局和功能配置的加载、校验、默认值 | `src/kisara/config/`、`config/features/` |
| 静态资源 | 随 Python 包发布的食物、聊天、塔罗数据 | `src/kisara/resources/`、`pyproject.toml` |

普通消息的主链路：平台事件 → 适配器转为 `MessageEvent` → `Dispatcher.dispatch_result()` 检查授权与去重 → `_route()` 匹配命令并调用服务 → `DispatchResult` / `OutgoingMessage` → 适配器发送。离线控制台也使用同一个 `Dispatcher`，但只构造聊天和塔罗等本地服务，不代表所有线上能力都能在控制台运行。

OneBot 在进入普通分发前，还会处理已授权用户的引用图片导出，以及启用后的私聊 setu 合并转发归档；相关逻辑分别在 `application/services/export_img.py`、`setu.py`。这类功能依赖引用消息、转发节点或文件发送能力，不能只在 `Dispatcher` 中加一个文本命令。官方适配器目前发送文本；图片 URL 会转成文本链接，OneBot 可发送原生图片和音乐段。

`domain/models/`、`domain/repositories/`、`shared/` 当前只有包占位。新增功能应依实际需要落到现有的应用服务和基础设施，不必为了目录对称创建空抽象。

可复用的纯文本间距、折行与原子文件写入位于 `src/kisara/utils/`，分别从 `pangu.py`、`text.py`、`files.py` 导入；只有实际出现重复用途时才继续增加新的工具模块。`pangu()` 接收普通文本，先从 HTML 提取文字后再调用，不直接改写 Markdown 或 HTML 源码。

### 分层约束

| 问题 | 放置位置与检查点 |
| --- | --- |
| 谁能调用、命令如何解析？ | `Dispatcher` 或适配器进入专属流程前判断；群聊同时检查用户与群组名单。参数错误使用 `CommandInputError`。 |
| 功能实际做什么？ | `application/services/` 表达行为与状态转换；简单命令的用户可见格式可放 `bot/commands/`。 |
| 平台消息如何收发？ | 适配器负责 OneBot/官方消息转换与发送；共享功能只依赖 `MessageEvent` 或明确的窄 `Protocol`。 |
| 配置在哪校验、服务在哪创建？ | `config/` 在启动时解析和校验，`bot/main.py` 负责依赖组装；不要在每条消息中重新读配置文件。 |
| 外部数据如何取得？ | HTTP、SQLite、文件访问放在 `infrastructure/` 或现有应用服务明确封装的边界；说明超时、失败和重试。 |
| 回复如何到平台？ | 普通命令返回 `DispatchResult`，跨适配器发送使用 `OutgoingMessage`；引用、撤回、文件等平台动作需明确适配器能力。 |

### utils 脚手架约束

`src/kisara/utils/` 是可组合的小工具集合，不是自动生成服务、命令或配置的插件框架。新功能先复用现有工具，再决定是否确有跨功能的共同行为需要抽取；只服务单个功能的规则仍放在该 service 或其基础设施实现中。工具模块不承担消息路由、权限、功能配置、平台 API 或数据库状态，避免把 `utils` 变成宽泛的业务入口。从具体模块直接导入，例如 `from kisara.utils.text import wrap_text`。

| 工具 | 当前契约 | 调用前后要确认 |
| --- | --- | --- |
| `pangu.py` 的 `pangu(text)` | 为普通中日韩文本与半角内容添加间距，保留段落和 URL | HTML 应先提取纯文本；不要把原始 Markdown/HTML 交给它改写 |
| `text.py` 的 `wrap_text(text, max_width, text_width)` | 按调用者提供的宽度计算函数逐字符折行，返回各行 | 渲染器负责提供测量函数；`max_width` 必须为正 |
| `files.py` 的 `atomic_write_bytes(path, content)` | 在目标文件的父目录写临时文件，再原子替换目标 | 调用者先建父目录、校验内容并决定覆盖策略；该工具不负责下载、续传或缓存失效 |

新增或修改共享工具时，在 `tests/unit/test_utils.py` 验证其独立契约，并在使用该工具的功能测试中核对集成效果。需要断点续传时保留单独的部分下载文件与元数据；完整内容通过校验后才可用 `atomic_write_bytes()` 发布，不能把原子写入当成续传机制。

`Dispatcher` 的消息去重是有界内存缓存，进程重启后会清空。需要跨重启幂等的功能必须自行持久化去重键或完成记录。

## 已实现功能与对应模版

| 功能 | 入口与应用服务 | 类别及边界 |
| --- | --- | --- |
| `/ping`、`/help` | `bot/commands/ping.py`、`help.py` | 简单命令；帮助文本需与实际可用功能同步 |
| `/roll`、`/eat` | `bot/commands/roll.py`、`eat.py`；`application/services/dice.py`、`food.py` | 本地计算或打包资源；食物数据在 `resources/foods.json` |
| `/chat` 与普通消息回复 | `application/services/chat.py` | 打包短语库；按全局及群组策略匹配，随机触发；`cute`、`tsundere` CSV 与 `mixed` JSON |
| `/tarot` | `application/services/tarot.py` | 打包 78 张牌和牌阵；按实例、用户、中国标准时间日期生成稳定结果；本地图像仅在 OneBot 发送 |
| `/wallpaper`、`/ba`、`/source`、`/music`、`/love` | `application/services/public.py`；`infrastructure/integrations/http.py` | 外部 HTTP 服务；`/source` 需图片和密钥，`/music`、`/love` 需各自配置 |
| `/news` | `application/services/daily_news.py` | 获取当天新闻并渲染 PNG；按日期缓存，OneBot 发送图片 |
| 定时新闻推送 | OneBot 适配器的 `_run_daily_news()`；`infrastructure/persistence/news_delivery.py` | 仅 OneBot；按中国标准时间和群组发送，以 SQLite 记录已送达日期 |
| `/recall` | `bot/dispatcher.py` 与 OneBot 适配器 | 仅 OneBot；引用机器人消息，群内需管理员、群主或配置的管理员用户 |
| `/export-img`、`导出`、`转图片` 等 | `application/services/export_img.py`；OneBot 适配器 | 仅 OneBot；将被引用的图片作为文件附件发送，无持久化 |
| `保存`、`setu`、`/setu` | `application/services/setu.py`；`infrastructure/persistence/setu.py`、`setu_files.py` | 仅 OneBot 私聊；引用合并转发 → 引用 bot 提示回复“确认”或“取消” → 下载保存或撤销；SQLite 记录批次，文件另存 |

旧中文和 `#` 命令别名由 `bot/dispatcher.py` 中的 `_normalize_legacy_command()` 处理；支持范围以该函数和 `docs/legacy-migration.md` 为准。外部 API 的真实可用性仍取决于服务方、网络和运行配置，不能仅凭离线测试判断。

## 新功能的改动清单

先回答：谁能触发、从什么消息触发、需要哪些平台能力、输出什么、是否访问网络、是否产生持久状态、失败后能否重试。然后选择最窄的实现路径。

### A. 本地或文本命令

适用于 `/roll`、`/eat` 一类无需平台特有消息操作的功能。

1. 在 `application/services/<feature>.py` 放可独立调用的行为；若只是固定回复，可仅加 `bot/commands/<feature>.py`。
2. 在 `bot/dispatcher.py` 的 `_route()` 中加入命令、别名、参数校验和服务调用；用 `CommandInputError` 表示用户输入错误。
3. 如需初始化依赖，在 `bot/main.py` 组装并传给 `Dispatcher`；同步更新功能模块开头 docstring 和 `bot/commands/help.py`。若有历史别名，明确加入 `_normalize_legacy_command()`。
4. 在 `tests/unit/` 测服务行为和分发结果；跨平台能力应使用归一化的 `MessageEvent` 验证。

### B. 带配置、资源或外部 HTTP 的命令

在 A 的基础上，按需增加以下文件：

- 配置：`config/features/<feature>/config.toml.example` 是可复制示例；实际 `config.toml` 被 Git 忽略。普通功能在 `config/feature_files.py` 注册允许的键，在 `config/settings.py` 加载、校验并传入组装。缺失文件通常回退到代码默认值或旧环境变量。setu 使用单独的 `config/setu.py`，因为它有较多专属校验。
- 打包资源：放在 `src/kisara/resources/`，并加入 `pyproject.toml` 的 package-data。运行时通过包资源读取；不要依赖当前工作目录中的开发文件。
- HTTP：把请求约束放在 `infrastructure/integrations/http.py` 或同层适配器，应用服务返回协议无关结果；`PublicServices` 当前使用 `RemoteResult(text, image_urls, music_id)`。在分发器中转换为 `DispatchResult`，由适配器负责平台格式。
- 密钥与错误：示例文件不得包含真实密钥；`RemoteServiceError` 可由分发器转换为用户可见错误。新增外部接口还需核对超时、返回类型、可接受的 URL 与失败输出。

### 外部数据的缓存与续用

获取、下载文件或访问同一目标的 API 时，优先设计可复用缓存，减少重复请求和传输。默认把临时下载及响应缓存放在运行环境的 `/tmp/kisara/<feature>/` 下，不放进源码树。实现前先说明“同一目标”的判定方式：用规范化资源标识及影响结果的参数生成稳定缓存键，不把密钥或完整私有 URL 直接写进文件名。

每次访问先检查缓存是否仍适用且内容完整；可用时直接复用。下载中断时保留受控的部分文件和必要元数据；服务端支持 `Range`、`ETag` 或 `Last-Modified` 时按其规则续传或校验，不能确认可续传时重新下载并原子替换完整缓存。并发处理同一目标时避免重复下载及读到未完成文件。规定大小上限、有效期和清理方式；API 结果会变化或含敏感数据时，明确失效与访问范围。

`/tmp` 只保证当前运行环境中的临时复用，容器重建后可能消失。需要跨容器重建复用时，可把缓存放在宿主机应用数据目录 `data/kisara/<feature>/cache/`，并在 `deploy/compose.yaml` 中显式挂载到该服务的容器路径；现有 Compose 没有把整个 `data/kisara` 自动挂入容器。记录宿主机与容器路径、权限、清理方式，并验证重建后同一目标仍能命中缓存。跨机器复用还需要迁移或共享这份数据。不能把 `/tmp` 当数据库或永久归档。验证至少覆盖同一目标第二次不重复请求、部分下载的续用或安全重下、过期/损坏缓存的重新获取。

### C. 带状态或平台特有操作的流程

适用于定时推送、引用消息、合并转发、下载与保存。

1. 在应用服务中写清事件状态及转换；用窄 `Protocol` 声明需要的适配器能力，参考 `SetuGateway`、`ExportImgGateway`。
2. 仅在真正需要平台能力时修改 `bot/adapters/onebot_v11.py`；鉴权必须发生在读取引用内容、拉取媒体、发送文件等操作之前。确认官方适配器的降级或不支持行为。
3. 需要恢复或幂等时，在 `infrastructure/persistence/` 建立持久状态。定义重启后状态、重复消息和部分失败后的处理方式；归档文件与 SQLite 元数据分别管理。
4. 若增加 Compose 路径或挂载，同步核对 `deploy/compose.yaml`、`deploy/Dockerfile`、启动脚本、功能模块 docstring 和 `docs/operations.md` 的运行说明。
5. 在 `tests/unit/` 覆盖状态转换、边界和失败重试；协议解析与发送行为在 `tests/integration/` 验证。

## 配置、数据与数据库的落地规则

### 配置闭环

普通功能若新增配置键，应核对以下链路，少一环都可能导致示例可写但运行时无效：

```text
config/features/<feature>/config.toml.example
    → config/feature_files.py 的 FEATURE_KEYS 与类型校验
    → config/settings.py 的 Settings 字段、默认值和 from_environment()
    → bot/main.py 的依赖组装
    → application 服务或适配器实际使用
    → tests/unit/test_settings.py 的加载、覆盖与错误输入验证
```

当前普通功能的同名配置优先级是功能 TOML 中明确给出的值，高于旧环境变量，未给出时使用旧环境变量或代码默认值。`config/groups.json` 只提供 chat、tarot 的旧群组覆盖；对应的功能 TOML 群组表优先。群组 ID 仍须在 `KISARA_ALLOWED_GROUPS` 中；新增功能不会自动获得群组覆盖能力。`setu` 由 `config/setu.py` 独立加载，只有 OneBot 路径会启用。新增专属配置应写明缺失文件、非法值、关闭功能时各是什么行为。改动运行环境变量或挂载时，还要同步检查 `.env.example` 和 `deploy/compose.yaml`。

### 状态与数据库选择

| 需求 | 现有做法或新增建议 | 新功能应说明 |
| --- | --- | --- |
| 每次请求独立、无恢复要求 | `/roll`、`/eat`、外部查询不建库 | 随机或远端结果是否允许重复变化 |
| 只需进程内去重或缓存 | `Dispatcher` 的消息 ID 缓存 | 容量、有效期和重启后的行为 |
| 重复获取同一外部目标 | 新功能优先在 `/tmp/kisara/<feature>/` 暂存；跨重建时可用 `data/kisara/<feature>/cache/` 并挂载 | 稳定缓存键、完整性、有效期、续传与并发行为 |
| 重启后要记住“已发送” | `NewsDeliveryStore` 的 SQLite 完成记录 | 业务日期、对象 ID、唯一键、何时写入及失败重试 |
| 按日期复用生成结果 | `DailyNews` 的 PNG 缓存 | 日期命名、有效性校验、保留天数与共享卷路径 |
| 多步骤确认与部分成功 | `SetuStore` 的 SQLite 批次和已见消息，`SetuFileSaver` 保存媒体 | 状态转换、超时、重复确认、恢复、文件与记录的一致性 |
| 大文件或静态素材 | setu 媒体在独立挂载；塔罗等版本化资源在 Python 包内 | 文件来源、大小上限、可写路径、清理及是否需要备份 |

项目目前没有通用数据库层或统一迁移框架。若新增 SQLite 状态，把仓储实现放到 `infrastructure/persistence/<feature>.py`，数据库置于 `KISARA_STATE_DIR` 下；给出表名、字段、主键或唯一键、索引、事务边界和保留/清理策略。既有表的结构变化必须考虑旧数据库升级和失败恢复，不能假设部署后会自动重建。写入外部消息或文件前后要明确哪一步标记完成，确保重试不会重复发送或覆盖已保存内容。测试至少覆盖首次运行、重复请求、重启重开、部分失败及升级路径中实际涉及的情形。

文件路径需区分宿主机与容器。SQLite 的 Compose 位置是 `/app/state` 命名卷，不等于宿主机的 `data/kisara`；setu 媒体在宿主机 `data/kisara/setu`、容器 `/app/setu`。新增路径必须同时核对权限、Compose 挂载、备份边界和文档；不要把私有媒体放进包资源或 Git。

## 配置与存储路径

| 用途 | 仓库或宿主机路径 | Compose 容器路径 / 说明 |
| --- | --- | --- |
| 全局运行变量、引擎和授权 | `.env.example` → 私有 `.env` | Compose 注入环境变量；`.env` 被忽略 |
| 功能配置 | `config/features/{chat,tarot,news,source,music,love,setu}/config.toml.example` → 各自 `config.toml` | `config/` 只读挂载到 `/app/config`；修改后重启 |
| 旧群组覆盖配置 | `config/groups.example.json` → `config/groups.json` | 可由 `KISARA_GROUP_CONFIG_PATH` 改路径；功能 TOML 中对应群组值优先 |
| 应用持久状态 | 默认 `data/kisara` 或 `KISARA_STATE_DIR` | Compose 中为 `/app/state`，使用 `kisara_state` 命名卷；当前含 `news_delivery.sqlite3`、`setu.sqlite3` |
| 每日新闻图片缓存 | 默认 `data/daily-news` 或 news 功能的 `cache_dir` | Compose 中为 `/app/state/daily-news`，使用 `kisara_state` 命名卷 |
| 可重取的临时外部数据 | 运行环境的 `/tmp/kisara/<feature>/` | 容器内临时路径；跨重建复用需另设持久挂载 |
| 需跨重建复用的功能缓存 | `data/kisara/<feature>/cache/` | 在 `deploy/compose.yaml` 显式绑定到对应服务的可写容器路径 |
| setu 已确认的媒体文件 | `data/kisara/setu` | Compose 中为 `/app/setu`；`save_root` 需指向实际可写挂载路径 |
| 塔罗图片素材 | `data/kisara/tarotCards` | Compose 中为 `/app/tarot-cards`，Kisara 与 NapCat 只读共享；缺失时文字照常工作 |
| NapCat 登录与配置 | `data/napcat/QQ`、`data/napcat/config` | 分别挂载到 `/app/.config/QQ`、`/app/napcat/config`；QQ 缓存只读挂入 Kisara 供受限媒体读取 |

`data/`、`.env`、各功能的 `config.toml`、`config/groups.json` 均被 Git 忽略。不要把本地数据库、QQ 登录数据、媒体归档、实际密钥或运行配置放进模版。`tarot.json`、短语库、食物列表是版本化包资源，与运行状态不同。

## 功能规格填写模版

新增功能时，先在任务说明或设计记录中填完以下字段，再确定需改的文件；不需要的字段写“无”。

```text
功能名与用户场景：
验收样例：给定什么消息和配置，应得到什么回复或外部效果：
触发方式：命令 / 普通消息 / 引用 / 定时；参数与别名：
适用范围：OneBot / 官方 / 离线控制台；私聊 / 群聊：
权限：允许用户、允许群、管理员或功能专属名单：
输入与输出：MessageEvent 中读取哪些字段；返回文字、图片、音乐或平台动作：
依赖：包资源、外部 HTTP、平台接口；不可用时的回复：
缓存：是否复用外部数据；同一目标的键、/tmp 或 data/kisara 路径、挂载、有效期、完整性、续传、并发及清理：
配置：文件、键、类型、默认值、覆盖优先级、关闭行为、启动时校验：
状态：无 / 内存 / SQLite / 文件；宿主机与容器路径、主键、有效期、重启恢复：
数据库：表与字段、唯一键/索引、事务、旧库升级、清理策略；无则说明原因：
失败与重试：哪些步骤可重试；如何避免重复发送或重复保存：
改动文件：服务、utils 工具、命令、分发器、组装、配置、适配器、持久化、部署、文档：
验证：服务单测、分发测试、协议测试、真实账号验收条件：
```

交付时用同样字段回填“实际实现”和证据位置。至少核对：命令是否真正接入路由、服务是否在启动时组装、配置示例是否能被加载、外部数据是否按约定复用缓存、持久状态是否使用正确挂载、帮助与功能模块开头 docstring 是否同步、失败与重试是否有测试。若新功能不需要数据库，不为满足模版而建表。

开发时先用现有 `./dev.sh --test` 或针对性 `./hako python -m pytest tests/unit/<test_file>.py` 验证普通功能；涉及适配器的变更，再跑相关协议测试与 `./dev.sh --all`。离线测试无法证明真实 QQ 账号收发、外部 API 在线可用或连续运行稳定，线上验收应单独记录。
