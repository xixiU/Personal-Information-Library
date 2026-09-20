import client from './client'

// 高亮颜色枚举（契约 §1）
export type HighlightColor = 'yellow' | 'green' | 'blue' | 'pink'

export interface Highlight {
  id: number
  refined_result_id: number
  highlight_text: string
  note: string | null
  position_start: number | null
  position_end: number | null
  color: HighlightColor
  created_at: string
  updated_at: string | null
}

export interface CreateHighlightRequest {
  refined_result_id: number
  highlight_text: string
  note?: string
  position_start?: number
  position_end?: number
  color?: HighlightColor
}

export interface UpdateHighlightRequest {
  // 清空批注时传 null（与后端"不传=null"语义一致），不传空字符串
  note?: string | null
  color?: HighlightColor
}

export const highlightsApi = {
  // 创建高亮
  create: (data: CreateHighlightRequest) =>
    client.post<Highlight>('/highlights', data),
  // 列出某个精炼结果的所有高亮（统一用 /refine 前缀）
  listByResult: (resultId: number) =>
    client.get<Highlight[]>(`/results/refine/${resultId}/highlights`),
  // 更新高亮（改批注/颜色）
  update: (id: number, data: UpdateHighlightRequest) =>
    client.put<Highlight>(`/highlights/${id}`, data),
  // 删除高亮
  delete: (id: number) =>
    client.delete(`/highlights/${id}`),
  // 导出所有高亮为 Markdown（返回 blob）
  export: (format: 'markdown' = 'markdown') =>
    client.get(`/highlights/export?format=${format}`, { responseType: 'blob' }),
}
