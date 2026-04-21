import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import type { APIOrgDetail, APIOrgInvite } from '@/types';

export function useOrganization() {
  return useQuery({
    queryKey: ['organization'],
    queryFn: async () => {
      const data = await apiFetch<APIOrgDetail>('/api/v1/organizations/me');
      return data;
    },
  });
}

export function useUpdateOrganization() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { name?: string; phone?: string; billing_email?: string; website?: string }) => {
      const data = await apiFetch<APIOrgDetail>(
        '/api/v1/organizations/me',
        { method: 'PATCH', body: payload }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization'] });
    },
  });
}

export function useCreateInvite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: {
      default_role?: string;
      max_uses?: number | null;
      expires_at?: string | null;
      email?: string | null;
    }) => {
      const data = await apiFetch<APIOrgInvite>(
        '/api/v1/organizations/invites',
        { method: 'POST', body: payload }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization'] });
    },
  });
}

export function useRevokeInvite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (inviteId: number) => {
      await apiFetch<null>(
        `/api/v1/organizations/invites/${inviteId}`,
        { method: 'DELETE' }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization'] });
    },
  });
}

export function useUpdateMemberRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ userId, role }: { userId: number; role: string }) => {
      const data = await apiFetch<APIOrgDetail>(
        `/api/v1/organizations/members/${userId}`,
        { method: 'PATCH', body: { role } }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization'] });
    },
  });
}

export function useRemoveMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId: number) => {
      await apiFetch<APIOrgDetail>(
        `/api/v1/organizations/members/${userId}`,
        { method: 'DELETE' }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization'] });
    },
  });
}

export function useLeaveOrganization() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await apiFetch<null>('/api/v1/organizations/leave', {
        method: 'POST',
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization'] });
    },
  });
}
