import { useState, useEffect } from 'react'
import { Table, Card, message, Tabs, Input, Space, DatePicker, Slider, Select } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { resultsApi, CrawlResult, RefinedResult } from '../api/results'
import dayjs, { Dayjs } from 'dayjs'

const { RangePicker } = DatePicker

export default function ResultDetail() {
  const [crawlResults, setCrawlResults] = useState<CrawlResult[]>([])
  const [refinedResults, setRefinedResults] = useState<RefinedResult[]>([])
  const [filteredCrawlResults, setFilteredCrawlResults] = useState<CrawlResult[]>([])
  const [filteredRefinedResults, setFilteredRefinedResults] = useState<RefinedResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const [scoreRange, setScoreRange] = useState<[number, number]>([0, 100])
  const [orderBy, setOrderBy] = useState<string>('created_at')
  const [order, setOrder] = useState<string>('desc')
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const sourceId = searchParams.get('source_id')

  const loadResults = async () => {
    setLoading(true)
    try {
      const params = sourceId ? { source_id: Number(sourceId) } : {}
      const refinedParams = {
        ...params,
        // 只有用户收窄默认区间时才传分数过滤，避免 min_score=0 把 NULL 记录全部过滤掉
        ...(scoreRange[0] > 0 && { min_score: scoreRange[0] }),
        ...(scoreRange[1] < 100 && { max_score: scoreRange[1] }),
        order_by: orderBy,
        order,
      }
      const [crawlRes, refinedRes] = await Promise.all([
        resultsApi.listCrawl(params),
        resultsApi.listRefined(refinedParams)
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
  }, [sourceId, scoreRange, orderBy, order])

  useEffect(() => {
    if (!searchText && !dateRange) {
      setFilteredCrawlResults(crawlResults)
      setFilteredRefinedResults(refinedResults)
    } else {
      let filteredCrawl = crawlResults
      let filteredRefined = refinedResults

      // 文本搜索
      if (searchText) {
        filteredCrawl = filteredCrawl.filter(
          (r) =>
            r.title?.toLowerCase().includes(searchText.toLowerCase()) ||
            r.content?.toLowerCase().includes(searchText.toLowerCase())
        )
        filteredRefined = filteredRefined.filter(
          (r) =>
            r.summary?.toLowerCase().includes(searchText.toLowerCase()) ||
            r.keywords?.some((k) => k.toLowerCase().includes(searchText.toLowerCase()))
        )
      }

      // 时间范围过滤
      if (dateRange && dateRange[0] && dateRange[1]) {
        const startDate = dateRange[0].startOf('day')
        const endDate = dateRange[1].endOf('day')

        filteredCrawl = filteredCrawl.filter((r) => {
          const resultDate = dayjs(r.created_at)
          return resultDate.isAfter(startDate) && resultDate.isBefore(endDate)
        })

        filteredRefined = filteredRefined.filter((r) => {
          const resultDate = dayjs(r.created_at)
          return resultDate.isAfter(startDate) && resultDate.isBefore(endDate)
        })
      }

      setFilteredCrawlResults(filteredCrawl)
      setFilteredRefinedResults(filteredRefined)
    }
  }, [searchText, dateRange, crawlResults, refinedResults])

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

  // 清理多余空白：合并连续空行为单个空行，去除行首尾空格
  const cleanContent = (content: string) =>
    content
      .split('\n')
      .map((line) => line.trimEnd())
      .join('\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim()

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
      title: '质量评分',
      dataIndex: 'quality_score',
      key: 'quality_score',
      width: 100,
      render: (score: number | null) => score != null ? score : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="搜索标题、内容、关键词"
          style={{ width: 300 }}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          prefix={<SearchOutlined />}
          allowClear
        />
        <RangePicker
          value={dateRange}
          onChange={setDateRange}
          placeholder={['开始时间', '结束时间']}
          style={{ width: 280 }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ whiteSpace: 'nowrap' }}>质量分数筛选：</span>
          <Slider
            range
            min={0}
            max={100}
            value={scoreRange}
            onChange={(val) => setScoreRange(val as [number, number])}
            style={{ width: 200 }}
          />
        </div>
        <Select
          value={orderBy === 'quality_score' ? `quality_score_${order}` : 'default'}
          onChange={(val) => {
            if (val === 'default') {
              setOrderBy('created_at')
              setOrder('desc')
            } else if (val === 'quality_score_desc') {
              setOrderBy('quality_score')
              setOrder('desc')
            } else {
              setOrderBy('quality_score')
              setOrder('asc')
            }
          }}
          style={{ width: 160 }}
          options={[
            { label: '默认（时间）', value: 'default' },
            { label: '质量分数↓', value: 'quality_score_desc' },
            { label: '质量分数↑', value: 'quality_score_asc' },
          ]}
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
                      <pre style={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        margin: 0,
                        fontFamily: 'inherit',
                        fontSize: '14px',
                        lineHeight: '1.6'
                      }}>
                        {record.content ? cleanContent(record.content) : '无内容'}
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
