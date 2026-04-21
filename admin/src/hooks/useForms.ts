import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

// ── Types ───────────────────────────────────────────────────────────────────

export interface FormFieldOption {
  value: string
  label: string
}

export interface FormFieldValidation {
  min?: number
  max?: number
  min_length?: number
  max_length?: number
  pattern?: string
}

export interface FormFieldCondition {
  field_key: string
  operator: string
  value: unknown
}

export interface FormField {
  key: string
  label: string
  field_type: string
  required: boolean
  placeholder?: string
  help_text?: string
  default_value?: unknown
  options?: FormFieldOption[]
  validation?: FormFieldValidation
  width?: 'full' | 'half' | 'third'
  group?: string
  order: number
  conditions?: FormFieldCondition[]
}

export interface ConditionalCondition {
  field_key: string
  operator: string
  value: unknown
}

export interface ConditionalRule {
  target_field: string
  action: 'show' | 'hide'
  conditions: ConditionalCondition[]
  match: 'all' | 'any'
}

export interface FormDefinition {
  id: number
  name: string
  slug: string
  version: number
  description: string
  fields: FormField[]
  conditional_logic: { rules?: ConditionalRule[] } | null
  rating_field_mappings: Record<string, string> | null
  coverage_type: string | null
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface FormDefinitionInput {
  name: string
  slug: string
  version?: number
  description?: string
  fields: FormField[]
  conditional_logic?: { rules: ConditionalRule[] }
  rating_field_mappings?: Record<string, string>
  coverage_type?: string | null
  is_active?: boolean
}

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useForms() {
  return useQuery<FormDefinition[]>({
    queryKey: ['forms'],
    queryFn: async () => {
      const { data } = await api.get('/admin/forms')
      return data
    },
  })
}

export function useForm(id: number | null) {
  return useQuery<FormDefinition>({
    queryKey: ['forms', id],
    queryFn: async () => {
      const { data } = await api.get(`/admin/forms/${id}`)
      return data
    },
    enabled: id !== null,
  })
}

export function useCreateForm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (input: FormDefinitionInput) => {
      const { data } = await api.post('/admin/forms', input)
      return data as FormDefinition
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['forms'] }),
  })
}

export function useUpdateForm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...input }: FormDefinitionInput & { id: number }) => {
      const { data } = await api.put(`/admin/forms/${id}`, input)
      return data as FormDefinition
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['forms'] }),
  })
}

export function useDeleteForm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/admin/forms/${id}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['forms'] }),
  })
}

export function useDuplicateForm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.post(`/admin/forms/${id}/duplicate`)
      return data as FormDefinition
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['forms'] }),
  })
}
