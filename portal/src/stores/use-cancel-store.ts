import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// ─── Cancel flow data shape ───

export type CancelReason =
  | ''
  | 'too_expensive'
  | 'not_using'
  | 'switching_carrier'
  | 'business_closed'
  | 'coverage_not_needed'
  | 'other';

export type CancelStep = 'confirm' | 'alternatives' | 'effective-date' | 'success';

export interface CancelFormData {
  policy_id: number | null;
  policy_number: string | null;
  reason: CancelReason;
  reason_text: string;
  effective_date: string; // YYYY-MM-DD
  acknowledged_alternatives: boolean;
}

// ─── Store ───

interface CancelState {
  formData: CancelFormData;
  completedSteps: CancelStep[];
  submitStatus: 'idle' | 'submitting' | 'success' | 'error';
  submitError: string | null;

  setPolicy: (policyId: number, policyNumber: string) => void;
  updateFormData: (partial: Partial<CancelFormData>) => void;
  markStepCompleted: (step: CancelStep) => void;
  setSubmitStatus: (status: 'idle' | 'submitting' | 'success' | 'error') => void;
  setSubmitError: (error: string | null) => void;
  reset: () => void;
}

const initialFormData: CancelFormData = {
  policy_id: null,
  policy_number: null,
  reason: '',
  reason_text: '',
  effective_date: '',
  acknowledged_alternatives: false,
};

export const useCancelStore = create<CancelState>()(
  persist(
    (set) => ({
      formData: initialFormData,
      completedSteps: [],
      submitStatus: 'idle',
      submitError: null,

      setPolicy: (policyId, policyNumber) =>
        set((state) => ({
          formData: { ...state.formData, policy_id: policyId, policy_number: policyNumber },
        })),

      updateFormData: (partial) =>
        set((state) => ({
          formData: { ...state.formData, ...partial },
        })),

      markStepCompleted: (step) =>
        set((state) => ({
          completedSteps: state.completedSteps.includes(step)
            ? state.completedSteps
            : [...state.completedSteps, step],
        })),

      setSubmitStatus: (status) => set({ submitStatus: status }),

      setSubmitError: (error) => set({ submitError: error }),

      reset: () =>
        set({
          formData: initialFormData,
          completedSteps: [],
          submitStatus: 'idle',
          submitError: null,
        }),
    }),
    {
      name: 'corgi-cancel',
      storage: createJSONStorage(() => {
        if (typeof window === 'undefined') {
          return { getItem: () => null, setItem: () => {}, removeItem: () => {} };
        }
        return sessionStorage;
      }),
    }
  )
);
