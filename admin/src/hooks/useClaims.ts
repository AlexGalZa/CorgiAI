import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { PaginatedResponse } from '@/types'

export interface ClaimListItem {
  id: number
  claim_number: string
  policy: number
  user: number
  organization_name: string
  first_name: string
  last_name: string
  email: string
  description: string
  status: string
  loss_state: string
  paid_loss: string
  paid_lae: string
  case_reserve_loss: string
  case_reserve_lae: string
  total_incurred: string
  claim_report_date: string | null
  created_at: string
  updated_at: string
}

export interface ClaimFilters {
  page?: number
  status?: string
  policy?: number
  search?: string
  ordering?: string
}

export function useClaims(filters: ClaimFilters = {}) {
  return useQuery<PaginatedResponse<ClaimListItem>>({
    queryKey: ['claims', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.status) params.set('status', filters.status)
      if (filters.policy) params.set('policy', String(filters.policy))
      if (filters.search) params.set('search', filters.search)
      if (filters.ordering) params.set('ordering', filters.ordering)
      const { data } = await api.get(`/admin/claims?${params.toString()}`)
      return data
    },
  })
}

// ─── Update Claim Mutation ───────────────────────────────────────────────────

export function useUpdateClaim() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number
      payload: Partial<ClaimListItem>
    }) => {
      const { data } = await api.patch(`/admin/claims/${id}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claims'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    },
  })
}

// ─── Update Internal Document Mutation ───────────────────────────────────────

export interface InternalDocument {
  id: number
  claim: number
  claim_number: string
  document_type: string
  status: string
  reviewed_by: string
  notes: string
  created_at: string
  updated_at: string
}

export function useUpdateInternalDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number
      payload: Partial<InternalDocument>
    }) => {
      const { data } = await api.patch(`/admin/internal-documents/${id}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['internal-documents'] })
      queryClient.invalidateQueries({ queryKey: ['claims'] })
    },
  })
}
