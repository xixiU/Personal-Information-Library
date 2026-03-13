# Personal Information Library - Backend

个人信源库后端服务，基于 FastAPI 构建。

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装 uv
pip install uv

# 安装项目依赖
uv pip install -e ".[dev]"
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置必要的参数（如 OPENAI_API_KEY）
```

### 3. 运行服务

```bash
# 开发模式
uvicorn app.main:app --reload

# 或直接运行
python -m app.main
```

服务将在 http://localhost:8000 启动

### 4. 查看API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
backend/
├── app/
│   ├── api/              # REST API 路由
│   ├── core/             # 核心业务逻辑
│   │   ├── scheduler.py  # 任务调度器
│   │   ├── crawler.py    # 爬取引擎
│   │   └── refiner.py    # AI精炼引擎
│   ├── models/           # 数据模型
│   ├── plugins/          # 内置插件
│   │   ├── base.py       # 插件基类
│   │   └── generic.py    # 通用插件
│   ├── schemas/          # Pydantic 模型
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库连接
│   └── main.py           # FastAPI 入口
├── plugins/              # 用户自定义插件
├── tests/                # 测试代码
├── pyproject.toml        # 项目配置
└── README.md
```

## 开发

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
black app/
ruff check app/
```

## Week 1 任务清单

- [x] 后端骨架搭建
- [x] 数据模型创建（6张表）
- [x] 插件框架基础（base.py + generic.py）
- [ ] 任务系统基础实现
- [ ] 基础 API 端点
- [ ] 单元测试框架搭建
