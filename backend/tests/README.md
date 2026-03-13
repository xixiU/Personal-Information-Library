# 测试框架说明

## 测试环境搭建

### 安装依赖

```bash
pip install fastapi uvicorn sqlalchemy httpx beautifulsoup4 lxml playwright apscheduler openai pydantic pydantic-settings pytest pytest-asyncio pytest-cov pytest-mock
```

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_models.py
pytest tests/test_plugins.py

# 运行测试并生成覆盖率报告
pytest tests/ --cov=app --cov-report=term-missing

# 运行测试（详细输出）
pytest tests/ -v

# 运行特定测试类或方法
pytest tests/test_models.py::TestSourceModel
pytest tests/test_models.py::TestSourceModel::test_create_source
```

## 测试结构

```
backend/tests/
├── __init__.py
├── conftest.py           # 共享 fixtures（数据库、测试数据）
├── test_models.py        # 数据模型测试（DB-U01/U02/U03）
└── test_plugins.py       # 插件框架测试（PLG-U01/U02）
```

## 已实现的测试用例

### 数据模型测试 (test_models.py)

**DB-U01: 创建信源记录**
- ✅ test_create_source - 创建基本信源
- ✅ test_create_source_with_cron - 创建带定时表达式的信源
- ✅ test_source_unique_url - URL唯一性约束

**DB-U02: 查询信源**
- ✅ test_query_source_by_url - 按URL查询
- ✅ test_query_source_by_status - 按状态查询

**DB-U03: 更新信源**
- ✅ test_update_source - 更新信源内容
- ✅ test_update_source_status - 更新信源状态

**任务模型测试**
- ✅ test_create_crawl_task - 创建爬取任务
- ✅ test_create_refine_task - 创建精炼任务
- ✅ test_create_child_task - 创建子任务（递归爬取）
- ✅ test_query_tasks_by_status - 按状态查询任务
- ✅ test_update_task_status - 更新任务状态
- ✅ test_update_task_retry - 更新重试计数

**爬取结果测试**
- ✅ test_create_crawl_result - 创建爬取结果
- ✅ test_query_result_by_source - 按信源查询
- ✅ test_query_result_by_url - 按URL查询
- ✅ test_update_crawl_result - 更新结果

**精炼结果测试**
- ✅ test_create_refined_result - 创建精炼结果
- ✅ test_query_refined_by_crawl_result - 按爬取结果查询

**插件模型测试**
- ✅ test_create_plugin - 创建插件记录
- ✅ test_plugin_unique_name - 插件名称唯一性
- ✅ test_query_enabled_plugins - 查询启用的插件
- ✅ test_update_plugin - 更新插件信息

**任务日志测试**
- ✅ test_create_task_log - 创建任务日志
- ✅ test_query_logs_by_task - 按任务查询日志

### 插件框架测试 (test_plugins.py)

**PLG-U01: 加载有效插件**
- ✅ test_generic_plugin_instantiation - GenericPlugin实例化
- ✅ test_generic_plugin_with_config - 自定义配置
- ✅ test_generic_plugin_is_crawler_plugin - 继承关系验证
- ✅ test_plugin_get_name - 获取插件名称
- ✅ test_plugin_get_domain_pattern_default - 默认域名模式

**PLG-U02: 加载无效插件**
- ✅ test_cannot_instantiate_abstract_base - 不能实例化抽象基类
- ✅ test_incomplete_plugin_missing_fetch - 缺少fetch方法
- ✅ test_incomplete_plugin_missing_parse - 缺少parse方法
- ✅ test_incomplete_plugin_missing_discover_links - 缺少discover_links方法
- ✅ test_complete_custom_plugin_works - 完整自定义插件可用

**GenericPlugin.parse 解析测试**
- ✅ test_parse_extracts_title - 提取标题
- ✅ test_parse_extracts_content - 提取正文
- ✅ test_parse_extracts_metadata - 提取元数据
- ✅ test_parse_empty_html - 空HTML处理
- ✅ test_parse_title_fallback_to_h1 - 标题回退到h1
- ✅ test_parse_title_fallback_to_untitled - 无标题时返回Untitled

**GenericPlugin.discover_links 链接发现测试**
- ✅ test_discover_same_domain_links - 发现同域名链接
- ✅ test_exclude_external_links - 排除外部链接
- ✅ test_resolve_relative_urls - 相对路径解析
- ✅ test_deduplicate_links - 链接去重
- ✅ test_remove_fragments - 移除URL fragment
- ✅ test_empty_html_no_links - 空HTML无链接

**辅助方法测试**
- ✅ test_is_same_domain_true - 同域名判断
- ✅ test_is_same_domain_false - 不同域名判断
- ✅ test_is_same_domain_with_subdomain - 子域名判断

## 测试覆盖率

当前覆盖率：26%（总体）

**已覆盖模块：**
- ✅ app/models/ - 100% (所有数据模型)
- ✅ app/plugins/generic.py - 93%
- ✅ app/plugins/base.py - 83%
- ✅ app/config.py - 100%

**待覆盖模块（Week 2-4）：**
- ⏳ app/core/crawler.py - 0% (Week 2)
- ⏳ app/core/scheduler.py - 0% (Week 2-3)
- ⏳ app/api/ - 0% (Week 3-4)
- ⏳ app/main.py - 0% (Week 4)

## Fixtures 说明

### 数据库 Fixtures

- `engine` - 内存SQLite引擎，每个测试后自动清理
- `db` - 数据库会话，每个测试后自动回滚

### 测试数据 Fixtures

- `sample_source` - 示例信源记录
- `sample_task` - 示例爬取任务
- `sample_crawl_result` - 示例爬取结果
- `sample_plugin` - 示例插件记录

## 注意事项

1. **SQLite内存模式**：测试使用 `sqlite:///:memory:`，数据不持久化
2. **自动回滚**：每个测试后自动回滚事务，保证测试隔离
3. **异步测试**：使用 `@pytest.mark.asyncio` 标记异步测试
4. **metadata字段**：SQLAlchemy保留字段，已改为 `meta_data`

## 下一步计划（Week 2）

根据测试计划 `docs/test-plan.md`，Week 2 重点：

1. **爬虫引擎测试（CRW-U01~U10）**
   - Mock HTTP Server 搭建
   - 单页爬取测试
   - 整站爬取测试
   - 链接发现和去重测试

2. **集成测试（CRW-I01~I05）**
   - 完整爬取流程
   - 失败重试机制
   - 并发爬取测试

3. **边界条件测试**
   - 循环链接检测
   - 超大页面处理
   - 超时和错误处理
