import { useState, useEffect } from 'react'
import { Table, Card, message, Tabs, Input, Space } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { resultsApi, CrawlResult, RefinedResult } from '../api/results'
import dayjs from 'dayjs'

export default function ResultDetail() {
  const [crawlResults, setCrawlResults] = useState<CrawlResult[]>([])
  const [refinedResults, setRefinedResults] = useState<RefinedResult[]>([])
  const [filteredCrawlResults, setFilteredCrawlResults] = useState<CrawlResult[]>([])
  const [filteredRefinedResults, setFilteredRefinedResults] = useState<RefinedResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const sourceId = searchParams.get('source_id')

  const loadResults = async () => {
    setLoading(true)
    try {
      const params = sourceId ? { source_id: Number(sourceId) } : {}
      const [crawlRes, refinedRes] = await Promise.all([
        resultsApi.listCrawl(params),
        resultsApi.listRefined(params)
      ])
      setCrawlResults(crawlRes.data)
      setRefinedResults(refinedRes.data)
      setFilteredCrawlResults(crawlRes.data)
      setFilteredRefinedResults(refinedRes.data)
    } catch (error) {
      message.error('加载结果失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadResults()
  }, [sourceId])

  useEffect(() => {
    if (!searchText) {
      setFilteredCrawlResults(crawlResults)
      setFilteredRefinedResults(refinedResults)
    } else {
      const filteredCrawl = crawlResults.filter(
        (r) =>
          r.title?.toLowerCase().includes(searchText.toLowerCase()) ||
          r.content?.toLowerCase().includes(searchText.toLowerCase())
      )
      const filteredRefined = refinedResults.filter(
        (r) =>
          r.summary?.toLowerCase().includes(searchText.toLowerCase()) ||
          r.keywords?.some((k) => k.toLowerCase().includes(searchText.toLowerCase()))
      )
      setFilteredCrawlResults(filteredCrawl)
      setFilteredRefinedResults(filteredRefined)
    }
  }, [searchText, crawlResults, refinedResults])

  const crawlColumns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '标题', dataIndex: 'title', key: 'title' },
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      render: (url: string | null) =>
        url ? (
          <a href={url} target="_blank" rel="noopener noreferrer">
            链接
          </a>
        ) : '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')
    }
  ]

  const refinedColumns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '摘要', dataIndex: 'summary', key: 'summary', ellipsis: true },
    {
      title: '关键词',
      dataIndex: 'keywords',
      key: 'keywords',
      render: (keywords: string[] | null) => keywords ? keywords.join(', ') : '-'
    },
    { title: '分类', dataIndex: 'category', key: 'category' },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索标题、内容、关键词"
          style={{ width: 300 }}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          prefix={<SearchOutlined />}
          allowClear
        />
      </Space>
      <Tabs
        items={[
          {
            key: 'crawl',
            label: '原始采集结果',
            children: (
              <Table
                columns={crawlColumns}
                dataSource={filteredCrawlResults}
                rowKey="id"
                loading={loading}
                expandable={{
                  expandedRowRender: (record) => (
                    <Card>
                      <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {record.content || '无内容'}
                      </pre>
                    </Card>
                  )
                }}
              />
            )
          },
          {
            key: 'refined',
            label: '精炼结果',
            children: (
              <Table
                columns={refinedColumns}
                dataSource={filteredRefinedResults}
                rowKey="id"
                loading={loading}
                onRow={(record) => ({
                  onClick: () => navigate(`/refined/${record.id}`),
                  style: { cursor: 'pointer' }
                })}
                expandable={{
                  expandedRowRender: (record) => (
                    <Card>
                      {record.summary && (
                        <div style={{ marginBottom: 16 }}>
                          <strong>摘要：</strong>
                          <p>{record.summary}</p>
                        </div>
                      )}
                      {record.keywords && (
                        <div style={{ marginBottom: 16 }}>
                          <strong>关键词：</strong>
                          <p>{record.keywords.join(', ')}</p>
                        </div>
                      )}
                      {record.category && (
                        <div>
                          <strong>分类：</strong>
                          <p>{record.category}</p>
                        </div>
                      )}
                    </Card>
                  )
                }}
              />
            )
          }
        ]}
      />
    </div>
  )
}
