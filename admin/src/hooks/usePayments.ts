import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { Payment, PaginatedResponse } from '@/types'

export function usePayments(filters: { page?: number; status?: string; search?: string; ordering?: string } = {}) {
  return useQuery<PaginatedResponse<Payment>>({
    queryKey: ['payments', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.status) params.set('status', filters.status)
      if (filters.search) params.set('search', filters.search)
      if (filters.ordering) params.set('ordering', filters.ordering)
      const { data } = await api.get(`/admin/payments?${params.toString()}`)
      return data
    },
  })
}

// ─── Update Payment Mutation ─────────────────────────────────────────────────

export function useUpdatePayment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number
      payload: Partial<Payment>
    }) => {
      const { data } = await api.patch(`/admin/payments/${id}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] })
      queryClient.invalidateQueries({ queryKey: ['analytics', 'payment-summary'] })
    },
  })
}
