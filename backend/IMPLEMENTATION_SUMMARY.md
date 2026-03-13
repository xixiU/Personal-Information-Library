# 个人信源库 - 后端实现总结

## 项目概述

个人信源库是一个自动化信息采集与精炼系统，支持整站爬取、任务调度、插件化扩展和AI内容精炼。

**技术栈**：
- 后端：FastAPI + SQLAlchemy + SQLite
- 任务队列：asyncio.PriorityQueue + APScheduler
- 爬取：httpx + BeautifulSoup4
- AI：OpenAI兼容接口

## 已完成功能（Week 1-3）

### Week 1：核心基础设施 ✅

**任务调度系统** (`app/core/scheduler.py`)
- asyncio.PriorityQueue 优先级队列
- 5个并发worker（可配置）
- 任务状态机：PENDING → RUNNING → SUCCESS/FAILED
- 自动重试机制（最多3次）
- 进程重启后恢复未完成任务

**爬取引擎** (`app/core/crawler.py`)
- 插件系统集成
- 单页面爬取
- 整站递归爬取（链接发现 + 子任务创建）
- 深度和页面数量限制
- URL去重

**REST API**
- `/api/sources` - 信源管理（CRUD + 手动触发）
- `/api/tasks` - 任务管理（列表/详情/统计/取消/重试）
- `/api/results` - 结果查询（爬取结果 + 精炼结果）

### Week 2：调度优化与反爬 ✅

**APScheduler集成**
- AsyncIOScheduler支持cron定时任务
- 启动时自动加载active信源的定时任务
- 定时任务管理API（添加/移除/查询）

**整站爬取优化**
- 循环链接检测（URL哈希集合）
- URL模式过滤（url_pattern + exclude_pattern）
- 子任务优先级策略（递减，最低为0）

**反爬处理**
- User-Agent轮换（5个常用UA）
- 请求限速（基于域名，默认1秒间隔）
- 单域名并发限制（每域名最多2个并发）

**定时任务API**
- POST /api/sources/{id}/schedule - 添加/更新定时任务
- DELETE /api/sources/{id}/schedule - 移除定时任务
- GET /api/sources/{id}/schedule - 查询定时任务

### Week 3：AI精炼引擎 ✅

**AI精炼引擎** (`app/core/refiner.py`)
- OpenAI兼容接口集成（AsyncOpenAI）
- 3种内置模板：摘要、关键词、摘要+关键词
- 自定义模板支持
- 重试机制（3次，指数退避）
- 内容截断（4000字符）
- 智能解析（JSON优先，回退纯文本）

**自动精炼流程**
- 爬取完成后自动创建精炼任务
- 精炼任务执行逻辑
- 去重检测（避免重复精炼）
- 精炼结果存储

**精炼API** (`/api/refine`)
- POST /api/refine/{id} - 手动触发精炼
- GET /api/refine/templates - 获取模板列表
- POST /api/refine/templates - 创建自定义模板
- GET /api/refine/preview/{id} - 预览精炼结果（不保存）

## 项目结构

```
backend/
├── app/
│   ├── main.py                 # FastAPI入口
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接
│   ├── api/                    # REST API
│   │   ├── sources.py          # 信源管理
│   │   ├── tasks.py            # 任务管理
│   │   ├── results.py          # 结果查询
│   │   └── refine.py           # 精炼管理
│   ├── core/                   # 核心业务逻辑
│   │   ├── scheduler.py        # 任务调度器
│   │   ├── crawler.py          # 爬取引擎
│   │   └── refiner.py          # AI精炼引擎
│   ├── models/                 # 数据模型（6张表）
│   │   ├── source.py
│   │   ├── task.py
│   │   ├── result.py
│   │   ├── plugin.py
│   │   └── task_log.py
│   ├── schemas/                # Pydantic模型
│   │   ├── source.py
│   │   ├── task.py
│   │   └── result.py
│   └── plugins/                # 插件
│       ├── base.py             # 插件基类
│       └── generic.py          # 通用插件
├── data/                       # 数据存储
│   └── app.db                  # SQLite数据库
├── pyproject.toml
├── WEEK1_IMPLEMENTATION.md
├── WEEK2_IMPLEMENTATION.md
└── WEEK3_IMPLEMENTATION.md
```

## 数据模型

### 核心表结构

**sources** - 信源配置
- id, name, url, crawl_mode, cron_expr, plugin_id, config, status

**tasks** - 任务记录
- id, type, status, priority, source_id, parent_task_id, url, payload, retry_count

