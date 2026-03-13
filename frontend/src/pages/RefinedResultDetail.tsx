import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Button, message, Spin } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { resultsApi, RefinedResult, CrawlResult } from '../api/results'
import dayjs from 'dayjs'

export default function RefinedResultDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [refined, setRefined] = useState<RefinedResult | null>(null)
  const [crawl, setCrawl] = useState<CrawlResult | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!id) return

    const loadDetail = async () => {
      setLoading(true)
      try {
        const refinedRes = await resultsApi.getRefined(Number(id))
        setRefined(refinedRes.data)

        // 加载对应的爬取结果
        if (refinedRes.data.crawl_result_id) {
          const crawlRes = await resultsApi.getCrawl(refinedRes.data.crawl_result_id)
          setCrawl(crawlRes.data)
        }
      } catch (error) {
        message.error('加载详情失败')
      } finally {
        setLoading(false)
      }
    }

    loadDetail()
  }, [id])

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
          <Descriptions.Item label="创建时间">
            {dayjs(refined.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
        </Descriptions>
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
