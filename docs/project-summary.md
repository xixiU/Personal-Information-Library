# 个人信源库项目 - 团队分析总结

> 生成时间：2026-03-13
> 团队成员：产品经理、技术架构师、QA工程师

---

## 📋 项目概述

**项目名称**：个人信源库（Personal Information Library）

**核心理念**：通过自动化爬取和AI精炼，将分散的网络信息转化为结构化的个人知识库

**价值链**：`信源发现 → 自动采集 → AI精炼 → 结构化入库 → 可检索复用`

---

## 🎯 产品需求分析（产品经理）

### 核心价值

解决三大痛点：
1. **信息获取成本高** - 手动逐站浏览效率低
2. **精炼耗时** - 信息量大，难以快速提取关键洞察
3. **知识沉淀困难** - 收藏夹堆积，缺乏结构化整理

### 典型用户场景

| 场景 | 用户画像 | 痛点 |
|------|---------|------|
| 技术跟踪 | 开发者，关注多个技术博客/文档站 | 手动逐站浏览效率低，信息分散 |
| 行业研究 | 分析师/创业者，监控行业动态 | 信息量大，难以快速提取关键洞察 |
| 内容创作 | 自媒体/写作者，需要素材积累 | 收藏夹堆积，缺乏结构化整理 |
| 学术追踪 | 研究人员，跟踪论文/报告 | 原始内容冗长，需要摘要和要点提取 |

### MVP范围（修订版）

**核心公式**：`MVP = 整站爬取 + 任务系统 + 插件框架 + AI精炼 + 基础UI`

**修订理由**：原MVP仅含单页面抓取，过于保守，无法验证核心架构（任务递归生成、插件可扩展性）。

#### 核心流程

1. 用户输入站点入口URL
2. 系统抓取入口页，解析出子页面链接（如文章列表）
3. 为每个子页面创建抓取任务（任务递归生成）
4. 任务队列依次执行，调用插件抓取正文
5. 抓取完成后自动触发AI精炼
6. UI展示任务执行状态和精炼结果

#### MVP包含

- **整站爬取**：入口页 → 子页面列表 → N个单页任务，验证任务递归生成机制
- **任务系统**：优先级队列、状态机（PENDING → RUNNING → SUCCESS/FAILED）、失败重试
- **插件框架**：插件接口定义（抓取/解析/清洗三个钩子）+ 一个通用插件实现 + 按域名/URL模式匹配路由
- **AI精炼**：单一精炼策略（摘要+关键词提取），OpenAI兼容接口
- **基础UI**：任务列表 + 信源详情页（原文+精炼结果对比）

#### MVP不包含

定时任务、标签分类、导出功能、多种精炼模板、搜索筛选、插件市场、热加载

#### 技术验证目标

- 任务系统能否稳定处理递归生成的任务队列
- 插件机制能否解耦通用逻辑和定制逻辑
- AI精炼的成本和质量是否可接受

### 4周实现计划

- **Week 1**：任务系统 + 通用插件（单页抓取能力）
- **Week 2**：整站爬取逻辑（链接提取 + 任务递归生成）
- **Week 3**：AI精炼集成 + 基础UI
- **Week 4**：联调测试 + 边界case处理

### 后续迭代

- **Sprint 2**：定时任务 + 更多插件
- **Sprint 3**：标签分类 + 搜索筛选
- **Sprint 4**：导出功能 + 体验打磨

### 关键风险与缓解策略

| 风险 | 缓解策略 |
|------|---------|
| 反爬机制 | MVP先聚焦静态页面；P1引入策略包机制 |
| 内容解析质量 | 使用readability算法做正文提取 |
| AI精炼成本 | 支持本地模型（Ollama）；提供精炼前预览 |
| 法律合规 | 定位为个人使用工具；尊重robots.txt |
| 动态渲染页面 | P1通过Playwright解决 |

---

## 🏗️ 技术架构设计（技术架构师）

### 技术栈选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 后端框架 | FastAPI (Python) | 异步支持好，生态丰富，爬虫库多 |
| 任务队列 | asyncio.Queue + APScheduler | 个人项目无需Celery/Redis的复杂度 |
| 爬取引擎 | httpx + BeautifulSoup4 + Playwright | httpx异步请求，BS4解析，Playwright处理JS渲染 |
| 数据库 | SQLite (通过SQLAlchemy) | 零部署成本，单用户场景足够 |
| AI集成 | OpenAI SDK (兼容接口) | 支持OpenAI/DeepSeek/本地模型 |
| 前端 | React + Vite + Ant Design | 成熟的管理后台方案 |
| 包管理 | uv (后端) + pnpm (前端) | 现代高效的包管理工具 |

### 系统架构

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

### 核心模块设计

#### 1. 任务调度系统
- **定时触发**：APScheduler负责cron定时触发
- **优先级队列**：asyncio.PriorityQueue管理任务优先级
- **并发控制**：N个并发worker消费任务
- **状态机**：PENDING → RUNNING → SUCCESS/FAILED
- **任务递归**：爬取任务可产生子任务（整站爬取时发现新链接）
- **自动精炼**：爬取完成自动创建精炼任务

#### 2. 爬取引擎（策略模式 + 插件化）
- **插件基类**：`CrawlerPlugin`定义接口：`fetch()` / `parse()` / `discover_links()`
- **内置插件**：GenericPlugin（通用）、RSSPlugin（RSS订阅）
- **爬取模式**：单页面爬取、整站递归爬取
- **反爬处理**：UA轮换、请求限速、单域名并发限制

