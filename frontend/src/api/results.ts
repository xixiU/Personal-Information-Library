import client from './client'

export interface CrawlResult {
  id: number
  task_id: number
  source_id: number
  url: string
  title: string | null
  content: string | null
  meta_data: Record<string, any> | null
  created_at: string
}

export interface RefinedResult {
  id: number
  crawl_result_id: number
  summary: string | null
  keywords: string[] | null
  category: string | null
  quality_score: number | null
  meta_data: Record<string, any> | null
  created_at: string
}

export const resultsApi = {
  listCrawl: (params?: { source_id?: number; skip?: number; limit?: number }) =>
    client.get<CrawlResult[]>('/results/crawl', { params }),
  getCrawl: (id: number) => client.get<CrawlResult>(`/results/crawl/${id}`),
  listRefined: (params?: { source_id?: number; skip?: number; limit?: number; min_score?: number; max_score?: number; order_by?: string; order?: string }) =>
    client.get<RefinedResult[]>('/results/refine', { params }),
  getRefined: (id: number) => client.get<RefinedResult>(`/results/refine/${id}`)
}


