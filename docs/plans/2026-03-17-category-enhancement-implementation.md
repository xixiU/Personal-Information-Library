# 分类管理增强功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标**: 为分类管理增加结构化配置和质量评分功能，提升内容精炼体验

**架构**: 后端修改 Category 和 RefinedResult 模型，精炼引擎集成分类配置；前端重构菜单结构，增强分类表单和结果筛选功能

**技术栈**: FastAPI + SQLAlchemy + SQLite (后端), React + TypeScript + Ant Design (前端)

---

## 第一阶段：数据模型和数据库迁移

### Task 1: 修改 Category 模型

**Files:**
- Modify: `backend/app/models/category.py:1-21`

**Step 1: 修改 Category 模型字段**

将 `system_prompt` 和 `user_prompt_template` 字段重命名为 `refine_prompt_system` 和 `quality_criteria`，并设置为必填。

```python
"""Category model - 分类配置."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base


class Category(Base):
    """Category model."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    color = Column(String(20), nullable=False, default="#1677ff")
    refine_prompt_system = Column(Text, nullable=False)  # 总结重点
    quality_criteria = Column(Text, nullable=False)  # 质量评分标准
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Step 2: Commit**

```bash
git add backend/app/models/category.py
git commit -m "refactor: rename Category fields to refine_prompt_system and quality_criteria"
```

---

### Task 2: 修改 RefinedResult 模型

**Files:**
- Modify: `backend/app/models/result.py:24-36`

**Step 1: 添加 quality_score 字段**

在 RefinedResult 模型中添加 `quality_score` 字段。

```python
class RefinedResult(Base):
    """Refined result model."""

    __tablename__ = "refined_results"

    id = Column(Integer, primary_key=True, index=True)
    crawl_result_id = Column(Integer, ForeignKey("crawl_results.id"), nullable=False, unique=True, index=True)
    summary = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # List of keywords
    category = Column(String(100), nullable=True)
    quality_score = Column(Integer, nullable=True)  # 质量评分 0-100
    meta_data = Column(JSON, nullable=True)  # Additional refined data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

**Step 2: Commit**

```bash
git add backend/app/models/result.py
git commit -m "feat: add quality_score field to RefinedResult model"
```

---

### Task 3: 删除旧数据库并重建

**Files:**
- Execute: `rm backend/personal_info.db`

**Step 1: 删除旧数据库**

```bash
cd /mnt/d/source/Personal-Information-Library
rm -f backend/personal_info.db
```

**Step 2: 启动后端服务重建数据库**

```bash
cd backend
source .venv/bin/activate
python run.py
```

预期：服务启动，自动创建新数据库表结构。

**Step 3: 验证数据库表结构**

```bash
sqlite3 backend/personal_info.db ".schema categories"
sqlite3 backend/personal_info.db ".schema refined_results"
```

预期：categories 表包含 refine_prompt_system 和 quality_criteria 字段，refined_results 表包含 quality_score 字段。

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: rebuild database with new schema"
```

---

## 第二阶段：后端 API 和 Schema 更新

### Task 4: 更新 Category Schema

**Files:**
- Modify: `backend/app/schemas/category.py`

**Step 1: 读取现有 schema 文件**

```bash
cat backend/app/schemas/category.py
```

**Step 2: 更新 CategoryBase schema**

将 `system_prompt` 和 `user_prompt_template` 字段改为 `refine_prompt_system` 和 `quality_criteria`，并设置为必填。

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100, description="分类名称")
    description: Optional[str] = Field(None, max_length=500, description="分类描述")
    color: str = Field(default="#1677ff", max_length=20, description="分类颜色")
    refine_prompt_system: str = Field(..., description="总结重点")
    quality_criteria: str = Field(..., description="质量评分标准")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    name: Optional[str] = Field(None, max_length=100)
    refine_prompt_system: Optional[str] = None
    quality_criteria: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
```

**Step 3: Commit**

