import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message, Space, Tag, Popconfirm, ColorPicker, Select } from 'antd'
import { PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { categoriesApi, Category, CreateCategoryRequest } from '../api/categories'

const DEFAULT_COLORS = ['#1677ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16']

const PRESET_TEMPLATES = [
  {
    label: '技术文档',
    value: 'tech',
    refine_prompt_system: '你是一个专业的技术文档分析助手，擅长提取技术实现细节、使用场景和代码示例。',
    quality_criteria: '技术深度（30分）：是否深入讲解技术原理和实现细节\n实用性（40分）：是否提供可直接应用的解决方案和最佳实践\n代码质量（30分）：代码示例是否完整、规范、可运行',
  },
  {
    label: '投资资讯',
    value: 'investment',
    refine_prompt_system: '你是一个专业的投资分析助手，擅长提取投资观点、标的分析和风险提示。',
    quality_criteria: '观点独特性（30分）：是否提出独特的投资视角和见解\n分析深度（40分）：是否深入分析标的基本面、估值和风险\n数据支撑（30分）：是否用充分的数据和事实支撑观点',
  },
  {
    label: '阅读笔记',
    value: 'reading',
    refine_prompt_system: '你是一个专业的阅读笔记助手，擅长提取核心观点、启发思考和可行动建议。',
    quality_criteria: '思想深度（40分）：是否触及深层次的思考和洞察\n逻辑性（30分）：观点是否清晰、论证是否严密\n可读性（30分）：表达是否流畅、结构是否清晰',
  },
]

export default function CategoryList() {
  const [categories, setCategories] = useState<Category[]>([])
  const [filteredCategories, setFilteredCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [searchText, setSearchText] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState<string | undefined>(undefined)
  const [form] = Form.useForm()

  const loadCategories = async () => {
    setLoading(true)
    try {
      const res = await categoriesApi.list()
      setCategories(res.data)
      setFilteredCategories(res.data)
    } catch (error) {
      message.error('加载分类失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCategories()
  }, [])

  useEffect(() => {
    if (!searchText) {
      setFilteredCategories(categories)
    } else {
      const filtered = categories.filter(
        (c) =>
          c.name.toLowerCase().includes(searchText.toLowerCase()) ||
          (c.description || '').toLowerCase().includes(searchText.toLowerCase())
      )
      setFilteredCategories(filtered)
    }
  }, [searchText, categories])

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
      setSelectedTemplate(undefined)
      loadCategories()
    } catch (error) {
      message.error(editingCategory ? '更新分类失败' : '创建分类失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await categoriesApi.delete(id)
      message.success('分类已删除')
      loadCategories()
    } catch (error) {
      message.error('删除分类失败')
    }
  }

  const openEditModal = (category: Category) => {
    setEditingCategory(category)
    form.setFieldsValue({
      name: category.name,
      description: category.description,
      color: category.color,
      refine_prompt_system: category.refine_prompt_system,
      quality_criteria: category.quality_criteria,
    })
    setSelectedTemplate(undefined)
    setModalOpen(true)
  }

  const openCreateModal = () => {
    setEditingCategory(null)
    form.resetFields()
    form.setFieldsValue({ color: '#1677ff' })
    setSelectedTemplate(undefined)
    setModalOpen(true)
  }

  const handleTemplateChange = (value: string) => {
    setSelectedTemplate(value)
    const template = PRESET_TEMPLATES.find(t => t.value === value)
    if (template) {
      form.setFieldsValue({
        refine_prompt_system: template.refine_prompt_system,
        quality_criteria: template.quality_criteria,
      })
    }
  }

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
      render: (text: string) => text ? <span title={text}>{text.slice(0, 50)}...</span> : '-',
    },
    {
      title: '质量评分标准',
      dataIndex: 'quality_criteria',
      key: 'quality_criteria',
      ellipsis: true,
      render: (text: string) => text ? <span title={text}>{text.slice(0, 50)}...</span> : '-',
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

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Input
          placeholder="搜索分类名称或描述"
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ width: 300 }}
          allowClear
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
          新增分类
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={filteredCategories}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title={editingCategory ? '编辑分类' : '新增分类'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingCategory(null); form.resetFields(); setSelectedTemplate(undefined) }}
        onOk={() => form.submit()}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          {!editingCategory && (
            <Form.Item label="选择模板">
              <Select
                placeholder="选择预设模板（可选）"
                value={selectedTemplate}
                onChange={handleTemplateChange}
                allowClear
                options={PRESET_TEMPLATES.map(t => ({ label: t.label, value: t.value }))}
              />
            </Form.Item>
          )}
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
            extra="AI 总结时应该关注的重点内容"
          >
            <Input.TextArea rows={3} placeholder="请描述 AI 总结时应该关注的重点..." />
          </Form.Item>
          <Form.Item
            name="quality_criteria"
            label="质量评分标准"
            rules={[{ required: true, message: '请输入质量评分标准' }]}
            extra="用于评估内容质量的标准（0-100分）"
          >
            <Input.TextArea rows={4} placeholder="请描述评分标准..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
