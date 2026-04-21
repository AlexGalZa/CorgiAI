/**
 * Quote API hooks using TanStack Query + the portal's authApi client.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/lib/api';
import type { StepId } from '@/lib/quote-flow';

// ─── Types ───

export interface DraftQuoteResponse {
  quote_number: string;
  status: string;
  completed_steps: string[];
  current_step: string;
}

export interface QuoteFormDataResponse {
  quote_number: string;
  status: string;
  completed_steps: string[];
  current_step: string;
  form_data: Record<string, unknown>;
  rating_result?: RatingResult;
  available_coverages?: string[];
  custom_products?: CustomProduct[];
  promo_code?: string | null;
  discount_percentage?: number | null;
}

export interface RatingResult {
  total_annual_premium: number;
  total_monthly_premium: number;
  coverages: Record<string, CoverageRating>;
}

export interface CoverageRating {
  annual_premium: number;
  monthly_premium: number;
  per_occurrence_limit: number;
  aggregate_limit: number;
  retention: number;
}

export interface CustomProduct {
  id: string;
  name: string;
  price: number;
  monthly_price: number;
}

export type BillingFrequency = 'annual' | 'monthly';

// ─── Queries ───

export function useQuote(quoteNumber: string | null) {
  return useQuery({
    queryKey: ['quote', quoteNumber],
    queryFn: () => authApi<QuoteFormDataResponse>(`/api/v1/quotes/${quoteNumber}/form-data`),
    enabled: !!quoteNumber,
  });
}

export function useQuoteRating(quoteNumber: string | null) {
  return useQuery({
    queryKey: ['quote-rating', quoteNumber],
    queryFn: () => authApi<{ rating_result: RatingResult }>(`/api/v1/quotes/${quoteNumber}`),
    enabled: !!quoteNumber,
  });
}

export function useUserQuotes() {
  return useQuery({
    queryKey: ['user-quotes'],
    queryFn: () => authApi<Array<{ id: number; quote_number: string; status: string; created_at: string }>>('/api/v1/quotes/me'),
  });
}

// ─── Mutations ───

export function useCreateQuote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { coverages: string[]; selected_package?: string }) =>
      authApi<DraftQuoteResponse>('/api/v1/quotes/draft', {
        method: 'POST',
        body: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-quotes'] });
    },
  });
}

export function useSaveQuoteStep(quoteNumber: string | null) {
  return useMutation({
    mutationFn: (data: { step_id: StepId; data: Record<string, unknown>; next_step?: StepId }) =>
      authApi<{ quote_number: string; completed_steps: string[] }>(
        `/api/v1/quotes/${quoteNumber}/step`,
        { method: 'PATCH', body: data }
      ),
  });
}

export interface UploadedQuoteDocument {
  id: number;
  file_type: string;
  original_filename: string;
  file_size: number;
  s3_key: string;
}

export function useUploadQuoteDocument(quoteNumber: string | null) {
  return useMutation({
    mutationFn: async (data: { file: File; document_type?: string }) => {
      const formData = new FormData();
      formData.append('file', data.file);
      formData.append('document_type', data.document_type ?? 'claim-documents');
      return authApi<UploadedQuoteDocument>(
        `/api/v1/quotes/${quoteNumber}/documents`,
        { method: 'POST', body: formData }
      );
    },
  });
}

export function useSubmitQuote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { quoteNumber: string; formData: FormData }) =>
      authApi<{ quote_number: string; rating_result: RatingResult }>(
        `/api/v1/quotes/`,
        { method: 'POST', body: data.formData }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-quotes'] });
    },
  });
}

export function useCheckout() {
  return useMutation({
    mutationFn: (data: {
      quoteNumber: string;
      billing_frequency: BillingFrequency;
      effective_date?: string;
      coverages?: string[];
      success_url?: string;
      cancel_url?: string;
    }) =>
      authApi<{ checkout_url: string }>(
        `/api/v1/quotes/${data.quoteNumber}/checkout`,
        { method: 'POST', body: data }
      ),
  });
}
