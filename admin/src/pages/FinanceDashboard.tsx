import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { DollarSign, Repeat, TrendingUp, Scale } from 'lucide-react'
import api from '@/lib/api'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import MetricCard from '@/components/ui/MetricCard'
import QueryError from '@/components/ui/QueryError'
import { formatCurrency } from '@/lib/formatters'
import { currencyFormatter } from '@/lib/recharts'

// ─── Types ───────────────────────────────────────────────────────────────────

interface ArrSnapshot {
  arr: number
  annual_contribution: number
  monthly_contribution: number
  active_policy_count: number
  monthly_policy_count: number
  annual_policy_count: number
  as_of: string
  currency: string
}

interface OperatingRevenue {
  operating_revenue: number
  gross_written_premium: number
  refunds: number
  start: string
  end: string
  currency: string
}

interface BrokeredDirectSplit {
  brokered: number
  direct: number
  total: number
  brokered_pct: number
  direct_pct: number
  start: string
  end: string
  currency: string
}

// ─── Hooks ───────────────────────────────────────────────────────────────────

function useArr() {
  return useQuery<ArrSnapshot>({
    queryKey: ['analytics', 'arr'],
    queryFn: async () => {
      const { data } = await api.get('/analytics/arr')
      return data as ArrSnapshot
    },
  })
}

function useOperatingRevenue(start: string, end: string) {
  return useQuery<OperatingRevenue>({
    queryKey: ['analytics', 'operating-revenue', start, end],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (start) params.set('start', start)
      if (end) params.set('end', end)
      const { data } = await api.get(
        `/analytics/operating-revenue?${params.toString()}`,
      )
      return data as OperatingRevenue
    },
  })
}

function useBrokeredDirectSplit(start: string, end: string) {
  return useQuery<BrokeredDirectSplit>({
    queryKey: ['analytics', 'brokered-direct-split', start, end],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (start) params.set('start', start)
      if (end) params.set('end', end)
      const { data } = await api.get(
        `/analytics/brokered-direct-split?${params.toString()}`,
      )
      return data as BrokeredDirectSplit
    },
  })
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function defaultRange(): { start: string; end: string } {
  const today = new Date()
  const monthAgo = new Date()
  monthAgo.setDate(today.getDate() - 30)
  const iso = (d: Date) => d.toISOString().slice(0, 10)
  return { start: iso(monthAgo), end: iso(today) }
}

function formatPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(1)}%`
}

const BROKERED_COLOR = '#ff5c00'
const DIRECT_COLOR = '#0ea5e9'

// ─── Component ───────────────────────────────────────────────────────────────

export default function FinanceDashboard() {
  const initial = useMemo(defaultRange, [])
  const [start, setStart] = useState(initial.start)
  const [end, setEnd] = useState(initial.end)

  const arrQ = useArr()
  const orQ = useOperatingRevenue(start, end)
  const splitQ = useBrokeredDirectSplit(start, end)

  const arr = arrQ.data
  const or = orQ.data
  const split = splitQ.data

  const pieData = split
    ? [
        { name: 'Brokered', value: split.brokered, color: BROKERED_COLOR },
        { name: 'Direct', value: split.direct, color: DIRECT_COLOR },
      ]
    : []

  const barData = split
    ? [
        {
          bucket: 'Revenue',
          Brokered: split.brokered,
          Direct: split.direct,
        },
      ]
    : []

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Analytics' }, { label: 'Finance' }]} />
      <PageHeader
        title="Finance Dashboard"
        subtitle="ARR, operating revenue, and brokered-vs-direct revenue mix."
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
        <p className="ml-auto text-xs text-gray-400">
          ARR is a live snapshot; OR and revenue split use the window above.
        </p>
      </div>

      {/* ─── Errors ─────────────────────────────────────────────────────── */}
      {arrQ.isError && <QueryError onRetry={() => arrQ.refetch()} />}
      {orQ.isError && <QueryError onRetry={() => orQ.refetch()} />}
      {splitQ.isError && <QueryError onRetry={() => splitQ.refetch()} />}

      {/* ─── Metric cards ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="ARR"
          value={formatCurrency(arr?.arr ?? 0)}
          subtitle={
            arr
              ? `${arr.active_policy_count} active policies · as of ${arr.as_of}`
              : undefined
          }
          icon={Repeat}
          accent="primary"
          isLoading={arrQ.isLoading}
        />
        <MetricCard
          title="Operating Revenue"
          value={formatCurrency(or?.operating_revenue ?? 0)}
          subtitle={
            or ? `GWP ${formatCurrency(or.gross_written_premium)} · Refunds ${formatCurrency(or.refunds)}` : undefined
          }
          icon={TrendingUp}
          accent="emerald"
          isLoading={orQ.isLoading}
        />
        <MetricCard
          title="Brokered Revenue"
          value={formatCurrency(split?.brokered ?? 0)}
          subtitle={split ? formatPct(split.brokered_pct) + ' of total' : undefined}
          icon={Scale}
          accent="amber"
          isLoading={splitQ.isLoading}
        />
        <MetricCard
          title="Direct Revenue"
          value={formatCurrency(split?.direct ?? 0)}
          subtitle={split ? formatPct(split.direct_pct) + ' of total' : undefined}
          icon={DollarSign}
          accent="sky"
          isLoading={splitQ.isLoading}
        />
      </div>

      {/* ─── Charts ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-gray-700">Brokered vs Direct (mix)</h3>
          <div className="h-72">
            {split && split.total > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={(entry) => `${entry.name}: ${formatCurrency(entry.value as number)}`}
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={currencyFormatter} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="flex h-full items-center justify-center text-sm text-gray-400">
                {splitQ.isLoading ? 'Loading…' : 'No revenue in this window.'}
              </p>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-gray-700">Brokered vs Direct (amounts)</h3>
          <div className="h-72">
            {split && split.total > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="bucket" />
                  <YAxis
                    tickFormatter={(v: number) =>
                      v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`
                    }
                  />
                  <Tooltip formatter={currencyFormatter} />
                  <Legend />
                  <Bar dataKey="Brokered" fill={BROKERED_COLOR} />
                  <Bar dataKey="Direct" fill={DIRECT_COLOR} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="flex h-full items-center justify-center text-sm text-gray-400">
                {splitQ.isLoading ? 'Loading…' : 'No revenue in this window.'}
              </p>
            )}
          </div>
        </div>
      </div>

      <p className="text-xs text-gray-400">
        ARR = annual premium + (monthly_premium × 12) across active policies. OR = GWP (accounting date in window) − refunds in window.
      </p>
    </div>
  )
}
