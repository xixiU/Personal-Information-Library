import client from './client'

export interface Plugin {
  id: number
  name: string
  display_name: string
  description: string | null
  plugin_class: string
  domain_pattern: string | null
  enabled: boolean
  created_at: string
  updated_at: string
}

export const pluginsApi = {
  list: (enabled?: boolean) => {
    const params = enabled !== undefined ? { enabled } : {}
    return client.get<Plugin[]>('/plugins', { params })
  },
  get: (id: number) => client.get<Plugin>(`/plugins/${id}`),
}
