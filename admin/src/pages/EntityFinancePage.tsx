import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { DollarSign, Flame, Percent, Timer } from 'lucide-react'
import api from '@/lib/api'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import MetricCard from '@/components/ui/MetricCard'
import QueryError from '@/components/ui/QueryError'
import { formatCurrency } from '@/lib/formatters'
import { currencyFormatter } from '@/lib/recharts'

// ─── Types & constants ───────────────────────────────────────────────────────

type EntityKey = 'corgi_admin' | 'techrrg' | 'corgire' | 'dane'

const ENTITY_TABS: { key: EntityKey; label: string }[] = [
  { key: 'corgi_admin', label: 'Corgi Admin' },
  { key: 'techrrg', label: 'TechRRG' },
  { key: 'corgire', label: 'CorgiRe' },
  { key: 'dane', label: 'Dane' },
]

interface EntityRoi {
  entity: EntityKey
  revenue: number
  expenses: number
  net: number
  roi_pct: number | null
  start: string
  end: string
  currency: string
}

interface EntityBurn {
  entity: EntityKey
  revenue: number
  expenses: number
  burn: number
  window_days: number
  start: string
  end: string
  currency: string
}

interface EntityRunway {
  entity: EntityKey
  cash_balance: number
  monthly_burn: number
  runway_months: number | null
  as_of: string
  currency: string
}

// ─── Hooks ───────────────────────────────────────────────────────────────────

function useEntityRoi(entity: EntityKey, start: string, end: string) {
  return useQuery<EntityRoi>({
    queryKey: ['analytics', 'entity-roi', entity, start, end],
    queryFn: async () => {
      const params = new URLSearchParams({ entity })
      if (start) params.set('start', start)
      if (end) params.set('end', end)
      const { data } = await api.get(`/analytics/entity-roi?${params.toString()}`)
      return data as EntityRoi
    },
  })
}

function useEntityBurn(entity: EntityKey) {
  return useQuery<EntityBurn>({
    queryKey: ['analytics', 'entity-burn', entity],
    queryFn: async () => {
      const { data } = await api.get(
        `/analytics/entity-burn?entity=${entity}`,
      )
      return data as EntityBurn
    },
  })
}

