# Personal Information Library

个人信源库 - 自动化信息采集与AI精炼系统

## 项目概述

通过自动化爬取和AI精炼，将分散的网络信息转化为结构化的个人知识库。

**核心价值链**：`信源发现 → 自动采集 → AI精炼 → 结构化入库 → 可检索复用`

## MVP功能

- ✅ **整站爬取**：入口页 → 子页面列表 → 递归爬取
- ✅ **任务系统**：优先级队列、状态机、失败重试
- ✅ **插件框架**：可扩展的爬取策略
- ✅ **AI精炼**：摘要+关键词提取
- ✅ **基础UI**：任务列表 + 结果预览

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **任务队列**: asyncio.Queue + APScheduler
- **爬取引擎**: httpx + BeautifulSoup4 + Playwright
- **AI集成**: OpenAI兼容接口
- **前端**: React + Vite + Ant Design
- **包管理**: uv (后端) + pnpm (前端)

## 快速开始

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install uv
uv pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env，配置 OPENAI_API_KEY

# 运行服务
uvicorn app.main:app --reload
```

访问 http://localhost:8000/docs 查看API文档

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

## 项目结构

```
Personal-Information-Library/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/         # REST API
│   │   ├── core/        # 核心逻辑
│   │   ├── models/      # 数据模型
│   │   ├── plugins/     # 插件系统
│   │   └── schemas/     # Pydantic模型
│   └── tests/           # 测试代码
├── frontend/            # React 前端
│   └── src/
├── docs/                # 项目文档
│   ├── architecture.md  # 技术架构
│   ├── test-plan.md     # 测试计划
│   └── PRD.md          # 产品需求
└── README.md
```

## 开发状态

### ✅ Week 1 - 核心基础设施（已完成）
- [x] 后端骨架 + 数据模型（6张表）
- [x] 插件框架基础
- [x] 任务系统实现
- [x] 基础API端点
- [x] 50个测试用例通过

### ✅ Week 2 - 调度优化与反爬（已完成）
- [x] APScheduler集成（定时任务）
- [x] 整站爬取优化（循环检测 + URL过滤）
- [x] 反爬处理（UA轮换 + 限速 + 并发控制）

### ✅ Week 3 - AI精炼引擎（已完成）
- [x] OpenAI兼容接口集成
- [x] 自动精炼流程
- [x] 精炼API（手动触发 + 模板管理 + 预览）

### ✅ Week 4 - React前端（已完成）
- [x] React + TypeScript + Vite
- [x] Ant Design UI
- [x] 信源管理、任务列表、结果详情页面

## 🎉 项目已完成交付！

**后端**：23个API端点，3个核心引擎，完整的任务调度和AI精炼系统
**前端**：15个文件，3个页面组件，完整的用户界面
**测试**：50个测试用例，核心模块100%覆盖率
**文档**：完整的架构、测试、产品文档


### Tmux 常用操作

项目使用 tmux 进行多窗口开发，方便查看不同 agent 的工作进程。

**基本操作**：
```bash
# 查看所有会话
tmux ls

# 连接到会话
tmux attach -t <session-name>

# 创建新会话
tmux new -s <session-name>
```

**窗口操作**（在 tmux 会话中）：
```bash
Ctrl+b c        # 创建新窗口
Ctrl+b n        # 切换到下一个窗口
Ctrl+b p        # 切换到上一个窗口
Ctrl+b 0-9      # 切换到指定编号的窗口
Ctrl+b w        # 列出所有窗口
Ctrl+b ,        # 重命名当前窗口
Ctrl+b &        # 关闭当前窗口
```

**会话操作**：
```bash
Ctrl+b d        # 分离会话（后台运行）
Ctrl+b s        # 列出所有会话
Ctrl+b $        # 重命名会话
```

**面板操作**：
```bash
Ctrl+b %        # 垂直分割面板
Ctrl+b "        # 水平分割面板
Ctrl+b 方向键   # 切换面板
Ctrl+b x        # 关闭当前面板
```

**其他**：
```bash
Ctrl+b ?        # 显示所有快捷键
Ctrl+b [        # 进入复制模式（可滚动查看历史）
q               # 退出复制模式
```

## 文档

- [技术架构设计](docs/architecture.md)
- [测试计划](docs/test-plan.md)
- [产品需求文档](docs/PRD.md)
- [项目总结](docs/project-summary.md)

## License

MIT
