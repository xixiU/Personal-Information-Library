import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, Switch, message, Space, Tag, Popconfirm, Radio } from 'antd'
import { PlusOutlined, SendOutlined } from '@ant-design/icons'
import { channelsApi, NotificationChannel, CreateChannelRequest } from '../api/notifications'

export default function NotificationChannels() {
  const [channels, setChannels] = useState<NotificationChannel[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingChannel, setEditingChannel] = useState<NotificationChannel | null>(null)
  const [channelType, setChannelType] = useState<'webhook' | 'telegram' | 'feishu'>('webhook')
  const [testing, setTesting] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadChannels = async () => {
    setLoading(true)
    try {
      const res = await channelsApi.list()
      setChannels(res.data)
    } catch {
      message.error('加载通知渠道失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadChannels() }, [])

  const handleSubmit = async (values: any) => {
    try {
      let config: Record<string, any>
      if (values.channel_type === 'webhook') {
        config = {
          url: values.webhook_url,
          method: values.webhook_method || 'POST',
          headers: values.webhook_headers ? JSON.parse(values.webhook_headers) : {},
          secret: values.webhook_secret || null,
        }
      } else if (values.channel_type === 'feishu') {
        config = {
          webhook_url: values.feishu_webhook_url,
          use_card: values.feishu_use_card ?? true,
        }
      } else {
        config = {
          bot_token: values.telegram_bot_token,
          chat_id: values.telegram_chat_id,
          parse_mode: 'Markdown',
        }
      }

      const payload: CreateChannelRequest = {
        name: values.name,
        channel_type: values.channel_type,
        config,
        enabled: values.enabled ?? true,
      }

      if (editingChannel) {
        await channelsApi.update(editingChannel.id, payload)
        message.success('渠道已更新')
      } else {
        await channelsApi.create(payload)
        message.success('渠道已创建')
      }
      closeModal()
      loadChannels()
    } catch {
      message.error(editingChannel ? '更新渠道失败' : '创建渠道失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await channelsApi.delete(id)
      message.success('渠道已删除')
      loadChannels()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '删除渠道失败，可能存在关联的通知规则')
    }
  }

  const handleTest = async (id: number) => {
    setTesting(id)
    try {
      await channelsApi.test(id)
      message.success('测试消息已发送')
    } catch {
      message.error('测试发送失败')
    } finally {
      setTesting(null)
    }
  }

  const openEditModal = (channel: NotificationChannel) => {
    setEditingChannel(channel)
    setChannelType(channel.channel_type)
    const fields: any = {
      name: channel.name,
      channel_type: channel.channel_type,
      enabled: channel.enabled,
    }
    if (channel.channel_type === 'webhook') {
      fields.webhook_url = channel.config.url
      fields.webhook_method = channel.config.method || 'POST'
      fields.webhook_headers = channel.config.headers ? JSON.stringify(channel.config.headers) : ''
      fields.webhook_secret = channel.config.secret || ''
    } else if (channel.channel_type === 'feishu') {
      fields.feishu_webhook_url = channel.config.webhook_url
      fields.feishu_use_card = channel.config.use_card ?? true
    } else {
      fields.telegram_bot_token = channel.config.bot_token
      fields.telegram_chat_id = channel.config.chat_id
    }
    form.setFieldsValue(fields)
    setModalOpen(true)
  }

  const openCreateModal = () => {
    setEditingChannel(null)
    form.resetFields()
    setChannelType('webhook')
    form.setFieldsValue({ channel_type: 'webhook', enabled: true })
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setEditingChannel(null)
    form.resetFields()
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: '类型',
      dataIndex: 'channel_type',
      key: 'channel_type',
      width: 120,
      render: (type: string) => (
        <Tag color={type === 'webhook' ? 'blue' : type === 'feishu' ? 'green' : 'cyan'}>
          {type === 'webhook' ? 'Webhook' : type === 'feishu' ? '飞书' : 'Telegram'}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'default'}>{enabled ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      render: (_: any, record: NotificationChannel) => (
        <Space>
          <Button type="link" size="small" onClick={() => openEditModal(record)}>编辑</Button>
          <Button
            type="link"
            size="small"
            icon={<SendOutlined />}
            loading={testing === record.id}
            onClick={() => handleTest(record.id)}
          >
            测试
          </Button>
          <Popconfirm title="确定删除该渠道？删除后关联的通知规则也将失效。" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
          新增渠道
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={channels}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title={editingChannel ? '编辑渠道' : '新增渠道'}
        open={modalOpen}
        onCancel={closeModal}
        onOk={() => form.submit()}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入渠道名称' }]}>
            <Input placeholder="如：企业微信通知、Telegram 频道" />
          </Form.Item>
          <Form.Item name="channel_type" label="渠道类型" rules={[{ required: true }]}>
            <Select
              onChange={(val) => setChannelType(val)}
              options={[
                { label: 'Webhook', value: 'webhook' },
                { label: 'Telegram', value: 'telegram' },
                { label: '飞书', value: 'feishu' },
              ]}
            />
          </Form.Item>

          {channelType === 'webhook' && (
            <>
              <Form.Item name="webhook_url" label="Webhook URL" rules={[{ required: true, message: '请输入 URL' }]}>
                <Input placeholder="https://example.com/webhook" />
              </Form.Item>
              <Form.Item name="webhook_method" label="HTTP Method" initialValue="POST">
                <Select options={[
                  { label: 'POST', value: 'POST' },
                  { label: 'PUT', value: 'PUT' },
                ]} />
              </Form.Item>
              <Form.Item name="webhook_headers" label="Headers (JSON)" extra={'可选，如 {"Authorization": "Bearer xxx"}'}>
                <Input.TextArea rows={2} placeholder='{"Authorization": "Bearer xxx"}' />
              </Form.Item>
              <Form.Item name="webhook_secret" label="Secret" extra="可选，用于 HMAC 签名验证">
                <Input placeholder="hmac_secret_key" />
              </Form.Item>
            </>
          )}

          {channelType === 'telegram' && (
            <>
              <Form.Item name="telegram_bot_token" label="Bot Token" rules={[{ required: true, message: '请输入 Bot Token' }]}>
                <Input placeholder="123456:ABC-DEF" />
              </Form.Item>
              <Form.Item name="telegram_chat_id" label="Chat ID" rules={[{ required: true, message: '请输入 Chat ID' }]}>
                <Input placeholder="-1001234567890" />
              </Form.Item>
            </>
          )}

          {channelType === 'feishu' && (
            <>
              <Form.Item name="feishu_webhook_url" label="飞书 Webhook URL" rules={[{ required: true, message: '请输入飞书 Webhook URL' }]}
                extra="在飞书群设置中添加自定义机器人获取 Webhook 地址"
              >
                <Input placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxx" />
              </Form.Item>
              <Form.Item name="feishu_use_card" label="消息格式" initialValue={true}>
                <Radio.Group>
                  <Radio value={true}>消息卡片（推荐）</Radio>
                  <Radio value={false}>普通文本</Radio>
                </Radio.Group>
              </Form.Item>
            </>
          )}

          <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
