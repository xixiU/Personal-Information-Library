# 兴趣图谱 — 产品需求文档

> 创建日期: 2026-03-19
> 状态: 待确认

## 一、功能概述与核心价值

### 定位

在现有「信源采集 → AI 精炼 → 通知推送」链路基础上，引入用户反馈闭环和兴趣建模，实现个性化内容排序、过滤和推荐。

### 核心价值

| 价值 | 说明 |
|------|------|
| 从被动浏览到主动匹配 | 系统根据用户兴趣自动排序内容，高匹配度优先展示 |
| 越用越精准 | 用户反馈（点赞/收藏/踩/批注）持续优化兴趣模型 |
| 与通知联动 | 兴趣匹配分数可作为通知触发条件，只推送真正关心的内容 |
| AI 辅助发现 | 基于已有内容和反馈数据，AI 自动发现潜在兴趣点 |

---

## 二、用户反馈动作集

最终确认的反馈动作：`like | collect | dislike | comment`

| 动作 | 语义 | 对兴趣权重的影响 | 可重复 | 互斥关系 |
|------|------|-----------------|--------|---------|
| like | 点赞，表示内容有价值 | 关联关键词权重 +0.05 | 否（toggle） | 与 dislike 互斥 |
| collect | 收藏，表示内容值得留存 | 关联关键词权重 +0.05 | 否（toggle） | 无 |
| dislike | 踩，表示内容质量不佳 | 关联关键词权重 -0.05 | 否（toggle） | 与 like 互斥 |
| comment | 批注，记录个人想法 | 为 AI 发现提供语义信号 | 是（可多条） | 无 |

**交互规则**：
- like 和 collect 可共存（点赞 + 收藏）
- like 和 dislike 互斥：提交 dislike 时自动移除已有 like，反之亦然
- comment 定位为"个人批注"，非社交评论，不做回复/列表等社交功能

---

## 三、数据模型设计

### 新增表

**UserFeedback**（用户反馈）
```
id              Integer, PK, autoincrement
refined_result_id  Integer, FK → refined_results.id, NOT NULL, INDEX
action          String(20), NOT NULL        # like | collect | dislike | comment
comment_text    Text, nullable              # action=comment 时有值
created_at      DateTime, default=utcnow, INDEX

联合索引: (refined_result_id, action)
```

**InterestPoint**（兴趣点）
```
id              Integer, PK, autoincrement
name            String(100), NOT NULL, UNIQUE
description     Text, nullable
source          String(20), NOT NULL, default="manual"  # manual | ai_discovered
weight          Float, NOT NULL, default=0.5            # 0.0~1.0
category_id     Integer, FK → categories.id, nullable, INDEX
keywords        JSON, NOT NULL, default=[]              # ["rust", "wasm", "编译器"]
is_active       Boolean, NOT NULL, default=True
created_at      DateTime, default=utcnow
updated_at      DateTime, default=utcnow, onupdate=utcnow
```

### 已有表变更

**RefinedResult** 新增字段：
```
interest_score  Float, nullable, INDEX      # 0.0~1.0，兴趣匹配分数
```

### 设计决策

| 决策 | 理由 |
|------|------|
| UserFeedback 独立建表 | 一对多关系（一条精炼结果可有多次反馈），塞进 meta_data 无法高效查询和聚合 |
| InterestPoint 独立建表 | 与 Category 职责不同（分类指导精炼，兴趣点描述用户偏好），避免上帝类 |
| interest_score 独立字段 | 需支持排序和筛选，SQLite JSON 字段无法建索引，独立字段可直接 ORDER BY + INDEX |
| keywords 匹配用 json_each() | 小数据量毫秒级，interest_score 预计算后存字段，查询走索引避免实时计算 |

### ER 关系

```
RefinedResult ──1:N──→ UserFeedback
Category ──1:N──→ InterestPoint（可选归属）
InterestPoint.keywords ←匹配→ RefinedResult.keywords → interest_score
```

---

## 四、完整功能逻辑与数据流

### 数据流 1：用户反馈收集

```
精炼结果详情页 → 用户点赞/收藏/踩/批注
       ↓
写入 UserFeedback 表
       ↓
实时更新：该结果的关键词命中的 InterestPoint.weight
  - like/collect → weight += 0.05（上限 1.0）
  - dislike → weight -= 0.05（下限 0.0）
```

### 数据流 2：兴趣匹配评分（迭代二）

```
新 RefinedResult 产生
       ↓
提取 keywords（精炼时已生成）
       ↓
与所有 active InterestPoint.keywords 做交集匹配
       ↓
interest_score = Σ(匹配的兴趣点 weight) / 匹配数
       ↓
写入 RefinedResult.interest_score
```

### 数据流 3：AI 发现兴趣点

```
手动触发 或 定时任务
       ↓
收集近 N 天的 RefinedResult.keywords（可按分类过滤）
       ↓
收集 UserFeedback 数据，构建加权关键词频率表
  - like/collect 的内容关键词权重上调
  - dislike 的关键词权重下调
  - comment 文本提供语义补充
       ↓
调用 AI 分析（复用 OpenAI 兼容接口）
  - 输入：加权关键词、已有兴趣点、用户批注摘要
  - 输出：3-5 个兴趣点候选（name + keywords + reason）
       ↓
写入 InterestPoint（source=ai_discovered, is_active=false）
       ↓
用户在兴趣图谱页面确认启用或删除候选
```

**冷启动策略**：AI 发现不依赖反馈数据，第一版直接分析 RefinedResult.keywords 高频聚类。有反馈数据后再加权优化。

