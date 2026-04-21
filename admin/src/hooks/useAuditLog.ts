import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { AuditEntry } from '@/types'

export interface AuditLogResponse {
  entries: AuditEntry[]
  total: number
  limit: number
  offset: number
}

function mapEntry(e: Record<string, unknown>): AuditEntry {
  return {
    id: e.id as number,
    user_email: (e.actor ?? e.user_email ?? '') as string,
    user_name: (e.actor ?? e.user_name ?? '') as string,
    action: e.action as string,
    entity_type: (e.content_type ?? e.entity_type ?? '') as string,
    entity_id: Number(e.object_id ?? e.entity_id ?? 0),
    entity_name: (e.entity_name ?? '') as string,
    field_changed: (e.field_changed ?? '') as string,
    old_value: (e.old_value ?? '') as string,
    new_value: (e.new_value ?? '') as string,
    timestamp: (e.timestamp ?? e.created_at ?? '') as string,
  }
}

export function useAuditLog(
  modelNameOrFilters?: string | { limit?: number; offset?: number; model_name?: string; object_id?: number | string },
  objectId?: number | string,
) {
  // Support both legacy signature (modelName, objectId) and new object signature
  const filters = typeof modelNameOrFilters === 'object' ? modelNameOrFilters : {
    model_name: modelNameOrFilters,
    object_id: objectId,
  }

  return useQuery({
    queryKey: ['audit-log', filters],
    queryFn: async (): Promise<AuditLogResponse> => {
      const params = new URLSearchParams()
      if (filters.model_name) params.set('model_name', filters.model_name)
      if (filters.object_id) params.set('object_id', String(filters.object_id))
      params.set('limit', String(filters.limit ?? 50))
      if (filters.offset) params.set('offset', String(filters.offset))
      const { data } = await api.get(`/admin/audit-log?${params}`)
      const entries = (data?.entries ?? data?.results ?? data ?? []).map(mapEntry)
      return {
        entries,
        total: data?.total ?? entries.length,
        limit: data?.limit ?? (filters.limit ?? 50),
        offset: data?.offset ?? (filters.offset ?? 0),
      }
    },
    enabled: !filters.model_name || !!filters.object_id,
    select: (data: AuditLogResponse) => data,
  })
}

export function useRecentActivity() {
  return useQuery<AuditEntry[]>({
    queryKey: ['analytics', 'recent-activity'],
    queryFn: async () => {
      const { data } = await api.get('/admin/audit-log?limit=10')
      const entries = data?.entries ?? data ?? []
      return entries.map((e: Record<string, unknown>) => ({
        id: e.id as number,
        user_email: (e.actor ?? e.user_email ?? '') as string,
        user_name: (e.actor ?? e.user_name ?? '') as string,
        action: e.action as string,
        entity_type: (e.content_type ?? e.entity_type ?? '') as string,
        entity_id: Number(e.object_id ?? e.entity_id ?? 0),
        entity_name: (e.entity_name ?? '') as string,
        field_changed: (e.field_changed ?? '') as string,
        old_value: (e.old_value ?? '') as string,
        new_value: (e.new_value ?? '') as string,
        timestamp: (e.timestamp ?? e.created_at ?? '') as string,
      }))
    },
  })
}
