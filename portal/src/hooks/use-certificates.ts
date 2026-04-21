import { create } from 'zustand';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import type {
  CertParty,
  Certificate,
  CertStep,
  APICertificate,
  CertificateListResponse,
  AvailableCOI,
} from '@/types';

// ─── Zustand store for multi-step form state ───

interface CertificateState {
  certParties: CertParty[];
  certPolicy: string;
  certAddOpen: boolean;
  certEditIndex: number | null;
  currentStep: CertStep;
  setCurrentStep: (step: CertStep) => void;
  setCertPolicy: (policy: string) => void;
  setCertParties: (parties: CertParty[]) => void;
  addParty: (party: CertParty) => void;
  updateParty: (index: number, party: CertParty) => void;
  removeParty: (index: number) => void;
  setCertAddOpen: (open: boolean) => void;
  setCertEditIndex: (index: number | null) => void;
}

export const useCertificateStore = create<CertificateState>((set) => ({
  certParties: [],
  certPolicy: '',
  certAddOpen: false,
  certEditIndex: null,
  currentStep: 'landing',
  setCurrentStep: (step) => set({ currentStep: step }),
  setCertPolicy: (policy) => set({ certPolicy: policy }),
  setCertParties: (parties) => set({ certParties: parties }),
  addParty: (party) =>
    set((s) => ({ certParties: [...s.certParties, party] })),
  updateParty: (index, party) =>
    set((s) => {
      const parties = [...s.certParties];
      parties[index] = party;
      return { certParties: parties };
    }),
  removeParty: (index) =>
    set((s) => ({
      certParties: s.certParties.filter((_, i) => i !== index),
    })),
  setCertAddOpen: (open) => set({ certAddOpen: open }),
  setCertEditIndex: (index) => set({ certEditIndex: index }),
}));

// ─── TanStack Query hooks ───

export function useCertificates(search?: string, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['certificates', search, page, pageSize],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      params.set('page', String(page));
      params.set('page_size', String(pageSize));
      const qs = params.toString();
      const data = await apiFetch<CertificateListResponse>(
        `/api/v1/certificates/custom${qs ? `?${qs}` : ''}`
      );
      return data;
    },
  });
}

export function useCertificateDetail(id: number | null) {
  return useQuery({
    queryKey: ['certificate', id],
    queryFn: async () => {
      const data = await apiFetch<APICertificate>(
        `/api/v1/certificates/custom/${id}`
      );
      return data;
    },
    enabled: id !== null,
  });
}

export function useAvailableCOIs() {
  return useQuery({
    queryKey: ['available-cois'],
    queryFn: async () => {
      const data = await apiFetch<AvailableCOI[]>(
        '/api/v1/certificates/available-cois'
      );
      return data;
    },
  });
}

interface CreateCertificatePayload {
  coi_number: string;
  holder_name: string;
  holder_second_line?: string;
  holder_street_address: string;
  holder_suite?: string;
  holder_city: string;
  holder_state: string;
  holder_zip: string;
  is_additional_insured?: boolean;
  endorsements?: string[];
  service_location_job?: string;
  service_location_address?: string;
  service_you_provide_job?: string;
  service_you_provide_service?: string;
}

export function useCreateCertificate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateCertificatePayload) => {
      const data = await apiFetch<APICertificate>(
        '/api/v1/certificates/custom',
        { method: 'POST', body: payload }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] });
      queryClient.invalidateQueries({ queryKey: ['available-cois'] });
    },
  });
}

export function useRevokeCertificate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (certificateId: number) => {
      const data = await apiFetch<APICertificate>(
        `/api/v1/certificates/custom/${certificateId}`,
        { method: 'DELETE' }
      );
      return data;
    },
    onSuccess: (_data, certificateId) => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] });
      queryClient.invalidateQueries({ queryKey: ['certificate', certificateId] });
    },
  });
}

// ─── Consolidated COI ───

export interface ConsolidatedCOIPolicy {
  policy_number: string;
  coverage_type: string;
  coverage_display: string;
  carrier: string | { insurer_a: string; insurer_b: string };
  is_brokered: boolean;
  limits: Record<string, unknown>;
  premium: string;
  effective_date: string;
  expiration_date: string;
}

export interface ConsolidatedCOIGroup {
  coi_number: string;
  effective_date: string;
  expiration_date: string;
  policies: ConsolidatedCOIPolicy[];
}

export interface ConsolidatedCOIData {
  organization_id: number;
  coi_groups: ConsolidatedCOIGroup[];
  total_policies: number;
  total_coi_groups: number;
}

export function useConsolidatedCOI() {
  return useMutation({
    mutationFn: async () => {
      const data = await apiFetch<ConsolidatedCOIData>(
        '/api/v1/certificates/consolidated'
      );
      return data;
    },
  });
}

export function useDownloadCertificate() {
  return useMutation({
    mutationFn: async (certificateId: number) => {
      const data = await apiFetch<{ url: string; filename: string }>(
        `/api/v1/certificates/custom/${certificateId}/download`
      );
      return data;
    },
  });
}
