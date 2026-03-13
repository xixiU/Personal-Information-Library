import client from './client'

export interface Source {
  id: number
  name: string
  url: string
  crawl_mode: string
  cron_expr: string | null
  plugin_id: number | null
  config: Record<string, any> | null
  status: string
  created_at: string
  updated_at: string
}

export interface CreateSourceRequest {
  name: string
  url: string
  crawl_mode: string
  cron_expr?: string | null
  plugin_id?: number | null
  config?: Record<string, any> | null
}

export const sourcesApi = {
  list: () => client.get<Source[]>('/sources'),
  create: (data: CreateSourceRequest) => client.post<Source>('/sources', data),
  get: (id: number) => client.get<Source>(`/sources/${id}`),
  update: (id: number, data: Partial<CreateSourceRequest>) =>
    client.put<Source>(`/sources/${id}`, data),
  delete: (id: number) => client.delete(`/sources/${id}`),
  trigger: (id: number) => client.post(`/sources/${id}/trigger`)
}

