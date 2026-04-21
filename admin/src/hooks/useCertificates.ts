import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { PaginatedResponse } from '@/types'

export interface CertificateListItem {
  id: number
  user: number
  organization: number | null
  coi_number: string
  custom_coi_number: string
  holder_name: string
  holder_city: string
  holder_state: string
  is_additional_insured: boolean
  created_at: string
  updated_at: string
}

export interface CertificateFilters {
  page?: number
  user?: number
  organization?: number
  search?: string
  ordering?: string
}

export function useCertificates(filters: CertificateFilters = {}) {
  return useQuery<PaginatedResponse<CertificateListItem>>({
    queryKey: ['certificates', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.user) params.set('user', String(filters.user))
      if (filters.organization) params.set('organization', String(filters.organization))
      if (filters.search) params.set('search', filters.search)
      if (filters.ordering) params.set('ordering', filters.ordering)
      const { data } = await api.get(`/admin/certificates?${params.toString()}`)
      return data
    },
  })
}
