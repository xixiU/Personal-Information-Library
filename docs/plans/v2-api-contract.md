# v2 可用性迭代 — 接口契约（冻结版）

> **管理者产出** · 前后端唯一对齐依据
> 前端与后端**不互相阅读代码**，一切以本契约为准。任何字段/形状变更须先改本文件并通知双方。

---

## 0. 总原则

- 用户视角只有一个字段 `source_type`：`single_page` | `full_site` | `rss`。
- 前端**不再向用户暴露 `plugin_id`**，创建/编辑信源只提交 `source_type` + 表单化 `config`。
- 后端负责把 `source_type` 映射到内部执行（crawl_mode + 插件选择），前端无需感知。
- `config` 前端提交**扁平 JSON 对象**（不是字符串），后端负责存储与校验。

---

## 1. Source 数据模型（对外 JSON）

创建 / 更新 / 返回统一使用以下形状：

```jsonc
{
  "id": 1,                          // 返回时有
  "name": "阮一峰的网络日志",
  "url": "https://www.ruanyifeng.com/blog/",
  "source_type": "rss",             // 'single_page' | 'full_site' | 'rss'  ← 新增，前端主用
  "cron_expr": "0 */4 * * *",       // 可空
  "config": { "max_items": 20, "fetch_full_content": true },  // 扁平对象，随 source_type 不同
  "category_id": 3,                 // 可空
  "status": "active",               // 返回时有
  "created_at": "...", "updated_at": "..."  // 返回时有
}
```

**兼容策略（后端负责，前端无需关心）**
- 旧数据 `source_type` 为空 → 后端按规则推断后返回：
  - `plugin` 是 RSS 类 → `rss`
  - `crawl_mode == full_site` → `full_site`
  - 否则 → `single_page`
- `crawl_mode` / `plugin_id` 保留在库中作为内部实现，**不在前端交互中出现**（返回体可保留但前端忽略）。

---

## 2. 配置项 Schema API（驱动前端动态表单）

前端**不硬编码配置项**，进入表单时按 `source_type` 拉取 schema 渲染。

```
GET /api/sources/config-schema?source_type=full_site
```

响应：
```jsonc
{
  "source_type": "full_site",
  "fields": [
    {
      "name": "max_depth",
      "type": "number",        // number | switch | text | textarea | select
      "label": "最大深度",
      "default": 2,
      "min": 1, "max": 5,      // number 用
      "help": "爬取子链接的层数",
      "advanced": false,        // true 的字段前端收进「高级配置」折叠面板
      "options": null           // select 用: [{label,value}]
    }
  ]
}
```

**冻结的字段清单（后端按此返回，前端按此渲染）**

### single_page
| name | type | label | default | 约束 | advanced | help |
|---|---|---|---|---|---|---|
| content_selector | text | 内容选择器 | "" | — | true | CSS 选择器，留空自动提取正文 |
| timeout | number | 请求超时(秒) | 30 | 5–120 | true | — |
| max_retries | number | 重试次数 | 3 | 0–5 | true | — |

### full_site
| name | type | label | default | 约束 | advanced | help |
|---|---|---|---|---|---|---|
| max_depth | number | 最大深度 | 2 | 1–5 | false | 爬取子链接的层数 |
| max_pages | number | 最大页数 | 50 | 1–500 | false | 总共爬取的页面上限 |
| same_domain_only | switch | 仅同域名 | true | — | false | 仅爬取与入口同域名的链接 |
| url_whitelist | textarea | URL 白名单 | "" | — | true | 每行一个正则，只爬匹配的 URL（可选） |
| timeout | number | 请求超时(秒) | 30 | 5–120 | true | — |
| max_retries | number | 重试次数 | 3 | 0–5 | true | — |

### rss
| name | type | label | default | 约束 | advanced | help |
|---|---|---|---|---|---|---|
| max_items | number | 保留条目数 | 20 | 1–200 | false | 每次最多爬取的文章数 |
| fetch_full_content | switch | 爬取全文 | true | — | false | 关闭则只保留 feed 摘要 |
| timeout | number | 请求超时(秒) | 30 | 5–120 | true | — |

> 说明：RSS 的「更新频率」不进 config，直接用信源的 `cron_expr` 字段。前端在 RSS 表单里用下拉（每小时/每4小时/每天/每周）写入 `cron_expr`。

---

## 3. 批量导入 API

```
POST /api/sources/batch-import
```

请求：
```jsonc
{
  "import_type": "opml",            // 'opml' | 'url_list'
  "data": "<opml>...</opml>",       // opml: XML 字符串；url_list: string[]
  "default_category_id": 3,          // 可空
  "default_config": {                // 可空，套用到所有导入项
    "max_items": 20, "fetch_full_content": true
  },
  "default_cron_expr": "0 */4 * * *" // 可空
}
```

响应：
```jsonc
{
  "success_count": 12,
  "failed_count": 1,
  "skipped_count": 3,               // URL 已存在
  "details": [
    { "name": "xxx", "url": "https://...", "status": "success", "reason": "" },
    { "name": "yyy", "url": "https://...", "status": "skipped", "reason": "URL 已存在" }
  ]
}
```

**预览需求**：前端 OPML 解析可在前端本地做（FileReader + DOMParser）用于预览勾选；最终 `import_type=url_list` 提交已勾选的 URL 列表。OPML 直传也需支持（`import_type=opml`），后端负责解析。两条路径后端都要实现。导入的信源 `source_type` 一律为 `rss`。URL 去重：已存在则 `skipped`。

---

## 4. 仪表盘统计 API

```
GET /api/dashboard/stats
```

响应：
```jsonc
{
  "sources": { "total": 20, "today": 2 },
  "tasks": { "pending": 1, "running": 0, "success": 130, "failed": 4 },
  "results": { "total": 120, "today": 5, "avg_quality_score": 78.5 },
  "recent_results": [               // 最新精炼结果，最多 5 条
    { "id": 88, "title": "...", "summary": "...", "quality_score": 82, "created_at": "..." }
  ]
}
```

---

## 5. 联调约定

- 后端所有新 API 挂在现有 FastAPI router 下，路径严格按本文件。
- 字段名、类型、枚举值大小写严格一致（`single_page` 非 `singlePage`）。
- 出现契约不足或歧义 → 找管理者裁决改本文件，**不要私自约定**。
