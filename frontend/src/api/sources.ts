import client from './client'

export interface Source {
  id: number
  name: string
  url: string
  source_type: string // 'single_page' | 'full_site' | 'rss'
  cron_expr: string | null
  category_id: number | null
  config: Record<string, any> | null
  status: string
  created_at: string
  updated_at: string
}

export interface CreateSourceRequest {
  name: string
  url: string
  source_type: string // 'single_page' | 'full_site' | 'rss'
  cron_expr?: string | null
  category_id?: number | null
  config?: Record<string, any> | null
}

export interface ConfigField {
  name: string
  type: 'number' | 'switch' | 'text' | 'textarea' | 'select'
  label: string
  default: any
  min?: number
  max?: number
  help?: string
  advanced?: boolean
  options?: Array<{ label: string; value: any }>
}

export interface ConfigSchema {
  source_type: string
  fields: ConfigField[]
}

export interface BatchImportRequest {
  import_type: 'opml' | 'url_list'
  data: string | string[] // opml: XML 字符串；url_list: URL 数组
  default_category_id?: number | null
  default_config?: Record<string, any> | null
  default_cron_expr?: string | null
}

export interface BatchImportResponse {
  success_count: number
  failed_count: number
  skipped_count: number
  details: Array<{
    name: string
    url: string
    status: 'success' | 'failed' | 'skipped'
    reason: string
  }>
}

export const sourcesApi = {
  list: () => client.get<Source[]>('/sources'),
  create: (data: CreateSourceRequest) => client.post<Source>('/sources', data),
  get: (id: number) => client.get<Source>(`/sources/${id}`),
  update: (id: number, data: Partial<CreateSourceRequest>) =>
    client.put<Source>(`/sources/${id}`, data),
  delete: (id: number) => client.delete(`/sources/${id}`),
  trigger: (id: number) => client.post(`/sources/${id}/trigger`),
  addSchedule: (id: number, cron_expr: string) =>
    client.post(`/sources/${id}/schedule`, { cron_expr }),
  removeSchedule: (id: number) => client.delete(`/sources/${id}/schedule`),
  getSchedule: (id: number) => client.get(`/sources/${id}/schedule`),
  getConfigSchema: (source_type: string) =>
    client.get<ConfigSchema>(`/sources/config-schema?source_type=${source_type}`),
  batchImport: (data: BatchImportRequest) =>
    client.post<BatchImportResponse>('/sources/batch-import', data),
}

