import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { BrokeredQuoteRequest, PaginatedResponse } from '@/types'

// ─── Filters ─────────────────────────────────────────────────────────────────

export interface BrokeredRequestFilters {
  page?: number
  page_size?: number
  status?: string
  carrier?: string
  coverage_type?: string
  search?: string
  ordering?: string
  has_blocker?: string
  blocker_type?: string
  created_after?: string
  created_before?: string
  requester?: string
}

// ─── List (paginated) ────────────────────────────────────────────────────────

export function useBrokeredRequests(filters: BrokeredRequestFilters = {}) {
  return useQuery<PaginatedResponse<BrokeredQuoteRequest>>({
    queryKey: ['brokered-requests', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.page_size) params.set('page_size', String(filters.page_size))
      if (filters.status) params.set('status', filters.status)
      if (filters.carrier) params.set('carrier', filters.carrier)
      if (filters.coverage_type)
        params.set('coverage_type', filters.coverage_type)
      if (filters.search) params.set('search', filters.search)
      if (filters.ordering) params.set('ordering', filters.ordering)
      if (filters.has_blocker) params.set('has_blocker', filters.has_blocker)
      if (filters.blocker_type) params.set('blocker_type', filters.blocker_type)
      if (filters.created_after) params.set('created_after', filters.created_after)
      if (filters.created_before) params.set('created_before', filters.created_before)
      if (filters.requester) params.set('requester', filters.requester)

      const { data } = await api.get(
        `/admin/brokered-requests?${params.toString()}`,
      )
      return data
    },
  })
}

// ─── Single ──────────────────────────────────────────────────────────────────

export function useBrokeredRequest(id: number | undefined) {
  return useQuery<BrokeredQuoteRequest>({
    queryKey: ['brokered-requests', id],
    queryFn: async () => {
      const { data } = await api.get(`/admin/brokered-requests/${id}`)
      return data
    },
    enabled: !!id,
  })
}

// ─── Create Mutation ─────────────────────────────────────────────────────────

export function useCreateBrokeredRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: Partial<BrokeredQuoteRequest>) => {
      const { data } = await api.post('/admin/brokered-requests', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brokered-requests'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    },
  })
}

// ─── Update Mutation ─────────────────────────────────────────────────────────

export function useUpdateBrokeredRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number
      payload: Partial<BrokeredQuoteRequest>
    }) => {
      const { data } = await api.patch(`/admin/brokered-requests/${id}`, payload)
      return data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['brokered-requests'] })
      queryClient.invalidateQueries({
        queryKey: ['brokered-requests', variables.id],
      })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    },
  })
}
