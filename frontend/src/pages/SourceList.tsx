import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Space, Tag, Tooltip, Checkbox, Card, Row, Col, InputNumber, Switch, Collapse, Steps, Upload, Radio, Statistic, Empty, Alert } from 'antd'
import { SearchOutlined, ClockCircleOutlined, FileTextOutlined, GlobalOutlined, NotificationOutlined, ImportOutlined, UploadOutlined, CheckCircleOutlined, CloseCircleOutlined, MinusCircleOutlined } from '@ant-design/icons'
import { sourcesApi, Source, CreateSourceRequest, ConfigSchema, BatchImportRequest } from '../api/sources'
import { categoriesApi, Category } from '../api/categories'

const { Panel } = Collapse

// RSS 专用的更新频率预设
const RSS_CRON_PRESETS = [
  { label: '每小时', value: '0 * * * *' },
  { label: '每4小时', value: '0 */4 * * *' },
  { label: '每天', value: '0 8 * * *' },
  { label: '每周', value: '0 8 * * 1' },
]

// 非RSS的定时采集预设
const CRON_PRESETS = [
  { label: '每小时', value: '0 * * * *' },
  { label: '每天早8点', value: '0 8 * * *' },
  { label: '每天中午12点', value: '0 12 * * *' },
  { label: '每天晚8点', value: '0 20 * * *' },
  { label: '每周一早8点', value: '0 8 * * 1' },
]

// 信源类型定义
const SOURCE_TYPES = [
  {
    type: 'single_page',
    label: '单页爬取',
    icon: <FileTextOutlined style={{ fontSize: 24 }} />,
    description: '只爬取指定 URL 的内容',
    detail: '适合：文章、博客、新闻页',
  },
  {
    type: 'full_site',
    label: '整站爬取',
    icon: <GlobalOutlined style={{ fontSize: 24 }} />,
    description: '从入口页递归爬取所有子页面',
    detail: '适合：文档站、专题页、项目主页',
  },
  {
    type: 'rss',
    label: 'RSS 订阅',
    icon: <NotificationOutlined style={{ fontSize: 24 }} />,
    description: '自动获取 feed 中的最新文章',
    detail: '支持 RSS 2.0 和 Atom 格式',
  },
]

