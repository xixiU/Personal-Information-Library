import client from './client'

export interface Task {
  id: number
  type: string
  source_id: number
  url: string | null
  priority: number
  payload: Record<string, any> | null
  status: string
  parent_task_id: number | null
  retry_count: number
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export const tasksApi = {
  list: (params?: { status?: string; type?: string; source_id?: number }) =>
    client.get<Task[]>('/tasks', { params }),
  get: (id: number) => client.get<Task>(`/tasks/${id}`),
  cancel: (id: number) => client.post(`/tasks/${id}/cancel`),
  retry: (id: number) => client.post<Task>(`/tasks/${id}/retry`)
}

