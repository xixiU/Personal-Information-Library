# 功能层 P0 接口契约 — 高亮笔记 + 已读归档

> 前后端不互看代码，以本契约为唯一对齐依据。

---

## 1. 高亮笔记（Highlight + Annotation）

### 数据模型

**新表 `highlights`**：
```sql
CREATE TABLE highlights (
    id INTEGER PRIMARY KEY,
    refined_result_id INTEGER NOT NULL,  -- 外键到 refined_results
    highlight_text TEXT NOT NULL,        -- 被高亮的原文
    note TEXT,                            -- 用户的批注（可选）
    position_start INTEGER,               -- 在原文中的起始位置（字符索引，可选）
    position_end INTEGER,                 -- 结束位置（可选）
    color VARCHAR(20) DEFAULT 'yellow',  -- 高亮颜色：yellow/green/blue/pink
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    FOREIGN KEY (refined_result_id) REFERENCES refined_results(id) ON DELETE CASCADE
);
CREATE INDEX idx_highlights_result ON highlights(refined_result_id);
CREATE INDEX idx_highlights_created ON highlights(created_at DESC);
```

### API

#### 创建高亮
```
POST /api/highlights
Request:
{
  "refined_result_id": 123,
  "highlight_text": "这是被高亮的原文片段",
  "note": "我的批注（可选）",
  "position_start": 100,  // 可选
  "position_end": 130,    // 可选
  "color": "yellow"       // 可选，默认 yellow
}

Response: 201
{
  "id": 1,
  "refined_result_id": 123,
  "highlight_text": "...",
  "note": "...",
  "color": "yellow",
  "created_at": "2026-03-23T10:00:00Z",
  ...
}
```

#### 列出某个结果的所有高亮
```
GET /api/results/refine/{result_id}/highlights
Response: 200
[
  { "id": 1, "highlight_text": "...", "note": "...", "color": "yellow", ... },
  ...
]
```

#### 更新高亮（主要是改批注）
```
PUT /api/highlights/{highlight_id}
Request:
{
  "note": "更新后的批注",
  "color": "green"  // 可选
}
```

#### 删除高亮
```
DELETE /api/highlights/{highlight_id}
Response: 204
```

#### 导出所有高亮为 Markdown
```
GET /api/highlights/export?format=markdown
Response: 200
Content-Type: text/markdown

# 我的高亮笔记

## [文章标题1](URL)
> 高亮原文1
**批注**：xxx

> 高亮原文2
**批注**：yyy

## [文章标题2](URL)
...
```

### 前端交互

- 结果详情页：用户选中文本 → 弹出工具条（高亮按钮 + 颜色选择器）→ 点击后文本变色 + 弹出批注输入框
- 高亮文本显示为 `<mark>` 标签 + 对应颜色背景
- 鼠标悬停高亮文本 → 显示批注气泡
- 点击高亮 → 可编辑批注或删除
- 结果列表页显示高亮数量徽章（如"3 个高亮"）

---

## 2. 已读/未读/归档

### 数据模型变更

**修改表 `refined_results`**：
```sql
ALTER TABLE refined_results ADD COLUMN is_read BOOLEAN DEFAULT FALSE;
ALTER TABLE refined_results ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
ALTER TABLE refined_results ADD COLUMN read_at DATETIME;  -- 标记已读的时间
CREATE INDEX idx_results_read ON refined_results(is_read, created_at DESC);
CREATE INDEX idx_results_archived ON refined_results(is_archived);
```

### API

#### 标记已读/未读
```
POST /api/results/refine/{result_id}/mark-read
Request:
{
  "is_read": true  // true=已读, false=未读
}

Response: 200
{
  "id": 123,
  "is_read": true,
  "read_at": "2026-03-23T10:30:00Z",
  ...
}
```

#### 标记归档/取消归档
```
POST /api/results/refine/{result_id}/archive
Request:
{
  "is_archived": true  // true=归档, false=取消归档
}

Response: 200
{
  "id": 123,
  "is_archived": true,
  ...
}
```

#### 列表接口增强（已有的 GET /api/results/refine）
新增查询参数：
- `is_read`: `true` | `false` | 不传（显示全部）
- `is_archived`: `true` | `false` | 不传（默认 `false`，不显示已归档）

**响应字段增强**：
每条 RefinedResult 记录新增字段：
- `is_read: boolean` — 是否已读
- `is_archived: boolean` — 是否已归档
- `read_at: string | null` — 标记已读的时间（ISO8601）
- `highlight_count: number` — 该结果的高亮数量（避免 N+1 查询）

示例：
```
GET /api/results/refine?is_read=false&is_archived=false
→ 返回未读且未归档的结果（默认场景）

GET /api/results/refine?is_archived=true
→ 返回已归档的结果（归档箱）

Response:
[
  {
    "id": 123,
    "title": "...",
    "is_read": false,
    "is_archived": false,
    "read_at": null,
    "highlight_count": 3,
    ...
  }
]
```

### 前端交互

- 结果列表页：
  - 未读结果左侧有蓝点标记
  - 每条结果右侧有"标记已读"按钮（已读状态显示为"标记未读"）
  - 每条结果有"归档"按钮（归档后从默认列表消失）
  - 顶部 Tab：全部 / 未读（默认） / 已归档
- 结果详情页：
  - 打开详情时自动标记为已读（调用 mark-read API）
  - 顶部有"归档"按钮

---

## 3. 前后端联调注意

### 高亮笔记
- 前端选中文本用 `window.getSelection()` 获取，需计算在 `summary` 字段中的 position（如果原文存在）
- 后端 `highlight_text` 存储时不做截断，完整保存用户选中的文本
- 导出 Markdown 时，按 `refined_result_id` 分组、按 `created_at` 排序

### 已读归档
- 打开详情页自动标记已读：前端在 `useEffect` 里调 `mark-read`
- 默认列表不显示已归档（`is_archived=false` 为默认过滤条件）
- 已读/归档是**独立维度**：可以"已读但未归档"或"未读但归档"

---

## 4. 数据库迁移

后端首次启动时自动执行（类似 v2 的 `_migrate_add_source_type`）：
- 新建 `highlights` 表
- `refined_results` 加 3 个字段（`is_read`/`is_archived`/`read_at`）
- 旧数据默认 `is_read=false`、`is_archived=false`
