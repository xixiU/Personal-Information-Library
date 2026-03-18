# 兴趣图谱设计方案

> 讨论日期：2026-03-13
> 状态：待实现

## 背景

当前系统已完成「分类管理 + 通知管理」，下一步通过用户反馈构建兴趣图谱，实现个性化推荐和过滤。

---

## 数据模型

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

## 工作流

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

## 前端需求

**精炼结果详情页**（已有页面需扩展）：
- 点赞 / 收藏 / 踩 / 评论
- 相关推荐（基于兴趣图谱匹配）

**兴趣图谱页**（新页面）：
- 可视化展示兴趣点（词云或力导向图）
- 列表视图：来源（手动/AI）、权重、关联关键词
- 支持手动添加、编辑权重、删除、启用/禁用

## 实现优先级

| 优先级 | 功能 |
|--------|------|
| P0 | 精炼结果详情页 + 用户反馈（点赞/收藏） |
| P1 | InterestPoint CRUD + 手动配置 |
| P2 | AI 分析任务（需要足够反馈数据） |
| P2 | 兴趣图谱可视化页面 |
| P3 | 兴趣驱动的通知过滤 |

## 待决策

- [ ] 兴趣匹配分数的计算算法（关键词 TF-IDF？向量相似度？）
- [ ] 兴趣图谱可视化选用哪个前端库（ECharts / D3.js / AntV）