#### 3. 插件系统
- **插件发现**：扫描 `backend/app/plugins/` 和 `backend/plugins/`（用户自定义）
- **插件匹配**：按域名匹配 → 按信源配置指定 → 回退通用插件
- **热加载**：通过API触发重新扫描

#### 4. 数据模型（6张核心表）

```sql
-- 信源配置
sources: id, name, url, crawl_mode, cron_expr, plugin_id, config, status

-- 任务记录
tasks: id, type, status, priority, source_id, parent_task_id, created_at

-- 爬取结果
crawl_results: id, task_id, source_id, url, title, content, raw_html, created_at

-- AI精炼结果
refined_results: id, crawl_result_id, summary, keywords, category, created_at

-- 插件注册表
plugins: id, name, domain_pattern, plugin_class, enabled

-- 任务执行日志
task_logs: id, task_id, level, message, created_at
```

### 项目结构

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
│   │   ├── plugins/                # 内置插件
│   │   │   ├── base.py             # 插件基类
│   │   │   ├── generic.py          # 通用爬取策略
│   │   │   └── rss.py              # RSS 爬取策略
│   │   └── schemas/                # Pydantic 模型
│   ├── plugins/                    # 用户自定义插件目录
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/                  # 页面组件
│   │   ├── components/             # 通用组件
│   │   ├── api/                    # API 调用
│   │   └── stores/                 # 状态管理
│   └── package.json
├── docs/
│   ├── architecture.md             # 详细架构文档
│   └── project-summary.md          # 本文档
└── README.md
```

### API设计

**RESTful风格，按资源分组**：

- `GET /api/sources` - 获取信源列表
- `POST /api/sources` - 创建信源
- `GET /api/sources/{id}` - 获取信源详情
- `PUT /api/sources/{id}` - 更新信源
- `DELETE /api/sources/{id}` - 删除信源
- `POST /api/sources/{id}/trigger` - 手动触发爬取

- `GET /api/tasks` - 获取任务列表
- `GET /api/tasks/{id}` - 获取任务详情
- `POST /api/tasks/{id}/retry` - 重试失败任务

- `GET /api/results` - 获取结果列表
- `GET /api/results/{id}` - 获取结果详情

- `GET /api/plugins` - 获取插件列表
- `POST /api/plugins/reload` - 重新加载插件

### 开发阶段规划

- **P0**：后端骨架 + 数据模型 + 通用爬取 + 基础API
- **P1**：任务调度 + 整站爬取 + 插件系统
- **P2**：AI精炼集成
- **P3**：Web前端
- **P4**：更多插件 + 全文搜索

### 可扩展性设计

- **队列层**：可替换为 Redis + Celery
- **数据库**：可切换到 PostgreSQL
- **文件存储**：可切换到 S3/OSS
- **接口解耦**：各层独立替换

---

## 🧪 测试策略（待补充）

QA工程师的测试计划文档尚未生成，建议后续补充以下内容：

### 建议测试范围

1. **单元测试**
   - 爬取引擎各插件的fetch/parse/discover_links方法
   - 任务调度器的状态转换逻辑
   - AI精炼模块的提示词模板渲染

2. **集成测试**
   - 完整的爬取→精炼→存储流程
   - 任务递归生成机制
   - 插件系统的发现和匹配逻辑

3. **端到端测试**
   - 用户创建信源→触发爬取→查看结果的完整流程
   - 定时任务的触发和执行

4. **特殊场景测试**
   - Mock HTTP服务器测试爬取逻辑（避免网络依赖）
   - 反爬机制的应对测试
   - 异常页面的容错处理

---

## 📝 下一步行动

### 立即可做

1. **初始化项目结构**
   ```bash
   mkdir -p backend/app/{api,core,models,plugins,schemas}
   mkdir -p frontend/src/{pages,components,api,stores}
   mkdir -p backend/plugins
   ```

2. **安装依赖**
   ```bash
   # 后端
   cd backend
   uv init
   uv add fastapi sqlalchemy httpx beautifulsoup4 playwright apscheduler openai

   # 前端
   cd frontend
   pnpm create vite . --template react
   pnpm add antd axios
   ```

3. **搭建后端骨架**
   - 创建FastAPI应用入口
   - 配置SQLAlchemy数据库连接
   - 定义数据模型

### 短期目标（1-2周）

- 完成P0阶段开发：后端骨架 + 数据模型 + 通用爬取 + 基础API
- 实现单页面爬取的完整流程
- 搭建简单的前端界面进行测试

### 中期目标（1个月）

- 完成MVP四大功能
- 集成AI精炼模块
- 完善Web界面

---

## 📚 参考文档

- **详细架构设计**：`docs/architecture.md`（528行）
- **产品需求分析**：见本文档"产品需求分析"章节
- **技术选型理由**：见本文档"技术架构设计"章节

---

## 👥 团队贡献

- **产品经理**：完成产品需求分析、用户场景定义、MVP范围规划
- **技术架构师**：完成技术选型、系统架构设计、数据模型设计、详细架构文档编写
- **QA工程师**：测试计划待补充

---

*本文档由AI团队协作生成，旨在为个人信源库项目提供全面的规划指导。*