```bash
git add backend/app/schemas/category.py
git commit -m "refactor: update Category schema with new field names"
```

---

### Task 5: 更新 RefinedResult Schema

**Files:**
- Modify: `backend/app/schemas/result.py`

**Step 1: 读取现有 schema 文件**

```bash
cat backend/app/schemas/result.py
```

**Step 2: 在 RefinedResultResponse 中添加 quality_score 字段**

```python
class RefinedResultResponse(BaseModel):
    id: int
    crawl_result_id: int
    summary: Optional[str]
    keywords: Optional[List[str]]
    category: Optional[str]
    quality_score: Optional[int] = Field(None, ge=0, le=100, description="质量评分")
    meta_data: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True
```

**Step 3: Commit**

```bash
git add backend/app/schemas/result.py
git commit -m "feat: add quality_score to RefinedResult schema"
```

---

### Task 6: 更新 Results API 支持质量分数筛选和排序

**Files:**
- Modify: `backend/app/api/results.py:43-57`

**Step 1: 修改 list_refined_results 函数**

添加 `min_score`, `max_score`, `order_by`, `order` 查询参数。

```python
@router.get("/refined", response_model=List[RefinedResultResponse])
async def list_refined_results(
    skip: int = 0,
    limit: int = 100,
    min_score: int = None,
    max_score: int = None,
    order_by: str = None,
    order: str = "desc",
    db: Session = Depends(get_db),
):
    """获取精炼结果列表."""
    query = db.query(RefinedResult)

    # 质量分数筛选
    if min_score is not None:
        query = query.filter(RefinedResult.quality_score >= min_score)
    if max_score is not None:
        query = query.filter(RefinedResult.quality_score <= max_score)

    # 排序
    if order_by == "quality_score":
        if order == "asc":
            query = query.order_by(RefinedResult.quality_score.asc())
        else:
            query = query.order_by(RefinedResult.quality_score.desc())
    else:
        query = query.order_by(RefinedResult.created_at.desc())

    results = query.offset(skip).limit(limit).all()
    return results
```

**Step 2: Commit**

```bash
git add backend/app/api/results.py
git commit -m "feat: add quality score filtering and sorting to refined results API"
```

---

## 第三阶段：精炼引擎集成

### Task 7: 修改精炼引擎支持分类配置

**Files:**
- Modify: `backend/app/core/refiner.py:154-184`

**Step 1: 修改 _get_category_prompt 方法**

更新字段名称从 `system_prompt` 和 `user_prompt_template` 改为 `refine_prompt_system` 和 `quality_criteria`。

```python
def _get_category_prompt(
    self, crawl_result: CrawlResult, db: Optional[Session]
) -> Optional[Dict[str, str]]:
    """从 crawl_result 关联的 source 的分类中获取自定义 prompt."""
    if not db:
        return None

    try:
        # 通过 crawl_result -> task -> source -> category 链路查询
        task = db.query(Task).filter(Task.id == crawl_result.task_id).first()
        if not task or not task.source_id:
            return None

        source = db.query(Source).filter(Source.id == task.source_id).first()
        if not source or not source.category_id:
            return None

        category = db.query(Category).filter(Category.id == source.category_id).first()
        if not category:
            return None

        if category.refine_prompt_system and category.quality_criteria:
            logger.info(f"Using category '{category.name}' prompt for crawl result {crawl_result.id}")
            # 构造包含质量评分的提示词
            user_prompt = f"""请对以下内容进行分析：

标题：{{title}}
内容：{{content}}

总结重点：{category.refine_prompt_system}
质量评分标准：{category.quality_criteria}

请以 JSON 格式输出：
{{
  "summary": "内容摘要",
  "keywords": ["关键词1", "关键词2"],
  "category": "内容分类",
  "quality_score": 85
}}

其中 quality_score 是 0-100 的整数，根据以下标准评分：{category.quality_criteria}
"""
            return {
                "system": "你是一个专业的内容分析助手。请严格按照 JSON 格式返回结果。",
                "user": user_prompt,
            }
    except Exception as e:
        logger.warning(f"Failed to get category prompt: {e}")

    return None
```

