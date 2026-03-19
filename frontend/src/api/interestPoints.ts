import client from './client'

export interface InterestPoint {
  id: number
  name: string
  description: string | null
  source: 'manual' | 'ai_discovered'
  weight: number
  category_id: number | null
  keywords: string[]
  is_active: boolean
  created_at: string
  updated_at: string
  category?: { id: number; name: string; color: string }
}

export interface CreateInterestPointRequest {
  name: string
  description?: string | null
  source?: 'manual' | 'ai_discovered'
  weight?: number
  category_id?: number | null
  keywords?: string[]
  is_active?: boolean
}

export interface InterestPointStats {
  items: Array<{
    name: string
    weight: number
    source: 'manual' | 'ai_discovered'
  }>
  total: number
  active: number
}

export const interestPointsApi = {
  list: (params?: { source?: string; is_active?: boolean; category_id?: number }) =>
    client.get<InterestPoint[]>('/interest-points', { params }),
  get: (id: number) =>
    client.get<InterestPoint>(`/interest-points/${id}`),
  create: (data: CreateInterestPointRequest) =>
    client.post<InterestPoint>('/interest-points', data),
  update: (id: number, data: Partial<CreateInterestPointRequest>) =>
    client.put<InterestPoint>(`/interest-points/${id}`, data),
  delete: (id: number) =>
    client.delete(`/interest-points/${id}`),
  activate: (id: number) =>
    client.post<InterestPoint>(`/interest-points/${id}/activate`),
  deactivate: (id: number) =>
    client.post<InterestPoint>(`/interest-points/${id}/deactivate`),
  discover: () =>
    client.post<InterestPoint[]>('/interest-points/discover'),
  stats: () =>
    client.get<InterestPointStats>('/interest-points/stats'),
}
