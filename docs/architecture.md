# 个人信源库 - 技术架构设计

## 1. 系统概览

个人信源库是一个自动化信息采集与精炼系统，核心流程：

```
信源配置 → 任务调度 → 爬取引擎 → 数据存储 → AI精炼 → Web展示
```

### 1.1 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Web UI (React)                        │
│              任务配置 / 结果预览 / 信源管理               │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────┐
│                 Backend (FastAPI)                        │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ 信源管理 │ │ 任务调度  │ │ 爬取引擎  │ │  AI精炼    │  │
│  │  模块   │ │  模块    │ │   模块   │ │   模块     │  │
│  └─────────┘ └──────────┘ └──────────┘ └────────────┘  │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │   插件系统       │  │       任务队列 (内置)         │  │
│  └─────────────────┘  └──────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  SQLite + 文件存储                        │
│         任务记录 / 爬取结果 / 精炼结果 / 配置             │
└─────────────────────────────────────────────────────────┘
```

## 2. 技术栈选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 后端框架 | **FastAPI (Python)** | 异步支持好，生态丰富，爬虫库多 |
| 任务队列 | **内置异步队列 + APScheduler** | 个人项目无需 Celery/Redis 的复杂度 |
| 爬取引擎 | **httpx + BeautifulSoup4 + Playwright** | httpx 异步请求，BS4 解析，Playwright 处理 JS 渲染页面 |
| 数据库 | **SQLite (通过 SQLAlchemy)** | 零部署成本，单用户场景足够 |
| AI集成 | **OpenAI SDK (兼容接口)** | 支持 OpenAI/DeepSeek/本地模型等兼容接口 |
| 前端 | **React + Vite + Ant Design** | 成熟的管理后台方案 |
| 包管理 | **uv (后端) + pnpm (前端)** | 现代高效的包管理工具 |

### 2.1 为什么不用 Redis/Celery？

个人项目，单机部署。内置的 `asyncio.Queue` + APScheduler 足以处理：
- 定时触发爬取任务
- 任务优先级排序
- 并发控制
- 任务递归产生

如果未来需要扩展到分布式，可以将队列层替换为 Redis + Celery，接口保持不变。

## 3. 核心模块设计

### 3.1 项目结构

```
Personal-Information-Library/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # 配置管理
│   │   ├── database.py             # 数据库连接
│   │   ├── api/                    # REST API 路由
│   │   │   ├── sources.py          # 信源管理 API
│   │   │   ├── tasks.py            # 任务管理 API
│   │   │   ├── results.py          # 结果查询 API
│   │   │   └── plugins.py          # 插件管理 API
│   │   ├── core/                   # 核心业务逻辑
│   │   │   ├── scheduler.py        # 任务调度器
│   │   │   ├── crawler.py          # 爬取引擎
│   │   │   ├── refiner.py          # AI精炼引擎
│   │   │   └── plugin_manager.py   # 插件管理器
│   │   ├── models/                 # 数据模型
│   │   │   ├── source.py           # 信源模型
│   │   │   ├── task.py             # 任务模型
│   │   │   └── result.py           # 结果模型
│   │   ├── plugins/                # 内置插件
│   │   │   ├── base.py             # 插件基类
│   │   │   ├── generic.py          # 通用爬取策略
│   │   │   └── rss.py              # RSS 爬取策略
│   │   └── schemas/                # Pydantic 模型
│   │       ├── source.py
│   │       ├── task.py
│   │       └── result.py
│   ├── plugins/                    # 用户自定义插件目录
│   ├── pyproject.toml
│   └── alembic/                    # 数据库迁移
├── frontend/
│   ├── src/
│   │   ├── pages/                  # 页面组件
│   │   ├── components/             # 通用组件
│   │   ├── api/                    # API 调用
│   │   └── stores/                 # 状态管理
│   ├── package.json
│   └── vite.config.ts
├── data/                           # 数据存储目录
│   ├── db.sqlite                   # SQLite 数据库
│   └── crawled/                    # 爬取的原始文件
└── docs/
    └── architecture.md
```

### 3.2 任务调度系统

调度系统是整个应用的心脏，负责管理爬取任务和精炼任务的生命周期。

```python
# 任务状态机
# PENDING → RUNNING → SUCCESS
#                   → FAILED → PENDING (重试)
#                   → CANCELLED