**Step 2: Commit**

```bash
git add backend/app/core/refiner.py
git commit -m "feat: integrate category config into refiner engine"
```

---

### Task 8: 修改精炼引擎解析质量评分

**Files:**
- Modify: `backend/app/core/refiner.py:61-152`

**Step 1: 修改 refine 方法提取 quality_score**

在创建 RefinedResult 时，从 refined_data 中提取 quality_score。

```python
async def refine(
    self,
    crawl_result: CrawlResult,
    template_name: str = "summary_keywords",
    custom_prompt: Optional[str] = None,
    db: Optional[Session] = None,
) -> Optional[RefinedResult]:
    """
    执行精炼任务.

    Args:
        crawl_result: 爬取结果
        template_name: 模板名称
        custom_prompt: 自定义提示词（覆盖模板）
        db: 数据库会话（用于查询分类 prompt）

    Returns:
        精炼结果对象，失败返回None
    """
    try:
        # 检查内容是否为空
        if not crawl_result.content or len(crawl_result.content.strip()) < 50:
            logger.warning(f"Content too short for crawl result {crawl_result.id}")
            return None

        # 尝试从分类获取自定义 prompt
        category_prompt = self._get_category_prompt(crawl_result, db)

        # 构建提示词（优先级：custom_prompt > 分类 prompt > 模板）
        if custom_prompt:
            messages = [
                {"role": "system", "content": "你是一个专业的内容分析助手。"},
                {"role": "user", "content": custom_prompt.format(
                    title=crawl_result.title or "无标题",
                    content=self._truncate_content(crawl_result.content),
                )},
            ]
        elif category_prompt:
            messages = [
                {"role": "system", "content": category_prompt["system"]},
                {"role": "user", "content": category_prompt["user"].format(
                    title=crawl_result.title or "无标题",
                    content=self._truncate_content(crawl_result.content),
                )},
            ]
            template_name = "category_custom"
        else:
            # 使用默认模板，但要求输出 quality_score
            template = self.TEMPLATES.get(template_name)
            if not template:
                logger.error(f"Template {template_name} not found")
                return None

            # 修改默认模板的 user prompt，要求输出 quality_score
            user_prompt = template["user"] + """

请额外输出 quality_score 字段（0-100 的整数），根据以下标准评分：
- 内容质量：信息是否准确、完整
- 信息密度：单位文字包含的有效信息量
- 可读性：表达是否清晰、易懂
"""
            messages = [
                {"role": "system", "content": template["system"]},
                {"role": "user", "content": user_prompt.format(
                    title=crawl_result.title or "无标题",
                    content=self._truncate_content(crawl_result.content),
                )},
            ]

        logger.info(f"Refining crawl result {crawl_result.id} with template {template_name}")

        # 调用OpenAI API（带重试）
        response_text = await self._call_openai_with_retry(messages)

        if not response_text:
            logger.error(f"Failed to refine crawl result {crawl_result.id}")
            return None

        # 解析响应
        refined_data = self._parse_response(response_text, template_name)

        # 创建精炼结果
        refined_result = RefinedResult(
            crawl_result_id=crawl_result.id,
            summary=refined_data.get("summary"),
            keywords=refined_data.get("keywords"),
            category=refined_data.get("category"),
            quality_score=refined_data.get("quality_score"),  # 提取质量评分
            meta_data={
                "template": template_name,
                "model": self.model,
                "raw_response": response_text[:500],  # 保存前500字符
            },
            created_at=datetime.utcnow(),
        )

        logger.info(f"Refined result created for crawl result {crawl_result.id}")
        return refined_result

    except Exception as e:
        logger.error(f"Failed to refine crawl result {crawl_result.id}: {e}", exc_info=True)
        return None
```

