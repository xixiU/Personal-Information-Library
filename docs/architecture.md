# 个人信源库 — 技术架构设计

> 更新日期: 2026-03-17

## 1. 系统概览

```
信源配置 → 任务调度 → 爬取引擎 → 数据存储 → AI精炼 → 通知推送 → Web展示
```

### 1.1 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Web UI (React)                        │
│   信源/分类/任务/结果/通知渠道 管理界面                    │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────┐
│                 Backend (FastAPI)                        │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ 信源管理 │ │ 任务调度  │ │ 爬取引擎  │ │  AI精炼    │  │
│  └─────────┘ └──────────┘ └──────────┘ └────────────┘  │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │   插件系统       │  │       通知引擎               │  │
│  └─────────────────┘  └──────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  SQLite (SQLAlchemy)                     │
│  sources / tasks / crawl_results / refined_results      │
│  categories / notification_channels / notification_rules │
│  notification_logs / plugins / task_logs                 │
└─────────────────────────────────────────────────────────┘
```

## 2. 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python) + SQLAlchemy + SQLite |
| 任务队列 | asyncio.PriorityQueue + APScheduler |
| 爬取引擎 | httpx + BeautifulSoup4 |
| AI 集成 | OpenAI 兼容接口（支持 DeepSeek/本地模型） |
| 通知推送 | httpx（Webhook/Telegram/飞书） |
| 前端 | React + Vite + Ant Design + TypeScript |
| 包管理 | uv（后端）+ pnpm（前端） |

## 3. 项目结构

```
Personal-Information-Library/
├── backend/app/
│   ├── main.py                         # FastAPI 入口，路由注册，lifespan
│   ├── config.py                       # 环境变量配置
│   ├── database.py                     # SQLAlchemy 连接
│   ├── api/
│   │   ├── sources.py                  # 信源 CRUD + 手动触发
│   │   ├── categories.py               # 分类 CRUD
│   │   ├── tasks.py                    # 任务列表/取消/重试
│   │   ├── results.py                  # 爬取/精炼结果查询
│   │   ├── refine.py                   # 手动精炼触发
│   │   ├── notification_channels.py    # 通知渠道 CRUD + 测试
│   │   ├── notification_rules.py       # 通知规则 CRUD（挂在 categories 下）
│   │   └── plugins.py                  # 插件列表
│   ├── core/
│   │   ├── scheduler.py                # 任务调度器（队列 + worker + APScheduler）
│   │   ├── crawler.py                  # 爬取引擎
│   │   ├── refiner.py                  # AI 精炼引擎（精炼完成后触发通知）
│   │   ├── notifier.py                 # 通知引擎（NotificationEngine）
│   │   └── notifiers/
│   │       ├── base.py                 # BaseNotifier 抽象基类
│   │       ├── webhook.py              # WebhookNotifier
│   │       ├── telegram.py             # TelegramNotifier
│   │       └── feishu.py               # FeishuNotifier（飞书 Webhook）
│   ├── models/
│   │   ├── source.py                   # Source
│   │   ├── task.py                     # Task + TaskLog
│   │   ├── result.py                   # CrawlResult + RefinedResult
│   │   ├── category.py                 # Category
│   │   ├── notification.py             # NotificationChannel + NotificationRule + NotificationLog
│   │   └── plugin.py                   # Plugin（已加载插件记录）
│   ├── schemas/                        # Pydantic 校验模型（与 models 一一对应）
│   └── plugins/
│       ├── base.py                     # CrawlerPlugin 抽象基类
│       ├── generic.py                  # 通用网页爬取（readability 正文提取）
│       └── rss.py                      # RSS/Atom feed 解析
└── frontend/src/
    ├── api/                            # API 客户端（axios 封装）
    │   ├── sources.ts / categories.ts / tasks.ts
    │   ├── results.ts / notifications.ts
    │   └── client.ts                   # axios 实例
    └── pages/
        ├── SourceList.tsx              # 信源管理
        ├── CategoryList.tsx            # 分类管理（含通知规则 Tab）
        ├── TaskList.tsx                # 任务列表
        ├── ResultDetail.tsx            # 采集结果列表
        ├── RefinedResultDetail.tsx     # 精炼结果详情
        └── NotificationChannels.tsx    # 通知渠道管理
```

## 4. 数据模型

### 4.1 ER 图

```
Source ──N:1──→ Category
  │
  └──1:N──→ Task ──1:1──→ CrawlResult ──1:N──→ RefinedResult
                                                      │
                                              NotificationEngine.evaluate()
                                                      │
Category ──1:N──→ NotificationRule ──N:1──→ NotificationChannel
                       │
                       └──1:N──→ NotificationLog ──N:1──→ RefinedResult
