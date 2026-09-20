import { useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { Card, Descriptions, Tag, Button, message, Spin, Space, Input, List, Popconfirm, Tooltip, Modal, Badge } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined, LikeOutlined, LikeFilled, StarOutlined, StarFilled, DislikeOutlined, DislikeFilled, EditOutlined, DeleteOutlined, InboxOutlined, HighlightOutlined, DownloadOutlined } from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { resultsApi, RefinedResult, CrawlResult } from '../api/results'
import client from '../api/client'
import { feedbackApi, UserFeedback } from '../api/feedback'
import { highlightsApi, Highlight, HighlightColor } from '../api/highlights'
import DOMPurify from 'dompurify'
import dayjs from 'dayjs'

// 高亮颜色 → 背景色映射
const COLOR_MAP: Record<HighlightColor, string> = {
  yellow: '#fff3a0',
  green: '#b7eb8f',
  blue: '#91d5ff',
  pink: '#ffadd2',
}
const COLOR_OPTIONS: { key: HighlightColor; label: string }[] = [
  { key: 'yellow', label: '黄' },
  { key: 'green', label: '绿' },
  { key: 'blue', label: '蓝' },
  { key: 'pink', label: '粉' },
]

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
  const [reRefining, setReRefining] = useState(false)
  const [archiving, setArchiving] = useState(false)

  // 高亮笔记状态
  const [highlights, setHighlights] = useState<Highlight[]>([])
  const summaryRef = useRef<HTMLDivElement>(null)
  // 选中文本后弹出的工具条
  const [toolbar, setToolbar] = useState<{ x: number; y: number; text: string } | null>(null)
  // 新建高亮：选颜色后弹批注输入框
  const [createModal, setCreateModal] = useState<{ text: string; color: HighlightColor } | null>(null)
  const [createNote, setCreateNote] = useState('')
  // 编辑已有高亮
  const [editModal, setEditModal] = useState<Highlight | null>(null)
  const [editNote, setEditNote] = useState('')
  const [editColor, setEditColor] = useState<HighlightColor>('yellow')
  const [highlightSaving, setHighlightSaving] = useState(false)

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

  const loadHighlights = useCallback(async () => {
    if (!refinedId) return
    try {
      const res = await highlightsApi.listByResult(refinedId)
      setHighlights(res.data)
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

        // 打开详情自动标记已读（契约 §2）
        if (!refinedRes.data.is_read) {
          try {
            await resultsApi.markRead(Number(id), true)
            setRefined((prev) => (prev ? { ...prev, is_read: true } : prev))
          } catch {
            // 标记失败不影响阅读
          }
        }
      } catch {
        message.error('加载详情失败')
      } finally {
        setLoading(false)
      }
    }

    loadDetail()
    loadFeedbacks()
    loadHighlights()
  }, [id, loadFeedbacks, loadHighlights])

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

  const handleReRefine = async () => {
    if (!refined?.crawl_result_id) return
    setReRefining(true)
    try {
      await client.post(`/refine/${refined.crawl_result_id}/re-refine`)
      message.success('已提交重新精炼任务')
    } catch {
      message.error('重新精炼失败')
    } finally {
      setReRefining(false)
    }
  }

  // 归档/取消归档
  const handleToggleArchive = async () => {
    if (!refined) return
    setArchiving(true)
    try {
      const next = !refined.is_archived
      await resultsApi.archive(refined.id, next)
      setRefined({ ...refined, is_archived: next })
      message.success(next ? '已归档' : '已取消归档')
    } catch {
      message.error('操作失败')
    } finally {
      setArchiving(false)
    }
  }

  // ===== 高亮笔记 =====

  // 选中摘要文本后弹出颜色工具条
  const handleSummaryMouseUp = () => {
    const selection = window.getSelection()
    const text = selection?.toString().trim()
    if (!text || !selection || selection.rangeCount === 0) {
      setToolbar(null)
      return
    }
    // 选区必须落在摘要容器内
    if (summaryRef.current && !summaryRef.current.contains(selection.anchorNode)) {
      setToolbar(null)
      return
    }
    const rect = selection.getRangeAt(0).getBoundingClientRect()
    setToolbar({ x: rect.left + rect.width / 2, y: rect.top - 8, text })
  }

  // 点击工具条颜色 → 打开批注输入框
  const handlePickColor = (color: HighlightColor) => {
    if (!toolbar) return
    setCreateModal({ text: toolbar.text, color })
    setCreateNote('')
    setToolbar(null)
    window.getSelection()?.removeAllRanges()
  }

  // 确认创建高亮
  const handleCreateHighlight = async () => {
    if (!createModal || !refinedId) return
    setHighlightSaving(true)
    try {
      // position 前端暂不计算，传 null（契约允许可选）
      await highlightsApi.create({
        refined_result_id: refinedId,
        highlight_text: createModal.text,
        note: createNote.trim() || undefined,
        color: createModal.color,
      })
      await loadHighlights()
      setCreateModal(null)
      message.success('已添加高亮')
    } catch {
      message.error('添加高亮失败')
    } finally {
      setHighlightSaving(false)
    }
  }

  // 打开编辑高亮 Modal
  const openEditHighlight = (h: Highlight) => {
    setEditModal(h)
    setEditNote(h.note || '')
    setEditColor(h.color)
  }

  // 保存高亮编辑
  const handleUpdateHighlight = async () => {
    if (!editModal) return
    setHighlightSaving(true)
    try {
      // 批注清空时传 null（不传空字符串），与后端"不传=null"语义一致
      await highlightsApi.update(editModal.id, { note: editNote.trim() || null, color: editColor })
      await loadHighlights()
      setEditModal(null)
      message.success('已更新')
    } catch {
      message.error('更新失败')
    } finally {
      setHighlightSaving(false)
    }
  }

  // 删除高亮
  const handleDeleteHighlight = async () => {
    if (!editModal) return
    setHighlightSaving(true)
    try {
      await highlightsApi.delete(editModal.id)
      await loadHighlights()
      setEditModal(null)
      message.success('已删除高亮')
    } catch {
      message.error('删除失败')
    } finally {
      setHighlightSaving(false)
    }
  }

  // 导出所有高亮为 Markdown 文件（契约 §1，返回 text/markdown blob）
  const handleExportHighlights = async () => {
    try {
      const res = await highlightsApi.export('markdown')
      const blob = new Blob([res.data as BlobPart], { type: 'text/markdown;charset=utf-8' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `我的高亮笔记_${dayjs().format('YYYYMMDD_HHmmss')}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      message.success('高亮笔记已导出')
    } catch {
      message.error('导出失败')
    }
  }

  // 将 summary 按 highlight_text 匹配渲染为高亮片段
  // 简单方案：按每个高亮文本在原文中做首次匹配，切分为普通文本 + <mark> 片段
  const renderSummaryWithHighlights = (summary: string) => {
    if (highlights.length === 0) return summary

    // 记录每个匹配区间 [start, end, highlight]，按出现位置排序，跳过重叠
    type Seg = { start: number; end: number; h: Highlight }
    const segs: Seg[] = []
    highlights.forEach((h) => {
      if (!h.highlight_text) return
      const idx = summary.indexOf(h.highlight_text)
      if (idx >= 0) segs.push({ start: idx, end: idx + h.highlight_text.length, h })
    })
    segs.sort((a, b) => a.start - b.start)

    const nodes: ReactNode[] = []
    let cursor = 0
    segs.forEach((seg, i) => {
      if (seg.start < cursor) return // 与前一段重叠，跳过
      if (seg.start > cursor) nodes.push(summary.slice(cursor, seg.start))
      nodes.push(
        <Tooltip key={`h-${seg.h.id}-${i}`} title={seg.h.note || '（无批注）'}>
          <mark
            style={{ backgroundColor: COLOR_MAP[seg.h.color] || COLOR_MAP.yellow, cursor: 'pointer', padding: '0 1px' }}
            onClick={() => openEditHighlight(seg.h)}
          >
            {summary.slice(seg.start, seg.end)}
          </mark>
        </Tooltip>
      )
      cursor = seg.end
    })
    if (cursor < summary.length) nodes.push(summary.slice(cursor))
    return nodes
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
      <Space style={{ marginBottom: 16 }} wrap>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate(-1)}
        >
          返回
        </Button>
        <Button
          icon={<ReloadOutlined />}
          onClick={handleReRefine}
          loading={reRefining}
          disabled={!refined.crawl_result_id}
        >
          重新精炼
        </Button>
        <Tooltip title="归档后不再出现在默认列表">
          <Button
            icon={<InboxOutlined />}
            onClick={handleToggleArchive}
            loading={archiving}
            type={refined.is_archived ? 'primary' : 'default'}
          >
            {refined.is_archived ? '取消归档' : '归档'}
          </Button>
        </Tooltip>
        <Badge count={highlights.length} showZero={false} color="#faad14">
          <Button icon={<HighlightOutlined />}>
            {highlights.length} 个高亮
          </Button>
        </Badge>
        <Tooltip title="导出全部高亮笔记为 Markdown">
          <Button icon={<DownloadOutlined />} onClick={handleExportHighlights}>
            导出高亮
          </Button>
        </Tooltip>
      </Space>

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

      <Card title="摘要" style={{ marginBottom: 16 }} extra={<span style={{ color: '#999', fontSize: 12 }}>选中文本可添加高亮</span>}>
        <div
          ref={summaryRef}
          onMouseUp={handleSummaryMouseUp}
          style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}
        >
          {refined.summary ? renderSummaryWithHighlights(refined.summary) : '无摘要'}
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

          <Card title="正文内容" style={{ marginBottom: 16 }}>
            {crawl.content ? (
              <div
                className="rich-content"
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(crawl.content, { ADD_TAGS: ['iframe', 'audio'], ADD_ATTR: ['allowfullscreen', 'frameborder', 'scrolling', 'controls', 'src'] }) }}
              />
            ) : (
              <div>无内容</div>
            )}
          </Card>
        </>
      )}

      {/* 反馈按钮组 */}
      <Card title="反馈">
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

      {/* 选中文本后的颜色工具条（fixed 定位在选区上方） */}
      {toolbar && (
        <div
          style={{
            position: 'fixed',
            left: toolbar.x,
            top: toolbar.y,
            transform: 'translate(-50%, -100%)',
            zIndex: 1050,
            background: '#fff',
            borderRadius: 6,
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            padding: 4,
            display: 'flex',
            gap: 4,
          }}
          // 阻止 mousedown 清空选区
          onMouseDown={(e) => e.preventDefault()}
        >
          {COLOR_OPTIONS.map((c) => (
            <Tooltip key={c.key} title={c.label}>
              <span
                onClick={() => handlePickColor(c.key)}
                style={{
                  display: 'inline-block',
                  width: 20,
                  height: 20,
                  borderRadius: '50%',
                  backgroundColor: COLOR_MAP[c.key],
                  cursor: 'pointer',
                  border: '1px solid #d9d9d9',
                }}
              />
            </Tooltip>
          ))}
        </div>
      )}

      {/* 新建高亮：填写批注 */}
      <Modal
        title="添加批注"
        open={!!createModal}
        onCancel={() => setCreateModal(null)}
        onOk={handleCreateHighlight}
        confirmLoading={highlightSaving}
        okText="保存"
        cancelText="取消"
      >
        {createModal && (
          <>
            <mark style={{ backgroundColor: COLOR_MAP[createModal.color], padding: '2px 4px' }}>
              {createModal.text}
            </mark>
            <Input.TextArea
              value={createNote}
              onChange={(e) => setCreateNote(e.target.value)}
              placeholder="输入批注内容（可选）..."
              autoSize={{ minRows: 3, maxRows: 6 }}
              style={{ marginTop: 12 }}
            />
          </>
        )}
      </Modal>

      {/* 编辑已有高亮：改批注 / 改颜色 / 删除 */}
      <Modal
        title="编辑高亮"
        open={!!editModal}
        onCancel={() => setEditModal(null)}
        okText="保存"
        cancelText="取消"
        confirmLoading={highlightSaving}
        onOk={handleUpdateHighlight}
        footer={[
          <Popconfirm
            key="delete"
            title="确定删除此高亮？"
            onConfirm={handleDeleteHighlight}
          >
            <Button danger icon={<DeleteOutlined />} loading={highlightSaving}>
              删除
            </Button>
          </Popconfirm>,
          <Button key="cancel" onClick={() => setEditModal(null)}>
            取消
          </Button>,
          <Button key="save" type="primary" loading={highlightSaving} onClick={handleUpdateHighlight}>
            保存
          </Button>,
        ]}
      >
        {editModal && (
          <>
            <mark style={{ backgroundColor: COLOR_MAP[editColor], padding: '2px 4px' }}>
              {editModal.highlight_text}
            </mark>
            <div style={{ margin: '12px 0 8px' }}>颜色：</div>
            <Space>
              {COLOR_OPTIONS.map((c) => (
                <span
                  key={c.key}
                  onClick={() => setEditColor(c.key)}
                  style={{
                    display: 'inline-block',
                    width: 24,
                    height: 24,
                    borderRadius: '50%',
                    backgroundColor: COLOR_MAP[c.key],
                    cursor: 'pointer',
                    border: editColor === c.key ? '2px solid #1890ff' : '1px solid #d9d9d9',
                  }}
                />
              ))}
            </Space>
            <Input.TextArea
              value={editNote}
              onChange={(e) => setEditNote(e.target.value)}
              placeholder="输入批注内容..."
              autoSize={{ minRows: 3, maxRows: 6 }}
              style={{ marginTop: 12 }}
            />
          </>
        )}
      </Modal>
    </div>
  )
}
