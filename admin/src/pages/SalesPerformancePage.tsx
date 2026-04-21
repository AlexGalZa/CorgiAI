import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, Users, Target, Clock, Briefcase } from 'lucide-react'
import api from '@/lib/api'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import MetricCard from '@/components/ui/MetricCard'
import QueryError from '@/components/ui/QueryError'
import { formatCurrency } from '@/lib/formatters'

// ─── Types ───────────────────────────────────────────────────────────────────

interface ProducerRow {
  producer_id: number
  name: string
  role: string
  policies_bound: number
  gross_premium: number
  quotes_touched: number
  close_rate: number | null
  avg_time_to_bind_days: number | null
  active_pipeline_count: number
}

interface Totals {
  producer_count: number
  policies_bound: number
  gross_premium: number
  quotes_touched: number
  close_rate: number | null
  active_pipeline_count: number
}

interface PerformanceResponse {
  role: 'ae' | 'bdr'
  start: string
  end: string
  totals: Totals
  producers: ProducerRow[]
}

type RoleTab = 'ae' | 'bdr'
type SortKey =
  | 'name'
  | 'policies_bound'
  | 'gross_premium'
  | 'close_rate'
  | 'avg_time_to_bind_days'
  | 'active_pipeline_count'

// ─── Hooks ───────────────────────────────────────────────────────────────────

function usePerformance(role: RoleTab, start: string, end: string) {
  return useQuery<PerformanceResponse>({
    queryKey: ['analytics', `${role}-performance`, { start, end }],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (start) params.set('start', start)
      if (end) params.set('end', end)
      const endpoint = role === 'ae' ? 'ae-performance' : 'bdr-performance'
      const { data } = await api.get(`/analytics/${endpoint}?${params.toString()}`)
      return (data?.data ?? data) as PerformanceResponse
    },
  })
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatPct(value: number | null): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(1)}%`
}

function formatDays(value: number | null): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${value.toFixed(1)} d`
}

function defaultRange(): { start: string; end: string } {
  const today = new Date()
  const thirty = new Date()
  thirty.setDate(today.getDate() - 30)
  const iso = (d: Date) => d.toISOString().slice(0, 10)
  return { start: iso(thirty), end: iso(today) }
}