```

### 4.2 核心表字段

**Category**
```
id, name, description, color
refine_prompt_system    # AI 总结时的系统提示词（关注重点）
quality_criteria        # 质量评分标准（0-100 分维度定义）
created_at, updated_at
```

**RefinedResult**
```
id, crawl_result_id, task_id
title, summary, keywords
quality_score           # 0-100 质量评分
result_text, model_used, token_usage
created_at
```

**NotificationChannel**
```
id, name
channel_type            # webhook | telegram | feishu
config                  # JSON，渠道配置（敏感字段 API 返回时脱敏）
enabled, created_at, updated_at
```

**NotificationRule**
```
id, name, category_id, channel_id
rule_type               # new_content | quality_threshold | keyword_match
notify_mode             # instant | batch
conditions              # JSON，触发条件参数
message_template        # 自定义消息模板（null 则用渠道默认）
enabled, created_at, updated_at
```

**NotificationLog**
```
id, rule_id, channel_id, refined_result_id
batch_id                # 聚合批次 UUID（同批次共享）
status                  # pending | success | failed
error_message, sent_at, created_at
```

## 5. 核心模块

### 5.1 任务调度

```
APScheduler (cron 触发)
    │
    ▼
submit_task() → asyncio.PriorityQueue
    │
    ▼
_consumer_loop() (N 个并发 worker)
    │
    ├─ crawl 任务 → CrawlerEngine.crawl()
    │     │
    │     ├─ plugin.supports_link_discovery() == True
    │     │     └─ 发现子链接 → submit_task() (递归)
    │     └─ 爬取完成 → submit_task(refine 任务)
    │
    └─ refine 任务 → RefinerEngine.refine()
          │
          └─ 精炼完成 → NotificationEngine.evaluate()
```

**并发控制**：全局 max_workers 可配置（默认 5），单域名 semaphore 限制。

### 5.2 插件系统

```python
class CrawlerPlugin(ABC):
    def supports_link_discovery(self) -> bool:
        return False  # RSS/整站插件覆盖返回 True

    @abstractmethod
    async def fetch(self, url, client) -> RawContent: ...

    @abstractmethod
    async def parse(self, raw) -> ParsedContent: ...

    async def discover_links(self, raw, base_url) -> list[str]:
        return []
```

内置插件：`GenericPlugin`（通用网页）、`RSSPlugin`（RSS/Atom）。

**统一爬取模型**：不管 RSS、整站还是单页，每个子链接都产生一条独立的 CrawlResult，通过 `parent_task_id` 关联入口任务。

### 5.3 通知引擎

```python
class NotificationEngine:
    NOTIFIER_MAP = {
        "webhook": WebhookNotifier,
        "telegram": TelegramNotifier,
        "feishu": FeishuNotifier,
    }

    async def evaluate(self, refined_result, db):
        # 1. 查询 category 下所有 enabled 规则
        # 2. 逐条评估 conditions（质量阈值/关键词）
        # 3. 去重检查（NotificationLog）
        # 4. instant → 立即发送；batch → 写 pending + APScheduler 延迟任务
```

**聚合策略**：`batch_window`（时间窗口秒数）+ `batch_max_count`（数量上限），先到先触发。

**飞书消息格式**：默认使用 interactive 消息卡片（`use_card=True`），支持纯文本降级。

### 5.4 BaseNotifier 接口

```python
class BaseNotifier(ABC):
    def __init__(self, config: dict): ...

    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool: ...

    @abstractmethod
    async def send_batch(self, message: BatchNotificationMessage) -> bool: ...

    @abstractmethod
    def validate_config(self) -> Tuple[bool, str]: ...

    @abstractmethod
    async def send_test(self) -> Tuple[bool, str]: ...
```

## 6. API 端点

```
# 信源
POST/GET/PUT/DELETE  /api/sources
POST                 /api/sources/{id}/trigger

# 分类
POST/GET/PUT/DELETE  /api/categories

# 任务
GET                  /api/tasks
POST                 /api/tasks/{id}/cancel
POST                 /api/tasks/{id}/retry

# 结果
GET                  /api/results/crawl
GET                  /api/results/crawl/{id}
GET                  /api/results/refine
GET                  /api/results/refine/{id}
POST                 /api/refine/{crawl_result_id}

# 通知渠道
POST/GET/PUT/DELETE  /api/notification-channels
POST                 /api/notification-channels/{id}/test

# 通知规则（挂在分类下）
POST/GET/PUT/DELETE  /api/categories/{category_id}/notification-rules

# 插件
GET                  /api/plugins
```

## 7. 关键设计决策

**SQLite 而非 PostgreSQL**：单用户个人项目，零部署成本，WAL 模式支持并发读写。SQLAlchemy ORM 屏蔽差异，未来可无缝迁移。

**内置队列而非 Redis**：`asyncio.PriorityQueue` + APScheduler 足够个人规模，减少外部依赖。任务状态持久化在 SQLite，重启可恢复。

**统一爬取模型**：RSS/整站/单页统一产生 CrawlResult，AI 精炼逻辑无需区分来源类型。

**通知不阻塞精炼**：`NotificationEngine.evaluate()` 在 try/except 中调用，失败只记录日志，不影响精炼结果写入。

**渠道配置脱敏**：`bot_token`、`secret` 等敏感字段 GET 接口返回 `***`，仅 POST/PUT 时接收明文。

## 8. 安全性

- 请求限速 + UA 轮换，避免对目标站点造成压力
- API Key 存储在环境变量，不入库
- 通知渠道敏感配置 API 返回脱敏
- 所有 API 输入通过 Pydantic 严格校验
