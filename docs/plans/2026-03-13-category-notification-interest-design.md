# 分类管理 + 通知管理 + 兴趣图谱 设计方案

> 讨论日期：2026-03-13
> 状态：待实现

---

## 背景与动机

当前系统已完成信源采集、AI 精炼的核心流程，但缺乏以下能力：

1. **分类管理**：信源没有分组，无法按主题（技术文档、投资、悦读等）差异化配置精炼策略
2. **通知管理**：没有推送能力，用户需要主动打开页面查看结果
3. **兴趣图谱**：系统不了解用户偏好，无法做个性化推荐和过滤

---

## 核心设计原则

- 一个信源只属于一个分类（多类别场景通过创建不同爬取插件解决）
- 分类有专属精炼模板，支持继承通用模板（通过特殊格式标记）
- 通知按 Cron 定时汇总推送，不是每条都推
- 兴趣图谱分存量（手动配置）和增量（AI 从行为中发现），可见可编辑

---

## 一、分类管理（Category）

### 数据模型

```
Category
├── id
├── name                  # 分类名称，如"技术文档"、"投资"、"悦读"
├── description           # 描述
├── refine_template_id    # 关联精炼模板（null = 使用通用模板）
├── default_priority      # 影响任务队列优先级（数字越大越优先）
├── auto_refine           # 是否自动精炼（bool）
├── created_at
└── updated_at
```

### 精炼模板继承机制

- 未设置 `refine_template_id` → 使用系统通用模板
- 设置了专属模板 → 使用专属模板
- 专属模板内容支持 `{{inherit}}` 占位符，表示继承通用模板的 prompt 内容

示例：
```
你是一个投资分析助手。
{{inherit}}
额外要求：重点提取公司名称、估值、融资轮次、投资机构。
```

### 分类级别的扩展配置

- **爬取频率**：分类可设置默认 Cron，信源未单独配置时继承分类的
- **自动精炼开关**：纯存档类分类可关闭 AI 精炼，节省 token
- **任务优先级**：影响调度器队列，"投资"类可设为高优先级

### Source 表变更

```
Source 新增字段：
└── category_id    # FK → Category.id（可为 null，表示未分类）
```

---

## 二、用户反馈与兴趣图谱

### 数据模型

```
UserFeedback
├── id
├── refined_result_id     # FK → RefinedResult.id
├── action                # like | collect | comment | dislike
├── comment_text          # 评论内容（action=comment 时有值）
└── created_at

InterestPoint
├── id
├── name                  # 兴趣点名称，如"Rust 语言"、"AI 芯片"
├── description
├── source                # manual（手动创建）| ai_discovered（AI 发现）
├── weight                # 权重 0.0~1.0，影响推荐排序
├── category_id           # 可选，归属某个分类
├── keywords              # JSON，关键词列表
├── is_active             # 用户可手动关闭某个兴趣点
├── created_at
└── updated_at
```

### 兴趣图谱工作流

```
用户行为（点赞/收藏）
        ↓
定期（如每天凌晨）触发 AI 分析任务
        ↓
提取近期高评分内容的共性特征（关键词、主题、实体）
        ↓
与现有 InterestPoint 对比
  ├── 已有 → 更新 weight
  └── 新发现 → 创建新 InterestPoint（source=ai_discovered）
        ↓
用户在"兴趣图谱"页面查看、编辑、删除兴趣点
```

### 前端：精炼结果详情页

每条精炼结果需要独立详情页，支持：
- 点赞 / 收藏 / 踩 / 评论
- 查看原文链接
- 查看 AI 摘要和关键词
- 相关推荐（基于兴趣图谱匹配）

### 前端：兴趣图谱页

- 可视化展示兴趣点（词云或力导向图）
- 列表视图：显示每个兴趣点的来源（手动/AI）、权重、关联关键词
- 支持手动添加、编辑权重、删除、启用/禁用

---

## 三、通知管理

### 数据模型

```
NotificationChannel（通知渠道）
├── id
├── name
├── type                  # webhook | telegram
├── config                # JSON
│   ├── webhook: { url, headers, method }
│   └── telegram: { bot_token, chat_id }
├── message_template      # 消息格式模板，支持变量
├── enabled
├── created_at
└── updated_at

NotificationRule（通知规则）
├── id
├── name
├── channel_id            # FK → NotificationChannel.id
├── cron_expr             # 触发时机，如 "0 9 * * *"（每天9点）
├── interest_filter       # JSON，使用哪些兴趣点过滤内容
├── category_filter       # JSON，只推送哪些分类的内容
├── min_score             # 最低兴趣匹配分数（0.0~1.0）
├── max_items             # 每次最多推送几条
├── last_sent_at
├── enabled
├── created_at
└── updated_at
```

### 通知触发流程

```
Cron 触发 NotificationRule
        ↓
查询 last_sent_at 之后的新精炼结果
        ↓
用 interest_filter + category_filter 过滤
        ↓
按兴趣匹配分数排序，取 top max_items 条
        ↓
渲染 message_template
        ↓
发送到对应渠道（Webhook / Telegram）
        ↓
更新 last_sent_at
```

### 消息模板示例

**Telegram 模板：**
```
📚 今日信息汇总（{{date}}）

共 {{count}} 条新内容：

{{#each items}}
{{index}}. **{{title}}**
   {{summary}}
   🔗 {{url}}

{{/each}}
```

**Webhook JSON 模板：**
```json
{
  "date": "{{date}}",
  "items": [
    {
      "title": "{{title}}",
      "summary": "{{summary}}",
      "url": "{{url}}",
      "score": "{{score}}"
    }
  ]
}
```

---

## 四、实现优先级建议

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 分类管理 CRUD + Source 关联 | 基础能力，其他功能依赖它 |
| P0 | 精炼结果详情页 + 用户反馈 | 点赞/收藏是兴趣图谱的数据来源 |
| P1 | 精炼模板继承机制 | 分类差异化精炼 |
| P1 | 通知渠道 + 通知规则管理 | Webhook 先于 Telegram |
| P2 | 兴趣图谱 AI 分析任务 | 需要足够的反馈数据才有意义 |
| P2 | 兴趣图谱可视化页面 | 词云/力导向图 |
| P3 | 增量兴趣驱动的通知过滤 | 依赖兴趣图谱成熟后再做 |

---

## 五、待决策事项

- [ ] 精炼模板的 `{{inherit}}` 语法具体格式和解析方式
- [ ] 兴趣匹配分数的计算算法（关键词 TF-IDF？向量相似度？）
- [ ] Telegram Bot 的申请和配置方式是否需要文档说明
- [ ] 兴趣图谱可视化选用哪个前端库（ECharts / D3.js / AntV）