class TaskScheduler:
    """
    核心调度器，职责：
    1. 定时触发：根据信源配置的 cron 表达式触发爬取任务
    2. 队列管理：维护任务优先级队列，控制并发数
    3. 任务编排：爬取完成后自动创建精炼任务
    4. 递归处理：爬取任务可以产生子任务（如发现新链接）
    """

    async def start(self):
        """启动调度器，初始化定时任务和消费者"""

    async def submit_task(self, task: Task) -> str:
        """提交任务到队列，返回任务ID"""

    async def cancel_task(self, task_id: str):
        """取消任务"""

    async def _consumer_loop(self):
        """消费者循环：从队列取任务并执行"""

    async def _execute_task(self, task: Task):
        """执行单个任务，根据类型分发到爬取引擎或精炼引擎"""

    async def _handle_task_result(self, task: Task, result: CrawlResult):
        """处理任务结果：存储结果、创建子任务、触发精炼"""
```

**调度流程**：

```
APScheduler (cron触发)
    │
    ▼
submit_task() → asyncio.PriorityQueue
    │
    ▼
_consumer_loop() (N个并发worker)
    │
    ├─ 爬取任务 → CrawlerEngine.crawl()
    │     │
    │     ├─ 发现新链接 → submit_task() (递归)
    │     └─ 爬取完成 → submit_task(精炼任务)
    │
    └─ 精炼任务 → RefinerEngine.refine()
          │
          └─ 存储精炼结果
```

**并发控制**：
- 全局最大并发数：可配置（默认5）
- 单域名并发限制：可配置（默认2），避免被封
- 请求间隔：可配置（默认1-3秒随机）

### 3.3 爬取引擎

爬取引擎采用策略模式，通过插件系统支持不同的爬取策略。

```python
class CrawlerEngine:
    """
    爬取引擎，职责：
    1. 根据信源配置选择爬取策略（插件）
    2. 执行爬取并返回结构化结果
    3. 处理反爬（UA轮换、代理、限速）
    4. 支持整站爬取（递归发现链接）和单页面爬取
    """

    async def crawl(self, task: CrawlTask) -> CrawlResult:
        """
        执行爬取任务
        1. 加载对应的插件策略
        2. 调用插件的 fetch() 获取页面
        3. 调用插件的 parse() 解析内容
        4. 调用插件的 discover_links() 发现新链接（整站模式）
        5. 返回结构化结果
        """

    async def _fetch_page(self, url: str, use_browser: bool) -> str:
        """获取页面内容，支持 httpx 和 Playwright 两种模式"""
```

**两种爬取模式**：

| 模式 | 说明 | 实现 |
|------|------|------|
| 单页面 | 爬取指定URL，提取内容 | 直接爬取，不产生子任务 |
| 整站爬取 | 从入口URL开始，递归爬取 | 爬取后调用 `discover_links()`，对新链接创建子任务 |

### 3.4 插件系统

插件系统是可扩展性的核心。每个插件定义了针对特定信源的爬取和解析策略。

```python
class CrawlerPlugin(ABC):
    """爬取插件基类"""

    name: str                    # 插件名称
    description: str             # 插件描述
    supported_domains: list[str] # 支持的域名模式（可选）

    @abstractmethod
    async def fetch(self, url: str, client: httpx.AsyncClient) -> RawContent:
        """获取页面原始内容"""

    @abstractmethod
    async def parse(self, raw: RawContent) -> ParsedContent:
        """解析页面内容为结构化数据"""

    async def discover_links(self, raw: RawContent, base_url: str) -> list[str]:
        """发现页面中的新链接（整站爬取模式用），默认返回空"""
        return []

    def should_follow(self, url: str, depth: int) -> bool:
        """判断是否应该跟进某个链接，默认True"""
        return True

    async def before_fetch(self, url: str) -> dict:
        """fetch前的钩子，可返回额外的请求参数"""
        return {}

    async def after_parse(self, content: ParsedContent) -> ParsedContent:
        """parse后的钩子，可对结果做后处理"""
        return content
