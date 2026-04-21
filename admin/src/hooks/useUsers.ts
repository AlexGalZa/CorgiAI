import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { User, PaginatedResponse } from '@/types'

export interface UserFilters {
  page?: number
  search?: string
  ordering?: string
  role?: string
}

export function useUsers(filters: UserFilters = {}) {
  return useQuery<PaginatedResponse<User>>({
    queryKey: ['users', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.search) params.set('search', filters.search)
      if (filters.ordering) params.set('ordering', filters.ordering)
      if (filters.role) params.set('role', filters.role)
      const { data } = await api.get(`/admin/users?${params.toString()}`)
      return data
    },
  })
}

export interface CreateUserPayload {
  email: string
  first_name: string
  last_name: string
  phone_number?: string
  company_name?: string
  role: string
  is_active: boolean
  password: string
}

export interface UpdateUserPayload {
  email?: string
  first_name?: string
  last_name?: string
  phone_number?: string
  company_name?: string
  role?: string
  is_active?: boolean
}

export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: CreateUserPayload) => {
      const { data } = await api.post('/admin/users', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateUserPayload }) => {
      const { data } = await api.patch(`/admin/users/${id}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