**Step 2: Commit**

```bash
git add backend/app/core/refiner.py
git commit -m "feat: extract quality_score from AI response"
```

---

## 第四阶段：前端菜单结构调整

### Task 9: 重构菜单结构

**Files:**
- Modify: `frontend/src/App.tsx:17-50`

**Step 1: 修改 menuItems 配置**

将"信源管理"改为父菜单，包含"信源列表"和"分类管理"两个子菜单。

```typescript
const menuItems = [
  {
    key: 'sources-parent',
    icon: <DatabaseOutlined />,
    label: '信源管理',
    children: [
      {
        key: 'sources',
        icon: <DatabaseOutlined />,
        label: <Link to="/">信源列表</Link>,
      },
      {
        key: 'categories',
        icon: <TagsOutlined />,
        label: <Link to="/categories">分类管理</Link>,
      },
    ],
  },
  {
    key: 'tasks',
    icon: <UnorderedListOutlined />,
    label: '任务管理',
    children: [
      {
        key: 'crawl-tasks',
        icon: <ThunderboltOutlined />,
        label: <Link to="/tasks/crawl">爬取任务</Link>,
      },
      {
        key: 'refine-tasks',
        icon: <CheckCircleOutlined />,
        label: <Link to="/tasks/refine">精炼任务</Link>,
      },
    ],
  },
  {
    key: 'results',
    icon: <FileTextOutlined />,
    label: <Link to="/results">采集结果</Link>,
  },
]
```

**Step 2: 修改 getOpenKeys 函数**

```typescript
const getOpenKeys = () => {
  const path = location.pathname
  if (path === '/' || path === '/categories') return ['sources-parent']
  if (path.startsWith('/tasks')) return ['tasks']
  return []
}
```

**Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "refactor: restructure menu with sources as parent menu"
```

---

## 第五阶段：前端分类管理页面改造

### Task 10: 更新 Category API 类型定义

**Files:**
- Modify: `frontend/src/api/categories.ts`

**Step 1: 读取现有 API 文件**

```bash
cat frontend/src/api/categories.ts
```

**Step 2: 更新 Category 和 CreateCategoryRequest 类型**

将 `system_prompt` 和 `user_prompt_template` 改为 `refine_prompt_system` 和 `quality_criteria`。

```typescript
export interface Category {
  id: number
  name: string
  description: string | null
  color: string
  refine_prompt_system: string
  quality_criteria: string
  created_at: string
  updated_at: string | null
}

