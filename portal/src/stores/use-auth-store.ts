import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { useOrgStore } from './use-org-store';

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  company_name: string;
  is_impersonated: boolean;
  organizations: Array<{
    id: number;
    name: string;
    role: string;
    is_personal: boolean;
  }>;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface AuthState {
  user: User | null;
  tokens: Tokens | null;
  isAuthenticated: boolean;
  setAuth: (user: User, tokens: Tokens) => void;
  updateUser: (user: User) => void;
  updateTokens: (tokens: Tokens) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      tokens: null,
      isAuthenticated: false,

      setAuth: (user, tokens) => {
        // Set localStorage tokens + auth cookie first. A later failure in
        // the org-store sync (e.g. user.organizations undefined) must not
        // prevent the auth cookie from being written, otherwise the
        // middleware bounces the user back to /login right after register.
        if (typeof window !== 'undefined') {
          localStorage.setItem('corgi_access_token', tokens.access_token);
          localStorage.setItem('corgi_refresh_token', tokens.refresh_token);
          document.cookie = `corgi_auth=1; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
        }

        set({ user, tokens, isAuthenticated: true });

        // Sync org store. Tolerate a missing organizations array.
        const orgs = user.organizations ?? [];
        const orgStore = useOrgStore.getState();
        if (!orgStore.activeOrgId && orgs.length > 0) {
          const personal = orgs.find((o) => o.is_personal);
          orgStore.setActiveOrgId(personal?.id ?? orgs[0].id);
        }
      },

      updateUser: (user) => set({ user }),

      updateTokens: (tokens) => {
        if (typeof window !== 'undefined') {
          localStorage.setItem('corgi_access_token', tokens.access_token);
          localStorage.setItem('corgi_refresh_token', tokens.refresh_token);
        }
        set({ tokens });
      },

      logout: () => {
        useOrgStore.getState().clearActiveOrg();
        if (typeof window !== 'undefined') {
          localStorage.removeItem('corgi_access_token');
          localStorage.removeItem('corgi_refresh_token');
          document.cookie = 'corgi_auth=; path=/; max-age=0';
        }
        set({ user: null, tokens: null, isAuthenticated: false });
      },
    }),
    {
      name: 'corgi-auth',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
