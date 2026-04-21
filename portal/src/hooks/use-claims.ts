import { create } from 'zustand';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch, apiFormFetch } from '@/lib/api';
import type {
  APIClaimListItem,
  APIClaimDetail,
  ClaimsStep,
} from '@/types';

// ─── Zustand store for UI step state ───
interface ClaimsUIState {
  currentStep: ClaimsStep;
  setCurrentStep: (step: ClaimsStep) => void;
}

export const useClaimsStore = create<ClaimsUIState>((set) => ({
  currentStep: 'landing',
  setCurrentStep: (step) => set({ currentStep: step }),
}));

// ─── TanStack Query hooks ───

export function useClaims() {
  return useQuery({
    queryKey: ['claims'],
    queryFn: async () => {
      const data = await apiFetch<APIClaimListItem[]>('/api/v1/claims/me');
      return data;
    },
  });
}

export function useClaimDetail(claimNumber: string | null) {
  return useQuery({
    queryKey: ['claim', claimNumber],
    queryFn: async () => {
      const data = await apiFetch<APIClaimDetail>(
        `/api/v1/claims/${claimNumber}`
      );
      return data;
    },
    enabled: !!claimNumber,
  });
}

interface CreateClaimPayload {
  policy_id: number;
  organization_name: string;
  first_name: string;
  last_name: string;
  email: string;
  phone_number: string;
  description: string;
}

export function useCreateClaim() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      data,
      attachments,
    }: {
      data: CreateClaimPayload;
      attachments?: File[];
    }) => {
      const formData = new FormData();
      formData.append('data', JSON.stringify(data));
      if (attachments) {
        for (const file of attachments) {
          formData.append('attachments', file);
        }
      }
      const result = await apiFormFetch<APIClaimDetail>(
        '/api/v1/claims/',
        formData
      );
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claims'] });
    },
  });
}
