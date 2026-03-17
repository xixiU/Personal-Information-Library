# 分类管理增强功能设计文档

**日期**: 2026-03-17
**状态**: 已批准
**设计者**: Team Lead + 产品经理

## 一、背景与目标

### 当前问题
- 分类管理功能过于简单，只是一个"标签"
- 缺少实质性的管理功能
- AI 精炼提示词配置体验差，需要用户理解模板语法

### 目标
1. 提供结构化的分类配置方式，降低使用门槛
2. 为所有精炼结果增加质量评分（0-100）
3. 支持按质量分数筛选和排序
4. 优化菜单结构，将分类管理整合到信源管理下

## 二、核心功能

### 2.1 结构化配置
- 用户通过表单配置"总结重点"和"质量评分标准"
- 系统自动生成 AI 提示词，无需用户编写
- 提供预设模板快速应用（技术文档、投资资讯、阅读笔记）

### 2.2 质量评分
- 所有精炼结果自动进行质量评分（0-100）
- 有分类：根据分类的"质量评分标准"打分
- 无分类：使用通用标准（内容质量、信息密度、可读性）
- 评分结果存储在 RefinedResult.quality_score 字段

### 2.3 菜单整合
- 分类管理作为信源管理的子菜单
- 菜单结构：
  ```
  信源管理
  ├── 信源列表
  └── 分类管理
  ```

## 三、数据模型设计

### 3.1 Category 表改动

新增字段：
- `refine_prompt_system` (Text, 必填) - 总结重点
- `quality_criteria` (Text, 必填) - 质量评分标准（文字描述）

完整字段列表：
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(20) DEFAULT '#1677ff',
    refine_prompt_system TEXT NOT NULL,
    quality_criteria TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME
);
```

### 3.2 RefinedResult 表改动

新增字段：
- `quality_score` (Integer, 0-100, nullable) - 质量评分

### 3.3 预设分类模板

系统内置 3 个模板：

**技术文档**：
- 总结重点：技术实现细节、使用场景、代码示例
- 质量评分标准：技术深度、实用性、代码质量

**投资资讯**：
- 总结重点：投资观点、标的分析、风险提示
- 质量评分标准：观点独特性、分析深度、数据支撑

**阅读笔记**：
- 总结重点：核心观点、启发思考、可行动建议
- 质量评分标准：思想深度、逻辑性、可读性

## 四、前端设计

### 4.1 菜单结构调整

左侧菜单"信源管理"改为可展开的父菜单：
- 信源列表 (/)
- 分类管理 (/categories)

### 4.2 分类管理页面

**列表展示**：
- ID、名称（彩色标签）、描述、总结重点、质量评分标准、创建时间、操作

**新增/编辑 Modal**：
1. 快速应用模板（下拉框）：技术文档、投资资讯、阅读笔记、自定义
2. 名称（必填）
3. 描述（可选）
4. 颜色选择器
5. 总结重点（TextArea，必填）
   - 占位符："请描述 AI 总结时应该关注的重点，如：技术实现细节、投资观点、核心思想等"
6. 质量评分标准（TextArea，必填）
   - 占位符："请描述评分标准，如：信息密度、技术深度、实用性等"

### 4.3 采集结果页面改造

**新增功能**：
1. 精炼结果列表新增"质量评分"列（显示 0-100 的数字）
2. 筛选区新增"质量分数"滑块（范围 0-100）
3. 支持按质量分数排序（升序/降序）

## 五、后端实现

### 5.1 精炼引擎改造

**逻辑流程**：
1. 获取 crawl_result 关联的 source
2. 检查 source 是否有 category_id
3. 如果有分类：
   - 读取 category.refine_prompt_system 和 category.quality_criteria
   - 构造提示词：
     ```
     请对以下内容进行分析：

     标题：{title}
     内容：{content}

     总结重点：{refine_prompt_system}
     质量评分标准：{quality_criteria}

     请以 JSON 格式输出：
     {
       "summary": "内容摘要",
       "keywords": ["关键词1", "关键词2"],
       "category": "内容分类",
       "quality_score": 85
     }

     其中 quality_score 是 0-100 的整数，根据以下标准评分：{quality_criteria}
     ```
4. 如果无分类：
   - 使用默认 summary_keywords 模板
   - 额外要求输出 quality_score（根据通用标准：内容质量、信息密度、可读性）
5. 解析 AI 返回的 JSON，提取 quality_score
6. 保存到 RefinedResult 表

### 5.2 API 改动

**Category API**（已有，需确保字段对齐）：
- POST /api/categories - 创建分类
- GET /api/categories - 列表查询
- GET /api/categories/{id} - 详情
- PUT /api/categories/{id} - 更新
- DELETE /api/categories/{id} - 删除

**RefinedResult API 改动**：

`GET /api/results/refined` 新增查询参数：
- `min_score` (int, 0-100) - 最低分数
- `max_score` (int, 0-100) - 最高分数
- `order_by` (string) - 排序字段，支持 `quality_score`
- `order` (string) - 排序方向，`asc` 或 `desc`

## 六、实施阶段

### 第一阶段：基础功能
1. Category 模型字段调整（refine_prompt_system, quality_criteria）
2. RefinedResult 模型新增 quality_score 字段
3. 数据库迁移（删除旧库重建）
4. 分类管理前端页面改造（表单 + 模板）
5. 菜单结构调整（信源管理变为父菜单）

### 第二阶段：精炼集成
1. 精炼引擎集成分类配置
2. 质量评分逻辑实现
3. API 支持分数筛选和排序
4. 采集结果页增加分数滑块和排序

## 七、技术风险与注意事项

### 7.1 数据库迁移
- Category 表字段变更（重命名、新增）
- RefinedResult 表新增字段
- 建议：删除旧数据库重建（开发阶段）

### 7.2 AI 提示词效果
- 需要测试不同分类配置下的精炼质量
- 质量评分的准确性需要验证
- 建议：提供示例配置和最佳实践

### 7.3 向后兼容
- 无分类的信源仍使用默认模板
- 旧的精炼结果 quality_score 为 NULL

## 八、验收标准

1. ✅ 分类管理页面可以配置总结重点和质量评分标准
2. ✅ 提供 3 个预设模板可快速应用
3. ✅ 菜单结构调整为信源管理 → 信源列表 + 分类管理
4. ✅ 精炼结果包含 0-100 的质量分数
5. ✅ 采集结果页可以按分数范围筛选
6. ✅ 采集结果页可以按分数排序
7. ✅ 有分类的信源使用分类配置精炼，无分类使用默认模板

## 九、后续优化方向

1. 提示词测试功能（输入示例内容，预览 AI 输出）
2. 分类统计看板（文章数、平均质量分）
3. 质量分数趋势分析
4. 基于质量分数的自动过滤规则
