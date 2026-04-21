import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { PaginatedResponse } from '@/types'

export interface OrganizationListItem {
  id: number
  name: string
  owner: number
  owner_detail?: { email: string; full_name: string } | null
  is_personal: boolean
  created_at: string
  updated_at: string
}

export interface OrganizationFilters {
  page?: number
  search?: string
  ordering?: string
}

export function useOrganizations(filters: OrganizationFilters = {}) {
  return useQuery<PaginatedResponse<OrganizationListItem>>({
    queryKey: ['organizations', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.search) params.set('search', filters.search)
      if (filters.ordering) params.set('ordering', filters.ordering)
      const { data } = await api.get(`/admin/organizations?${params.toString()}`)
      return data
    },
  })
}

export function useCreateOrganization() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { name: string; is_personal: boolean }) => {
      const { data } = await api.post('/admin/organizations', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
    },
  })
}

export function useUpdateOrganization() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: number; name: string; is_personal: boolean }) => {
      const { data } = await api.patch(`/admin/organizations/${id}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
    },
  })
}