```

**插件加载机制**：

```python
class PluginManager:
    """
    插件管理器
    1. 扫描 backend/app/plugins/ 目录加载内置插件
    2. 扫描 backend/plugins/ 目录加载用户自定义插件
    3. 根据 URL 域名自动匹配插件，无匹配时使用通用插件
    """

    def load_plugins(self):
        """扫描插件目录，动态导入所有 CrawlerPlugin 子类"""

    def get_plugin(self, url: str) -> CrawlerPlugin:
        """根据URL匹配最合适的插件，fallback到GenericPlugin"""

    def register_plugin(self, plugin: CrawlerPlugin):
        """手动注册插件"""
```

**内置插件**：

| 插件 | 用途 |
|------|------|
| `GenericPlugin` | 通用网页爬取，使用 readability 算法提取正文 |
| `RSSPlugin` | RSS/Atom feed 解析 |

**自定义插件示例**（用户在 `backend/plugins/` 下创建）：

```python
# backend/plugins/zhihu.py
from app.plugins.base import CrawlerPlugin

class ZhihuPlugin(CrawlerPlugin):
    name = "zhihu"
    description = "知乎专栏爬取"
    supported_domains = ["zhuanlan.zhihu.com"]

    async def fetch(self, url, client):
        # 知乎特定的请求头和cookie处理
        ...

    async def parse(self, raw):
        # 知乎页面特定的内容提取逻辑
        ...

    async def discover_links(self, raw, base_url):
        # 发现专栏中的其他文章链接
        ...
```

### 3.5 AI精炼引擎

```python
class RefinerEngine:
    """
    AI精炼引擎，职责：
    1. 接收爬取的原始内容
    2. 调用 OpenAI 兼容接口进行内容精炼
    3. 支持多种精炼模式（摘要、翻译、结构化提取等）
    4. 存储精炼结果
    """

    def __init__(self, api_base: str, api_key: str, model: str):
        self.client = AsyncOpenAI(base_url=api_base, api_key=api_key)
        self.model = model

    async def refine(self, task: RefineTask) -> RefineResult:
        """
        执行精炼任务
        1. 加载原始爬取内容
        2. 根据精炼模式构建 prompt
        3. 调用 LLM
        4. 解析并存储结果
        """

    async def _build_prompt(self, content: str, mode: RefineMode) -> list[dict]:
        """根据精炼模式构建消息列表"""
```

**精炼模式**：

```python
class RefineMode(str, Enum):
    SUMMARY = "summary"           # 生成摘要
    KEY_POINTS = "key_points"     # 提取关键要点
    TRANSLATE = "translate"       # 翻译
    STRUCTURED = "structured"     # 结构化提取（JSON）
    CUSTOM = "custom"             # 自定义 prompt
```

## 4. 数据模型

### 4.1 ER 图

```
Source (信源)
├── id: UUID (PK)
├── name: str                    # 信源名称
├── url: str                     # 入口URL
├── source_type: enum            # single_page | site_crawl | rss
├── plugin_name: str?            # 指定插件（空则自动匹配）
├── cron_expression: str?        # 定时表达式（空则手动触发）
├── crawl_config: JSON           # 爬取配置（深度、并发、过滤规则等）
├── refine_config: JSON          # 精炼配置（模式、prompt等）
├── enabled: bool
├── created_at: datetime
└── updated_at: datetime

Task (任务)
├── id: UUID (PK)
├── source_id: UUID (FK → Source)
├── parent_task_id: UUID? (FK → Task, 自引用)
├── task_type: enum              # crawl | refine
├── status: enum                 # pending | running | success | failed | cancelled
├── priority: int                # 优先级（数字越小越优先）
├── url: str?                    # 爬取目标URL
├── depth: int                   # 当前爬取深度
├── retry_count: int
├── error_message: str?
├── started_at: datetime?
├── finished_at: datetime?
├── created_at: datetime
└── updated_at: datetime

CrawlResult (爬取结果)
├── id: UUID (PK)
├── task_id: UUID (FK → Task)
├── source_id: UUID (FK → Source)
├── url: str
├── title: str?
├── content_text: text           # 提取的纯文本
├── content_html: text?          # 原始HTML（可选保留）
├── metadata: JSON               # 额外元数据（作者、日期等）
├── content_hash: str            # 内容哈希（去重用）
├── file_path: str?              # 本地文件存储路径
├── created_at: datetime
└── updated_at: datetime