### 数据流 4：兴趣驱动通知（迭代二）

```
NotificationRule 新增 rule_type: interest_match
conditions: { min_interest_score: 0.6 }
       ↓
精炼完成 → NotificationEngine.evaluate()
  - 已有: quality_threshold / keyword_match / new_content
  - 新增: interest_match → 检查 interest_score ≥ 阈值
       ↓
命中规则 → 按渠道发送通知
```

### 用户操作路径

**路径 A：浏览 → 反馈 → 自动优化**
1. 用户在精炼结果列表浏览内容
2. 进入详情页，点赞/收藏/踩/批注
3. 系统记录反馈，自动微调相关兴趣点权重
4. 下次新内容匹配度高的排在前面（迭代二）

**路径 B：手动管理兴趣点**
1. 进入"兴趣图谱"页面（列表视图）
2. 手动添加兴趣点：名称、关键词、初始权重
3. 可关联到某个分类（可选）
4. 启用/禁用/调整权重/删除

**路径 C：AI 发现兴趣点**
1. 在兴趣图谱页面点击"发现新兴趣"
2. 系统调用 AI 分析，返回候选兴趣点
3. 候选以高亮样式展示，用户确认启用或删除

---

## 五、迭代一范围与验收标准

### 范围

| 模块 | 功能 | 后端 | 前端 |
|------|------|------|------|
| 用户反馈 | 点赞/收藏/踩/批注 | UserFeedback CRUD API | 精炼详情页反馈按钮组 |
| 兴趣点管理 | 手动 CRUD + AI 发现 | InterestPoint CRUD API + AI 分析服务 | 兴趣点列表页（含来源标记） |
| AI 发现 | 关键词聚类 + AI 分析 | 定时/手动触发，调用 AI | 发现结果展示，用户确认/拒绝 |
| 可视化 | 兴趣点词云 | 统计 API | ECharts 词云组件 |

### 后端任务（B1-B6）

| 编号 | 任务 | 依赖 |
|------|------|------|
| B1 | 数据模型：UserFeedback + InterestPoint 新表，RefinedResult 新增 interest_score | 无 |
| B2 | Pydantic Schema：校验模型 | B1 |
| B3 | UserFeedback CRUD API（含 like/dislike 互斥逻辑） | B2 |
| B4 | InterestPoint CRUD API（含筛选、启用/禁用） | B2 |
| B5 | AI 发现兴趣点服务（InterestDiscoverer + 触发 API） | B3, B4 |
| B6 | 兴趣点统计 API（供词云使用） | B4 |

### 前端任务（F1-F4）

| 编号 | 任务 | 依赖 |
|------|------|------|
| F1 | API 客户端封装（feedback + interestPoints） | 无 |
| F2 | 精炼详情页反馈按钮组 | F1 |
| F3 | 兴趣点列表页（CRUD + AI 发现触发 + 候选确认） | F1 |
| F4 | 词云可视化（ECharts + echarts-wordcloud） | F3 |

### 验收标准

**用户反馈**：
1. 精炼详情页展示 👍赞 / ⭐收藏 / 👎踩 / 📝批注 按钮
2. 按钮为 toggle 模式，已激活再点击 = 取消
3. 赞和踩互斥：点赞自动取消踩，反之亦然
4. 批注可多次提交，展示批注列表（时间 + 内容），支持删除

**兴趣点管理**：
1. 兴趣点列表页展示所有兴趣点，支持按来源/状态/分类筛选
2. 手动创建兴趣点：名称（唯一）、描述、关键词（Tags 输入）、权重（滑块）、分类（下拉）
3. 编辑/删除/启用/禁用操作完整
4. AI 发现的候选（is_active=false）高亮展示，支持"确认启用"/"删除"

**AI 发现**：
1. 点击"发现新兴趣"按钮触发 AI 分析
2. 返回 3-5 个候选兴趣点，写入数据库（source=ai_discovered, is_active=false）
3. 无数据时返回空列表，不报错
4. AI 接口失败时展示错误提示

**词云可视化**：
1. 兴趣点页面支持列表/词云 Tab 切换
2. 词大小与 weight 成正比
3. 颜色区分来源（手动 vs AI 发现）
4. 点击词弹出详情（权重、关键词、关联反馈数）

---

## 六、迭代二范围

| 模块 | 功能 | 说明 |
|------|------|------|
| 兴趣匹配评分 | 精炼完成后计算 interest_score | 关键词交集匹配 + 权重加权，写入独立字段 |
| 结果排序 | 综合排序 = quality_score × 0.6 + interest_score × 0.4 | 结果列表增加兴趣分数列 |
| 通知联动 | 新增 interest_match 规则类型 | NotificationEngine 新增评估逻辑 |
| 反馈驱动权重 | 用户反馈自动调整兴趣点权重 | 反馈写入时触发权重更新 |
| 可视化增强 | 力导向图（兴趣点 + 分类关联） | ECharts 力导向图组件 |

---

## 七、风险与应对

| 风险 | 应对 |
|------|------|
| 冷启动（无反馈数据） | AI 发现不依赖反馈，直接分析已有 keywords 聚类；手动兴趣点即时生效 |
| AI 发现质量不可控 | 候选默认 is_active=false，需用户手动确认启用 |
| 权重漂移 | weight 上下限 0.0~1.0，单次调整 ±0.05 |
| interest_match 与 keyword_match 重叠 | 定位不同：interest_match 是模糊匹配+权重，keyword_match 是精确匹配 |
| 词云性能 | 兴趣点通常几十个，ECharts 无压力 |
