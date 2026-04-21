// Auth utilities — token storage via localStorage (client-side)
// Next.js App Router doesn't support httpOnly cookies from client components,
// so we use localStorage + middleware reads from a non-httpOnly cookie for SSR checks.

const ACCESS_TOKEN_KEY = 'corgi_access_token';
const REFRESH_TOKEN_KEY = 'corgi_refresh_token';

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export function getTokens(): Tokens | null {
  if (typeof window === 'undefined') return null;
  const access = localStorage.getItem(ACCESS_TOKEN_KEY);
  const refresh = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!access || !refresh) return null;
  return { access_token: access, refresh_token: refresh, token_type: 'Bearer' };
}

export function setTokens(tokens: Tokens): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  // Also set a simple cookie for middleware to read (not httpOnly since it's client-set)
  document.cookie = `corgi_auth=1; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
}

export function clearTokens(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  document.cookie = 'corgi_auth=; path=/; max-age=0';
}

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

export async function refreshTokens(): Promise<Tokens | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.corginsurance.com';

  try {
    const res = await fetch(`${API_URL}/api/v1/users/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });

    if (!res.ok) {
      clearTokens();
      return null;
    }

    const tokens: Tokens = await res.json();
    setTokens(tokens);
    return tokens;
  } catch {
    clearTokens();
    return null;
  }
}