export interface CreateCategoryRequest {
  name: string
  description: string | null
  color: string
  refine_prompt_system: string
  quality_criteria: string
}
```

**Step 3: Commit**

```bash
git add frontend/src/api/categories.ts
git commit -m "refactor: update Category API types with new field names"
```

---

### Task 11: 更新分类管理页面表单

**Files:**
- Modify: `frontend/src/pages/CategoryList.tsx:1-206`

**Step 1: 添加预设模板常量**

在文件顶部添加预设模板配置。

```typescript
const PRESET_TEMPLATES = [
  {
    label: '技术文档',
    value: 'tech',
    refine_prompt_system: '技术实现细节、使用场景、代码示例',
    quality_criteria: '技术深度、实用性、代码质量',
  },
  {
    label: '投资资讯',
    value: 'investment',
    refine_prompt_system: '投资观点、标的分析、风险提示',
    quality_criteria: '观点独特性、分析深度、数据支撑',
  },
  {
    label: '阅读笔记',
    value: 'reading',
    refine_prompt_system: '核心观点、启发思考、可行动建议',
    quality_criteria: '思想深度、逻辑性、可读性',
  },
  {
    label: '自定义',
    value: 'custom',
    refine_prompt_system: '',
    quality_criteria: '',
  },
]
```

**Step 2: 修改表单字段**

将 `system_prompt` 和 `user_prompt_template` 改为 `refine_prompt_system` 和 `quality_criteria`。

```typescript
const handleSubmit = async (values: any) => {
  try {
    const color = typeof values.color === 'string' ? values.color : values.color?.toHexString?.() || '#1677ff'
    const payload: CreateCategoryRequest = {
      name: values.name,
      description: values.description || null,
      color,
      refine_prompt_system: values.refine_prompt_system,
      quality_criteria: values.quality_criteria,
    }

    if (editingCategory) {
      await categoriesApi.update(editingCategory.id, payload)
      message.success('分类已更新')
    } else {
      await categoriesApi.create(payload)
      message.success('分类已创建')
    }
    setModalOpen(false)
    form.resetFields()
    setEditingCategory(null)
    loadCategories()
  } catch (error) {
    message.error(editingCategory ? '更新分类失败' : '创建分类失败')
  }
}
```

**Step 3: 修改 openEditModal 函数**

```typescript
const openEditModal = (category: Category) => {
  setEditingCategory(category)
  form.setFieldsValue({
    name: category.name,
    description: category.description,
    color: category.color,
    refine_prompt_system: category.refine_prompt_system,
    quality_criteria: category.quality_criteria,
  })
  setModalOpen(true)
}
```

**Step 4: 修改表格列配置**

```typescript
const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  {
    title: '名称',
    dataIndex: 'name',
    key: 'name',
    render: (name: string, record: Category) => (
      <Tag color={record.color}>{name}</Tag>
    ),
  },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  {
    title: '总结重点',
    dataIndex: 'refine_prompt_system',
    key: 'refine_prompt_system',
    ellipsis: true,
    render: (text: string) => text ? <span title={text}>{text.slice(0, 30)}...</span> : '-',
  },
  {
    title: '质量评分标准',
    dataIndex: 'quality_criteria',
    key: 'quality_criteria',
    ellipsis: true,
    render: (text: string) => text ? <span title={text}>{text.slice(0, 30)}...</span> : '-',
  },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 180,
    render: (t: string) => new Date(t).toLocaleString(),
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (_: any, record: Category) => (
      <Space>
        <Button type="link" size="small" onClick={() => openEditModal(record)}>编辑</Button>
        <Popconfirm title="确定删除该分类？" onConfirm={() => handleDelete(record.id)}>
          <Button type="link" size="small" danger>删除</Button>
        </Popconfirm>
      </Space>
    ),
  },
]
```

**Step 5: 修改 Modal 表单**

```typescript
<Modal
  title={editingCategory ? '编辑分类' : '新增分类'}
  open={modalOpen}
  onCancel={() => { setModalOpen(false); setEditingCategory(null); form.resetFields() }}
  onOk={() => form.submit()}
  width={640}
  destroyOnClose
>
  <Form form={form} layout="vertical" onFinish={handleSubmit}>
    <Form.Item name="template" label="快速应用模板">
      <Select
        placeholder="选择预设模板"
        onChange={(value) => {
          const template = PRESET_TEMPLATES.find(t => t.value === value)
          if (template && value !== 'custom') {
            form.setFieldsValue({
              refine_prompt_system: template.refine_prompt_system,
              quality_criteria: template.quality_criteria,
            })
          }
        }}
      >
        {PRESET_TEMPLATES.map(t => (
          <Select.Option key={t.value} value={t.value}>{t.label}</Select.Option>
        ))}
      </Select>
    </Form.Item>
    <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入分类名称' }]}>
      <Input placeholder="如：技术文档、投资、悦读" />
    </Form.Item>
    <Form.Item name="description" label="描述">
      <Input placeholder="分类描述（可选）" />
    </Form.Item>
    <Form.Item name="color" label="颜色" initialValue="#1677ff">
      <ColorPicker
        presets={[{ label: '推荐颜色', colors: DEFAULT_COLORS }]}
      />
    </Form.Item>
    <Form.Item
      name="refine_prompt_system"
      label="总结重点"
      rules={[{ required: true, message: '请输入总结重点' }]}
      extra="请描述 AI 总结时应该关注的重点"
    >
      <Input.TextArea rows={3} placeholder="如：技术实现细节、投资观点、核心思想等" />
    </Form.Item>
    <Form.Item
      name="quality_criteria"
      label="质量评分标准"
      rules={[{ required: true, message: '请输入质量评分标准' }]}
      extra="请描述评分标准，AI 将根据此标准给出 0-100 的分数"
    >
      <Input.TextArea rows={3} placeholder="如：信息密度、技术深度、实用性等" />
    </Form.Item>
  </Form>
