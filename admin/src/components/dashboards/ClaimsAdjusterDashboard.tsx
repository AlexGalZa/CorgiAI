import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import MetricCard from '@/components/ui/MetricCard'
import DataTable, { type Column } from '@/components/ui/DataTable'
import PageHeader from '@/components/ui/PageHeader'
import StatusBadge from '@/components/ui/StatusBadge'
import Select from '@/components/ui/Select'
import Pagination from '@/components/ui/Pagination'
import { cn } from '@/lib/utils'
import api from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/formatters'
import { useClaims, type ClaimListItem } from '@/hooks/useClaims'

// ─── Types ───────────────────────────────────────────────────────────────────

interface AdjusterSummary {
  assigned_claims: number
  avg_resolution_days: number | null
  pending_reserves: number
  sla_compliance_rate: number
  total_slas: number
  sla_breaches: number
}

interface ReserveRow {
  id: number
  claim_number: string
  insured: string
  policy_number: string | null
  status: string
  case_reserve_loss: number
  case_reserve_lae: number
  paid_loss: number
  paid_lae: number
  total_incurred: number
}

interface SLARow {
  id: number
  entity_id: number
  metric_type: string
  metric_type_display: string
  target_hours: number
  elapsed_hours: number
  started_at: string
  completed_at: string | null
  breached: boolean
  notes: string
}

// ─── Hooks ───────────────────────────────────────────────────────────────────

function useAdjusterSummary() {
  return useQuery<AdjusterSummary>({
    queryKey: ['analytics', 'claims-adjuster-summary'],
    queryFn: async () => {
      const { data } = await api.get('/admin/analytics/claims-adjuster-summary')
      return data
    },
  })
}

function useClaimsReserves(filters: { page?: number; search?: string; status?: string } = {}) {
  return useQuery<{ count: number; results: ReserveRow[]; next: string | null; previous: string | null }>({
    queryKey: ['claims-reserves', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.search) params.set('search', filters.search)
      if (filters.status) params.set('status', filters.status)
      const { data } = await api.get(`/admin/analytics/claims-reserves?${params.toString()}`)
      return data
    },
  })
}

function useClaimsSLAMetrics(page: number = 1) {
  return useQuery<{ count: number; results: SLARow[]; next: string | null; previous: string | null }>({
    queryKey: ['claims-sla-metrics', page],
    queryFn: async () => {
      const { data } = await api.get(`/admin/analytics/claims-sla-metrics?page=${page}`)
      return data
    },
  })
}

// ─── Tab definitions ─────────────────────────────────────────────────────────

type Tab = 'dashboard' | 'all-claims' | 'reserves' | 'slas'

const TABS: { id: Tab; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'all-claims', label: 'All Claims' },
  { id: 'reserves', label: 'Reserves' },
  { id: 'slas', label: 'SLAs & Timelines' },
]

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'approved', label: 'Approved' },
  { value: 'denied', label: 'Denied' },
  { value: 'closed', label: 'Closed' },
]

// ─── Sub-panels ───────────────────────────────────────────────────────────────

function DashboardPanel() {
  const summary = useAdjusterSummary()
  const d = summary.data

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Assigned Claims"
          value={d?.assigned_claims ?? 0}
          subtitle="Total active claims"
          isLoading={summary.isLoading}
        />
        <MetricCard
          title="Avg Resolution Time"
          value={d?.avg_resolution_days != null ? `${d.avg_resolution_days}d` : '—'}
          subtitle="Days to close"
          accent="sky"
          isLoading={summary.isLoading}
        />
        <MetricCard
          title="Pending Reserves"
          value={formatCurrency(d?.pending_reserves ?? 0)}
          subtitle="Open case reserves"
          accent="amber"
          isLoading={summary.isLoading}
        />
        <MetricCard
          title="SLA Compliance"
          value={`${d?.sla_compliance_rate ?? 100}%`}
          subtitle={`${d?.sla_breaches ?? 0} breach${(d?.sla_breaches ?? 0) !== 1 ? 'es' : ''} / ${d?.total_slas ?? 0} total`}
          accent={(d?.sla_compliance_rate ?? 100) >= 90 ? 'emerald' : (d?.sla_compliance_rate ?? 100) >= 70 ? 'amber' : 'red'}
          progress={d?.sla_compliance_rate}
          isLoading={summary.isLoading}
        />
      </div>
    </div>
  )
}

