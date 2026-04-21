import { useAuthStore } from '@/stores/use-auth-store';
import { useOrgStore } from '@/stores/use-org-store';

// NEXT_PUBLIC_API_URL is the server origin for local dev
// (e.g. "http://localhost:8000"). In prod we serve the portal behind
// the same origin as the API, so leave it empty and API_BASE becomes a
// relative-path stub. Callers include the /api/v1 prefix in endpoints.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

// ─── Types ───

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
    public errors?: Record<string, string[]>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions<TBody = unknown> {
  method?: string;
  body?: TBody;
  params?: Record<string, string>;
  headers?: Record<string, string>;
}

// ─── Token refresh singleton ───

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const { tokens, updateTokens, logout } = useAuthStore.getState();
    if (!tokens?.refresh_token) {
      logout();
      return null;
    }

    try {
      const res = await fetch(`${API_BASE}/api/v1/users/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
      });

      if (!res.ok) {
        logout();
        return null;
      }

      const newTokens = await res.json();
      updateTokens(newTokens);
      return newTokens.access_token as string;
    } catch {
      logout();
      return null;
    }
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

// ─── Internal helpers ───

function buildUrl(endpoint: string, params?: Record<string, string>): string {
  const raw = `${API_BASE}${endpoint}`;
  // NEXT_PUBLIC_API_URL is a relative path in prod (e.g. "/api"), so raw
  // is relative and new URL(raw) throws. Give it the current origin as a
  // base when one is available. SSR has no window, so fall back to a
  // dummy base and strip it back off before returning.
  const base =
    typeof window !== 'undefined' ? window.location.origin : 'http://ssr.local';
  const url = new URL(raw, base);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.append(key, value);
    }
  }
  if (raw.startsWith('/')) {
    return `${url.pathname}${url.search}${url.hash}`;
  }
  return url.toString();
}

function buildHeaders(opts: {
  body?: unknown;
  headers?: Record<string, string>;
  accessToken?: string;
}): Record<string, string> {
  const { body, headers = {}, accessToken } = opts;
  const isFormData = body instanceof FormData;
  const activeOrgId = useOrgStore.getState().activeOrgId;

  return {
    ...(!isFormData && { 'Content-Type': 'application/json' }),
    ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
    ...(activeOrgId && { 'X-Organization-Id': String(activeOrgId) }),
    ...headers,
  };
}

function getAccessToken(): string | null {
  return useAuthStore.getState().tokens?.access_token ?? null;
}

// ─── Public API (no auth) ───

export async function publicApi<TResponse, TBody = unknown>(
  endpoint: string,
  options: RequestOptions<TBody> = {}
): Promise<TResponse> {
  const { method = 'GET', body, params, headers } = options;
  const url = buildUrl(endpoint, params);

  try {
    const res = await fetch(url, {
      method,
      headers: buildHeaders({ body, headers }),
      ...(body ? { body: body instanceof FormData ? body : JSON.stringify(body) } : {}),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new ApiError(
        res.status,
        data.message || data.detail || 'Request failed',
        data.code,
        data.errors
      );
    }

    return data as TResponse;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(500, error instanceof Error ? error.message : 'Unexpected error');
  }
}

// ─── Authenticated API ───

export async function authApi<TResponse, TBody = unknown>(
  endpoint: string,
  options: RequestOptions<TBody> = {}
): Promise<TResponse> {
  const { method = 'GET', body, params, headers } = options;
  const url = buildUrl(endpoint, params);

  const makeRequest = (token?: string | null) =>
    fetch(url, {
      method,
      headers: buildHeaders({ body, headers, accessToken: token ?? undefined }),
      ...(body ? { body: body instanceof FormData ? body : JSON.stringify(body) } : {}),
    });

  try {
    let res = await makeRequest(getAccessToken());

    // 401 → try refresh once. If refresh fails, bounce to the portal's own
    // /login (not the static-pages /ops login). Portal auth is internal.
    if (res.status === 401) {
      const newToken = await refreshAccessToken();
      if (!newToken) {
        if (typeof window !== 'undefined') {
          const here = window.location.pathname + window.location.search;
          window.location.href = `/login?redirect=${encodeURIComponent(here)}`;
        }
        throw new ApiError(401, 'Session expired. Please sign in again.', 'unauthorized');
      }
      res = await makeRequest(newToken);
    }

    const data = await res.json();

    if (!res.ok) {
      throw new ApiError(
        res.status,
        data.message || data.detail || 'Request failed',
        data.code,
        data.errors
      );
    }

    // The backend wraps responses in { success, message, data } for authenticated endpoints
    if (data.success !== undefined && data.data !== undefined) {
      return data.data as TResponse;
    }

    return data as TResponse;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(500, error instanceof Error ? error.message : 'Unexpected error');
  }
}

// ─── Backwards-compatible wrapper (used by existing hooks) ───

export async function apiFetch<T>(path: string, options: { method?: string; body?: unknown; headers?: Record<string, string> } = {}): Promise<T> {
  return authApi<T>(path, options);
}

export async function apiFormFetch<T>(path: string, formData: FormData, method = 'POST'): Promise<T> {
  return authApi<T>(path, { method, body: formData });
}