RefineResult (精炼结果)
├── id: UUID (PK)
├── crawl_result_id: UUID (FK → CrawlResult)
├── task_id: UUID (FK → Task)
├── refine_mode: enum
├── result_text: text            # 精炼后的文本
├── result_json: JSON?           # 结构化结果（structured模式）
├── model_used: str              # 使用的模型
├── token_usage: JSON            # token消耗统计
├── created_at: datetime
└── updated_at: datetime
```

### 4.2 关系说明

```
Source 1──N Task          一个信源产生多个任务
Task   1──1 CrawlResult   一个爬取任务对应一个爬取结果
Task   1──N Task          一个任务可以产生子任务（递归爬取）
CrawlResult 1──N RefineResult  一个爬取结果可以有多种精炼结果
```

## 5. API 设计

### 5.1 信源管理

```
POST   /api/sources              # 创建信源
GET    /api/sources              # 列表（支持分页、筛选）
GET    /api/sources/:id          # 详情
PUT    /api/sources/:id          # 更新
DELETE /api/sources/:id          # 删除
POST   /api/sources/:id/trigger  # 手动触发爬取
```

### 5.2 任务管理

```
GET    /api/tasks                # 任务列表（支持状态筛选）
GET    /api/tasks/:id            # 任务详情（含子任务树）
POST   /api/tasks/:id/cancel     # 取消任务
POST   /api/tasks/:id/retry      # 重试失败任务
GET    /api/tasks/stats          # 任务统计（各状态数量）
```

### 5.3 结果查询

```
GET    /api/results/crawl        # 爬取结果列表
GET    /api/results/crawl/:id    # 爬取结果详情
GET    /api/results/refine       # 精炼结果列表
GET    /api/results/refine/:id   # 精炼结果详情
GET    /api/results/search       # 全文搜索
```

### 5.4 插件管理

```
GET    /api/plugins              # 已加载插件列表
GET    /api/plugins/:name        # 插件详情
POST   /api/plugins/reload       # 重新加载插件
```

### 5.5 系统配置

```
GET    /api/settings             # 获取系统配置
PUT    /api/settings             # 更新系统配置（AI接口、并发数等）
GET    /api/settings/health      # 健康检查
```

## 6. 关键设计决策

### 6.1 为什么用 SQLite 而不是 PostgreSQL？

- 个人项目，单用户，零部署成本
- SQLite 的 WAL 模式支持并发读写，足够应对
- 如需迁移，SQLAlchemy ORM 层屏蔽了差异，换数据库只需改连接字符串

### 6.2 为什么用内置队列而不是 Redis？

- 减少外部依赖，`asyncio.PriorityQueue` 足以处理个人规模的任务
- APScheduler 支持持久化到 SQLite，重启不丢失定时任务
- 任务状态持久化在数据库中，进程重启后可恢复未完成任务

### 6.3 整站爬取的深度控制

```python
# 信源配置中的 crawl_config
{
    "max_depth": 3,              # 最大递归深度
    "max_pages": 100,            # 最大页面数
    "url_pattern": ".*\\.html$", # URL过滤正则
    "exclude_pattern": "/login|/register",  # 排除URL模式
    "same_domain_only": true     # 是否限制同域名
}
```

### 6.4 去重策略

- URL 去重：同一信源下，相同 URL 不重复爬取（可配置时间窗口）
- 内容去重：通过 `content_hash` 检测内容是否变化，未变化则跳过精炼

### 6.5 错误处理与重试

```python
# 重试策略
{
    "max_retries": 3,
    "retry_delay": [60, 300, 900],  # 递增延迟（秒）
    "retry_on": [500, 502, 503, 504, "timeout", "connection_error"]
}
```

## 7. 安全性考虑

1. **请求限速**：单域名并发限制 + 请求间隔，避免被封/对目标站点造成压力
2. **User-Agent 轮换**：内置 UA 池，降低被识别为爬虫的概率
3. **API Key 安全**：AI 接口的 API Key 存储在环境变量或加密配置中，不入库
4. **输入校验**：所有 API 输入通过 Pydantic 严格校验
5. **爬取范围限制**：`robots.txt` 尊重（可配置）、域名白名单
6. **XSS 防护**：前端展示爬取内容时做 sanitize 处理

## 8. 可扩展性路径

当前设计为单机部署，但预留了扩展接口：

| 当前方案 | 扩展方案 | 改动点 |
|---------|---------|--------|
| asyncio.Queue | Redis + Celery | 替换 scheduler.py 中的队列实现 |
| SQLite | PostgreSQL | 修改数据库连接字符串 |
| 本地文件存储 | S3/OSS | 替换文件存储层 |
| 单进程 | 多 worker | Celery worker 横向扩展 |

## 9. 开发阶段规划

### MVP 范围（P0，4周）

MVP = 整站爬取 + 任务系统 + 插件框架 + AI精炼 + 基础UI

#### Week 1：后端骨架 + 数据模型 + 基础爬取

| 天 | 任务 | 产出 |
|----|------|------|
| D1-D2 | 项目初始化：FastAPI 骨架、SQLAlchemy 模型定义、Alembic 迁移、配置管理 | 可启动的后端服务，6张表建好 |
| D3-D4 | 通用爬取插件（GenericPlugin）：httpx 请求 + BeautifulSoup 解析 + Readability 正文提取 | 单页面爬取可用 |
| D5 | 插件基类（CrawlerPlugin ABC）+ 插件管理器（扫描/注册/匹配）| 插件框架可用 |

技术要点：
- 数据模型一次性建好全部6张表（sources/tasks/crawl_results/refined_results/plugins/task_logs）
- GenericPlugin 实现 `fetch()` / `parse()` / `discover_links()` 三个核心方法
- 插件管理器支持内置插件目录 + 用户自定义插件目录扫描

#### Week 2：任务调度 + 整站爬取

| 天 | 任务 | 产出 |
|----|------|------|
| D1-D2 | 任务调度器：asyncio.PriorityQueue + worker 消费循环 + 任务状态机 | 任务提交/执行/状态流转可用 |
| D3 | APScheduler 集成：cron 定时触发 + 信源关联 | 定时爬取可用 |
| D4-D5 | 整站爬取：`discover_links()` → 子任务创建 → 深度/数量限制 → URL去重 | 递归爬取可用 |

技术要点：
- 调度器生命周期绑定 FastAPI 的 lifespan
- 并发控制：全局 max_workers=5，单域名 semaphore=2
- 整站爬取需要 `visited_urls` 集合去重 + `max_depth` / `max_pages` 限制
- 任务递归：爬取任务完成后，对发现的新链接调用 `submit_task()` 创建子任务

#### Week 3：AI精炼 + REST API

| 天 | 任务 | 产出 |
|----|------|------|
| D1-D2 | AI精炼引擎：OpenAI 兼容接口调用 + prompt 模板 + 结果结构化存储 | 爬取结果可自动精炼 |
| D3 | 任务编排：爬取完成 → 自动创建精炼任务 → 精炼结果写入 refined_results | 爬取→精炼全链路打通 |
| D4-D5 | REST API 完整实现：信源 CRUD、任务管理、结果查询（分页/过滤）、插件管理 | 全部 API 可用 |

技术要点：
- RefinerEngine 通过 `openai.AsyncOpenAI` 调用，`base_url` 可配置以支持不同后端
- Prompt 模板支持：摘要生成、关键词提取、分类标注、自定义 prompt
- 精炼结果 JSON 结构：`{ summary, keywords[], category, custom_fields{} }`
- API 统一响应格式：`{ code, message, data, pagination? }`

#### Week 4：基础UI + 联调 + 稳定性

| 天 | 任务 | 产出 |
|----|------|------|
| D1-D2 | React 前端骨架：信源管理页（CRUD表单）+ 任务列表页（状态/进度） | 基础管理界面 |
| D3 | 结果预览页：爬取结果列表 + 精炼结果展示 + 内容详情 | 结果可视化 |
| D4 | 前后端联调 + Playwright 集成（JS渲染页面支持） | 全链路可用 |
| D5 | 错误处理完善 + 重试机制 + 日志完善 + 基础测试 | MVP 稳定可用 |

技术要点：
- 前端使用 Ant Design ProTable 快速搭建列表页
- 信源配置表单：URL、cron表达式、爬取模式（单页/整站）、关联插件、AI精炼开关
- 结果预览：Markdown 渲染精炼摘要，可展开查看原始爬取内容

### MVP 后续迭代

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| P1 | RSS插件 + 更多内置插件 + Playwright 深度集成 | 中 |
| P2 | 全文搜索（SQLite FTS5）+ 标签系统 + 收藏功能 | 中 |
| P3 | 数据导出 + 通知推送 + 仪表盘统计 | 低 |
