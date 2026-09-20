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
  // 已读/归档维度（契约 §2）
  is_read: boolean
  is_archived: boolean
  read_at: string | null
  // 高亮数量（列表徽章用，后端若返回则显示；可选）
  highlight_count?: number
}

export const resultsApi = {
  listCrawl: (params?: { source_id?: number; skip?: number; limit?: number }) =>
    client.get<CrawlResult[]>('/results/crawl', { params }),
  getCrawl: (id: number) => client.get<CrawlResult>(`/results/crawl/${id}`),
  listRefined: (params?: { source_id?: number; skip?: number; limit?: number; min_score?: number; max_score?: number; order_by?: string; order?: string; is_read?: boolean; is_archived?: boolean }) =>
    client.get<RefinedResult[]>('/results/refine', { params }),
  getRefined: (id: number) => client.get<RefinedResult>(`/results/refine/${id}`),
  // 标记已读/未读（契约 §2，统一用 /refine 前缀）
  markRead: (id: number, is_read: boolean) =>
    client.post<RefinedResult>(`/results/refine/${id}/mark-read`, { is_read }),
  // 归档/取消归档（契约 §2，统一用 /refine 前缀）
  archive: (id: number, is_archived: boolean) =>
    client.post<RefinedResult>(`/results/refine/${id}/archive`, { is_archived })
}


