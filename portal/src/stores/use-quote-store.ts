import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { StepId, AllCoverageType, FormSection } from '@/lib/quote-flow';

// ─── Form data shape ───

export interface QuoteFormData {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone_number?: string;
  company_name?: string;
  coverages?: AllCoverageType[];
  company_info?: {
    business_address?: {
      street_address?: string;
      suite?: string;
      city?: string;
      state?: string;
      zip?: string;
    };
    organization_info?: {
      entity_legal_name?: string;
      dba_name?: string;
      naics_code?: string;
      naics_description?: string;
      organization_type?: string;
      organization_type_other?: string;
      is_for_profit?: boolean;
      federal_ein?: string;
      no_ein?: boolean;
      business_start_date?: string;
      estimated_payroll?: number;
    };
    financial_details?: {
      last_12_months_revenue?: number;
      projected_next_12_months_revenue?: number;
      full_time_employees?: number;
      part_time_employees?: number;
      financial_statements?: string[];
    };
    structure_operations?: {
      is_technology_company?: boolean;
      has_subsidiaries?: boolean;
      subsidiaries?: Array<{ name: string; jurisdiction: string }>;
      planned_acquisitions?: boolean;
      planned_acquisitions_details?: string;
      business_description?: string;
    };
  };
  // Coverage questionnaire answers stored by coverage slug
  coverage_answers?: Record<string, Record<string, unknown>>;
  claims_history?: {
    loss_history?: {
      has_past_claims?: boolean;
      claim_details?: string;
      claim_documents?: string[];
      has_known_circumstances?: boolean;
      known_circumstances_details?: string;
    };
    insurance_history?: {
      has_prior_coverage?: boolean;
      prior_coverage_details?: string;
      has_refused_insurance?: boolean;
      refused_insurance_details?: string;
    };
  };
  notices_signatures?: {
    agreed_to_terms?: boolean;
    applicant_name?: string;
  };
  limits_retentions?: Record<string, unknown>;
  effective_date?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  referrer_url?: string;
  landing_page_url?: string;
}

// ─── Store ───

interface QuoteState {
  quoteNumber: string | null;
  formData: QuoteFormData;
  completedSteps: StepId[];
  expandedSections: FormSection[];
  saveStatus: 'idle' | 'saving' | 'saved' | 'error';

  setQuoteNumber: (qn: string) => void;
  setFormData: (data: QuoteFormData) => void;
  updateFormData: (partial: Partial<QuoteFormData>) => void;
  setCompletedSteps: (steps: StepId[]) => void;
  markStepCompleted: (stepId: StepId) => void;
  expandSection: (section: FormSection) => void;
  setSaveStatus: (status: 'idle' | 'saving' | 'saved' | 'error') => void;
  reset: () => void;
}

const initialFormData: QuoteFormData = {};

export const useQuoteStore = create<QuoteState>()(
  persist(
    (set) => ({
      quoteNumber: null,
      formData: initialFormData,
      completedSteps: [],
      expandedSections: [],
      saveStatus: 'idle',

      setQuoteNumber: (qn) => set({ quoteNumber: qn }),

      setFormData: (data) => set({ formData: data }),

      updateFormData: (partial) =>
        set((state) => ({
          formData: deepMerge(state.formData, partial),
        })),

      setCompletedSteps: (steps) => set({ completedSteps: steps }),

      markStepCompleted: (stepId) =>
        set((state) => ({
          completedSteps: state.completedSteps.includes(stepId)
            ? state.completedSteps
            : [...state.completedSteps, stepId],
        })),

      expandSection: (section) =>
        set((state) => ({
          expandedSections: state.expandedSections.includes(section)
            ? state.expandedSections
            : [...state.expandedSections, section],
        })),

      setSaveStatus: (status) => set({ saveStatus: status }),

      reset: () =>
        set({
          quoteNumber: null,
          formData: initialFormData,
          completedSteps: [],
          expandedSections: [],
          saveStatus: 'idle',
        }),
    }),
    {
      name: 'corgi-quote',
      storage: createJSONStorage(() => {
        if (typeof window === 'undefined') {
          return { getItem: () => null, setItem: () => {}, removeItem: () => {} };
        }
        return sessionStorage;
      }),
    }
  )
);

// ─── Deep merge helper ───

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function deepMerge<T extends Record<string, any>>(target: T, source: Partial<T>): T {
  const result = { ...target };
  for (const key of Object.keys(source) as Array<keyof T>) {
    const sv = source[key];
    const tv = target[key];
    if (sv && typeof sv === 'object' && !Array.isArray(sv) && tv && typeof tv === 'object' && !Array.isArray(tv)) {
      (result as Record<string, unknown>)[key as string] = deepMerge(tv as Record<string, unknown>, sv as Record<string, unknown>);
    } else {
      (result as Record<string, unknown>)[key as string] = sv;
    }
  }
  return result;
}