function useEntityRunway(entity: EntityKey, cashBalanceCents: number) {
  return useQuery<EntityRunway>({
    queryKey: ['analytics', 'entity-runway', entity, cashBalanceCents],
    queryFn: async () => {
      const { data } = await api.get(
        `/analytics/entity-runway?entity=${entity}&cash_balance=${cashBalanceCents}`,
      )
      return data as EntityRunway
    },
    enabled: cashBalanceCents >= 0,
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

function formatMonths(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '∞'
  return `${value.toFixed(1)} mo`
}

// Build a simple runway-depletion curve: starting cash, minus monthly burn,
// month by month, until the balance would hit zero. Useful for eyeballing
// which month treasury needs to raise / shift spend.
function buildRunwayCurve(
  cashBalance: number,
  monthlyBurn: number,
  months = 12,
): { month: string; balance: number }[] {
  const rows: { month: string; balance: number }[] = []
  let balance = cashBalance
  const today = new Date()
  for (let i = 0; i <= months; i++) {
    const d = new Date(today.getFullYear(), today.getMonth() + i, 1)
    const month = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    rows.push({ month, balance: Math.max(0, Math.round(balance)) })
    balance -= monthlyBurn
    if (balance < 0) balance = 0
  }
  return rows
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function EntityFinancePage() {
  const initial = useMemo(defaultRange, [])
  const [start, setStart] = useState(initial.start)
  const [end, setEnd] = useState(initial.end)
  const [entity, setEntity] = useState<EntityKey>('corgi_admin')
  const [cashBalanceDollars, setCashBalanceDollars] = useState<string>('500000')

  const cashBalanceCents = Math.max(
    0,
    Math.round(parseFloat(cashBalanceDollars || '0') * 100),
  )

  const roiQ = useEntityRoi(entity, start, end)
  const burnQ = useEntityBurn(entity)
  const runwayQ = useEntityRunway(entity, cashBalanceCents)

  const roi = roiQ.data
  const burn = burnQ.data
  const runway = runwayQ.data

  const revenueExpenseData = roi
    ? [
        { bucket: 'Revenue', amount: roi.revenue },
        { bucket: 'Expenses', amount: roi.expenses },
        { bucket: 'Net', amount: roi.net },
      ]
    : []

  const runwayCurve = runway
    ? buildRunwayCurve(runway.cash_balance, runway.monthly_burn)
    : []

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[{ label: 'Analytics' }, { label: 'Entity Finance' }]}
      />
      <PageHeader
        title="Entity Finance"
        subtitle="ROI, burn rate, and runway per legal entity (Corgi Admin, TechRRG, CorgiRe, Dane)."
      />

      {/* ─── Entity tabs ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2 border-b border-gray-200">
        {ENTITY_TABS.map((tab) => {
          const active = entity === tab.key
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setEntity(tab.key)}
              className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                active
                  ? 'border-[#ff5c00] text-[#ff5c00]'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* ─── Filters ─────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">ROI window start</label>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">ROI window end</label>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">Cash balance (USD)</label>
          <input
            type="number"
            min={0}
            step="0.01"
            value={cashBalanceDollars}
            onChange={(e) => setCashBalanceDollars(e.target.value)}
            className="w-40 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
          />
        </div>
        <p className="ml-auto text-xs text-gray-400">
          Burn is trailing 30 days; runway projects forward from cash balance.
        </p>
      </div>

      {/* ─── Errors ──────────────────────────────────────────────────────── */}
      {roiQ.isError && <QueryError onRetry={() => roiQ.refetch()} />}
      {burnQ.isError && <QueryError onRetry={() => burnQ.refetch()} />}
      {runwayQ.isError && <QueryError onRetry={() => runwayQ.refetch()} />}

      {/* ─── Metric cards ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Revenue"
          value={formatCurrency(roi?.revenue ?? 0)}
          subtitle={roi ? `${roi.start} → ${roi.end}` : undefined}
          icon={DollarSign}
          accent="emerald"
          isLoading={roiQ.isLoading}
        />
        <MetricCard
          title="ROI"
          value={formatPct(roi?.roi_pct ?? null)}
          subtitle={
            roi
              ? `Net ${formatCurrency(roi.net)} · Expenses ${formatCurrency(roi.expenses)}`
              : undefined
          }
          icon={Percent}
          accent={
            roi?.roi_pct != null && roi.roi_pct >= 0.2
              ? 'emerald'
              : roi?.roi_pct != null && roi.roi_pct >= 0
                ? 'amber'
                : 'red'
          }
          isLoading={roiQ.isLoading}
        />
        <MetricCard
          title="Burn (30d)"
          value={formatCurrency(burn?.burn ?? 0)}
          subtitle={
            burn
              ? `${burn.start} → ${burn.end} · Rev ${formatCurrency(burn.revenue)}`
              : undefined
          }
          icon={Flame}
          accent={burn && burn.burn > 0 ? 'red' : 'emerald'}
          isLoading={burnQ.isLoading}
        />
        <MetricCard
          title="Runway"
          value={formatMonths(runway?.runway_months ?? null)}
          subtitle={
            runway
              ? `Cash ${formatCurrency(runway.cash_balance)} · Burn/mo ${formatCurrency(runway.monthly_burn)}`
              : undefined
          }
          icon={Timer}
          accent={
            runway?.runway_months == null
              ? 'emerald'
              : runway.runway_months < 6
                ? 'red'
                : runway.runway_months < 12
                  ? 'amber'
                  : 'emerald'
          }
          isLoading={runwayQ.isLoading}
        />
      </div>

      {/* ─── Charts ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-gray-700">
            Revenue vs Expenses (ROI window)
          </h3>
          <div className="h-72">
            {roi ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={revenueExpenseData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="bucket" />
                  <YAxis
                    tickFormatter={(v: number) =>
                      v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`
                    }
                  />
                  <Tooltip formatter={currencyFormatter} />
                  <Legend />
                  <Bar dataKey="amount" fill="#ff5c00" name="Amount (USD)" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="flex h-full items-center justify-center text-sm text-gray-400">
                {roiQ.isLoading ? 'Loading…' : 'No data in window.'}
              </p>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-gray-700">
            Runway projection (12 months)
          </h3>
          <div className="h-72">
            {runway && runway.monthly_burn > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={runwayCurve}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis
                    tickFormatter={(v: number) =>
                      v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`
                    }
                  />
                  <Tooltip formatter={currencyFormatter} />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="balance"
                    stroke="#ff5c00"
                    name="Projected cash"
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="flex h-full items-center justify-center text-sm text-gray-400">
                {runwayQ.isLoading
                  ? 'Loading…'
                  : runway
                    ? 'No burn in the trailing 30 days — runway is effectively infinite.'
                    : 'Enter a cash balance to project runway.'}
              </p>
            )}
          </div>
        </div>
      </div>

      <p className="text-xs text-gray-400">
        ROI = (revenue − expenses) / expenses. Burn = expenses − revenue (trailing 30d).
        Runway = cash balance / monthly burn.
      </p>
    </div>
  )
}
