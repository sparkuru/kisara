
```bash
$ tree
.
├── src/
│   └── kisara/
│       ├── config/                 # 配置加载
│       ├── bot/                    # qqbot/botpy 接入层
│       │   ├── commands/           # 指令处理
│       │   └── events/             # 事件处理
│       ├── application/
│       │   └── services/           # 业务用例
│       ├── domain/
│       │   ├── models/             # 领域模型
│       │   └── repositories/       # 数据访问接口
│       ├── infrastructure/
│       │   ├── integrations/       # 外部 API
│       │   ├── persistence/        # 数据库、缓存、文件
│       │   └── logging/            # 日志
│       └── shared/                 # 常量、通用异常等
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── config/
├── scripts/
├── docs/
└── deploy/
```


## refer

1. qq bot 官方 sdk，https://bot.q.qq.com/wiki/
2. botpy，https://github.com/tencent-connect/botpy.git
3. 