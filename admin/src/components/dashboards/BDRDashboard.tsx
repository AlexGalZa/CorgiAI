import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import { Plus, FileText, TrendingUp, Target, ArrowRight } from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import ChartCard from '@/components/ui/ChartCard'
import ChartTooltip, { TOOLTIP_PROPS } from '@/components/ui/ChartTooltip'
import StatusBadge from '@/components/ui/StatusBadge'
import DataTable, { type Column } from '@/components/ui/DataTable'
import PageHeader from '@/components/ui/PageHeader'
import {
  usePipelineSummary,
  useCoverageBreakdown,
} from '@/hooks/useAnalytics'
import { useBrokeredRequests } from '@/hooks/useBrokeredRequests'
import { useAuthStore } from '@/stores/auth'
import CoverageTags from '@/components/ui/CoverageTags'
import { formatDate } from '@/lib/formatters'
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

export default function BDRDashboard() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const pipeline = usePipelineSummary()
  const coverage = useCoverageBreakdown()

  // Fetch recent requests by this user
  const myRequests = useBrokeredRequests({
    page_size: 10,
    ordering: '-created_at',
    requester: user?.email,
  })

  // Full pipeline data for charts
  const allRequests = useBrokeredRequests({
    page_size: 500,
    requester: user?.email,
  })

  const pipelineData = pipeline.data ?? []
  const barData = pipelineData.map((s) => ({ name: fmtStatus(s.status), count: s.count }))
  const pieData = consolidate(
    (coverage.data ?? []).map((c) => ({ name: c.coverage_type_display, value: c.count })),
  )

  // Compute BDR metrics from their own requests
  const myData = allRequests.data?.results ?? []
  const myTotal = allRequests.data?.count ?? 0
  const myQuoted = myData.filter((r) => ['quoted', 'bound'].includes(r.status)).length
  const conversionRate = myTotal > 0 ? Math.round((myQuoted / myTotal) * 100) : 0

  // Today / this week counts
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const startOfWeek = new Date(startOfToday)
  startOfWeek.setDate(startOfWeek.getDate() - startOfWeek.getDay())

  const todayCount = myData.filter((r) => new Date(r.created_at) >= startOfToday).length
  const weekCount = myData.filter((r) => new Date(r.created_at) >= startOfWeek).length

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
      key: 'status', header: 'Status',
      render: (r) => <StatusBadge status={r.status} variant="brokerage" />,
    },
    {
      key: 'created_at', header: 'Created',
      render: (r) => formatDate(r.created_at),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Your sales pipeline and request tracking"
      />

      {/* Hero Action Card */}
      <div className="rounded-xl border-2 border-dashed border-orange-300 bg-gradient-to-r from-orange-50 to-amber-50 p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Ready to create a new request?</h2>
            <p className="mt-1 text-sm text-gray-600">
              Start a new brokered quote request to get your client covered.
            </p>
          </div>
          <button
            onClick={() => navigate('/brokered-requests')}
            className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-6 py-3 text-sm font-semibold text-white shadow-md transition-colors hover:bg-[#ea580c]"
          >
            <Plus className="h-5 w-5" />
            New Brokered Request
          </button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="My Requests Today"
          value={todayCount}
          subtitle="Created today"
          icon={FileText}
          isLoading={allRequests.isLoading}
        />
        <MetricCard
          title="My Requests This Week"
          value={weekCount}
          subtitle="Created this week"
          icon={FileText}
          accent="emerald"
          isLoading={allRequests.isLoading}
        />
        <MetricCard
          title="Total Pipeline"
          value={myTotal}
          subtitle={`${myQuoted} quoted/bound`}
          icon={Target}
          accent="amber"
          isLoading={allRequests.isLoading}
        />
        <MetricCard
          title="Conversion Rate"
          value={`${conversionRate}%`}
          subtitle={`${myQuoted} of ${myTotal} requests`}
          icon={TrendingUp}
          accent={conversionRate >= 30 ? 'emerald' : conversionRate >= 15 ? 'amber' : 'red'}
          isLoading={allRequests.isLoading}
          progress={conversionRate}
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
              <Bar dataKey="count" fill="#ff5c00" radius={[4, 4, 0, 0]} maxBarSize={40} name="Requests" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Coverage Type Breakdown"
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

      {/* Recent Requests Table */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">My Recent Requests</h2>
          <button
            onClick={() => navigate('/brokered-requests')}
            className="inline-flex items-center gap-1 text-xs font-medium text-[#ff5c00] hover:text-[#ea580c]"
          >
            View all <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
        <DataTable
          columns={cols}
          data={myRequests.data?.results ?? []}
          isLoading={myRequests.isLoading}
          onRowClick={(r) => navigate(`/brokered-requests?highlight=${r.id}`)}
          emptyMessage="No requests yet — create your first one!"
        />
      </div>
    </div>
  )
}