**crawl_results** - 爬取结果
- id, task_id, source_id, url, title, content, raw_html, meta_data

**refined_results** - 精炼结果
- id, crawl_result_id, summary, keywords, category, meta_data

## 配置说明

### 环境变量 (.env)

```env
# Database
DATABASE_URL=sqlite:///./data/app.db

# Crawler
CRAWLER_MAX_WORKERS=5
CRAWLER_REQUEST_TIMEOUT=30
CRAWLER_RATE_LIMIT=1.0
CRAWLER_MAX_DEPTH=3

# Task Queue
TASK_QUEUE_SIZE=1000
TASK_MAX_RETRIES=3

# AI
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 信源配置示例

```json
{
  "name": "技术博客",
  "url": "https://example.com",
  "crawl_mode": "full_site",
  "cron_expr": "0 */6 * * *",
  "config": {
    "max_depth": 3,
    "max_pages": 100,
    "url_pattern": ".*\\.html$",
    "exclude_pattern": "/login|/register",
    "save_html": false
  }
}
```

## API端点总览

### 信源管理
- POST /api/sources - 创建信源
- GET /api/sources - 列表
- GET /api/sources/{id} - 详情
- PUT /api/sources/{id} - 更新
- DELETE /api/sources/{id} - 删除
- POST /api/sources/{id}/trigger - 手动触发爬取
- POST /api/sources/{id}/schedule - 添加定时任务
- DELETE /api/sources/{id}/schedule - 移除定时任务
- GET /api/sources/{id}/schedule - 查询定时任务

### 任务管理
- POST /api/tasks - 创建任务
- GET /api/tasks - 列表
- GET /api/tasks/{id} - 详情
- GET /api/tasks/stats - 统计
- POST /api/tasks/{id}/cancel - 取消
- POST /api/tasks/{id}/retry - 重试

### 结果查询
- GET /api/results/crawl - 爬取结果列表
- GET /api/results/crawl/{id} - 爬取结果详情
- GET /api/results/refine - 精炼结果列表
- GET /api/results/refine/{id} - 精炼结果详情

### 精炼管理
- POST /api/refine/{id} - 手动触发精炼
- GET /api/refine/templates - 获取模板列表
- POST /api/refine/templates - 创建自定义模板
- GET /api/refine/preview/{id} - 预览精炼结果

## 核心流程

### 爬取流程

```
1. 创建信源（手动或定时触发）
   ↓
2. 创建爬取任务（PENDING）
   ↓
3. 调度器提交到队列
   ↓
4. Worker执行爬取
   - 单域名并发控制
   - 请求限速
   - UA轮换
   ↓
5. 保存爬取结果
   ↓
6. 如果是整站爬取
   - 发现新链接
   - 创建子任务
   ↓
7. 自动创建精炼任务
```

### 精炼流程

```
1. 爬取完成后自动创建精炼任务
   ↓
2. 调度器提交到队列
   ↓
3. Worker执行精炼
   - 调用OpenAI API
   - 重试机制
   - 智能解析
   ↓
4. 保存精炼结果
```

## 性能特性

- **并发控制**：全局5个worker，单域名2个并发
- **请求限速**：默认1秒间隔，可配置
- **内存优化**：URL哈希去重，节省内存
- **成本控制**：内容截断、预览功能、去重检测

## 运行方式

```bash
# 安装依赖
cd backend
uv sync

# 启动服务
uv run uvicorn app.main:app --reload

# 访问API文档
http://localhost:8000/docs
```

## 测试

```bash
# 运行测试脚本
cd backend
uv run python test_implementation.py
```

## 下一步（Week 4）

- [ ] React前端开发
- [ ] 信源管理页面
- [ ] 任务列表页面
- [ ] 结果预览页面
- [ ] 前后端联调

## 技术亮点

1. **插件化架构**：易于扩展新的爬取策略
2. **异步优先**：全异步设计，高性能
3. **智能调度**：优先级队列 + 并发控制
4. **反爬友好**：UA轮换、限速、并发控制
5. **成本优化**：内容截断、预览、去重
6. **配置灵活**：支持OpenAI和本地模型

## 已知限制

1. 单机部署（可扩展到分布式）
2. SQLite数据库（可切换到PostgreSQL）
3. 内存存储visited_urls（重启后清空）
4. 无分布式锁（单机无需）

## 扩展路径

| 当前方案 | 扩展方案 |
|---------|---------|
| asyncio.Queue | Redis + Celery |
| SQLite | PostgreSQL |
| 本地文件 | S3/OSS |
| 单进程 | 多worker |
