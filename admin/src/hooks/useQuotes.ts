import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { PaginatedResponse, Quote, Policy } from '@/types'

export interface QuoteListItem {
  id: number
  quote_number: string
  company: number
  company_detail: { id: number; entity_legal_name: string }
  user: number
  organization: number | null
  status: string
  quote_amount: string
  quoted_at: string | null
  billing_frequency: string
  current_step: string
  created_at: string
  updated_at: string
}

export interface QuoteFilters {
  page?: number
  status?: string
  user?: number
  organization?: number
  search?: string
  ordering?: string
}

export function useQuotes(filters: QuoteFilters = {}) {
  return useQuery<PaginatedResponse<QuoteListItem>>({
    queryKey: ['quotes', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.status) params.set('status', filters.status)
      if (filters.user) params.set('user', String(filters.user))
      if (filters.organization) params.set('organization', String(filters.organization))
      if (filters.search) params.set('search', filters.search)
      if (filters.ordering) params.set('ordering', filters.ordering)
      const { data } = await api.get(`/admin/quotes?${params.toString()}`)
      return data
    },
  })
}

export function useQuote(id: string | undefined) {
  return useQuery<Quote>({
    queryKey: ['quote', id],
    queryFn: async () => {
      const { data } = await api.get(`/admin/quotes/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useQuotePolicies(quoteId: string | undefined) {
  return useQuery<PaginatedResponse<Policy>>({
    queryKey: ['quote-policies', quoteId],
    queryFn: async () => {
      const { data } = await api.get(`/admin/policies?quote=${quoteId}`)
      return data
    },
    enabled: !!quoteId,
  })
}

export function useQuoteBrokeredRequests(quoteId: string | undefined) {
  return useQuery<PaginatedResponse<Record<string, unknown>>>({
    queryKey: ['quote-brokered-requests', quoteId],
    queryFn: async () => {
      const { data } = await api.get(`/admin/brokered-requests?quote=${quoteId}`)
      return data
    },
    enabled: !!quoteId,
  })
}

// ─── Update Quote Mutation ───────────────────────────────────────────────────

export function useUpdateQuote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number
      payload: Partial<QuoteListItem>
    }) => {
      const { data } = await api.patch(`/admin/quotes/${id}`, payload)
      return data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
      queryClient.invalidateQueries({ queryKey: ['quote', String(variables.id)] })
    },
  })
}

// ─── Admin Actions ───────────────────────────────────────────────────────────

export function useApproveQuote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      send_email = true,
      effective_date,
    }: {
      id: number
      send_email?: boolean
      effective_date?: string
    }) => {
      const { data } = await api.post(`/admin/quotes/${id}/approve`, {
        send_email,
        effective_date,
      })
      return data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
      queryClient.invalidateQueries({ queryKey: ['quote', String(variables.id)] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    },
  })
}

export function useRecalculateQuote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      coverages,
      revenue,
      state,
    }: {
      id: number
      coverages?: string[]
      revenue?: number
      state?: string
    }) => {
      const { data } = await api.post(`/admin/quotes/${id}/recalculate`, {
        coverages,
        revenue,
        state,
      })
      return data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
      queryClient.invalidateQueries({ queryKey: ['quote', String(variables.id)] })
    },
  })
}

export function useDuplicateQuote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id }: { id: number }) => {
      const { data } = await api.post(`/admin/quotes/${id}/duplicate`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
    },
  })
}

export function useSimulateQuote() {
  return useMutation({
    mutationFn: async ({
      id,
      ...overrides
    }: {
      id: number
      coverages?: string[]
      coverage_data?: Record<string, unknown>
      limits_retentions?: Record<string, unknown>
      revenue?: number
      employee_count?: number
      state?: string
      business_description?: string
    }) => {
      const { data } = await api.post(`/admin/quotes/${id}/simulate`, overrides)
      return data
    },
  })
}
