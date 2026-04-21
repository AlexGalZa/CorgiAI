import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type {
  PipelineStatusCount,
  PremiumByCarrier,
  CoverageBreakdown,
  PolicyStats,
  ClaimsSummary,
  RequesterStat,
  PaymentSummary,
  ActionItems,
  MonthlyPremium,
  LossRatio,
} from '@/types'

export function usePipelineSummary() {
  return useQuery<PipelineStatusCount[]>({
    queryKey: ['analytics', 'pipeline-summary'],
    queryFn: async () => {
      const { data } = await api.get('/admin/analytics/pipeline')
      // Backend returns {statuses: [...], total: N}
      return data?.statuses ?? data ?? []
    },
  })
}

export function usePremiumByCarrier() {
  return useQuery<PremiumByCarrier[]>({
    queryKey: ['analytics', 'premium-by-carrier'],
    queryFn: async () => {
      const { data } = await api.get('/admin/analytics/premium-by-carrier')
      // Backend returns {carriers: [...]}
      const carriers = data?.carriers ?? data ?? []
      return carriers.map((c: Record<string, unknown>) => ({
        carrier: c.carrier as string,
        total_premium: Number(c.total_premium ?? 0),
        policy_count: c.policy_count as number,
      }))
    },
  })
}

export function useCoverageBreakdown() {
  return useQuery<CoverageBreakdown[]>({
    queryKey: ['analytics', 'coverage-breakdown'],
    queryFn: async () => {
      const { data } = await api.get('/admin/analytics/coverage-breakdown')
      // Backend returns {coverages: [{coverage_type, display_name, count}]}
      const coverages = data?.coverages ?? data ?? []
      return coverages.map((c: Record<string, unknown>) => ({
        coverage_type_display: (c.display_name ?? c.coverage_type_display ?? c.coverage_type) as string,
        count: c.count as number,
      }))
    },
  })
}

export function usePolicyStats() {
  return useQuery<PolicyStats>({
    queryKey: ['analytics', 'policy-stats'],
    queryFn: async () => {
      const { data } = await api.get('/admin/analytics/policy-stats')
      return {
        active_count: data?.active_count ?? 0,
        total_premium: Number(data?.total_premium ?? 0),
      }
    },
  })
}

export function useClaimsSummary() {
  return useQuery<ClaimsSummary>({
    queryKey: ['analytics', 'claims-summary'],
    queryFn: async () => {
      const { data } = await api.get('/admin/analytics/claims-summary')
      return {
        by_status: data?.by_status ?? [],
        total_case_reserve_loss: Number(data?.total_reserves ?? 0),
        total_case_reserve_lae: 0,
        total_paid_loss: Number(data?.total_paid ?? 0),
        total_paid_lae: 0,
        total_reserves: Number(data?.total_reserves ?? 0),
      }
    },
  })
}

export function useRequesterStats() {
  return useQuery<RequesterStat[]>({
    queryKey: ['analytics', 'requester-stats'],
    queryFn: async () => {
      // No dedicated admin endpoint yet — use brokered requests to compute
      // For now return from analytics if available
      const { data } = await api.get('/admin/analytics/pipeline')
      // This endpoint doesn't return requester stats directly;
      // we'll return an empty array until the backend adds this endpoint
      return (data?.requesters ?? []) as RequesterStat[]
    },
  })
}

export function usePaymentSummary() {
  return useQuery<PaymentSummary>({
    queryKey: ['analytics', 'payment-summary'],
    queryFn: async () => {
      // Use the payments list to compute summary
      // No dedicated admin endpoint, so we aggregate from the list
      const { data } = await api.get('/admin/payments', { params: { page_size: 1 } })
      // Return stub with zeros if no dedicated endpoint
      return {
        total_paid: 0,
        total_pending: 0,
        total_failed: 0,
        total_refunded: 0,
        paid_count: data?.count ?? 0,
        pending_count: 0,
        failed_count: 0,
      }
    },
  })
}

export function useActionItems() {
  return useQuery<ActionItems>({
    queryKey: ['analytics', 'action-items'],
    queryFn: async () => {
      const { data } = await api.get('/admin/analytics/action-items')
      // Backend returns {items: [...], total: N}
      const items = data?.items ?? []
      return {
        blocked_requests: items.filter((i: Record<string, unknown>) => i.type === 'blocker').length,
        unreviewed_documents: items.filter((i: Record<string, unknown>) => i.type === 'pending').length,
        expiring_policies_30d: items.filter((i: Record<string, unknown>) => i.type === 'expiring').length,
        pending_claims: items.filter((i: Record<string, unknown>) => i.type === 'pending').length,
      }
    },
  })
}

export function useMonthlyPremium() {
  return useQuery<MonthlyPremium[]>({
    queryKey: ['analytics', 'monthly-premium'],
    queryFn: async () => {
      const { data } = await api.get('/admin/analytics/monthly-premium')
      // Backend returns {data: [{month, premium}]}
      const points = data?.data ?? data ?? []
      return points.map((p: Record<string, unknown>) => ({
        month: p.month as string,
        premium: Number(p.premium ?? 0),
      }))
    },
  })
}

export function useLossRatio() {
  return useQuery<LossRatio>({
    queryKey: ['analytics', 'loss-ratio'],
    queryFn: async () => {
      const { data } = await api.get('/admin/analytics/loss-ratio')
      return {
        total_paid_losses: Number(data?.paid_losses ?? 0),
        total_paid_lae: 0,
        total_earned_premium: Number(data?.earned_premium ?? 0),
        loss_ratio: Number(data?.loss_ratio ?? 0),
      }
    },
  })
}
