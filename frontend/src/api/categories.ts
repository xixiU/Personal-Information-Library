import client from './client'

export interface Category {
  id: number
  name: string
  description: string | null
  color: string
  refine_prompt_system: string
  quality_criteria: string
  created_at: string
  updated_at: string
}

export interface CreateCategoryRequest {
  name: string
  description?: string | null
  color?: string
  refine_prompt_system: string
  quality_criteria: string
}

export const categoriesApi = {
  list: () => client.get<Category[]>('/categories'),
  get: (id: number) => client.get<Category>(`/categories/${id}`),
  create: (data: CreateCategoryRequest) => client.post<Category>('/categories', data),
  update: (id: number, data: Partial<CreateCategoryRequest>) =>
    client.put<Category>(`/categories/${id}`, data),
  delete: (id: number) => client.delete(`/categories/${id}`),
}
