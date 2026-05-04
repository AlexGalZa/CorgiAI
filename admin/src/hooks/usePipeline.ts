import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export type PipelineNextAction =
  | 'send_followup'
  | 'send_expiry_warning'
  | 'review_underwriting'
  | 'awaiting_rating'
  | 'none'

export interface PipelineRow {
  quote_id: number
  quote_number: string
  company_name: string
  customer_email: string
  customer_name: string
  status: string
  premium: string | null
  billing_frequency: string
  days_since_update: number
  days_until_expiry: number | null
  next_action: PipelineNextAction
  closeability_score: number
  updated_at: string
  quoted_at: string | null
}

export interface PipelineList {
  items: PipelineRow[]
  total: number
}

export function usePipeline() {
  return useQuery<PipelineList>({
    queryKey: ['pipeline'],
    queryFn: async () => {
      const { data } = await api.get('/admin/pipeline')
      return data
    },
    refetchInterval: 60_000,
  })
}

export interface FollowUpResult {
  quote_number: string
  sent_to: string
  subject: string
}

export function useSendFollowUp() {
  const queryClient = useQueryClient()
  return useMutation<FollowUpResult, Error, { quote_id: number }>({
    mutationFn: async ({ quote_id }) => {
      const { data } = await api.post(`/admin/pipeline/${quote_id}/follow-up`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline'] })
    },
  })
}
