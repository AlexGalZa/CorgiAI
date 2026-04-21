import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { publicApi, authApi } from '@/lib/api';
import { useAuthStore, type User, type Tokens } from '@/stores/use-auth-store';
import { useOrgStore } from '@/stores/use-org-store';

// ─── Types ───

interface AuthResponse {
  user: User;
  tokens: Tokens;
}

interface OtpResponse {
  success: boolean;
  message: string;
}

interface SSOSessionResponse {
  sso_token: string;
  redirect_uri: string;
}

// ─── SSO redirect helper ───

async function handleSSORedirect(
  tokens: Tokens,
  redirectUri: string,
): Promise<boolean> {
  try {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.corginsurance.com';
    const res = await fetch(`${API_BASE}/api/v1/users/create-sso-session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${tokens.access_token}`,
      },
      body: JSON.stringify({ redirect_uri: redirectUri }),
    });

    if (!res.ok) return false;

    const data: SSOSessionResponse = await res.json();
    const separator = redirectUri.includes('?') ? '&' : '?';
    window.location.href = `${redirectUri}${separator}sso_token=${data.sso_token}`;
    return true;
  } catch {
    return false;
  }
}

// ─── useLogin — request OTP code ───

export function useLogin() {
  return useMutation({
    mutationFn: (email: string) =>
      publicApi<OtpResponse>('/api/v1/users/request-login-code', {
        method: 'POST',
        body: { email },
      }),
  });
}

// ─── usePasswordLogin — email + password for staff ───

export function usePasswordLogin() {
  const { setAuth } = useAuthStore.getState();
  const router = useRouter();
  const searchParams = useSearchParams();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      publicApi<AuthResponse>('/api/v1/users/login', {
        method: 'POST',
        body: { email, password },
      }),
    onSuccess: async (data) => {
      setAuth(data.user, data.tokens);

      const redirect = searchParams.get('redirect');
      if (redirect && redirect.startsWith('http')) {
        const redirected = await handleSSORedirect(data.tokens, redirect);
        if (redirected) return;
      }

      router.push(redirect || '/');
    },
  });
}

// ─── useVerifyCode — verify OTP and get tokens ───

export function useVerifyCode() {
  const { setAuth } = useAuthStore.getState();
  const router = useRouter();
  const searchParams = useSearchParams();

  return useMutation({
    mutationFn: ({ email, code }: { email: string; code: string }) =>
      publicApi<AuthResponse>('/api/v1/users/verify-login-code', {
        method: 'POST',
        body: { email, code },
      }),
    onSuccess: async (data) => {
      setAuth(data.user, data.tokens);

      const redirect = searchParams.get('redirect');
      if (redirect && redirect.startsWith('http')) {
        const redirected = await handleSSORedirect(data.tokens, redirect);
        if (redirected) return;
      }

      router.push(redirect || '/');
    },
  });
}

// ─── useRegister ───

export function useRegister() {
  const { setAuth } = useAuthStore.getState();
  const router = useRouter();
  const searchParams = useSearchParams();

  return useMutation({
    mutationFn: (data: {
      email: string;
      first_name: string;
      last_name: string;
      company_name?: string;
      phone_number?: string;
    }) =>
      publicApi<AuthResponse>('/api/v1/users/register', {
        method: 'POST',
        body: data,
      }),
    onSuccess: async (data) => {
      setAuth(data.user, data.tokens);

      const redirect = searchParams.get('redirect');
      if (redirect && redirect.startsWith('http')) {
        const redirected = await handleSSORedirect(data.tokens, redirect);
        if (redirected) return;
      }

      router.push(redirect || '/');
    },
  });
}

// ─── useUser — fetch current user ───

export function useUser() {
  const { isAuthenticated } = useAuthStore();

  return useQuery({
    queryKey: ['user', 'me'],
    queryFn: () => authApi<User>('/api/v1/users/me'),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

// ─── useLogout ───

export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return () => {
    useAuthStore.getState().logout();
    useOrgStore.getState().clearActiveOrg();
    queryClient.clear();
    // Portal owns its own auth. Stay on the portal and land on its /login.
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    } else {
      router.push('/login');
    }
  };
}
