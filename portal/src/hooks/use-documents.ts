import { useQuery, useMutation } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import type { APIDocumentsByCategory, APIDocument } from '@/types';

export function useDocuments() {
  return useQuery({
    queryKey: ['documents'],
    queryFn: async () => {
      const data = await apiFetch<APIDocumentsByCategory>(
        '/api/v1/users/documents'
      );
      return data;
    },
  });
}

/** Flatten all document categories into a single array */
export function useDocumentsFlat() {
  const { data, ...rest } = useDocuments();

  const flat: APIDocument[] = data
    ? [
        ...data.policies,
        ...data.certificates,
        ...data.endorsements,
        ...data.receipts,
        ...data.loss_runs,
      ]
    : [];

  return { data: flat, ...rest };
}

export function useDownloadDocument() {
  return useMutation({
    mutationFn: async (documentId: number) => {
      const data = await apiFetch<{ url: string; filename: string }>(
        `/api/v1/users/documents/${documentId}/download`
      );
      return data;
    },
  });
}