</Modal>
```

**Step 6: 添加 Select 导入**

在文件顶部的 import 语句中添加 Select。

```typescript
import { Table, Button, Modal, Form, Input, message, Space, Tag, Popconfirm, ColorPicker, Select } from 'antd'
```

**Step 7: Commit**

```bash
git add frontend/src/pages/CategoryList.tsx
git commit -m "feat: add template selector and update form fields in CategoryList"
```

---

## 第六阶段：前端结果页面改造

### Task 12: 更新 RefinedResult API 类型定义

**Files:**
- Modify: `frontend/src/api/results.ts` (假设存在)

**Step 1: 读取或创建 results API 文件**

```bash
cat frontend/src/api/results.ts || echo "File not found"
```

**Step 2: 更新 RefinedResult 类型**

添加 `quality_score` 字段。

```typescript
export interface RefinedResult {
  id: number
  crawl_result_id: number
  summary: string | null
  keywords: string[] | null
  category: string | null
  quality_score: number | null
  meta_data: any
  created_at: string
}
```

**Step 3: 更新 listRefinedResults 函数**

添加查询参数支持。

```typescript
export const resultsApi = {
  listRefinedResults: (params?: {
    skip?: number
    limit?: number
    min_score?: number
    max_score?: number
    order_by?: string
    order?: 'asc' | 'desc'
  }) => {
    return axios.get<RefinedResult[]>('/api/results/refined', { params })
  },
  // ... 其他方法
}
```

**Step 4: Commit**

```bash
git add frontend/src/api/results.ts
git commit -m "feat: add quality_score to RefinedResult type and API"
```

---

### Task 13: 更新 ResultDetail 页面

**Files:**
- Modify: `frontend/src/pages/ResultDetail.tsx`

**Step 1: 读取现有文件**

```bash
cat frontend/src/pages/ResultDetail.tsx
```

**Step 2: 添加质量分数筛选和排序状态**

在组件顶部添加状态管理。

```typescript
const [scoreRange, setScoreRange] = useState<[number, number]>([0, 100])
const [sortOrder, setSortOrder] = useState<'asc' | 'desc' | null>(null)
```

**Step 3: 修改数据加载函数**

```typescript
const loadRefinedResults = async () => {
  setLoading(true)
  try {
    const params: any = {
      skip: 0,
      limit: 100,
    }
    
    if (scoreRange[0] > 0) params.min_score = scoreRange[0]
    if (scoreRange[1] < 100) params.max_score = scoreRange[1]
    if (sortOrder) {
      params.order_by = 'quality_score'
      params.order = sortOrder
    }
    
    const res = await resultsApi.listRefinedResults(params)
    setRefinedResults(res.data)
  } catch (error) {
    message.error('加载精炼结果失败')
  } finally {
    setLoading(false)
  }
}
```

**Step 4: 添加筛选控件**

在表格上方添加筛选区域。

```typescript
<div style={{ marginBottom: 16 }}>
  <Space>
    <span>质量分数:</span>
    <Slider
      range
      min={0}
      max={100}
      value={scoreRange}
      onChange={setScoreRange}
      style={{ width: 200 }}
    />
    <span>{scoreRange[0]} - {scoreRange[1]}</span>
    <Button onClick={loadRefinedResults}>筛选</Button>
  </Space>
