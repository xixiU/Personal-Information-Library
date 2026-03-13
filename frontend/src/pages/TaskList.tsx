import { useState, useEffect } from 'react'
import { Table, Tag, message, Input, Select, Space, Button, Tooltip } from 'antd'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { tasksApi, Task } from '../api/tasks'
import dayjs from 'dayjs'

export default function TaskList() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [sourceIdFilter, setSourceIdFilter] = useState<string>('')
  const navigate = useNavigate()

  const loadTasks = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (statusFilter) params.status = statusFilter
      if (sourceIdFilter) params.source_id = Number(sourceIdFilter)

      const res = await tasksApi.list(params)
      setTasks(res.data)
    } catch (error) {
      message.error('加载任务失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
  }, [statusFilter, sourceIdFilter])

  const handleReset = () => {
    setStatusFilter('')
    setSourceIdFilter('')
  }

  const statusColors: Record<string, string> = {
    pending: 'default',
    running: 'processing',
    success: 'success',
    failed: 'error',
    timeout: 'warning'
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '类型', dataIndex: 'type', key: 'type', width: 100 },
    { title: '信源ID', dataIndex: 'source_id', key: 'source_id', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Tag color={statusColors[status]}>{status}</Tag>
      )
    },
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
      render: (url: string | null) => url || '-'
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      width: 200,
      ellipsis: true,
      render: (error: string | null) =>
        error ? (
          <Tooltip title={error}>
            <span style={{ color: 'red' }}>{error}</span>
          </Tooltip>
        ) : '-'
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 180,
      render: (time: string | null) =>
        time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 180,
      render: (time: string | null) =>
        time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="筛选状态"
          style={{ width: 150 }}
          value={statusFilter || undefined}
          onChange={setStatusFilter}
          allowClear
        >
          <Select.Option value="pending">pending</Select.Option>
          <Select.Option value="running">running</Select.Option>
          <Select.Option value="success">success</Select.Option>
          <Select.Option value="failed">failed</Select.Option>
          <Select.Option value="timeout">timeout</Select.Option>
        </Select>
        <Input
          placeholder="信源ID"
          style={{ width: 150 }}
          value={sourceIdFilter}
          onChange={(e) => setSourceIdFilter(e.target.value)}
          prefix={<SearchOutlined />}
          allowClear
        />
        <Button icon={<ReloadOutlined />} onClick={handleReset}>
          重置
        </Button>
        <Button type="primary" icon={<ReloadOutlined />} onClick={loadTasks}>
          刷新
        </Button>
      </Space>
      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="id"
        loading={loading}
        onRow={(record) => ({
          onClick: () => navigate(`/results?source_id=${record.source_id}`),
          style: { cursor: 'pointer' }
        })}
      />
    </div>
  )
}
