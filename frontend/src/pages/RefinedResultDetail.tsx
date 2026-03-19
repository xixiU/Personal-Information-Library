import { useState, useEffect, useCallback } from 'react'
import { Card, Descriptions, Tag, Button, message, Spin, Space, Input, List, Popconfirm } from 'antd'
import { ArrowLeftOutlined, LikeOutlined, LikeFilled, StarOutlined, StarFilled, DislikeOutlined, DislikeFilled, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { resultsApi, RefinedResult, CrawlResult } from '../api/results'
import { feedbackApi, UserFeedback } from '../api/feedback'
import dayjs from 'dayjs'

export default function RefinedResultDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [refined, setRefined] = useState<RefinedResult | null>(null)
  const [crawl, setCrawl] = useState<CrawlResult | null>(null)
  const [loading, setLoading] = useState(false)

  // 反馈状态
  const [feedbacks, setFeedbacks] = useState<UserFeedback[]>([])
  const [feedbackLoading, setFeedbackLoading] = useState(false)
  const [commentOpen, setCommentOpen] = useState(false)
  const [commentText, setCommentText] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const refinedId = id ? Number(id) : 0

  const loadFeedbacks = useCallback(async () => {
    if (!refinedId) return
    try {
      const res = await feedbackApi.list(refinedId)
      setFeedbacks(res.data)
    } catch {
      // 静默失败，不影响主流程
    }
  }, [refinedId])

  useEffect(() => {
    if (!id) return

    const loadDetail = async () => {
      setLoading(true)
      try {
        const refinedRes = await resultsApi.getRefined(Number(id))
        setRefined(refinedRes.data)

        if (refinedRes.data.crawl_result_id) {
          const crawlRes = await resultsApi.getCrawl(refinedRes.data.crawl_result_id)
          setCrawl(crawlRes.data)
        }
      } catch {
        message.error('加载详情失败')
      } finally {
        setLoading(false)
      }
    }

    loadDetail()
    loadFeedbacks()
  }, [id, loadFeedbacks])

  // 判断某个 action 是否已激活
  const hasAction = (action: string) => feedbacks.some(f => f.action === action)
  const getActionFeedback = (action: string) => feedbacks.find(f => f.action === action)
  const comments = feedbacks.filter(f => f.action === 'comment')

  const handleToggleFeedback = async (action: 'like' | 'collect' | 'dislike') => {
    if (!refinedId) return
    setFeedbackLoading(true)
    try {
      const existing = getActionFeedback(action)
      if (existing) {
        await feedbackApi.delete(existing.id)
      } else {
        await feedbackApi.submit(refinedId, { action })
      }
      await loadFeedbacks()
    } catch {
      message.error('操作失败')
    } finally {
      setFeedbackLoading(false)
    }
  }

  const handleSubmitComment = async () => {
    if (!refinedId || !commentText.trim()) return
    setSubmitting(true)
    try {
      await feedbackApi.submit(refinedId, { action: 'comment', comment_text: commentText.trim() })
      setCommentText('')
      await loadFeedbacks()
      message.success('批注已提交')
    } catch {
      message.error('提交批注失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteComment = async (feedbackId: number) => {
    try {
      await feedbackApi.delete(feedbackId)
      await loadFeedbacks()
      message.success('批注已删除')
    } catch {
      message.error('删除失败')
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!refined) {
    return (
      <div style={{ padding: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
          返回
        </Button>
        <div style={{ marginTop: 24, textAlign: 'center' }}>未找到精炼结果</div>
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate(-1)}
        style={{ marginBottom: 16 }}
      >
        返回
      </Button>

      <Card title="精炼结果详情" style={{ marginBottom: 16 }}>
        <Descriptions column={1} bordered>
          <Descriptions.Item label="ID">{refined.id}</Descriptions.Item>
          <Descriptions.Item label="分类">
            {refined.category || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="关键词">
            {refined.keywords && refined.keywords.length > 0 ? (
              <div>
                {refined.keywords.map((keyword, index) => (
                  <Tag key={index} color="blue">
                    {keyword}
                  </Tag>
                ))}
              </div>
            ) : (
              '-'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="质量评分">
            {refined.quality_score != null ? refined.quality_score : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {dayjs(refined.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 反馈按钮组 */}
      <Card title="反馈" style={{ marginBottom: 16 }}>
        <Space size="middle" style={{ marginBottom: commentOpen ? 16 : 0 }}>
          <Button
            icon={hasAction('like') ? <LikeFilled /> : <LikeOutlined />}
            type={hasAction('like') ? 'primary' : 'default'}
            onClick={() => handleToggleFeedback('like')}
            loading={feedbackLoading}
          >
            赞
          </Button>
          <Button
            icon={hasAction('collect') ? <StarFilled /> : <StarOutlined />}
            type={hasAction('collect') ? 'primary' : 'default'}
            onClick={() => handleToggleFeedback('collect')}
            loading={feedbackLoading}
            style={hasAction('collect') ? { background: '#faad14', borderColor: '#faad14' } : {}}
          >
            收藏
          </Button>
          <Button
            icon={hasAction('dislike') ? <DislikeFilled /> : <DislikeOutlined />}
            type={hasAction('dislike') ? 'primary' : 'default'}
            danger={hasAction('dislike')}
            onClick={() => handleToggleFeedback('dislike')}
            loading={feedbackLoading}
          >
            踩
          </Button>
          <Button
            icon={<EditOutlined />}
            type={commentOpen ? 'primary' : 'default'}
            onClick={() => setCommentOpen(!commentOpen)}
          >
            批注
          </Button>
        </Space>

        {commentOpen && (
          <div>
            <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
              <Input.TextArea
                value={commentText}
                onChange={e => setCommentText(e.target.value)}
                placeholder="输入批注内容..."
                autoSize={{ minRows: 2, maxRows: 4 }}
                style={{ flex: 1 }}
              />
            </Space.Compact>
            <Button
              type="primary"
              onClick={handleSubmitComment}
              loading={submitting}
              disabled={!commentText.trim()}
              style={{ marginBottom: 16 }}
            >
              提交批注
            </Button>

            {comments.length > 0 && (
              <List
                size="small"
                dataSource={comments}
                renderItem={item => (
                  <List.Item
                    actions={[
                      <Popconfirm
                        key="delete"
                        title="确定删除此批注？"
                        onConfirm={() => handleDeleteComment(item.id)}
                      >
                        <Button type="link" danger icon={<DeleteOutlined />} size="small">
                          删除
                        </Button>
                      </Popconfirm>
                    ]}
                  >
                    <List.Item.Meta
                      description={dayjs(item.created_at).format('YYYY-MM-DD HH:mm:ss')}
                      title={item.comment_text}
                    />
                  </List.Item>
                )}
              />
            )}
          </div>
        )}
      </Card>

      <Card title="摘要" style={{ marginBottom: 16 }}>
        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
          {refined.summary || '无摘要'}
        </div>
      </Card>

      {crawl && (
        <>
          <Card title="原始内容" style={{ marginBottom: 16 }}>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="标题">{crawl.title || '-'}</Descriptions.Item>
              <Descriptions.Item label="URL">
                {crawl.url ? (
                  <a href={crawl.url} target="_blank" rel="noopener noreferrer">
                    {crawl.url}
                  </a>
                ) : (
                  '-'
                )}
              </Descriptions.Item>
              <Descriptions.Item label="采集时间">
                {dayjs(crawl.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="正文内容">
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
              {crawl.content || '无内容'}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