function AllClaimsPanel() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')

  const { data, isLoading } = useClaims({ page, status, search })

  const cols: Column<ClaimListItem>[] = [
    { key: 'claim_number', header: 'Claim #' },
    { key: 'organization_name', header: 'Insured', render: (r) => r.organization_name || `${r.first_name} ${r.last_name}`.trim() },
    { key: 'policy', header: 'Policy', render: (r) => String(r.policy) },
    { key: 'claim_report_date', header: 'Incident Date', render: (r) => formatDate(r.claim_report_date ?? '') },
    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
    { key: 'total_incurred', header: 'Total Incurred', align: 'right', render: (r) => formatCurrency(r.total_incurred) },
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <input
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#ff5c00] focus:ring-1 focus:ring-[#ff5c00]"
          placeholder="Search claims…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <Select
          value={status}
          onChange={(v) => { setStatus(v); setPage(1) }}
          options={STATUS_OPTIONS}
        />
      </div>
      <DataTable
        columns={cols}
        data={data?.results ?? []}
        isLoading={isLoading}
        onRowClick={(r) => navigate(`/claims/${r.id}`)}
        emptyMessage="No claims found"
      />
      {data && (
        <Pagination
          page={page}
          pageSize={25}
          total={data.count}
          onPageChange={setPage}
        />
      )}
    </div>
  )
}

function ReservesPanel() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const { data, isLoading } = useClaimsReserves({ page, status })

  const cols: Column<ReserveRow>[] = [
    { key: 'claim_number', header: 'Claim #' },
    { key: 'insured', header: 'Insured' },
    { key: 'policy_number', header: 'Policy', render: (r) => r.policy_number ?? '—' },
    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
    { key: 'case_reserve_loss', header: 'Case Reserve', align: 'right', render: (r) => formatCurrency(r.case_reserve_loss) },
    { key: 'paid_loss', header: 'Paid Loss', align: 'right', render: (r) => formatCurrency(r.paid_loss) },
    { key: 'paid_lae', header: 'Paid LAE', align: 'right', render: (r) => formatCurrency(r.paid_lae) },
    { key: 'total_incurred', header: 'Total Incurred', align: 'right', render: (r) => (
      <span className="font-semibold">{formatCurrency(r.total_incurred)}</span>
    )},
  ]

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <Select
          value={status}
          onChange={(v) => { setStatus(v); setPage(1) }}
          options={STATUS_OPTIONS}
        />
      </div>
      <DataTable
        columns={cols}
        data={data?.results ?? []}
        isLoading={isLoading}
        emptyMessage="No reserve data found"
      />
      {data && (
        <Pagination page={page} pageSize={25} total={data.count} onPageChange={setPage} />
      )}
    </div>
  )
}

function SLAsPanel() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useClaimsSLAMetrics(page)

  const cols: Column<SLARow>[] = [
    { key: 'entity_id', header: 'Claim ID', render: (r) => `CLM-${r.entity_id}` },
    { key: 'metric_type_display', header: 'SLA Type' },
    { key: 'target_hours', header: 'Target', render: (r) => `${r.target_hours}h` },
    { key: 'elapsed_hours', header: 'Elapsed', render: (r) => `${r.elapsed_hours.toFixed(1)}h` },
    { key: 'breached', header: 'Status', render: (r) => (
      <span className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        r.breached ? 'bg-red-100 text-red-700' : r.completed_at ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
      )}>
        {r.breached ? '⚠ Breached' : r.completed_at ? '✓ Met' : 'Open'}
      </span>
    )},
    { key: 'started_at', header: 'Started', render: (r) => formatDate(r.started_at) },
    { key: 'completed_at', header: 'Completed', render: (r) => r.completed_at ? formatDate(r.completed_at) : '—' },
  ]

  return (
    <div className="space-y-4">
      <DataTable
        columns={cols}
        data={data?.results ?? []}
        isLoading={isLoading}
        emptyMessage="No SLA records found"
      />
      {data && (
        <Pagination page={page} pageSize={25} total={data.count} onPageChange={setPage} />
      )}
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function ClaimsAdjusterDashboard() {
  const [tab, setTab] = useState<Tab>('dashboard')

  return (
    <div className="space-y-6">
      <PageHeader title="Claims Adjuster" subtitle="Manage claims, reserves, and SLA compliance" />

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-1 -mb-px">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                'px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                tab === t.id
                  ? 'border-[#ff5c00] text-[#ff5c00]'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {tab === 'dashboard' && <DashboardPanel />}
      {tab === 'all-claims' && <AllClaimsPanel />}
      {tab === 'reserves' && <ReservesPanel />}
      {tab === 'slas' && <SLAsPanel />}
    </div>
  )
}
