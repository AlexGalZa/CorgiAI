import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Loader2, AlertTriangle } from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import logo from '@/../assets/full-logo.svg'

// Ops doesn't ship its own login UI. Unauthenticated users are bounced
// straight to the shared static-pages login; the same route comes back
// as the SSO callback with ?code= and completes the exchange.
const SSO_LOGIN_URL = import.meta.env.VITE_SSO_LOGIN_URL || ''

function normalizedSsoUrl(): string {
  if (!SSO_LOGIN_URL) return ''
  return SSO_LOGIN_URL.endsWith('/') ? SSO_LOGIN_URL : SSO_LOGIN_URL + '/'
}

// Trailing slash matches the redirect shape bulldog-law and other Corgi
// apps use, in case static-pages enforces an exact-match allow-list.
const CALLBACK_PATH = '/ops/login/'

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [error, setError] = useState<string | null>(null)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  // Already signed in → dashboard.
  useEffect(() => {
    if (isAuthenticated && !searchParams.get('code')) {
      navigate('/dashboard', { replace: true })
    }
  }, [isAuthenticated, navigate, searchParams])

  // Two paths:
  //   1. ?code=<code> on the URL → exchange with Corgi, store JWTs, go to
  //      dashboard.
  //   2. No code and not authenticated → immediately bounce to static-pages.
  useEffect(() => {
    const code = searchParams.get('code')

    if (!code) {
      if (isAuthenticated) return
      const ssoUrl = normalizedSsoUrl()
      if (!ssoUrl) {
        setError('SSO is not configured (VITE_SSO_LOGIN_URL missing).')
        return
      }
      const redirectUri = window.location.origin + CALLBACK_PATH
      const sep = ssoUrl.includes('?') ? '&' : '?'
      window.location.replace(`${ssoUrl}${sep}redirect=${encodeURIComponent(redirectUri)}`)
      return
    }

    ;(async () => {
      try {
        const res = await fetch('/api/v1/users/sso/exchange', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code,
            redirect_uri: window.location.origin + CALLBACK_PATH,
          }),
        })
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.message || data.detail || `SSO exchange failed (${res.status})`)
        }
        const data = await res.json()
        const tokens = data.tokens ?? data.data?.tokens
        const userData = data.user ?? data.data?.user
        const ssoPermissions: Array<{ key: string }> =
          data.sso?.permissions ?? data.data?.sso?.permissions ?? []
        if (!tokens?.access_token || !userData) {
          throw new Error('Corgi SSO response missing tokens or user')
        }
        if (userData.is_staff === false) {
          setError('Access denied. Staff account required.')
          return
        }
        localStorage.setItem('access_token', tokens.access_token)
        localStorage.setItem('refresh_token', tokens.refresh_token)
        useAuthStore.setState({
          user: {
            id: userData.id,
            email: userData.email,
            first_name: userData.first_name,
            last_name: userData.last_name,
            phone_number: userData.phone_number ?? '',
            company_name: userData.company_name ?? '',
            role: userData.role ?? 'ae',
            full_name: userData.full_name ?? `${userData.first_name} ${userData.last_name}`.trim(),
            is_staff: userData.is_staff ?? true,
            is_impersonated: userData.is_impersonated ?? false,
            permissions: ssoPermissions.map((p) => p.key),
            organizations: userData.organizations,
          },
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isAuthenticated: true,
        })
        navigate('/dashboard', { replace: true })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'SSO login failed')
      }
    })()
  }, [searchParams, isAuthenticated, navigate])

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f2f5f9] px-4">
      <div className="w-full max-w-md text-center">
        <img src={logo} alt="Corgi Insurance" className="mx-auto mb-6 h-10" />
        {error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-left text-sm text-red-700">
            <div className="mb-2 flex items-center gap-2 font-medium">
              <AlertTriangle className="h-4 w-4" />
              Sign-in failed
            </div>
            <p>{error}</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-[#092b58]">
            <Loader2 className="h-6 w-6 animate-spin" />
            <p className="text-sm text-[#6b7280]">Signing you in…</p>
          </div>
        )}
      </div>
    </div>
  )
}