function sortRows(
  rows: ProducerRow[],
  key: SortKey,
  dir: 'asc' | 'desc',
): ProducerRow[] {
  const sorted = [...rows].sort((a, b) => {
    const av = a[key]
    const bv = b[key]
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    if (typeof av === 'string' && typeof bv === 'string') {
      return av.localeCompare(bv)
    }
    return (av as number) - (bv as number)
  })
  return dir === 'desc' ? sorted.reverse() : sorted
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function SalesPerformancePage() {
  const initial = useMemo(defaultRange, [])
  const [start, setStart] = useState(initial.start)
  const [end, setEnd] = useState(initial.end)
  const [roleTab, setRoleTab] = useState<RoleTab>('ae')
  const [sortKey, setSortKey] = useState<SortKey>('policies_bound')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const perfQ = usePerformance(roleTab, start, end)
  const resp = perfQ.data
  const totals = resp?.totals
  const rows = useMemo(
    () => (resp?.producers ? sortRows(resp.producers, sortKey, sortDir) : []),
    [resp, sortKey, sortDir],
  )

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const headerLabel = roleTab === 'ae' ? 'Account Executives' : 'Business Development Reps'

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Analytics' }, { label: 'Sales Performance' }]} />
      <PageHeader
        title="Sales Performance Dashboard"
        subtitle="Per-rep scorecards pulled from Django (policies, producers, quotes). Toggle AE / BDR to scope."
      />

      {/* ─── Filters ──────────────────────────────────────────────────── */}
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
          <label className="text-xs font-medium text-gray-500">Role</label>
          <div className="inline-flex rounded-lg border border-gray-300 bg-white p-0.5">
            {(['ae', 'bdr'] as RoleTab[]).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRoleTab(r)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  roleTab === r
                    ? 'bg-[#ff5c00] text-white'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {r.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ─── Error ────────────────────────────────────────────────────── */}
      {perfQ.isError && <QueryError onRetry={() => perfQ.refetch()} />}

      {/* ─── Metric cards ─────────────────────────────────────────────── */}
      {!perfQ.isError && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Policies Bound"
            value={totals?.policies_bound ?? 0}
            subtitle={
              totals ? `${totals.producer_count} ${headerLabel.toLowerCase()}` : undefined
            }
            icon={Target}
            isLoading={perfQ.isLoading}
          />
          <MetricCard
            title="Gross Premium"
            value={formatCurrency(totals?.gross_premium ?? 0)}
            subtitle={resp ? `${resp.start} → ${resp.end}` : undefined}
            icon={TrendingUp}
            accent="emerald"
            isLoading={perfQ.isLoading}
          />
          <MetricCard
            title="Close Rate"
            value={formatPct(totals?.close_rate ?? null)}
            subtitle={
              totals
                ? `${totals.policies_bound} / ${totals.quotes_touched} quotes touched`
                : undefined
            }
            icon={Users}
            accent={
              totals?.close_rate != null && totals.close_rate >= 0.4
                ? 'emerald'
                : totals?.close_rate != null && totals.close_rate >= 0.2
                  ? 'amber'
                  : 'red'
            }
            progress={
              totals?.close_rate != null ? Math.round(totals.close_rate * 100) : undefined
            }
            isLoading={perfQ.isLoading}
          />
          <MetricCard
            title="Open Pipeline"
            value={totals?.active_pipeline_count ?? 0}
            subtitle="Quotes in submitted / quoted / needs review"
            icon={Briefcase}
            isLoading={perfQ.isLoading}
          />
        </div>
      )}

      {/* ─── Rep table ────────────────────────────────────────────────── */}
      {!perfQ.isError && (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-gray-900">{headerLabel}</h2>
            <span className="text-xs text-gray-500">
              {rows.length} {rows.length === 1 ? 'person' : 'people'}
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
                <tr>
                  <SortableTh label="Name" sortKey="name" currentKey={sortKey} dir={sortDir} onSort={toggleSort} />
                  <SortableTh label="Bound" sortKey="policies_bound" currentKey={sortKey} dir={sortDir} onSort={toggleSort} align="right" />
                  <SortableTh label="GWP" sortKey="gross_premium" currentKey={sortKey} dir={sortDir} onSort={toggleSort} align="right" />
                  <SortableTh label="Close Rate" sortKey="close_rate" currentKey={sortKey} dir={sortDir} onSort={toggleSort} align="right" />
                  <SortableTh label="Avg Time-to-Bind" sortKey="avg_time_to_bind_days" currentKey={sortKey} dir={sortDir} onSort={toggleSort} align="right" />
                  <SortableTh label="Pipeline" sortKey="active_pipeline_count" currentKey={sortKey} dir={sortDir} onSort={toggleSort} align="right" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {perfQ.isLoading && (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-gray-400">
                      Loading…
                    </td>
                  </tr>
                )}
                {!perfQ.isLoading && rows.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-gray-400">
                      No {roleTab.toUpperCase()}s with activity in this range.
                    </td>
                  </tr>
                )}
                {rows.map((r) => (
                  <tr key={r.producer_id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-gray-900">{r.name}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-gray-700">{r.policies_bound}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-gray-700">{formatCurrency(r.gross_premium)}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-gray-700">{formatPct(r.close_rate)}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-gray-700">
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5 text-gray-400" />
                        {formatDays(r.avg_time_to_bind_days)}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-gray-700">{r.active_pipeline_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <p className="text-xs text-gray-400">
        Source: Django (Policy / PolicyProducer / Quote). Close rate = policies bound / quotes touched in window. Time-to-bind measured from quote creation.
      </p>
    </div>
  )
}

// ─── Sortable <th> helper ────────────────────────────────────────────────────

function SortableTh({
  label,
  sortKey,
  currentKey,
  dir,
  onSort,
  align = 'left',
}: {
  label: string
  sortKey: SortKey
  currentKey: SortKey
  dir: 'asc' | 'desc'
  onSort: (k: SortKey) => void
  align?: 'left' | 'right'
}) {
  const active = currentKey === sortKey
  const arrow = active ? (dir === 'desc' ? '▼' : '▲') : ''
  return (
    <th
      scope="col"
      className={`cursor-pointer select-none px-4 py-2 font-semibold ${
        align === 'right' ? 'text-right' : 'text-left'
      } ${active ? 'text-gray-900' : ''}`}
      onClick={() => onSort(sortKey)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <span className="text-[10px] text-gray-400">{arrow}</span>
      </span>
    </th>
  )
}
