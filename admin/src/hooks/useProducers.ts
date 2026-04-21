import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { PaginatedResponse } from '@/types'

export interface ProducerListItem {
  id: number
  name: string
  producer_type: string
  email: string
  license_number: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProducerFilters {
  page?: number
  producer_type?: string
  is_active?: boolean
  search?: string
  ordering?: string
}

export function useProducers(filters: ProducerFilters = {}) {
  return useQuery<PaginatedResponse<ProducerListItem>>({
    queryKey: ['producers', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.producer_type) params.set('producer_type', filters.producer_type)
      if (filters.is_active !== undefined) params.set('is_active', String(filters.is_active))
      if (filters.search) params.set('search', filters.search)
      if (filters.ordering) params.set('ordering', filters.ordering)
      const { data } = await api.get(`/admin/producers?${params.toString()}`)
      return data
    },
  })
}

export interface CreateProducerPayload {
  name: string
  producer_type: string
  email: string
  license_number?: string
  is_active: boolean
}

export interface UpdateProducerPayload {
  name?: string
  producer_type?: string
  email?: string
  license_number?: string
  is_active?: boolean
}

export function useCreateProducer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: CreateProducerPayload) => {
      const { data } = await api.post('/admin/producers', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['producers'] })
    },
  })
}

export function useUpdateProducer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateProducerPayload }) => {
      const { data } = await api.patch(`/admin/producers/${id}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['producers'] })
    },
  })
}
