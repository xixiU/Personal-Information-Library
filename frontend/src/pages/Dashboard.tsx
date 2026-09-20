import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Button, List, Tag, Empty, Progress, Space } from 'antd'
import { DatabaseOutlined, ThunderboltOutlined, FileTextOutlined, StarOutlined, PlusOutlined, ImportOutlined, CheckCircleOutlined, CloseCircleOutlined, SyncOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'

interface DashboardStats {
  sources: { total: number; today: number }
  tasks: { pending: number; running: number; success: number; failed: number }
  results: { total: number; today: number; avg_quality_score: number }
  recent_results: Array<{
    id: number
    title: string
    summary: string
    quality_score: number
    created_at: string
  }>
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const loadStats = async () => {
    setLoading(true)
    try {
      const res = await client.get<DashboardStats>('/dashboard/stats')
      setStats(res.data)
    } catch (error) {
      console.error('加载仪表盘数据失败', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
  }, [])

  // 计算任务总数和成功率
  const totalTasks = stats
    ? stats.tasks.pending + stats.tasks.running + stats.tasks.success + stats.tasks.failed
    : 0
  const successRate = totalTasks > 0 ? (stats!.tasks.success / totalTasks) * 100 : 0

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24 }}>个人信息库仪表盘</h2>

      {/* 快速开始 */}
      {stats && stats.sources.total === 0 ? (
        <Card style={{ marginBottom: 24 }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <div>
                <div style={{ fontSize: 16, marginBottom: 8 }}>还没有信源，开始创建您的第一个信源</div>
                <div style={{ color: '#666', fontSize: 14 }}>
                  信源是您获取信息的来源，支持单页爬取、整站爬取和 RSS 订阅三种模式
                </div>
              </div>
            }
          >
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/sources')}>
                创建第一个信源
              </Button>
              <Button icon={<ImportOutlined />} onClick={() => navigate('/sources')}>
                导入 RSS 订阅
              </Button>
            </Space>
          </Empty>
        </Card>
      ) : (
        <>
          {/* 数据概览 */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card hoverable onClick={() => navigate('/sources')} style={{ cursor: 'pointer' }}>
                <Statistic
                  title="信源总数"
                  value={stats?.sources.total || 0}
                  prefix={<DatabaseOutlined />}
                  suffix={stats?.sources.today ? `(+${stats.sources.today})` : ''}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card hoverable onClick={() => navigate('/tasks/crawl')} style={{ cursor: 'pointer' }}>
                <Statistic
                  title="任务总数"
                  value={totalTasks}
                  prefix={<ThunderboltOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card hoverable onClick={() => navigate('/results')} style={{ cursor: 'pointer' }}>
                <Statistic
                  title="采集结果"
                  value={stats?.results.total || 0}
                  prefix={<FileTextOutlined />}
                  suffix={stats?.results.today ? `(+${stats.results.today})` : ''}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="平均质量分"
                  value={stats?.results.avg_quality_score || 0}
                  precision={1}
                  prefix={<StarOutlined />}
                  valueStyle={{ color: (stats?.results.avg_quality_score || 0) >= 70 ? '#3f8600' : '#faad14' }}
                />
              </Card>
            </Col>
          </Row>

          {/* 任务状态 */}
          <Card title="任务状态" style={{ marginBottom: 24 }} loading={loading}>
            <Row gutter={16}>
              <Col span={12}>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ marginBottom: 8 }}>
                    <span>成功率：</span>
                    <span style={{ fontWeight: 'bold', fontSize: 18 }}>
                      {successRate.toFixed(1)}%
                    </span>
                  </div>
                  <Progress
                    percent={successRate}
                    status={successRate >= 80 ? 'success' : successRate >= 60 ? 'normal' : 'exception'}
                    strokeColor={successRate >= 80 ? '#52c41a' : successRate >= 60 ? '#1890ff' : '#ff4d4f'}
                  />
                </div>
              </Col>
              <Col span={12}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                    成功: <Tag color="success">{stats?.tasks.success || 0}</Tag>
                  </div>
                  <div>
                    <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                    失败: <Tag color="error">{stats?.tasks.failed || 0}</Tag>
                  </div>
                  <div>
                    <SyncOutlined style={{ color: '#1890ff', marginRight: 8 }} />
                    运行中: <Tag color="processing">{stats?.tasks.running || 0}</Tag>
                  </div>
                  <div>
                    <ClockCircleOutlined style={{ color: '#faad14', marginRight: 8 }} />
                    等待中: <Tag color="warning">{stats?.tasks.pending || 0}</Tag>
                  </div>
                </Space>
              </Col>
            </Row>
          </Card>

          {/* 最新精炼结果 */}
          <Card title="最新精炼结果" extra={<Button type="link" onClick={() => navigate('/results')}>查看全部</Button>} loading={loading}>
            {stats?.recent_results && stats.recent_results.length > 0 ? (
              <List
                dataSource={stats.recent_results}
                renderItem={(item) => (
                  <List.Item
                    key={item.id}
                    actions={[
                      <Tag color={item.quality_score >= 80 ? 'success' : item.quality_score >= 60 ? 'processing' : 'warning'}>
                        质量分: {item.quality_score}
                      </Tag>,
                    ]}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/refined/${item.id}`)}
                  >
                    <List.Item.Meta
                      title={item.title}
                      description={
                        <>
                          <div style={{ marginBottom: 4 }}>{item.summary}</div>
                          <div style={{ fontSize: 12, color: '#999' }}>
                            {new Date(item.created_at).toLocaleString('zh-CN')}
                          </div>
                        </>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="暂无精炼结果" />
            )}
          </Card>
        </>
      )}
    </div>
  )
}
