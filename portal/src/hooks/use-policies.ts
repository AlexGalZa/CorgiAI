import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import type { APIPolicy } from '@/types';

export function usePolicies() {
  return useQuery({
    queryKey: ['policies'],
    queryFn: async () => {
      const data = await apiFetch<APIPolicy[]>('/api/v1/policies/me');
      return data ?? [];
    },
  });
}

/** Returns a map of policy_number → APIPolicy for quick lookup */
export function usePoliciesMap() {
  const { data } = usePolicies();
  if (!data) return {};
  const map: Record<string, APIPolicy> = {};
  for (const p of data) {
    map[p.policy_number] = p;
  }
  return map;
}

/** Computed KPIs from policies */
export function usePolicyKPIs() {
  const { data: policies, isLoading } = usePolicies();

  const activePolicies = policies?.filter((p) => p.status === 'active') ?? [];
  const activeCount = activePolicies.length;

  const totalCoverage = activePolicies.reduce(
    (sum, p) => sum + (p.aggregate_limit || 0),
    0
  );

  const nextRenewal = activePolicies
    .map((p) => p.expiration_date)
    .filter(Boolean)
    .sort()[0] ?? null;

  return {
    activeCount,
    totalCoverage,
    nextRenewal,
    isLoading,
  };
}

export function usePolicyDetail(policyNumber: string | null) {
  return useQuery({
    queryKey: ['policy', policyNumber],
    queryFn: async () => {
      const data = await apiFetch<{ url: string; filename: string }>(
        `/api/v1/policies/${policyNumber}/coi`
      );
      return data;
    },
    enabled: !!policyNumber,
  });
}

export function useCoverageRecommendations() {
  return useQuery({
    queryKey: ['policies', 'recommendations'],
    queryFn: async () => {
      const data = await apiFetch<string[]>('/api/v1/policies/recommendations');
      return data ?? [];
    },
  });
}
