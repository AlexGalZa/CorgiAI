import { create } from 'zustand';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import type {
  APIQuoteListItem,
  APIQuoteDetail,
  QuoteStep,
  QuoteType,
} from '@/types';

// ─── Static coverage data ───

export const QUOTE_TYPES: QuoteType[] = [
  { id: 'tech_pro', name: 'Tech E&O', desc: 'Covers financial losses caused by failures of your tech product or services.' },
  { id: 'cyber', name: 'Cyber Liability', desc: 'Covers costs associated with data breaches, cyber attacks, and other incidents.' },
  { id: 'fiduciary', name: 'Fiduciary Liability', desc: 'Protects plan fiduciaries against claims of mismanagement of employee benefit plans.' },
  { id: 'gl', name: 'General Liability', desc: 'Protects from third-party claims of bodily injury, property damage, and advertising injury.' },
  { id: 'eo', name: 'Errors & Omissions', desc: 'Covers claims of negligent acts or failure to perform professional duties.' },
  { id: 'key_person', name: 'Key Person Insurance', desc: 'Compensates your business for losses if a key employee becomes unable to work.' },
  { id: 'hnoa', name: 'Hired & Non-Owned Auto', desc: 'Covers liability when employees use personal or rented vehicles for business.' },
];

export const AVAIL_COVERAGES = [
  { name: 'Tech E&O', desc: 'Covers financial losses caused by failures of your tech product or services. Required by most enterprise contracts.' },
  { name: 'General Liability', desc: 'Protects your business from third-party claims of bodily injury, property damage, and advertising injury.' },
  { name: 'Cyber Liability', desc: 'Covers costs associated with data breaches, cyber attacks, and other technology-related incidents.' },
  { name: "Workers' Compensation", desc: 'Covers medical costs and lost wages for employees injured on the job. Required by most states.' },
  { name: 'Commercial Property', desc: 'Protects your business property, equipment, and inventory from damage due to fire, theft, or natural disasters.' },
  { name: 'Business Interruption', desc: 'Covers lost income and operating expenses when your business is disrupted by a covered event.' },
];

// ─── Zustand store for quote flow UI state ───

interface QuotesState {
  currentStep: QuoteStep;
  selectedType: string | null;
  setCurrentStep: (step: QuoteStep) => void;
  setSelectedType: (type: string | null) => void;
}

export const useQuotesStore = create<QuotesState>((set) => ({
  currentStep: 'landing',
  selectedType: null,
  setCurrentStep: (step) => set({ currentStep: step }),
  setSelectedType: (type) => set({ selectedType: type }),
}));

// ─── TanStack Query hooks ───

export function useQuotes() {
  return useQuery({
    queryKey: ['quotes'],
    queryFn: async () => {
      const data = await apiFetch<APIQuoteListItem[]>('/api/v1/quotes/me');
      return data;
    },
  });
}

export function useQuoteDetail(quoteNumber: string | null) {
  return useQuery({
    queryKey: ['quote', quoteNumber],
    queryFn: async () => {
      const data = await apiFetch<APIQuoteDetail>(
        `/api/v1/quotes/${quoteNumber}`
      );
      return data;
    },
    enabled: !!quoteNumber,
  });
}
