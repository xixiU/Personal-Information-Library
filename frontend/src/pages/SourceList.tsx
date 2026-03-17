import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Space, Tag, Tooltip, Checkbox } from 'antd'
import { SearchOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { sourcesApi, Source, CreateSourceRequest } from '../api/sources'
import { pluginsApi, Plugin } from '../api/plugins'
import { categoriesApi, Category } from '../api/categories'

const CRON_PRESETS = [
  { label: '每小时', value: '0 * * * *' },
  { label: '每天早8点', value: '0 8 * * *' },
  { label: '每天中午12点', value: '0 12 * * *' },
  { label: '每天晚8点', value: '0 20 * * *' },
  { label: '每周一早8点', value: '0 8 * * 1' },
]

export default function SourceList() {
  const [sources, setSources] = useState<Source[]>([])
  const [filteredSources, setFilteredSources] = useState<Source[]>([])
  const [plugins, setPlugins] = useState<Plugin[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingSource, setEditingSource] = useState<Source | null>(null)
  const [searchText, setSearchText] = useState('')
  const [form] = Form.useForm()

  const loadSources = async () => {
    setLoading(true)
    try {
      const res = await sourcesApi.list()
      setSources(res.data)
      setFilteredSources(res.data)
    } catch (error) {
      message.error('加载信源失败')
    } finally {
      setLoading(false)
    }
  }

  const loadPlugins = async () => {
    try {
      const res = await pluginsApi.list(true)
      setPlugins(res.data)
    } catch (error) {
      // 插件加载失败不影响主流程
    }
  }

  const loadCategories = async () => {
    try {
      const res = await categoriesApi.list()
      setCategories(res.data)
    } catch (error) {
      // 分类加载失败不影响主流程
    }
  }

  useEffect(() => {
    loadSources()
    loadPlugins()
    loadCategories()
  }, [])

  useEffect(() => {
    if (!searchText) {
      setFilteredSources(sources)
    } else {
      const filtered = sources.filter(
        (s) =>
          s.name.toLowerCase().includes(searchText.toLowerCase()) ||
          s.url.toLowerCase().includes(searchText.toLowerCase())
      )
      setFilteredSources(filtered)
    }
  }, [searchText, sources])

  const handleSubmit = async (values: any) => {
    try {
      let configData = null
      if (values.config && values.config.trim()) {
        configData = JSON.parse(values.config)
      }

      const payload: CreateSourceRequest = {
        name: values.name,
        url: values.url,
        crawl_mode: values.crawl_mode || 'single_page',
        plugin_id: values.plugin_id || null,
        cron_expr: values.cron_expr || null,
        config: configData,
        category_id: values.category_id || null
      }

      let sourceId: number
      if (editingSource) {
        await sourcesApi.update(editingSource.id, payload)
        message.success('更新成功')
        sourceId = editingSource.id
      } else {
        const res = await sourcesApi.create(payload)
        message.success('创建成功')
        sourceId = res.data.id
      }

      // 如果勾选了立即运行，触发采集
      if (values.run_immediately) {
        await sourcesApi.trigger(sourceId)
        message.info('已触发采集任务')
      }

      setModalOpen(false)
      setEditingSource(null)
      form.resetFields()
      loadSources()
    } catch (error: any) {
      if (error instanceof SyntaxError) {
        message.error('配置JSON格式错误')
      } else {
        message.error((editingSource ? '更新' : '创建') + '失败: ' + (error.response?.data?.detail || error.message))
      }
    }
  }

  const handleEdit = (source: Source) => {
    setEditingSource(source)
    form.setFieldsValue({
      name: source.name,
      url: source.url,
      crawl_mode: source.crawl_mode,
      plugin_id: source.plugin_id || undefined,
      cron_expr: source.cron_expr || '',
      config: source.config ? JSON.stringify(source.config, null, 2) : '',
      category_id: source.category_id || undefined,
      run_immediately: false
    })
    setModalOpen(true)
  }

  const handleModalClose = () => {
    setModalOpen(false)
    setEditingSource(null)
    form.resetFields()
  }

  const handleTrigger = async (sourceId: number) => {
    try {
      await sourcesApi.trigger(sourceId)
      message.success('任务已触发')
    } catch (error) {
      message.error('触发失败')
    }
  }

  const handleDelete = async (sourceId: number) => {
    try {
      await sourcesApi.delete(sourceId)
      message.success('删除成功')
      loadSources()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
    { title: '爬取模式', dataIndex: 'crawl_mode', key: 'crawl_mode', width: 120 },
    {
      title: '分类',
      dataIndex: 'category_id',
      key: 'category_id',
      width: 120,
      render: (category_id: number | null) => {
        if (!category_id) return <Tag color="default">未分类</Tag>
        const cat = categories.find(c => c.id === category_id)
        return cat ? <Tag color={cat.color}>{cat.name}</Tag> : <Tag color="default">未分类</Tag>
      }
    },
    {
      title: '定时采集',
      dataIndex: 'cron_expr',
      key: 'cron_expr',
      width: 160,
      render: (cron_expr: string | null) =>
        cron_expr ? (
          <Tooltip title={cron_expr}>
            <Tag icon={<ClockCircleOutlined />} color="blue">
              {CRON_PRESETS.find(p => p.value === cron_expr)?.label || cron_expr}
            </Tag>
          </Tooltip>
        ) : (
          <Tag color="default">未设置</Tag>
        )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => (status === 'active' ? '启用' : '禁用')
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Source) => (
        <Space>
          <Button size="small" onClick={() => handleTrigger(record.id)}>
            触发采集
          </Button>
          <Button size="small" onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Button size="small" danger onClick={() => handleDelete(record.id)}>
            删除
          </Button>
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索名称或URL"
          style={{ width: 300 }}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          prefix={<SearchOutlined />}
          allowClear
        />
        <Button type="primary" onClick={() => setModalOpen(true)}>
          创建信源
        </Button>
      </Space>
      <Table
        columns={columns}
        dataSource={filteredSources}
        rowKey="id"
        loading={loading}
      />
      <Modal
        title={editingSource ? "编辑信源" : "创建信源"}
        open={modalOpen}
        onCancel={handleModalClose}
        onOk={() => form.submit()}
      >
        <Form form={form} onFinish={handleSubmit} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="url" label="URL" rules={[{ required: true }]}>
            <Input placeholder="https://example.com" />
          </Form.Item>
          <Form.Item name="crawl_mode" label="爬取模式" initialValue="single_page">
            <Select>
              <Select.Option value="single_page">单页爬取</Select.Option>
              <Select.Option value="full_site">整站爬取</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="plugin_id" label="爬取插件">
            <Select placeholder="选择插件（可选，默认使用通用插件）" allowClear>
              {plugins.map(p => (
                <Select.Option key={p.id} value={p.id}>
                  {p.display_name || p.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="category_id" label="分类">
            <Select placeholder="选择分类（可选）" allowClear>
              {categories.map(c => (
                <Select.Option key={c.id} value={c.id}>
                  <Tag color={c.color} style={{ marginRight: 4 }}>{c.name}</Tag>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="cron_expr" label="定时采集" extra="Cron 表达式，留空则不启用定时。格式：分 时 日 月 周">
            <Input placeholder="0 8 * * * (每天早8点)" allowClear />
          </Form.Item>
          <Form.Item label="快速选择定时">
            <Space wrap>
              {CRON_PRESETS.map(p => (
                <Button
                  key={p.value}
                  size="small"
                  onClick={() => form.setFieldsValue({ cron_expr: p.value })}
                >
                  {p.label}
                </Button>
              ))}
            </Space>
          </Form.Item>
          <Form.Item name="config" label="配置（JSON，可选）">
            <Input.TextArea placeholder='{"max_depth": 3}' />
          </Form.Item>
          <Form.Item name="run_immediately" valuePropName="checked" initialValue={false}>
            <Checkbox>保存后立即运行一次采集</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
