import { useNavigate, Link } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import {
  FileText, Shield, AlertTriangle, CreditCard,
  Plus, ArrowRight, Clock, FileWarning, CalendarClock, ClipboardList,
} from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import ChartCard from '@/components/ui/ChartCard'
import ChartTooltip, { TOOLTIP_PROPS } from '@/components/ui/ChartTooltip'
import StatusBadge from '@/components/ui/StatusBadge'
import CoverageTags from '@/components/ui/CoverageTags'
import ActivityTimeline from '@/components/ui/ActivityTimeline'
import DataTable, { type Column } from '@/components/ui/DataTable'
import PageHeader from '@/components/ui/PageHeader'
import {
  usePipelineSummary,
  useCoverageBreakdown,
  usePolicyStats,
  useClaimsSummary,
  useActionItems,
} from '@/hooks/useAnalytics'
import { useBrokeredRequests } from '@/hooks/useBrokeredRequests'
import { useClaims, type ClaimListItem } from '@/hooks/useClaims'
import { useRecentActivity } from '@/hooks/useAuditLog'
import { formatCurrency, formatDate } from '@/lib/formatters'
import type { BrokeredQuoteRequest } from '@/types'

const PIE_COLORS = [
  '#ff5c00', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16',
]

function fmtStatus(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function consolidate(data: { name: string; value: number }[], max = 6) {
  const sorted = [...data].sort((a, b) => b.value - a.value)
  if (sorted.length <= max) return sorted
  const top = sorted.slice(0, max)
  const rest = sorted.slice(max).reduce((s, d) => s + d.value, 0)
  if (rest > 0) top.push({ name: 'Other', value: rest })
  return top
}

export default function OperationsDashboard() {
  const navigate = useNavigate()
  const pipeline = usePipelineSummary()
  const policyStats = usePolicyStats()
  const claimsSummary = useClaimsSummary()
  const coverage = useCoverageBreakdown()
  const recent = useBrokeredRequests({ page_size: 8, ordering: '-created_at' })
  const actionItems = useActionItems()
  const recentClaims = useClaims({ ordering: '-created_at' })
  const recentActivity = useRecentActivity()

  const pipelineData = pipeline.data ?? []
  const totalRequests = pipelineData.reduce((s, d) => s + d.count, 0)
  const barData = pipelineData.map((s) => ({ name: fmtStatus(s.status), count: s.count }))
  const pieData = consolidate(
    (coverage.data ?? []).map((c) => ({ name: c.coverage_type_display, value: c.count })),
  )

  const claims = claimsSummary.data
  const openClaims = claims
    ? claims.by_status
        .filter((s) => !['closed', 'resolved', 'denied'].includes(s.status))
        .reduce((s, d) => s + d.count, 0)
    : 0

  const cols: Column<BrokeredQuoteRequest>[] = [
    { key: 'company_name', header: 'Company' },
    {
      key: 'coverage_types', header: 'Coverage',
      render: (r) => <CoverageTags codes={r.coverage_types} max={2} />,
    },
    {
      key: 'carrier', header: 'Carrier',
      render: (r) => r.carrier_display || r.carrier || '—',
    },
    {
      key: 'premium_amount', header: 'Premium', align: 'right',
      render: (r) => formatCurrency(r.premium_amount),
    },
    {
      key: 'status', header: 'Status',
      render: (r) => <StatusBadge status={r.status} variant="brokerage" />,
    },
    {
      key: 'created_at', header: 'Created',
      render: (r) => formatDate(r.created_at),
    },
  ]

  const claimCols: Column<ClaimListItem>[] = [
    { key: 'claim_number', header: 'Claim #' },
    { key: 'organization_name', header: 'Organization' },
    {
      key: 'status', header: 'Status',
      render: (r) => <StatusBadge status={r.status} variant="claim" />,
    },
    {
      key: 'total_incurred', header: 'Incurred', align: 'right',
      render: (r) => formatCurrency(r.total_incurred),
    },
    {
      key: 'created_at', header: 'Created',
      render: (r) => formatDate(r.created_at),
    },
  ]

  const ai = actionItems.data

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Overview of your insurance operations"
        action={
          <button
            onClick={() => navigate('/brokered-requests')}
            className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#ea580c]"
          >
            <Plus className="h-4 w-4" />
            New Request
          </button>
        }
      />

      {/* KPI row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Pipeline"
          value={totalRequests}
          subtitle={`${pipelineData.find((s) => s.status === 'bound')?.count ?? 0} bound`}
          icon={FileText}
          isLoading={pipeline.isLoading}
        />
        <MetricCard
          title="Active Policies"
          value={policyStats.data?.active_count ?? 0}
          subtitle={formatCurrency(policyStats.data?.total_premium ?? 0) + ' premium'}
          icon={Shield}
          accent="emerald"
          isLoading={policyStats.isLoading}
        />
        <MetricCard
          title="Open Claims"
          value={openClaims}
          subtitle={`${claims?.by_status.reduce((s, d) => s + d.count, 0) ?? 0} total`}
          icon={AlertTriangle}
          accent="amber"
          isLoading={claimsSummary.isLoading}
        />
        <MetricCard
          title="Total Reserves"
          value={formatCurrency(claims?.total_reserves ?? 0)}
          subtitle="Case reserves"
          icon={CreditCard}
          accent="red"
          isLoading={claimsSummary.isLoading}
        />
      </div>

      {/* Action Items + Expiring Policies + Unreviewed Docs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Action Items Card */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm sm:col-span-2 lg:col-span-1">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
            <ClipboardList className="h-4 w-4 text-[#ff5c00]" />
            Action Items
          </h3>
          {actionItems.isLoading ? (
            <div className="animate-pulse space-y-3">
              <div className="h-4 w-3/4 rounded bg-gray-200" />
              <div className="h-4 w-2/3 rounded bg-gray-200" />
              <div className="h-4 w-3/4 rounded bg-gray-200" />
              <div className="h-4 w-1/2 rounded bg-gray-200" />
            </div>
          ) : (
            <div className="space-y-3">
              <Link
                to="/brokered-requests?has_blocker=true"
                className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-orange-50"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-red-50 text-red-600">
                  <AlertTriangle className="h-4 w-4" />
                </span>
                <span className="flex-1 text-gray-700">
                  <span className="font-semibold text-gray-900">{ai?.blocked_requests ?? 0}</span> requests with blockers
                </span>
              </Link>
              <Link
                to="/claims"
                className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-orange-50"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
                  <FileWarning className="h-4 w-4" />
                </span>
                <span className="flex-1 text-gray-700">
                  <span className="font-semibold text-gray-900">{ai?.unreviewed_documents ?? 0}</span> documents not reviewed
                </span>
              </Link>
              <Link
                to="/policies?status=active"
                className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-orange-50"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-orange-50 text-[#ff5c00]">
                  <CalendarClock className="h-4 w-4" />
                </span>
                <span className="flex-1 text-gray-700">
                  <span className="font-semibold text-gray-900">{ai?.expiring_policies_30d ?? 0}</span> policies expiring in 30d
                </span>
              </Link>
              <Link
                to="/claims?status=filed"
                className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-orange-50"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-sky-50 text-sky-600">
                  <Clock className="h-4 w-4" />
                </span>
                <span className="flex-1 text-gray-700">
                  <span className="font-semibold text-gray-900">{ai?.pending_claims ?? 0}</span> pending claims
                </span>
              </Link>
            </div>
          )}
        </div>

        {/* Policies Expiring Soon */}
        <MetricCard
          title="Policies Expiring (30d)"
          value={ai?.expiring_policies_30d ?? 0}
          subtitle="Active policies expiring within 30 days"
          icon={CalendarClock}
          accent="amber"
          isLoading={actionItems.isLoading}
        />

        {/* Internal Docs Needing Review */}
        <MetricCard
          title="Docs Needing Review"
          value={ai?.unreviewed_documents ?? 0}
          subtitle="Internal documents not yet reviewed"
          icon={FileWarning}
          accent="red"
          isLoading={actionItems.isLoading}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartCard
          title="Pipeline by Status"
          isLoading={pipeline.isLoading}
          isEmpty={barData.length === 0}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData} margin={{ top: 4, right: 4, bottom: 0, left: -12 }}>
              <CartesianGrid vertical={false} stroke="#f3f4f6" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} {...TOOLTIP_PROPS} cursor={{ fill: 'rgba(0,0,0,.03)' }} />
              <Bar dataKey="count" fill="#ff5c00" radius={[4, 4, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Coverage Breakdown"
          isLoading={coverage.isLoading}
          isEmpty={pieData.length === 0}
        >
          <div className="flex h-full items-center gap-6">
            <div className="w-[55%]">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={88}
                    paddingAngle={2}
                    stroke="none"
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} {...TOOLTIP_PROPS} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col gap-2">
              {pieData.map((e, i) => (
                <div key={e.name} className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                  />
                  <span className="text-xs text-gray-600">{e.name}</span>
                  <span className="ml-auto text-xs font-semibold text-gray-900">{e.value}</span>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
      </div>

      {/* Recent requests */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">Recent Requests</h2>
          <button
            onClick={() => navigate('/brokered-requests')}
            className="inline-flex items-center gap-1 text-xs font-medium text-[#ff5c00] hover:text-[#ea580c]"
          >
            View all <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
        <DataTable
          columns={cols}
          data={recent.data?.results ?? []}
          isLoading={recent.isLoading}
          onRowClick={(r) => navigate(`/brokered-requests?id=${r.id}`)}
          emptyMessage="No brokered requests yet"
        />
      </div>

      {/* Recent Claims */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">Recent Claims</h2>
          <button
            onClick={() => navigate('/claims')}
            className="inline-flex items-center gap-1 text-xs font-medium text-[#ff5c00] hover:text-[#ea580c]"
          >
            View all <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
        <DataTable
          columns={claimCols}
          data={(recentClaims.data?.results ?? []).slice(0, 5)}
          isLoading={recentClaims.isLoading}
          onRowClick={(r) => navigate(`/claims/${r.id}`)}
          emptyMessage="No claims yet"
        />
      </div>

      {/* Recent Activity */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
          <Clock className="h-4 w-4 text-gray-400" />
          Recent Activity
        </h2>
        <ActivityTimeline
          entries={recentActivity.data ?? []}
          isLoading={recentActivity.isLoading}
          maxEntries={15}
        />
      </div>
    </div>
  )
}