export default function SourceList() {
  const [sources, setSources] = useState<Source[]>([])
  const [filteredSources, setFilteredSources] = useState<Source[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingSource, setEditingSource] = useState<Source | null>(null)
  const [searchText, setSearchText] = useState('')
  const [form] = Form.useForm()

  // 动态配置相关状态
  const [selectedSourceType, setSelectedSourceType] = useState<string>('single_page')
  const [configSchema, setConfigSchema] = useState<ConfigSchema | null>(null)
  const [loadingSchema, setLoadingSchema] = useState(false)

  // 批量导入相关状态
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [importStep, setImportStep] = useState(0)
  const [importSource, setImportSource] = useState<'opml' | 'url_list'>('url_list')
  const [importUrlList, setImportUrlList] = useState<Array<{ name: string; url: string }>>([])
  const [selectedUrls, setSelectedUrls] = useState<string[]>([])
  const [importDefaultCategory, setImportDefaultCategory] = useState<number | null>(null)
  const [importDefaultCron, setImportDefaultCron] = useState<string>('0 */4 * * *')
  const [importResult, setImportResult] = useState<any>(null)
  const [importing, setImporting] = useState(false)

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

  const loadCategories = async () => {
    try {
      const res = await categoriesApi.list()
      setCategories(res.data)
    } catch (error) {
      // 分类加载失败不影响主流程
    }
  }

  // 加载配置 Schema
  const loadConfigSchema = async (sourceType: string) => {
    setLoadingSchema(true)
    try {
      const res = await sourcesApi.getConfigSchema(sourceType)
      setConfigSchema(res.data)

      // 设置字段默认值
      const defaults: Record<string, any> = {}
      res.data.fields.forEach((field) => {
        defaults[field.name] = field.default
      })
      form.setFieldsValue(defaults)
    } catch (error) {
      message.error('加载配置模板失败')
      setConfigSchema(null)
    } finally {
      setLoadingSchema(false)
    }
  }

  useEffect(() => {
    loadSources()
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

  // 源类型变化时加载对应的配置模板
  useEffect(() => {
    if (modalOpen && selectedSourceType) {
      loadConfigSchema(selectedSourceType)
    }
  }, [selectedSourceType, modalOpen])

  const handleSubmit = async (values: any) => {
    try {
      // 组装配置对象（从动态表单字段中提取）
      const configData: Record<string, any> = {}
      if (configSchema) {
        configSchema.fields.forEach((field) => {
          if (values[field.name] !== undefined && values[field.name] !== null) {
            configData[field.name] = values[field.name]
          }
        })
      }

      const payload: CreateSourceRequest = {
        name: values.name,
        url: values.url,
        source_type: selectedSourceType,
        config: Object.keys(configData).length > 0 ? configData : null,
        category_id: values.category_id || null,
        cron_expr: values.cron_expr || null,
      }

      let sourceId: number
      if (editingSource) {
        await sourcesApi.update(editingSource.id, payload)
        message.success('更新成功')
        sourceId = editingSource.id
      } else {
        const res = await sourcesApi.create(payload)
        // 创建成功提示分情况
        if (values.run_immediately) {
          message.success('创建成功！正在触发采集任务...')
        } else {
          message.success('创建成功！点击「触发采集」按钮开始爬取内容', 5)
        }
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
      message.error((editingSource ? '更新' : '创建') + '失败: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleEdit = (source: Source) => {
    setEditingSource(source)
    setSelectedSourceType(source.source_type || 'single_page')

    // 设置基础字段
    const formValues: Record<string, any> = {
      name: source.name,
      url: source.url,
      category_id: source.category_id || undefined,
      cron_expr: source.cron_expr || '',
      run_immediately: false,
    }

    // 回填配置字段
    if (source.config) {
      Object.keys(source.config).forEach((key) => {
        formValues[key] = source.config![key]
      })
    }

    form.setFieldsValue(formValues)
    setModalOpen(true)
  }

  const handleModalClose = () => {
    setModalOpen(false)
    setEditingSource(null)
    setSelectedSourceType('single_page')
    setConfigSchema(null)
    form.resetFields()
  }

  const handleCreateNew = () => {
    setEditingSource(null)
    setSelectedSourceType('single_page')
    form.resetFields()
    setModalOpen(true)
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

  // 批量导入相关函数
  const handleImportModalOpen = () => {
    setImportModalOpen(true)
    setImportStep(0)
    setImportSource('url_list')
    setImportUrlList([])
    setSelectedUrls([])
    setImportDefaultCategory(null)
    setImportDefaultCron('0 */4 * * *')
    setImportResult(null)
  }

  const handleImportModalClose = () => {
    setImportModalOpen(false)
    setImportStep(0)
    setImportUrlList([])
    setSelectedUrls([])
    setImportResult(null)
  }

  // 解析 OPML 文件
  const parseOpml = (xmlString: string): Array<{ name: string; url: string }> => {
    try {
      const parser = new DOMParser()
      const xmlDoc = parser.parseFromString(xmlString, 'text/xml')
      const outlines = xmlDoc.getElementsByTagName('outline')
      const result: Array<{ name: string; url: string }> = []

      for (let i = 0; i < outlines.length; i++) {
        const outline = outlines[i]
        const xmlUrl = outline.getAttribute('xmlUrl')
        const title = outline.getAttribute('title') || outline.getAttribute('text')

        if (xmlUrl) {
          result.push({
            name: title || xmlUrl,
            url: xmlUrl,
          })
        }
      }

      return result
    } catch (error) {
      message.error('OPML 文件解析失败')
      return []
    }
  }

  // 处理文件上传
  const handleFileUpload = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      const parsed = parseOpml(content)
      if (parsed.length > 0) {
        setImportUrlList(parsed)
        setSelectedUrls(parsed.map((item) => item.url))
        message.success(`成功解析 ${parsed.length} 个订阅源`)
      } else {
        message.error('未能从文件中解析出订阅源')
      }
    }
    reader.readAsText(file)
    return false // 阻止自动上传
  }

  // 处理 URL 列表粘贴
  const handleUrlListPaste = (text: string) => {
    const lines = text.split('\n').filter((line) => line.trim())
    const parsed = lines.map((url) => ({
      name: url.trim(),
      url: url.trim(),
    }))
    setImportUrlList(parsed)
    setSelectedUrls(parsed.map((item) => item.url))
  }

  // 进入预览步骤
  const handleImportNext = () => {
    if (importUrlList.length === 0) {
      message.warning('请先上传文件或粘贴 URL 列表')
      return
    }
    setImportStep(1)
  }

  // 执行批量导入
  const handleImportSubmit = async () => {
    if (selectedUrls.length === 0) {
      message.warning('请至少选择一个订阅源')
      return
    }

    setImporting(true)
    try {
      const selectedItems = importUrlList.filter((item) => selectedUrls.includes(item.url))

      const payload: BatchImportRequest = {
        import_type: 'url_list',
        data: selectedItems.map((item) => item.url),
        default_category_id: importDefaultCategory,
        default_cron_expr: importDefaultCron,
        default_config: {
          max_items: 20,
          fetch_full_content: true,
        },
      }

      const res = await sourcesApi.batchImport(payload)
      setImportResult(res.data)
      setImportStep(2)
      loadSources()
      message.success(`成功导入 ${res.data.success_count} 个订阅源`)
    } catch (error: any) {
      message.error('批量导入失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      setImporting(false)
    }
  }

  // 获取源类型的中文名
  const getSourceTypeLabel = (sourceType: string) => {
    const type = SOURCE_TYPES.find((t) => t.type === sourceType)
    return type ? type.label : sourceType
  }

  // 渲染动态配置表单
  const renderDynamicConfigFields = () => {
    if (!configSchema || loadingSchema) {
      return <div style={{ textAlign: 'center', padding: '20px' }}>加载配置项...</div>
    }

    const basicFields = configSchema.fields.filter((f) => !f.advanced)
    const advancedFields = configSchema.fields.filter((f) => f.advanced)

    const renderField = (field: any) => {
      const commonProps = {
        label: field.label || field.name, // 兜底：字段名翻译缺失时用 name
        name: field.name,
        extra: field.help || undefined, // 空字符串不显示 extra
        initialValue: field.default,
      }

      switch (field.type) {
        case 'number':
          return (
            <Form.Item key={field.name} {...commonProps}>
              <InputNumber
                min={field.min}
                max={field.max}
                style={{ width: '100%' }}
              />
            </Form.Item>
          )
        case 'switch':
          return (
            <Form.Item key={field.name} {...commonProps} valuePropName="checked">
              <Switch />
            </Form.Item>
          )
        case 'text':
          return (
            <Form.Item key={field.name} {...commonProps}>
              <Input />
            </Form.Item>
          )
        case 'textarea':
          return (
            <Form.Item key={field.name} {...commonProps}>
              <Input.TextArea rows={3} />
            </Form.Item>
          )
        case 'select':
          return (
            <Form.Item key={field.name} {...commonProps}>
              <Select>
                {field.options?.map((opt: any) => (
                  <Select.Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          )
        default:
          return null
      }
    }

    return (
      <>
        {basicFields.map(renderField)}
        {advancedFields.length > 0 && (
          <Collapse ghost>
            <Panel header="高级配置" key="advanced">
              {advancedFields.map(renderField)}
            </Panel>
          </Collapse>
        )}
      </>
    )
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
    {
      title: '信源类型',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 120,
      render: (sourceType: string) => getSourceTypeLabel(sourceType),
    },
    {
      title: '分类',
      dataIndex: 'category_id',
      key: 'category_id',
      width: 120,
      render: (category_id: number | null) => {
        if (!category_id) return <Tag color="default">未分类</Tag>
        const cat = categories.find((c) => c.id === category_id)
        return cat ? <Tag color={cat.color}>{cat.name}</Tag> : <Tag color="default">未分类</Tag>
      },
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
              {CRON_PRESETS.find((p) => p.value === cron_expr)?.label ||
               RSS_CRON_PRESETS.find((p) => p.value === cron_expr)?.label ||
               cron_expr}
            </Tag>
          </Tooltip>
        ) : (
          <Tag color="default">未设置</Tag>
        ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => (status === 'active' ? '启用' : '禁用'),
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
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="搜索名称或URL"
            style={{ width: 300 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            prefix={<SearchOutlined />}
            allowClear
          />
          <Button type="primary" onClick={handleCreateNew}>
            创建信源
          </Button>
          <Button icon={<ImportOutlined />} onClick={handleImportModalOpen}>
            导入 RSS
          </Button>
        </Space>
        <Table
          columns={columns}
          dataSource={filteredSources}
          rowKey="id"
          loading={loading}
          locale={{
            emptyText: (
              <Empty
                description='还没有信源，点击"创建信源"开始使用'
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
        />
      </Card>
      <Modal
        title={editingSource ? '编辑信源' : '创建信源'}
        open={modalOpen}
        onCancel={handleModalClose}
        onOk={() => form.submit()}
        width={700}
      >
        <Form form={form} onFinish={handleSubmit} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入信源名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="url" label="URL" rules={[{ required: true, message: '请输入URL' }]}>
            <Input placeholder="https://example.com" />
          </Form.Item>

          {/* 信源类型三选一卡片 */}
          {!editingSource && (
            <>
              <Alert
                message="💡 提示：选择信源类型"
                description={
                  <div style={{ fontSize: 12 }}>
                    不确定选哪个？大多数情况选<strong>「单页爬取」</strong>即可。
                    <br />
                    整站爬取适合文档站，RSS 订阅适合新闻/博客追更。
                  </div>
                }
                type="info"
                closable
                style={{ marginBottom: 16 }}
              />
              <Form.Item label="信源类型" required>
                <Row gutter={12}>
                  {SOURCE_TYPES.map((type) => (
                    <Col span={8} key={type.type}>
                      <Card
                        hoverable
                        onClick={() => setSelectedSourceType(type.type)}
                        style={{
                          textAlign: 'center',
                          cursor: 'pointer',
                          border: selectedSourceType === type.type ? '2px solid #1890ff' : '1px solid #d9d9d9',
                          backgroundColor: selectedSourceType === type.type ? '#e6f7ff' : '#fff',
                        }}
                      >
                        <div style={{ marginBottom: 8 }}>{type.icon}</div>
                        <div style={{ fontWeight: 'bold', marginBottom: 4 }}>{type.label}</div>
                        <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>{type.description}</div>
                        <div style={{ fontSize: 11, color: '#999' }}>{type.detail}</div>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Form.Item>
            </>
          )}

          {editingSource && (
            <Form.Item label="信源类型">
              <Input value={getSourceTypeLabel(selectedSourceType)} disabled />
            </Form.Item>
          )}

          <Form.Item name="category_id" label="分类">
            <Select placeholder="选择分类（可选）" allowClear>
              {categories.map((c) => (
                <Select.Option key={c.id} value={c.id}>
                  <Tag color={c.color} style={{ marginRight: 4 }}>
                    {c.name}
                  </Tag>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          {/* RSS 专用：更新频率下拉 */}
          {selectedSourceType === 'rss' && (
            <>
              <Form.Item
                name="cron_expr"
                label="更新频率"
                initialValue="0 */4 * * *"
                extra="推荐「每4小时」，既能及时获取更新，又不会对目标站点造成压力"
              >
                <Select>
                  {RSS_CRON_PRESETS.map((p) => (
                    <Select.Option key={p.value} value={p.value}>
                      {p.label}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </>
          )}

          {/* 非RSS：定时采集（可选） */}
          {selectedSourceType !== 'rss' && (
            <>
              <Form.Item name="cron_expr" label="定时采集" extra="留空则不启用定时采集">
                <Input placeholder="0 8 * * * (每天早8点)" allowClear />
              </Form.Item>
              <Form.Item label="快速选择定时">
                <Space wrap>
                  {CRON_PRESETS.map((p) => (
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
            </>
          )}

          {/* 动态配置表单 */}
          {renderDynamicConfigFields()}

          <Form.Item name="run_immediately" valuePropName="checked" initialValue={false}>
            <Checkbox>保存后立即运行一次采集</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      {/* 批量导入对话框 */}
      <Modal
        title="批量导入 RSS 订阅"
        open={importModalOpen}
        onCancel={handleImportModalClose}
        width={800}
        footer={null}
      >
        <Steps current={importStep} style={{ marginBottom: 24 }}>
          <Steps.Step title="上传/粘贴" />
          <Steps.Step title="预览勾选" />
          <Steps.Step title="完成" />
        </Steps>

        {/* 步骤1：上传/粘贴 */}
        {importStep === 0 && (
          <div>
            <Radio.Group
              value={importSource}
              onChange={(e) => setImportSource(e.target.value)}
              style={{ marginBottom: 16 }}
            >
              <Radio value="url_list">粘贴 URL 列表</Radio>
              <Radio value="opml">上传 OPML 文件</Radio>
            </Radio.Group>

            {importSource === 'opml' && (
              <Upload
                accept=".opml,.xml"
                beforeUpload={handleFileUpload}
                showUploadList={false}
              >
                <Button icon={<UploadOutlined />}>选择 OPML 文件</Button>
              </Upload>
            )}

            {importSource === 'url_list' && (
              <Input.TextArea
                rows={10}
                placeholder="每行一个 RSS/Atom 订阅地址，例如：&#10;https://www.ruanyifeng.com/blog/atom.xml&#10;https://hnrss.org/frontpage"
                onChange={(e) => handleUrlListPaste(e.target.value)}
              />
            )}

            {importUrlList.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Tag color="blue">已识别 {importUrlList.length} 个订阅源</Tag>
              </div>
            )}

            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Button onClick={handleImportModalClose} style={{ marginRight: 8 }}>
                取消
              </Button>
              <Button type="primary" onClick={handleImportNext}>
                下一步
              </Button>
            </div>
          </div>
        )}

        {/* 步骤2：预览勾选 */}
        {importStep === 1 && (
          <div>
            <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
              <div>
                <span style={{ marginRight: 8 }}>默认分类：</span>
                <Select
                  style={{ width: 200 }}
                  placeholder="选择分类（可选）"
                  allowClear
                  value={importDefaultCategory}
                  onChange={setImportDefaultCategory}
                >
                  {categories.map((c) => (
                    <Select.Option key={c.id} value={c.id}>
                      <Tag color={c.color}>{c.name}</Tag>
                    </Select.Option>
                  ))}
                </Select>
              </div>
              <div>
                <span style={{ marginRight: 8 }}>默认更新频率：</span>
                <Select
                  style={{ width: 200 }}
                  value={importDefaultCron}
                  onChange={setImportDefaultCron}
                >
                  {RSS_CRON_PRESETS.map((p) => (
                    <Select.Option key={p.value} value={p.value}>
                      {p.label}
                    </Select.Option>
                  ))}
                </Select>
              </div>
            </Space>

            <Table
              rowSelection={{
                selectedRowKeys: selectedUrls,
                onChange: (keys) => setSelectedUrls(keys as string[]),
              }}
              columns={[
                { title: '名称', dataIndex: 'name', key: 'name' },
                { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
              ]}
              dataSource={importUrlList}
              rowKey="url"
              pagination={false}
              scroll={{ y: 300 }}
            />

            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Button onClick={() => setImportStep(0)} style={{ marginRight: 8 }}>
                上一步
              </Button>
              <Button
                type="primary"
                onClick={handleImportSubmit}
                loading={importing}
                disabled={selectedUrls.length === 0}
              >
                确认导入 ({selectedUrls.length})
              </Button>
            </div>
          </div>
        )}

        {/* 步骤3：完成 */}
        {importStep === 2 && importResult && (
          <div>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="成功"
                    value={importResult.success_count}
                    valueStyle={{ color: '#3f8600' }}
                    prefix={<CheckCircleOutlined />}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="跳过"
                    value={importResult.skipped_count}
                    valueStyle={{ color: '#faad14' }}
                    prefix={<MinusCircleOutlined />}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="失败"
                    value={importResult.failed_count}
                    valueStyle={{ color: '#cf1322' }}
                    prefix={<CloseCircleOutlined />}
                  />
                </Card>
              </Col>
            </Row>

            {importResult.details && importResult.details.length > 0 && (
              <Table
                columns={[
                  { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
                  { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
                  {
                    title: '状态',
                    dataIndex: 'status',
                    key: 'status',
                    width: 100,
                    render: (status: string) => {
                      const statusMap = {
                        success: { color: 'success', text: '成功' },
                        skipped: { color: 'warning', text: '跳过' },
                        failed: { color: 'error', text: '失败' },
                      }
                      const s = statusMap[status as keyof typeof statusMap]
                      return <Tag color={s.color}>{s.text}</Tag>
                    },
                  },
                  { title: '原因', dataIndex: 'reason', key: 'reason', width: 200 },
                ]}
                dataSource={importResult.details}
                rowKey={(record, index) => `${record.url}-${index}`}
                pagination={false}
                scroll={{ y: 300 }}
              />
            )}

            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Button type="primary" onClick={handleImportModalClose}>
                完成
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
