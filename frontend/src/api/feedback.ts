import client from './client'

export interface UserFeedback {
  id: number
  refined_result_id: number
  action: 'like' | 'collect' | 'dislike' | 'comment'
  comment_text: string | null
  created_at: string
}

export interface FeedbackCreate {
  action: 'like' | 'collect' | 'dislike' | 'comment'
  comment_text?: string
}

export const feedbackApi = {
  submit: (refinedResultId: number, data: FeedbackCreate) =>
    client.post<UserFeedback>(`/results/refine/${refinedResultId}/feedback`, data),
  list: (refinedResultId: number) =>
    client.get<UserFeedback[]>(`/results/refine/${refinedResultId}/feedback`),
  delete: (feedbackId: number) =>
    client.delete(`/feedback/${feedbackId}`),
  stats: () =>
    client.get<Record<string, number>>('/feedback/stats'),
}
