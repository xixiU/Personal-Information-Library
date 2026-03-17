import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message, Space, Tag, Popconfirm, ColorPicker, Select, Tabs, Switch, InputNumber, Radio } from 'antd'
import { PlusOutlined, SearchOutlined, DeleteOutlined } from '@ant-design/icons'
import { categoriesApi, Category, CreateCategoryRequest } from '../api/categories'
import { rulesApi, channelsApi, NotificationRule, CreateRuleRequest, NotificationChannel } from '../api/notifications'

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

const DEFAULT_MESSAGE_TEMPLATE = `📋 *{category_name}* 新内容通知

*{title}*
评分: ⭐{quality_score}
摘要: {summary}

🔗 查看详情: {url}`

export default function CategoryList() {
  const [categories, setCategories] = useState<Category[]>([])
  const [filteredCategories, setFilteredCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [searchText, setSearchText] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState<string | undefined>(undefined)
  const [form] = Form.useForm()

  // 通知规则相关状态
  const [rules, setRules] = useState<NotificationRule[]>([])
  const [channels, setChannels] = useState<NotificationChannel[]>([])
  const [rulesLoading, setRulesLoading] = useState(false)
  const [ruleModalOpen, setRuleModalOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<NotificationRule | null>(null)
  const [ruleForm] = Form.useForm()
  const [ruleType, setRuleType] = useState<string>('new_content')
  const [notifyMode, setNotifyMode] = useState<string>('instant')
  const [useCustomTemplate, setUseCustomTemplate] = useState(false)

  const loadCategories = async () => {
    setLoading(true)
    try {
      const res = await categoriesApi.list()
      setCategories(res.data)
      setFilteredCategories(res.data)
    } catch {
      message.error('加载分类失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadCategories() }, [])

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

  const loadRules = async (categoryId: number) => {
    setRulesLoading(true)
    try {
      const [rulesRes, channelsRes] = await Promise.all([
        rulesApi.list({ category_id: categoryId }),
        channelsApi.list(),
      ])
      setRules(rulesRes.data)
      setChannels(channelsRes.data)
    } catch {
      message.error('加载通知规则失败')
    } finally {
      setRulesLoading(false)
    }
  }

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
    } catch {
      message.error(editingCategory ? '更新分类失败' : '创建分类失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await categoriesApi.delete(id)
      message.success('分类已删除')
      loadCategories()
    } catch {
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
    loadRules(category.id)
  }

  const openCreateModal = () => {
    setEditingCategory(null)
    form.resetFields()
    form.setFieldsValue({ color: '#1677ff' })
    setSelectedTemplate(undefined)
    setRules([])
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

  // 通知规则 CRUD
  const handleRuleSubmit = async (values: any) => {
    if (!editingCategory) return
    try {
      const conditions: Record<string, any> = {}
      if (values.rule_type === 'quality_threshold') {
        conditions.min_quality_score = values.min_quality_score ?? 80
      } else if (values.rule_type === 'keyword_match') {
        conditions.keywords = values.keywords?.split(/[,，\s]+/).filter(Boolean) || []
      }
      if (values.notify_mode === 'batch') {
        conditions.batch_window = values.batch_window ?? 1800
        conditions.batch_max_count = values.batch_max_count ?? 10
      }

      const payload: CreateRuleRequest = {
        name: values.name,
        category_id: editingCategory.id,
        channel_id: values.channel_id,
        rule_type: values.rule_type,
        notify_mode: values.notify_mode,
        conditions,
        message_template: useCustomTemplate ? values.message_template : null,
        enabled: values.enabled ?? true,
      }

      if (editingRule) {
        await rulesApi.update(editingCategory.id, editingRule.id, payload)
        message.success('规则已更新')
      } else {
        await rulesApi.create(payload)
        message.success('规则已创建')
      }
      setRuleModalOpen(false)
      ruleForm.resetFields()
      setEditingRule(null)
      loadRules(editingCategory.id)
    } catch {
      message.error(editingRule ? '更新规则失败' : '创建规则失败')
    }
  }

  const handleRuleDelete = async (id: number) => {
    if (!editingCategory) return
    try {
      await rulesApi.delete(editingCategory.id, id)
      message.success('规则已删除')
      loadRules(editingCategory.id)
    } catch {
      message.error('删除规则失败')
    }
  }

  const handleRuleToggle = async (rule: NotificationRule) => {
    if (!editingCategory) return
    try {
      await rulesApi.update(editingCategory.id, rule.id, { enabled: !rule.enabled })
      loadRules(editingCategory.id)
    } catch {
      message.error('更新规则状态失败')
    }
  }

  const openRuleCreateModal = () => {
    setEditingRule(null)
    ruleForm.resetFields()
    ruleForm.setFieldsValue({ rule_type: 'new_content', notify_mode: 'instant', enabled: true })
    setRuleType('new_content')
    setNotifyMode('instant')
    setUseCustomTemplate(false)
    setRuleModalOpen(true)
  }

  const openRuleEditModal = (rule: NotificationRule) => {
    setEditingRule(rule)
    setRuleType(rule.rule_type)
    setNotifyMode(rule.notify_mode)
    setUseCustomTemplate(!!rule.message_template)
    const fields: any = {
      name: rule.name,
      channel_id: rule.channel_id,
      rule_type: rule.rule_type,
      notify_mode: rule.notify_mode,
      enabled: rule.enabled,
      message_template: rule.message_template || DEFAULT_MESSAGE_TEMPLATE,
    }
    if (rule.rule_type === 'quality_threshold') {
      fields.min_quality_score = rule.conditions.min_quality_score ?? 80
    } else if (rule.rule_type === 'keyword_match') {
      fields.keywords = (rule.conditions.keywords || []).join(', ')
    }
    if (rule.notify_mode === 'batch') {
      fields.batch_window = rule.conditions.batch_window ?? 1800
      fields.batch_max_count = rule.conditions.batch_max_count ?? 10
    }
    ruleForm.setFieldsValue(fields)
    setRuleModalOpen(true)
  }

  const ruleTypeLabels: Record<string, string> = {
    new_content: '新内容',
    quality_threshold: '质量阈值',
    keyword_match: '关键词匹配',
  }

  const notifyModeLabels: Record<string, string> = {
    instant: '即时',
    batch: '聚合',
  }

  const ruleColumns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: '渠道',
      key: 'channel',
      render: (_: any, record: NotificationRule) =>
        record.channel?.name || `渠道#${record.channel_id}`,
    },
    {
      title: '类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      width: 100,
      render: (type: string) => <Tag>{ruleTypeLabels[type] || type}</Tag>,
    },
    {
      title: '模式',
      dataIndex: 'notify_mode',
      key: 'notify_mode',
      width: 80,
      render: (mode: string) => notifyModeLabels[mode] || mode,
    },
    {
      title: '状态',
      key: 'enabled',
      width: 80,
      render: (_: any, record: NotificationRule) => (
        <Switch size="small" checked={record.enabled} onChange={() => handleRuleToggle(record)} />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: NotificationRule) => (
        <Space>
          <Button type="link" size="small" onClick={() => openRuleEditModal(record)}>编辑</Button>
          <Popconfirm title="确定删除该规则？" onConfirm={() => handleRuleDelete(record.id)}>
            <Button type="link" size="small" danger><DeleteOutlined /></Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

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

  const categoryFormContent = (
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
        <ColorPicker presets={[{ label: '推荐颜色', colors: DEFAULT_COLORS }]} />
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
  )

  const rulesTabContent = (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'flex-end' }}>
        <Button size="small" type="primary" icon={<PlusOutlined />} onClick={openRuleCreateModal}>
          新增规则
        </Button>
      </div>
      <Table
        columns={ruleColumns}
        dataSource={rules}
        rowKey="id"
        loading={rulesLoading}
        size="small"
        pagination={false}
      />
    </div>
  )

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
        width={700}
        destroyOnClose
      >
        {editingCategory ? (
          <Tabs items={[
            { key: 'info', label: '分类信息', children: categoryFormContent },
            { key: 'rules', label: '通知规则', children: rulesTabContent },
          ]} />
        ) : categoryFormContent}
      </Modal>

      {/* 通知规则新增/编辑 Modal */}
      <Modal
        title={editingRule ? '编辑通知规则' : '新增通知规则'}
        open={ruleModalOpen}
        onCancel={() => { setRuleModalOpen(false); setEditingRule(null); ruleForm.resetFields() }}
        onOk={() => ruleForm.submit()}
        width={560}
        destroyOnClose
      >
        <Form form={ruleForm} layout="vertical" onFinish={handleRuleSubmit}>
          <Form.Item name="name" label="规则名称" rules={[{ required: true, message: '请输入规则名称' }]}>
            <Input placeholder="如：高质量内容即时推送" />
          </Form.Item>
          <Form.Item name="channel_id" label="通知渠道" rules={[{ required: true, message: '请选择通知渠道' }]}>
            <Select
              placeholder="选择通知渠道"
              options={channels.map(c => ({ label: `${c.name} (${c.channel_type})`, value: c.id }))}
            />
          </Form.Item>
          <Form.Item name="rule_type" label="触发条件" rules={[{ required: true }]}>
            <Radio.Group onChange={(e) => setRuleType(e.target.value)}>
              <Radio.Button value="new_content">新内容</Radio.Button>
              <Radio.Button value="quality_threshold">质量阈值</Radio.Button>
              <Radio.Button value="keyword_match">关键词匹配</Radio.Button>
            </Radio.Group>
          </Form.Item>

          {ruleType === 'quality_threshold' && (
            <Form.Item name="min_quality_score" label="最低质量分数" initialValue={80}>
              <InputNumber min={0} max={100} style={{ width: '100%' }} />
            </Form.Item>
          )}

          {ruleType === 'keyword_match' && (
            <Form.Item name="keywords" label="关键词" rules={[{ required: true, message: '请输入关键词' }]}
              extra="多个关键词用逗号分隔"
            >
              <Input placeholder="AI, LLM, GPT" />
            </Form.Item>
          )}

          <Form.Item name="notify_mode" label="通知模式" rules={[{ required: true }]}>
            <Radio.Group onChange={(e) => setNotifyMode(e.target.value)}>
              <Radio.Button value="instant">即时发送</Radio.Button>
              <Radio.Button value="batch">聚合发送</Radio.Button>
            </Radio.Group>
          </Form.Item>

          {notifyMode === 'batch' && (
            <>
              <Form.Item name="batch_window" label="聚合窗口（秒）" initialValue={1800}
                extra="在此时间窗口内收集通知后合并发送"
              >
                <InputNumber min={60} max={86400} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="batch_max_count" label="最大聚合数量" initialValue={10}
                extra="达到此数量立即发送，不等窗口结束"
              >
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}

          <Form.Item label="消息模板">
            <Switch
              checked={useCustomTemplate}
              onChange={setUseCustomTemplate}
              checkedChildren="自定义"
              unCheckedChildren="默认"
              style={{ marginBottom: 8 }}
            />
            {useCustomTemplate && (
              <Form.Item name="message_template" noStyle>
                <Input.TextArea
                  rows={5}
                  placeholder={DEFAULT_MESSAGE_TEMPLATE}
                  style={{ marginTop: 8 }}
                />
              </Form.Item>
            )}
            {!useCustomTemplate && (
              <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>
                使用系统默认模板，支持变量: {'{category_name}'}, {'{title}'}, {'{summary}'}, {'{quality_score}'}, {'{url}'}
              </div>
            )}
          </Form.Item>

          <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
