import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, TrendingUp, Users, Target, CalendarX } from 'lucide-react'
import api from '@/lib/api'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import MetricCard from '@/components/ui/MetricCard'
import QueryError from '@/components/ui/QueryError'
import { formatCurrency } from '@/lib/formatters'

// ─── Types ───────────────────────────────────────────────────────────────────

interface SalesMetrics {
  close_rate: number | null
  no_show_rate: number | null
  total_deals: number
  deals_won: number
  deals_lost: number
  deals_open: number
  scheduled_meetings: number
  no_show_meetings: number
  total_won_amount: number
  currency: string
  start: string
  end: string
  owner_id: string | null
  product: string | null
  warnings: string[]
}

// ─── Hook ────────────────────────────────────────────────────────────────────

interface Filters {
  start: string
  end: string
  owner: string
  product: string
}

function useSalesMetrics(filters: Filters) {
  return useQuery<SalesMetrics>({
    queryKey: ['analytics', 'sales-metrics', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.start) params.set('start', filters.start)
      if (filters.end) params.set('end', filters.end)
      if (filters.owner) params.set('owner', filters.owner)
      if (filters.product) params.set('product', filters.product)
      const { data } = await api.get(
        `/analytics/sales-metrics?${params.toString()}`,
      )
      return data as SalesMetrics
    },
  })
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatPct(value: number | null): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(1)}%`
}

function defaultRange(): { start: string; end: string } {
  const today = new Date()
  const thirty = new Date()
  thirty.setDate(today.getDate() - 30)
  const iso = (d: Date) => d.toISOString().slice(0, 10)
  return { start: iso(thirty), end: iso(today) }
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function SalesMetricsPage() {
  const initial = useMemo(defaultRange, [])
  const [start, setStart] = useState(initial.start)
  const [end, setEnd] = useState(initial.end)
  const [owner, setOwner] = useState('')
  const [product, setProduct] = useState('')

  const filters: Filters = { start, end, owner, product }
  const metricsQ = useSalesMetrics(filters)

  const m = metricsQ.data
  const closeRatePct = m?.close_rate ?? null
  const noShowRatePct = m?.no_show_rate ?? null

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Analytics' }, { label: 'External Sales' }]} />
      <PageHeader
        title="External Sales Analytics"
        subtitle="Close rate and no-show rate sourced from HubSpot CRM. Read-only."
      />

      {/* ─── Filters ────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">Start</label>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">End</label>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">HubSpot Owner ID</label>
          <div className="relative">
            <Users className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              placeholder="e.g. 12345678"
              className="w-56 rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-3 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
            />
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">Product</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={product}
              onChange={(e) => setProduct(e.target.value)}
              placeholder="e.g. tech-eo"
              className="w-56 rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-3 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
            />
          </div>
        </div>
      </div>

      {/* ─── Error ──────────────────────────────────────────────────────── */}
      {metricsQ.isError && <QueryError onRetry={() => metricsQ.refetch()} />}

      {/* ─── Stat grid ──────────────────────────────────────────────────── */}
      {!metricsQ.isError && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Close Rate"
            value={formatPct(closeRatePct)}
            subtitle={
              m
                ? `${m.deals_won} won / ${m.deals_won + m.deals_lost} decided`
                : undefined
            }
            icon={Target}
            accent={
              closeRatePct != null && closeRatePct >= 0.4
                ? 'emerald'
                : closeRatePct != null && closeRatePct >= 0.2
                  ? 'amber'
                  : 'red'
            }
            progress={closeRatePct != null ? Math.round(closeRatePct * 100) : undefined}
            isLoading={metricsQ.isLoading}
          />
          <MetricCard
            title="No-Show Rate"
            value={formatPct(noShowRatePct)}
            subtitle={
              m && m.scheduled_meetings > 0
                ? `${m.no_show_meetings} of ${m.scheduled_meetings} meetings`
                : m && m.scheduled_meetings === 0
                  ? 'No meetings in range'
                  : undefined
            }
            icon={CalendarX}
            accent={
              noShowRatePct != null && noShowRatePct >= 0.2
                ? 'red'
                : noShowRatePct != null && noShowRatePct >= 0.1
                  ? 'amber'
                  : 'emerald'
            }
            progress={noShowRatePct != null ? Math.round(noShowRatePct * 100) : undefined}
            isLoading={metricsQ.isLoading}
          />
          <MetricCard
            title="Total Deals"
            value={m?.total_deals ?? 0}
            subtitle={
              m ? `${m.deals_open} open · ${m.deals_lost} lost` : undefined
            }
            icon={TrendingUp}
            isLoading={metricsQ.isLoading}
          />
          <MetricCard
            title="Won Amount"
            value={formatCurrency(m?.total_won_amount ?? 0)}
            subtitle={m ? `${m.start} → ${m.end}` : undefined}
            icon={TrendingUp}
            accent="emerald"
            isLoading={metricsQ.isLoading}
          />
        </div>
      )}

      {/* ─── Warnings ───────────────────────────────────────────────────── */}
      {m?.warnings && m.warnings.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900">
          <p className="mb-1 font-semibold uppercase tracking-wide">Data source notes</p>
          <ul className="list-inside list-disc space-y-0.5">
            {m.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-xs text-gray-400">
        Source: HubSpot CRM. Close rate = deals won / (won + lost); no-show rate = no-show meetings / scheduled meetings.
      </p>
    </div>
  )
}
