import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Select, message, Space, Tag, Popconfirm, Switch, Slider, Tabs, Empty, Spin, Popover, Descriptions } from 'antd'
import { PlusOutlined, SearchOutlined, DeleteOutlined, BulbOutlined } from '@ant-design/icons'
import { interestPointsApi, InterestPoint, CreateInterestPointRequest, InterestPointStats } from '../api/interestPoints'
import { categoriesApi, Category } from '../api/categories'

export default function InterestPoints() {
  const [points, setPoints] = useState<InterestPoint[]>([])
  const [filteredPoints, setFilteredPoints] = useState<InterestPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editingPoint, setEditingPoint] = useState<InterestPoint | null>(null)
  const [form] = Form.useForm()

  // 筛选
  const [searchText, setSearchText] = useState('')
  const [filterSource, setFilterSource] = useState<string | undefined>(undefined)
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined)
  const [filterCategory, setFilterCategory] = useState<number | undefined>(undefined)

  // 发现
  const [discovering, setDiscovering] = useState(false)

  // 词云
  const [activeTab, setActiveTab] = useState('list')
  const [stats, setStats] = useState<InterestPointStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(false)

  const loadPoints = async () => {
    setLoading(true)
    try {
      const res = await interestPointsApi.list()
      setPoints(res.data)
    } catch {
      message.error('加载兴趣点失败')
    } finally {
      setLoading(false)
    }
  }

  const loadCategories = async () => {
    try {
      const res = await categoriesApi.list()
      setCategories(res.data)
    } catch {
      // 静默
    }
  }

  const loadStats = async () => {
    setStatsLoading(true)
    try {
      const res = await interestPointsApi.stats()
      setStats(res.data)
    } catch {
      message.error('加载统计数据失败')
    } finally {
      setStatsLoading(false)
    }
  }

  useEffect(() => { loadPoints(); loadCategories() }, [])

  useEffect(() => {
    if (activeTab === 'wordcloud') loadStats()
  }, [activeTab])

  // 筛选逻辑
  useEffect(() => {
    let filtered = [...points]
    if (searchText) {
      const lower = searchText.toLowerCase()
      filtered = filtered.filter(p =>
        p.name.toLowerCase().includes(lower) ||
        p.keywords.some(k => k.toLowerCase().includes(lower))
      )
    }
    if (filterSource !== undefined) {
      filtered = filtered.filter(p => p.source === filterSource)
    }
    if (filterActive !== undefined) {
      filtered = filtered.filter(p => p.is_active === filterActive)
    }
    if (filterCategory !== undefined) {
      filtered = filtered.filter(p => p.category_id === filterCategory)
    }
    setFilteredPoints(filtered)
  }, [points, searchText, filterSource, filterActive, filterCategory])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingPoint) {
        await interestPointsApi.update(editingPoint.id, values)
        message.success('更新成功')
      } else {
        await interestPointsApi.create(values)
        message.success('创建成功')
      }
      closeModal()
      loadPoints()
    } catch {
      // 表单校验失败
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await interestPointsApi.delete(id)
      message.success('已删除')
      loadPoints()
    } catch {
      message.error('删除失败')
    }
  }

  const handleToggleActive = async (point: InterestPoint) => {
    try {
      if (point.is_active) {
        await interestPointsApi.deactivate(point.id)
      } else {
        await interestPointsApi.activate(point.id)
      }
      loadPoints()
    } catch {
      message.error('操作失败')
    }
  }

  const handleDiscover = async () => {
    setDiscovering(true)
    try {
      await interestPointsApi.discover()
      message.success('发现完成，已刷新列表')
      loadPoints()
    } catch {
      message.error('发现兴趣点失败')
    } finally {
      setDiscovering(false)
    }
  }

  const openCreate = () => {
    setEditingPoint(null)
    form.resetFields()
    form.setFieldsValue({ weight: 1.0, source: 'manual', keywords: [] })
    setModalOpen(true)
  }

  const openEdit = (point: InterestPoint) => {
    setEditingPoint(point)
    form.setFieldsValue({
      name: point.name,
      description: point.description,
      weight: point.weight,
      category_id: point.category_id,
      keywords: point.keywords,
    })
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setEditingPoint(null)
    form.resetFields()
  }

  const resetFilters = () => {
    setSearchText('')
    setFilterSource(undefined)
    setFilterActive(undefined)
    setFilterCategory(undefined)
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: InterestPoint) => (
        <span>
          {name}
          {record.source === 'ai_discovered' && !record.is_active && (
            <Tag color="orange" style={{ marginLeft: 8 }}>AI 候选</Tag>
          )}
        </span>
      ),
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (source: string) => (
        <Tag color={source === 'manual' ? 'blue' : 'green'}>
          {source === 'manual' ? '手动' : 'AI'}
        </Tag>
      ),
    },
    {
      title: '权重',
      dataIndex: 'weight',
      key: 'weight',
      width: 80,
      sorter: (a: InterestPoint, b: InterestPoint) => a.weight - b.weight,
    },
    {
      title: '关键词',
      dataIndex: 'keywords',
      key: 'keywords',
      render: (keywords: string[]) => (
        <>
          {keywords.slice(0, 5).map((k, i) => <Tag key={i}>{k}</Tag>)}
          {keywords.length > 5 && <Tag>+{keywords.length - 5}</Tag>}
        </>
      ),
    },
    {
      title: '分类',
      key: 'category',
      width: 100,
      render: (_: unknown, record: InterestPoint) =>
        record.category ? (
          <Tag color={record.category.color}>{record.category.name}</Tag>
        ) : '-',
    },
    {
      title: '状态',
      key: 'is_active',
      width: 80,
      render: (_: unknown, record: InterestPoint) => (
        <Switch
          checked={record.is_active}
          onChange={() => handleToggleActive(record)}
          size="small"
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: InterestPoint) => (
        <Space>
          {record.source === 'ai_discovered' && !record.is_active && (
            <Button type="link" size="small" onClick={() => handleToggleActive(record)}>
              确认启用
            </Button>
          )}
          <Button type="link" size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        {
          key: 'list',
          label: '列表',
          children: (
            <>
              <Space style={{ marginBottom: 16 }} wrap>
                <Input
                  placeholder="搜索名称/关键词"
                  prefix={<SearchOutlined />}
                  value={searchText}
                  onChange={e => setSearchText(e.target.value)}
                  style={{ width: 200 }}
                  allowClear
                />
                <Select
                  placeholder="来源"
                  value={filterSource}
                  onChange={setFilterSource}
                  allowClear
                  style={{ width: 120 }}
                  options={[
                    { label: '手动', value: 'manual' },
                    { label: 'AI', value: 'ai_discovered' },
                  ]}
                />
                <Select
                  placeholder="状态"
                  value={filterActive}
                  onChange={setFilterActive}
                  allowClear
                  style={{ width: 120 }}
                  options={[
                    { label: '启用', value: true },
                    { label: '禁用', value: false },
                  ]}
                />
                <Select
                  placeholder="分类"
                  value={filterCategory}
                  onChange={setFilterCategory}
                  allowClear
                  style={{ width: 150 }}
                  options={categories.map(c => ({ label: c.name, value: c.id }))}
                />
                <Button onClick={resetFilters}>重置</Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
                  新建
                </Button>
                <Button icon={<BulbOutlined />} loading={discovering} onClick={handleDiscover}>
                  发现新兴趣
                </Button>
              </Space>

              <Table
                rowKey="id"
                columns={columns}
                dataSource={filteredPoints}
                loading={loading}
                rowClassName={(record) =>
                  record.source === 'ai_discovered' && !record.is_active ? 'ai-candidate-row' : ''
                }
              />
              <style>{`.ai-candidate-row { background: #fffbe6 !important; }`}</style>
            </>
          ),
        },
        {
          key: 'wordcloud',
          label: '词云',
          children: <WordCloud stats={stats} loading={statsLoading} />,
        },
      ]} />

      <Modal
        title={editingPoint ? '编辑兴趣点' : '新建兴趣点'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={closeModal}
        okText="确定"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="keywords" label="关键词">
            <Select mode="tags" placeholder="输入后回车添加" />
          </Form.Item>
          <Form.Item name="weight" label="权重">
            <Slider min={0} max={10} step={0.1} marks={{ 0: '0', 5: '5', 10: '10' }} />
          </Form.Item>
          <Form.Item name="category_id" label="分类">
            <Select
              allowClear
              placeholder="选择分类"
              options={categories.map(c => ({ label: c.name, value: c.id }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

// F4: 词云组件
function WordCloud({ stats, loading }: { stats: InterestPointStats | null; loading: boolean }) {
  if (loading) {
    return <div style={{ textAlign: 'center', padding: 48 }}><Spin size="large" /></div>
  }

  if (!stats || stats.items.length === 0) {
    return <Empty description="暂无兴趣点数据" />
  }

  const maxWeight = Math.max(...stats.items.map(i => i.weight))
  const minSize = 14
  const maxSize = 48

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16, color: '#999', fontSize: 12 }}>
        共 {stats.total} 个兴趣点，活跃 {stats.active} 个 |
        <Tag color="blue" style={{ marginLeft: 8 }}>手动</Tag>
        <Tag color="green">AI 发现</Tag>
      </div>
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 12,
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 200,
        padding: 24,
      }}>
        {stats.items.map((item, index) => {
          const fontSize = maxWeight > 0
            ? minSize + (item.weight / maxWeight) * (maxSize - minSize)
            : minSize
          const color = item.source === 'manual' ? '#1677ff' : '#52c41a'

          return (
            <Popover
              key={index}
              content={
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="权重">{item.weight}</Descriptions.Item>
                  <Descriptions.Item label="来源">
                    {item.source === 'manual' ? '手动' : 'AI 发现'}
                  </Descriptions.Item>
                </Descriptions>
              }
              title={item.name}
            >
              <span style={{
                fontSize,
                color,
                cursor: 'pointer',
                transition: 'transform 0.2s',
                display: 'inline-block',
              }}
                onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.15)')}
                onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
              >
                {item.name}
              </span>
            </Popover>
          )
        })}
      </div>
    </div>
  )
}
