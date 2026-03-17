import { useState, useEffect } from 'react'
import { Table, Tag, message, Input, Select, Space, Button, Tooltip, DatePicker } from 'antd'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { tasksApi, Task } from '../api/tasks'
import dayjs, { Dayjs } from 'dayjs'

const { RangePicker } = DatePicker

interface Props {
  type: 'crawl' | 'refine'
}

export default function TaskList({ type }: Props) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [sourceIdFilter, setSourceIdFilter] = useState<string>('')
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const navigate = useNavigate()

  const loadTasks = async () => {
    setLoading(true)
    try {
      const params: any = { type }
      if (statusFilter) params.status = statusFilter
      if (sourceIdFilter) params.source_id = Number(sourceIdFilter)

      const res = await tasksApi.list(params)
      let filteredTasks = res.data

      if (dateRange && dateRange[0] && dateRange[1]) {
        const startDate = dateRange[0].startOf('day')
        const endDate = dateRange[1].endOf('day')
        filteredTasks = filteredTasks.filter((task) => {
          const taskDate = dayjs(task.created_at)
          return taskDate.isAfter(startDate) && taskDate.isBefore(endDate)
        })
      }

      setTasks(filteredTasks)
    } catch (error) {
      message.error('加载任务失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
  }, [type, statusFilter, sourceIdFilter, dateRange])

  const handleReset = () => {
    setStatusFilter('')
    setSourceIdFilter('')
    setDateRange(null)
  }

  const statusColors: Record<string, string> = {
    pending: 'default',
    running: 'processing',
    success: 'success',
    failed: 'error',
    timeout: 'warning'
  }

  const statusLabels: Record<string, string> = {
    pending: '待执行',
    running: '执行中',
    success: '成功',
    failed: '失败',
    timeout: '超时'
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '信源ID', dataIndex: 'source_id', key: 'source_id', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={statusColors[status]}>{statusLabels[status] || status}</Tag>
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
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')
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
          <Select.Option value="pending">待执行</Select.Option>
          <Select.Option value="running">执行中</Select.Option>
          <Select.Option value="success">成功</Select.Option>
          <Select.Option value="failed">失败</Select.Option>
          <Select.Option value="timeout">超时</Select.Option>
        </Select>
        <Input
          placeholder="信源ID"
          style={{ width: 150 }}
          value={sourceIdFilter}
          onChange={(e) => setSourceIdFilter(e.target.value)}
          prefix={<SearchOutlined />}
          allowClear
        />
        <RangePicker
          value={dateRange}
          onChange={setDateRange}
          placeholder={['开始时间', '结束时间']}
          style={{ width: 280 }}
        />
        <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
        <Button type="primary" icon={<ReloadOutlined />} onClick={loadTasks}>刷新</Button>
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
