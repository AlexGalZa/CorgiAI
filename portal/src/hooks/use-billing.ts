import { useQuery, useMutation } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import type { APIBillingInfo } from '@/types';

export function useBillingInfo() {
  return useQuery({
    queryKey: ['billing'],
    queryFn: async () => {
      const data = await apiFetch<APIBillingInfo>('/api/v1/policies/billing');
      return data;
    },
  });
}

export function useBillingPortal() {
  return useMutation({
    mutationFn: async () => {
      const data = await apiFetch<{ url: string }>(
        '/api/v1/policies/billing/portal',
        { method: 'POST' }
      );
      return data;
    },
  });
}
