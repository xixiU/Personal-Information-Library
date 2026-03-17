import client from './client'

export interface NotificationChannel {
  id: number
  name: string
  channel_type: 'webhook' | 'telegram' | 'feishu'
  config: Record<string, any>
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface CreateChannelRequest {
  name: string
  channel_type: 'webhook' | 'telegram' | 'feishu'
  config: Record<string, any>
  enabled?: boolean
}

export interface NotificationRule {
  id: number
  name: string
  category_id: number
  channel_id: number
  rule_type: 'new_content' | 'quality_threshold' | 'keyword_match'
  notify_mode: 'instant' | 'batch'
  conditions: Record<string, any>
  message_template: string | null
  enabled: boolean
  created_at: string
  updated_at: string
  category?: { id: number; name: string; color: string }
  channel?: { id: number; name: string; channel_type: string }
}

export interface CreateRuleRequest {
  name: string
  category_id: number
  channel_id: number
  rule_type: 'new_content' | 'quality_threshold' | 'keyword_match'
  notify_mode?: 'instant' | 'batch'
  conditions?: Record<string, any>
  message_template?: string | null
  enabled?: boolean
}

export const channelsApi = {
  list: () => client.get<NotificationChannel[]>('/notification-channels'),
  get: (id: number) => client.get<NotificationChannel>(`/notification-channels/${id}`),
  create: (data: CreateChannelRequest) => client.post<NotificationChannel>('/notification-channels', data),
  update: (id: number, data: Partial<CreateChannelRequest>) =>
    client.put<NotificationChannel>(`/notification-channels/${id}`, data),
  delete: (id: number) => client.delete(`/notification-channels/${id}`),
  test: (id: number) => client.post(`/notification-channels/${id}/test`),
}

export const rulesApi = {
  list: (params: { category_id: number }) =>
    client.get<NotificationRule[]>(`/categories/${params.category_id}/notification-rules`),
  create: (data: CreateRuleRequest) =>
    client.post<NotificationRule>(`/categories/${data.category_id}/notification-rules`, data),
  update: (categoryId: number, ruleId: number, data: Partial<CreateRuleRequest>) =>
    client.put<NotificationRule>(`/categories/${categoryId}/notification-rules/${ruleId}`, data),
  delete: (categoryId: number, ruleId: number) =>
    client.delete(`/categories/${categoryId}/notification-rules/${ruleId}`),
}