</div>
```

**Step 5: 添加质量评分列**

在表格列配置中添加质量评分列。

```typescript
{
  title: '质量评分',
  dataIndex: 'quality_score',
  key: 'quality_score',
  width: 100,
  render: (score: number | null) => score !== null ? score : '-',
  sorter: true,
  sortOrder: sortOrder === 'asc' ? 'ascend' : sortOrder === 'desc' ? 'descend' : null,
}
```

**Step 6: 处理表格排序事件**

```typescript
const handleTableChange = (pagination: any, filters: any, sorter: any) => {
  if (sorter.field === 'quality_score') {
    if (sorter.order === 'ascend') {
      setSortOrder('asc')
    } else if (sorter.order === 'descend') {
      setSortOrder('desc')
    } else {
      setSortOrder(null)
    }
  }
}
```

**Step 7: 添加 Slider 导入**

```typescript
import { Table, Button, message, Space, Slider } from 'antd'
```

**Step 8: Commit**

```bash
git add frontend/src/pages/ResultDetail.tsx
git commit -m "feat: add quality score filtering and sorting to ResultDetail"
```

---

## 第七阶段：测试和验证

### Task 14: 端到端测试

**Step 1: 启动后端服务**

```bash
cd /mnt/d/source/Personal-Information-Library/backend
source .venv/bin/activate
python run.py
```

预期：服务在 http://localhost:8000 启动成功。

**Step 2: 启动前端服务**

```bash
cd /mnt/d/source/Personal-Information-Library/frontend
npm run dev
```

预期：前端在 http://localhost:5173 启动成功。

**Step 3: 测试分类管理**

1. 访问 http://localhost:5173/categories
2. 点击"新增分类"
3. 选择"技术文档"模板
4. 填写名称"技术"
5. 点击确定
6. 验证：分类创建成功，表格显示总结重点和质量评分标准

**Step 4: 测试信源关联分类**

1. 访问 http://localhost:5173/
2. 编辑一个信源
3. 选择刚创建的"技术"分类
4. 保存

**Step 5: 测试爬取和精炼**

1. 对该信源执行爬取任务
2. 等待爬取完成
3. 执行精炼任务
4. 查看精炼结果，验证 quality_score 字段有值

**Step 6: 测试结果筛选**

1. 访问 http://localhost:5173/results
2. 调整质量分数滑块
3. 点击筛选
4. 验证：只显示符合分数范围的结果

**Step 7: 测试结果排序**

1. 点击"质量评分"列头
2. 验证：结果按分数降序排列
3. 再次点击
4. 验证：结果按分数升序排列

**Step 8: 最终提交**

```bash
git add -A
git commit -m "test: verify category enhancement features end-to-end"
```

---

## 验收标准

- [x] Category 模型包含 refine_prompt_system 和 quality_criteria 字段
- [x] RefinedResult 模型包含 quality_score 字段
- [x] 分类管理页面提供 3 个预设模板
- [x] 菜单结构调整为信源管理 → 信源列表 + 分类管理
- [x] 精炼引擎使用分类配置生成提示词
- [x] 精炼结果包含 0-100 的质量分数
- [x] 采集结果页可以按分数范围筛选
- [x] 采集结果页可以按分数排序
- [x] 有分类的信源使用分类配置，无分类使用默认模板

---

## 注意事项

1. **数据库迁移**: 本次改动需要删除旧数据库重建，生产环境需要编写迁移脚本
2. **向后兼容**: 旧的精炼结果 quality_score 为 NULL，前端需要处理
3. **AI 提示词测试**: 需要验证不同分类配置下的精炼质量和评分准确性
4. **错误处理**: 如果 AI 返回的 JSON 中缺少 quality_score，应设置为 NULL 而不是报错

---

## 后续优化

1. 提示词测试功能（输入示例内容，预览 AI 输出）
2. 分类统计看板（文章数、平均质量分）
3. 质量分数趋势分析
4. 基于质量分数的自动过滤规则
