import axios from 'axios'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'

/**
 * Base URL for the Django API.
 * VITE_API_URL should be the server origin (e.g. http://localhost:8000) for
 * local dev. In production we serve admin behind the same origin as the API,
 * so leave it empty and baseURL resolves to a relative /api/v1 path.
 * The /api/v1 prefix is appended automatically.
 */
const API_BASE = import.meta.env.VITE_API_URL ?? ''

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Error typing ────────────────────────────────────────────────────────────

export interface ApiError {
  success: false
  message: string
  data: unknown
}

export function isApiError(error: unknown): error is AxiosError<ApiError> {
  return axios.isAxiosError(error)
}

export function getErrorMessage(error: unknown): string {
  if (isApiError(error) && error.response?.data?.message) {
    return error.response.data.message
  }
  if (error instanceof Error) return error.message
  return 'An unexpected error occurred'
}

// ── Response unwrapping ─────────────────────────────────────────────────────
// All django-ninja endpoints return ApiResponseSchema: {success, message, data}.
// This interceptor unwraps so hooks receive the inner `data` directly.

api.interceptors.response.use(
  (response) => {
    const body = response.data
    if (
      body &&
      typeof body === 'object' &&
      'success' in body &&
      'data' in body
    ) {
      response.data = body.data
    }
    return response
  },
  // Error responses are handled by the 401 interceptor below
  (error) => Promise.reject(error),
)

// ── Auth interceptor ────────────────────────────────────────────────────────

let isRefreshing = false
let failedQueue: {
  resolve: (token: string) => void
  reject: (error: unknown) => void
}[] = []

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token!)
    }
  })
  failedQueue = []
}

// Public paths that don't need Authorization header
const PUBLIC_PATHS = [
  '/users/register',
  '/users/request-login-code',
  '/users/verify-login-code',
  '/users/refresh',
]

api.interceptors.request.use(
  (config) => {
    const isPublic = PUBLIC_PATHS.some((p) => config.url?.includes(p))
    if (!isPublic) {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Response interceptor: handle 401 with token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    if (error.response?.status !== 401) {
      return Promise.reject(error)
    }

    if (originalRequest._retry) {
      clearAuthAndRedirect()
      return Promise.reject(error)
    }

    // Don't try to refresh the refresh endpoint itself
    if (originalRequest.url?.includes('/users/refresh')) {
      clearAuthAndRedirect()
      return Promise.reject(error)
    }

    // Don't try to refresh login requests
    if (
      originalRequest.url?.includes('/users/verify-login-code') ||
      originalRequest.url?.includes('/users/request-login-code')
    ) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({
          resolve: (token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(api(originalRequest))
          },
          reject: (err: unknown) => {
            reject(err)
          },
        })
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    const refreshToken = localStorage.getItem('refresh_token')

    if (!refreshToken) {
      isRefreshing = false
      clearAuthAndRedirect()
      return Promise.reject(error)
    }

    try {
      // Call refresh endpoint directly with axios (not through `api` to avoid interceptors)
      const response = await axios.post(
        `${API_BASE}/api/v1/users/refresh`,
        { refresh_token: refreshToken },
      )

      const { access_token, refresh_token: newRefreshToken } = response.data

      // Update stored tokens
      localStorage.setItem('access_token', access_token)
      if (newRefreshToken) {
        localStorage.setItem('refresh_token', newRefreshToken)
      }

      // Update zustand persisted store
      try {
        const stored = localStorage.getItem('auth-storage')
        if (stored) {
          const parsed = JSON.parse(stored)
          if (parsed.state) {
            parsed.state.accessToken = access_token
            if (newRefreshToken) {
              parsed.state.refreshToken = newRefreshToken
            }
            localStorage.setItem('auth-storage', JSON.stringify(parsed))
          }
        }
      } catch {
        // Non-critical: store sync failed
      }

      processQueue(null, access_token)

      originalRequest.headers.Authorization = `Bearer ${access_token}`
      return api(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      clearAuthAndRedirect()
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)

function clearAuthAndRedirect() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')

  try {
    const stored = localStorage.getItem('auth-storage')
    if (stored) {
      const parsed = JSON.parse(stored)
      if (parsed.state) {
        parsed.state.user = null
        parsed.state.accessToken = null
        parsed.state.refreshToken = null
        parsed.state.isAuthenticated = false
        localStorage.setItem('auth-storage', JSON.stringify(parsed))
      }
    }
  } catch {
    // Non-critical
  }

  sessionStorage.setItem('session_expired', '1')

  if (!window.location.pathname.includes('/login')) {
    // Staff SPA is served under /ops/, so the login redirect must include
    // the prefix. Without it we'd bounce into the portal's /login which
    // belongs to customers.
    window.location.href = '/ops/login'
  }
}

export default api
