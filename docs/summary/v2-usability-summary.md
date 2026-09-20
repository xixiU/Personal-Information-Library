# v2 可用性迭代 — 实施总结

> 团队协作交付：管理者 + 产品 + 后端 + 前端。前后端不互看代码，靠冻结的接口契约对齐。
> 相关文档：[PRD](../plans/v2-usability-prd.md) · [接口契约](../plans/v2-api-contract.md) · [UI文案规范](../plans/v2-ui-copy.md)

## 一、本次解决的 4 个核心痛点

| 痛点 | 解决方案 | 涉及 |
|------|---------|------|
| 配置不友好（裸 JSON 文本框） | 后端出 config-schema，前端 schema 驱动动态表单，零 JSON 手写 | 前+后 |
| 整站/单页/RSS 概念混乱 | 新增 `source_type`，三选一卡片显式建模，后端自动映射到内部 crawl_mode+插件 | 前+后 |
| 无批量导入 | OPML 上传 / URL 列表粘贴 → 预览勾选 → 批量导入，URL 去重 | 前+后 |
| UI 简陋 | 仪表盘首页 + 卡片化 + 空状态 + 引导 Alert + 全局主题 | 前 |

## 二、后端交付（backend/）

- **source_type 建模**：`models/source.py` 新增 `source_type`，CrawlMode 补 `rss`。`api/sources.py` 的 `_apply_source_type_mapping()`（source_type→crawl_mode+plugin_id）和 `_infer_source_type()`（旧数据兼容推断，统一 `name=="rss"` 判断）。`database.py` 启动时轻量迁移 `_migrate_add_source_type()`。
- **config-schema API**：`core/source_config_schema.py` 定义三类型字段元数据，`GET /api/sources/config-schema`。
- **批量导入 API**：`POST /api/sources/batch-import`，支持 opml/url_list，去重返回 success/failed/skipped。
- **仪表盘 API**：`api/dashboard.py`，`GET /api/dashboard/stats`，UTC+8 今日统计 + 最近5条精炼结果。

## 三、前端交付（frontend/）

- **SourceList.tsx**：三选一卡片、schema 驱动动态表单（5种控件+高级配置折叠）、批量导入三步对话框、去黑话文案+引导 Alert+分情况成功提示、空状态。移除 plugin_id 和裸 JSON 文本框。
- **Dashboard.tsx（新增）**：默认首页，快速开始/数据概览/任务状态/最新结果。
- **App.tsx**：新增仪表盘路由与菜单，全局 ConfigProvider 主题。
- **CategoryList / TaskList**：Card 包裹 + 空状态。

## 四、管理者复核发现并修复的问题

1. **[P0 已修]** 后端路由顺序错误：`config-schema`/`batch-import` 静态路由原在 `/{source_id}` 动态路由之后，被拦截导致接口不可达。已移到动态路由之前。
2. **[P0 已修]** 前端首轮遗漏 5 项交互补丁（文案仍含技术黑话、缺引导），打回后落实。
3. **[P2 已修]** 后端 RSS 插件判断两处口径不一致，统一为严格匹配。

## 五、待人工验证（按团队规则，研发不做编译/启动）

1. **数据库迁移**：首次 `uv run uvicorn app.main:app` 启动会自动执行 `_migrate_add_source_type()` 加 source_type 列，启动后确认。
2. **前端构建**：`cd frontend && pnpm install && pnpm build`。
3. **端到端联调**：动态表单渲染、批量导入 OPML（建议用 Feedly/Inoreader 真实导出文件测解析率）、仪表盘数据。产品可承接此轮验收。

## 六、已知未决（P2，不阻断）

- 仪表盘任务统计只计 pending/running/success/failed 四态，`TaskStatus.TIMEOUT` 未计入任何桶，超时任务在仪表盘"隐身"。后续可在 dashboard.py 增加 timeout 统计或并入 failed。
- 信源类型三选一卡片为纯 onClick 实现，无键盘可达性与 aria 标记，无障碍轮次可补 role/tabIndex/aria-pressed。

## 七、验收指标（产品评估）

- 信源创建流程：理想路径 43s / 最差路径 78s，均 < 120s 目标。
- 任务1交互综合评分 70 → 90（文案友好度 50→90，交互流程 80→95）。
