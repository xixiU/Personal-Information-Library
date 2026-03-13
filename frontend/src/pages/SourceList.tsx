import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Space } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { sourcesApi, Source, CreateSourceRequest } from '../api/sources'
import { pluginsApi, Plugin } from '../api/plugins'

export default function SourceList() {
  const [sources, setSources] = useState<Source[]>([])
  const [filteredSources, setFilteredSources] = useState<Source[]>([])
  const [plugins, setPlugins] = useState<Plugin[]>([])
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

  useEffect(() => {
    loadSources()
    loadPlugins()
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
        config: configData
      }

      if (editingSource) {
        await sourcesApi.update(editingSource.id, payload)
        message.success('更新成功')
      } else {
        await sourcesApi.create(payload)
        message.success('创建成功')
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
      config: source.config ? JSON.stringify(source.config, null, 2) : ''
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
    { title: '爬取模式', dataIndex: 'crawl_mode', key: 'crawl_mode' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
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
              <Select.Option value="site_crawl">整站爬取</Select.Option>
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
          <Form.Item name="config" label="配置（JSON，可选）">
            <Input.TextArea placeholder='{"max_depth": 3}' />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
