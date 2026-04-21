import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '@/lib/api'

export interface AuthUser {
  id: number
  email: string
  first_name: string
  last_name: string
  phone_number: string
  company_name: string
  role: string
  full_name: string
  is_staff: boolean
  is_superuser?: boolean
  is_impersonated?: boolean
  /** SSO permission keys, e.g. ["admin.manage", "admin.view", "bulldog.ai.use"] */
  permissions: string[]
  organizations?: Array<{
    id: number
    name: string
    role: string
    is_personal: boolean
  }>
}

interface AuthState {
  user: AuthUser | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean

  /** Request a one-time login code via email */
  requestLoginCode: (email: string) => Promise<void>
  /** Verify OTP code and log in (staff-only) */
  verifyLoginCode: (email: string, code: string) => Promise<void>
  /** Legacy password login (dev/seed accounts via /accounts/login/) */
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshAccessToken: () => Promise<void>
}

function mapUser(
  raw: Record<string, unknown>,
  permissionKeys: string[] = [],
): AuthUser {
  return {
    id: raw.id as number,
    email: raw.email as string,
    first_name: raw.first_name as string,
    last_name: raw.last_name as string,
    phone_number: (raw.phone_number as string) ?? '',
    company_name: (raw.company_name as string) ?? '',
    role: (raw.role as string) ?? 'ae',
    full_name:
      (raw.full_name as string) ??
      `${raw.first_name as string} ${raw.last_name as string}`.trim(),
    is_staff: (raw.is_staff as boolean) ?? false,
    is_impersonated: (raw.is_impersonated as boolean) ?? false,
    permissions: permissionKeys,
    organizations: raw.organizations as AuthUser['organizations'],
  }
}

function storeTokens(
  accessToken: string,
  refreshToken: string,
  set: (state: Partial<AuthState>) => void,
  user: AuthUser,
) {
  localStorage.setItem('access_token', accessToken)
  localStorage.setItem('refresh_token', refreshToken)
  set({
    user,
    accessToken,
    refreshToken,
    isAuthenticated: true,
  })
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      requestLoginCode: async (email: string) => {
        await api.post('/users/request-login-code', { email })
      },

      verifyLoginCode: async (email: string, code: string) => {
        const response = await api.post('/users/verify-login-code', {
          email,
          code,
        })

        // Response shape: { user: {...}, tokens: {access_token, refresh_token} }
        // Note: api.ts unwraps ApiResponseSchema, but auth endpoints return AuthResponse directly
        const data = response.data
        const userData = data.user ?? data
        const tokens = data.tokens ?? data

        const user = mapUser(userData)

        // Staff check: non-staff users cannot access the admin panel
        if (!user.is_staff) {
          throw new Error('Access denied. Staff account required.')
        }

        storeTokens(
          tokens.access_token,
          tokens.refresh_token,
          set,
          user,
        )
      },

      login: async (email: string, password: string) => {
        // Password login endpoint for staff accounts
        const response = await api.post('/users/login', {
          email,
          password,
        })

        const data = response.data
        // Handle both wrapped and direct response shapes
        const access = data.access_token ?? data.access ?? data.tokens?.access_token
        const refresh = data.refresh_token ?? data.refresh ?? data.tokens?.refresh_token
        const userData = data.user ?? data

        const user = mapUser(userData)

        if (!user.is_staff) {
          throw new Error('Access denied. Staff account required.')
        }

        storeTokens(access, refresh, set, user)
      },

      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get()
        if (!refreshToken) {
          throw new Error('No refresh token available')
        }

        const response = await api.post('/users/refresh', {
          refresh_token: refreshToken,
        })

        const data = response.data
        const newAccess = data.access_token
        const newRefresh = data.refresh_token

        localStorage.setItem('access_token', newAccess)
        if (newRefresh) {
          localStorage.setItem('refresh_token', newRefresh)
        }

        set({
          accessToken: newAccess,
          ...(newRefresh ? { refreshToken: newRefresh } : {}),
        })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        // permissions live on user, persisted above: no separate field needed
      }),
    },
  ),
)
