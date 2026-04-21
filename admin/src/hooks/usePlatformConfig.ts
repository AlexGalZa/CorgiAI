import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

/**
 * Shape returned by GET /api/v1/config/options
 */
export interface PlatformConfigResponse {
  grouped: Record<string, Record<string, unknown>>
  options: Record<string, unknown>
}

export interface SelectOption {
  value: string
  label: string
}

/**
 * Fetch all platform config options.
 * Cached for 10 minutes — these rarely change mid-session.
 */
export function usePlatformConfig() {
  return useQuery<PlatformConfigResponse>({
    queryKey: ['platform-config'],
    queryFn: async () => {
      const { data } = await api.get('/config/options')
      return data
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000,
  })
}

/**
 * Helper: get a typed array of select options from config.
 * Falls back to the provided default if the key isn't loaded yet.
 */
export function useConfigOptions(
  key: string,
  fallback: SelectOption[] = [],
): SelectOption[] {
  const { data } = usePlatformConfig()
  if (!data?.options?.[key]) return fallback
  const raw = data.options[key]
  if (!Array.isArray(raw)) return fallback
  return raw.map((item: Record<string, unknown>) => ({
    value: String(item.value ?? ''),
    label: String(item.label ?? item.value ?? ''),
  }))
}

/**
 * Helper: get a single scalar config value.
 */
export function useConfigValue<T = unknown>(key: string, fallback: T): T {
  const { data } = usePlatformConfig()
  if (!data?.options?.[key]) return fallback
  return data.options[key] as T
}
