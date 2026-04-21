import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { PaginatedResponse } from '@/types'

export interface PolicyListItem {
  id: number
  policy_number: string
  quote: number | null
  coverage_type: string
  carrier: string
  is_brokered: boolean
  premium: string
  monthly_premium: string
  effective_date: string | null
  expiration_date: string | null
  status: string
  insured_legal_name: string
  principal_state: string
  transaction_count: number
  created_at: string
  updated_at: string
}

export interface PolicyFilters {
  page?: number
  status?: string
  coverage_type?: string
  carrier?: string
  is_brokered?: boolean
  effective_date_after?: string
  effective_date_before?: string
  search?: string
  ordering?: string
}

export function usePolicies(filters: PolicyFilters = {}) {
  return useQuery<PaginatedResponse<PolicyListItem>>({
    queryKey: ['policies', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.status) params.set('status', filters.status)
      if (filters.coverage_type) params.set('coverage_type', filters.coverage_type)
      if (filters.carrier) params.set('carrier', filters.carrier)
      if (filters.is_brokered !== undefined) params.set('is_brokered', String(filters.is_brokered))
      if (filters.effective_date_after) params.set('effective_date_after', filters.effective_date_after)
      if (filters.effective_date_before) params.set('effective_date_before', filters.effective_date_before)
      if (filters.search) params.set('search', filters.search)
      if (filters.ordering) params.set('ordering', filters.ordering)
      const { data } = await api.get(`/admin/policies?${params.toString()}`)
      return data
    },
  })
}

// ─── Update Policy Mutation ──────────────────────────────────────────────────

export function useUpdatePolicy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number
      payload: Partial<PolicyListItem>
    }) => {
      const { data } = await api.patch(`/admin/policies/${id}`, payload)
      return data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      queryClient.invalidateQueries({ queryKey: ['policy', String(variables.id)] })
    },
  })
}

// ─── Admin Actions ───────────────────────────────────────────────────────────

export function useEndorsePolicy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      action,
      reason,
      new_limits,
      new_premium,
      new_coverage_type,
      new_effective_date,
      is_brokered,
      carrier,
    }: {
      id: number
      action: string
      reason: string
      new_limits?: Record<string, unknown>
      new_premium?: number
      new_coverage_type?: string
      new_effective_date?: string
      is_brokered?: boolean
      carrier?: string
    }) => {
      const { data } = await api.post(`/admin/policies/${id}/endorse`, {
        action,
        reason,
        new_limits,
        new_premium,
        new_coverage_type,
        new_effective_date,
        is_brokered,
        carrier,
      })
      return data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      queryClient.invalidateQueries({ queryKey: ['policy', String(variables.id)] })
      queryClient.invalidateQueries({ queryKey: ['policy-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    },
  })
}

export function useCancelPolicy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) => {
      const { data } = await api.post(`/admin/policies/${id}/cancel`, {
        reason,
      })
      return data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      queryClient.invalidateQueries({ queryKey: ['policy', String(variables.id)] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    },
  })
}

export function useReactivatePolicy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      reactivation_date,
    }: {
      id: number
      reactivation_date: string
    }) => {
      const { data } = await api.post(`/admin/policies/${id}/reactivate`, {
        reactivation_date,
      })
      return data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      queryClient.invalidateQueries({ queryKey: ['policy', String(variables.id)] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    },
  })
}
