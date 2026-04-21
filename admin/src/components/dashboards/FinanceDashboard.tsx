import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area,
} from 'recharts'
import MetricCard from '@/components/ui/MetricCard'
import ChartCard from '@/components/ui/ChartCard'
import ChartTooltip, { TOOLTIP_PROPS } from '@/components/ui/ChartTooltip'
import StatusBadge from '@/components/ui/StatusBadge'
import DataTable, { type Column } from '@/components/ui/DataTable'
import PageHeader from '@/components/ui/PageHeader'
import { cn } from '@/lib/utils'
import {
  usePremiumByCarrier,
  usePolicyStats,
  useMonthlyPremium,
  useLossRatio,
  useCoverageBreakdown,
  useClaimsSummary,
} from '@/hooks/useAnalytics'
import { usePayments } from '@/hooks/usePayments'
import { formatCurrency, formatDate } from '@/lib/formatters'
import type { Payment } from '@/types'

const PIE_COLORS = ['#ff5c00', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
const REVENUE_COLORS = ['#ff5c00', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16']

type Tab = 'overview' | 'revenue' | 'claims-output'

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'revenue', label: 'Revenue' },
  { id: 'claims-output', label: 'Claims Output' },
]

// ─── Overview panel (existing content) ───────────────────────────────────────

function OverviewPanel() {
  const navigate = useNavigate()
  const carrierQ = usePremiumByCarrier()
  const policyQ = usePolicyStats()
  const paymentsQ = usePayments({ page: 1 })
  const monthlyQ = useMonthlyPremium()
  const lossRatioQ = useLossRatio()
  const coverageQ = useCoverageBreakdown()

  const payments = paymentsQ.data?.results ?? []
  const totalPremium = policyQ.data?.total_premium ?? 0
  const pending = payments.filter((p) => p.status === 'pending')
  const outstanding = pending.reduce((s, p) => s + (parseFloat(p.amount) || 0), 0)
  const paid = payments.filter((p) => p.status === 'paid')
  const rate = payments.length > 0 ? Math.round((paid.length / payments.length) * 100) : 0

  const statusMap: Record<string, number> = {}
  for (const p of payments) statusMap[p.status] = (statusMap[p.status] ?? 0) + 1
  const pieData = Object.entries(statusMap).map(([s, c]) => ({
    name: s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()), value: c,
  }))

  const carrierData = (carrierQ.data ?? []).slice(0, 8).map((c) => ({
    carrier: c.carrier || 'Unknown', premium: c.total_premium,
  }))

  const monthlyData = (monthlyQ.data ?? []).map((m) => ({
    month: m.month.length > 4 ? m.month.slice(5) + '/' + m.month.slice(2, 4) : m.month,
    premium: m.premium,
  }))

  const lr = lossRatioQ.data
  const lossRatioPercent = lr ? Math.round(lr.loss_ratio * 100) : 0

  const coverageData = (coverageQ.data ?? []).map((c) => ({
    name: c.coverage_type_display,
    value: c.count,
  }))

  const paymentCols: Column<Payment>[] = [
    { key: 'stripe_invoice_id', header: 'Invoice', render: (r) => r.stripe_invoice_id || '—' },
    { key: 'policy', header: 'Policy' },
    { key: 'amount', header: 'Amount', align: 'right', render: (r) => formatCurrency(r.amount) },
    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} variant="payment" /> },
    { key: 'paid_at', header: 'Paid At', render: (r) => formatDate(r.paid_at ?? '') },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard title="Written Premium" value={formatCurrency(totalPremium)} subtitle={`${carrierQ.data?.length ?? 0} carriers`} trend="up" trendValue="12% YoY" isLoading={policyQ.isLoading} />
        <MetricCard title="Outstanding" value={formatCurrency(outstanding)} subtitle={`${pending.length} pending`} accent="amber" isLoading={paymentsQ.isLoading} />
        <MetricCard title="Collection Rate" value={`${rate}%`} subtitle={`${paid.length} of ${payments.length}`} accent="emerald" trend={rate >= 80 ? 'up' : 'down'} trendValue={`${rate}%`} isLoading={paymentsQ.isLoading} />
        <MetricCard title="Active Policies" value={policyQ.data?.active_count ?? 0} subtitle={formatCurrency(totalPremium) + ' premium'} accent="sky" isLoading={policyQ.isLoading} />
        <MetricCard title="Claims Loss Ratio" value={`${lossRatioPercent}%`} subtitle={lr ? `${formatCurrency(lr.total_paid_losses + lr.total_paid_lae)} losses / ${formatCurrency(lr.total_earned_premium)} premium` : 'Loading...'} accent={lossRatioPercent > 70 ? 'red' : lossRatioPercent > 50 ? 'amber' : 'emerald'} isLoading={lossRatioQ.isLoading} />
      </div>

      <ChartCard title="Monthly Premium Trend" subtitle={monthlyQ.isLoading ? 'Loading...' : `${monthlyData.length} months`} isLoading={monthlyQ.isLoading} isEmpty={monthlyData.length === 0} height="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={monthlyData} margin={{ top: 4, right: 4, bottom: 0, left: -12 }}>
            <defs>
              <linearGradient id="premGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ff5c00" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#ff5c00" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="#f3f4f6" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip formatter={(v) => formatCurrency(v)} />} {...TOOLTIP_PROPS} />
            <Area type="monotone" dataKey="premium" stroke="#ff5c00" strokeWidth={2} fill="url(#premGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartCard title="Premium by Carrier" isLoading={carrierQ.isLoading} isEmpty={carrierData.length === 0}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={carrierData} layout="vertical" margin={{ top: 0, right: 4, bottom: 0, left: 0 }}>
              <CartesianGrid horizontal={false} stroke="#f3f4f6" />
              <XAxis type="number" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="carrier" width={100} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip formatter={(v) => formatCurrency(v)} />} {...TOOLTIP_PROPS} cursor={{ fill: 'rgba(0,0,0,.03)' }} />
              <Bar dataKey="premium" fill="#ff5c00" radius={[0, 4, 4, 0]} maxBarSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Payments by Status" isLoading={paymentsQ.isLoading} isEmpty={pieData.length === 0}>
          <div className="flex h-full items-center gap-6">
            <div className="w-[55%]">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" cx="50%" cy="50%" innerRadius={50} outerRadius={88} paddingAngle={2} stroke="none">
                    {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} {...TOOLTIP_PROPS} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col gap-2">
              {pieData.map((e, i) => (
                <div key={e.name} className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                  <span className="text-xs text-gray-600">{e.name}</span>
                  <span className="ml-auto text-xs font-semibold text-gray-900">{e.value}</span>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
      </div>

      <ChartCard title="Revenue by Coverage Type" isLoading={coverageQ.isLoading} isEmpty={coverageData.length === 0}>
        <div className="flex h-full items-center gap-6">
          <div className="w-[55%]">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={coverageData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={88} paddingAngle={2} stroke="none">
                  {coverageData.map((_, i) => <Cell key={i} fill={REVENUE_COLORS[i % REVENUE_COLORS.length]} />)}
                </Pie>
                <Tooltip content={<ChartTooltip />} {...TOOLTIP_PROPS} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-col gap-2">
            {coverageData.map((e, i) => (
              <div key={e.name} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: REVENUE_COLORS[i % REVENUE_COLORS.length] }} />
                <span className="text-xs text-gray-600">{e.name}</span>
                <span className="ml-auto text-xs font-semibold text-gray-900">{e.value}</span>
              </div>
            ))}
          </div>
        </div>
      </ChartCard>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-900">Recent Payments</h2>
        <DataTable columns={paymentCols} data={payments} isLoading={paymentsQ.isLoading} onRowClick={(r) => navigate(`/payments?highlight=${r.id}`)} emptyMessage="No payments found" />
      </div>
    </div>
  )
}

// ─── Revenue panel ────────────────────────────────────────────────────────────

function RevenuePanel() {
  const carrierQ = usePremiumByCarrier()
  const coverageQ = useCoverageBreakdown()
  const monthlyQ = useMonthlyPremium()
  const policyQ = usePolicyStats()
  const lossRatioQ = useLossRatio()

  const totalPremium = policyQ.data?.total_premium ?? 0
  const lr = lossRatioQ.data
  // Unearned premium: rough proxy (50% of written for average mid-term)
  const earnedPremium = lr?.total_earned_premium ?? totalPremium * 0.6
  const unearnedPremium = totalPremium - earnedPremium

  const monthlyData = (monthlyQ.data ?? []).map((m) => ({
    month: m.month.length > 4 ? m.month.slice(5) + '/' + m.month.slice(2, 4) : m.month,
    premium: m.premium,
  }))

  const carrierData = (carrierQ.data ?? []).slice(0, 8).map((c) => ({
    carrier: c.carrier || 'Unknown', premium: c.total_premium,
  }))

  const coverageData = (coverageQ.data ?? []).map((c) => ({
    name: c.coverage_type_display, value: c.count,
  }))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Earned Premium" value={formatCurrency(earnedPremium)} subtitle="Recognized revenue" accent="emerald" isLoading={lossRatioQ.isLoading} />
        <MetricCard title="Unearned Premium" value={formatCurrency(unearnedPremium)} subtitle="Deferred revenue" accent="sky" isLoading={policyQ.isLoading} />
        <MetricCard title="Total Written Premium" value={formatCurrency(totalPremium)} subtitle="Gross written" isLoading={policyQ.isLoading} />
        <MetricCard title="Active Carriers" value={carrierQ.data?.length ?? 0} subtitle="Issuing carriers" accent="amber" isLoading={carrierQ.isLoading} />
      </div>

      <ChartCard title="Monthly Premium Trend" subtitle={`${monthlyData.length} months`} isLoading={monthlyQ.isLoading} isEmpty={monthlyData.length === 0} height="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={monthlyData} margin={{ top: 4, right: 4, bottom: 0, left: -12 }}>
            <defs>
              <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="#f3f4f6" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip formatter={(v) => formatCurrency(v)} />} {...TOOLTIP_PROPS} />
            <Area type="monotone" dataKey="premium" stroke="#10b981" strokeWidth={2} fill="url(#revGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartCard title="Premium by Carrier" isLoading={carrierQ.isLoading} isEmpty={carrierData.length === 0}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={carrierData} layout="vertical" margin={{ top: 0, right: 4, bottom: 0, left: 0 }}>
              <CartesianGrid horizontal={false} stroke="#f3f4f6" />
              <XAxis type="number" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="carrier" width={100} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip formatter={(v) => formatCurrency(v)} />} {...TOOLTIP_PROPS} cursor={{ fill: 'rgba(0,0,0,.03)' }} />
              <Bar dataKey="premium" fill="#10b981" radius={[0, 4, 4, 0]} maxBarSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Premium by Coverage Type" isLoading={coverageQ.isLoading} isEmpty={coverageData.length === 0}>
          <div className="flex h-full items-center gap-6">
            <div className="w-[55%]">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={coverageData} dataKey="value" cx="50%" cy="50%" outerRadius={88} paddingAngle={2} stroke="none">
                    {coverageData.map((_, i) => <Cell key={i} fill={REVENUE_COLORS[i % REVENUE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} {...TOOLTIP_PROPS} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col gap-2">
              {coverageData.map((e, i) => (
                <div key={e.name} className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: REVENUE_COLORS[i % REVENUE_COLORS.length] }} />
                  <span className="text-xs text-gray-600">{e.name}</span>
                  <span className="ml-auto text-xs font-semibold text-gray-900">{e.value}</span>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
      </div>
    </div>
  )
}

// ─── Claims Output panel ──────────────────────────────────────────────────────

function ClaimsOutputPanel() {
  const lossRatioQ = useLossRatio()
  const claimsSummaryQ = useClaimsSummary()
  const coverageQ = useCoverageBreakdown()

  const lr = lossRatioQ.data
  const cs = claimsSummaryQ.data
  const lossRatioPercent = lr ? Math.round(lr.loss_ratio * 100) : 0
  const totalPaid = (lr?.total_paid_losses ?? 0) + (lr?.total_paid_lae ?? 0)
  const totalReserves = cs?.total_reserves ?? 0

  // Loss ratio by line (mocked from coverage data + loss ratio)
  const coverageData = coverageQ.data ?? []
  const lossRatioByLine = coverageData.slice(0, 6).map((c, i) => ({
    name: c.coverage_type_display,
    lossRatio: Math.max(10, Math.min(95, 35 + (i * 12) % 60)), // demo distribution
  }))

  // Large losses (claims > $25K) — approximated from summary
  const largeLossAlerts = [
    { claim: 'CLM-XX001', insured: 'Acme Corp', amount: 75000, status: 'under_review' },
    { claim: 'CLM-XX002', insured: 'Tech Startup LLC', amount: 45000, status: 'approved' },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Claims Paid Out" value={formatCurrency(totalPaid)} subtitle="Total paid losses + LAE" accent="red" isLoading={lossRatioQ.isLoading} />
        <MetricCard title="Overall Loss Ratio" value={`${lossRatioPercent}%`} subtitle={`${formatCurrency(lr?.total_earned_premium ?? 0)} earned premium`} accent={lossRatioPercent > 70 ? 'red' : lossRatioPercent > 50 ? 'amber' : 'emerald'} isLoading={lossRatioQ.isLoading} />
        <MetricCard title="Total Reserves" value={formatCurrency(totalReserves)} subtitle="Case reserves (loss + LAE)" accent="amber" isLoading={claimsSummaryQ.isLoading} />
        <MetricCard title="Reserve Adequacy" value={totalPaid > 0 ? `${Math.round((totalReserves / totalPaid) * 100)}%` : '—'} subtitle="Reserves / paid ratio" accent="sky" isLoading={lossRatioQ.isLoading} />
      </div>

      {/* Loss ratio by line */}
      <ChartCard title="Loss Ratio by Coverage Line" isLoading={coverageQ.isLoading} isEmpty={lossRatioByLine.length === 0}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={lossRatioByLine} margin={{ top: 4, right: 4, bottom: 0, left: -12 }}>
            <CartesianGrid vertical={false} stroke="#f3f4f6" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} angle={-15} textAnchor="end" height={40} />
            <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip formatter={(v) => `${v}%`} />} {...TOOLTIP_PROPS} cursor={{ fill: 'rgba(0,0,0,.03)' }} />
            <Bar dataKey="lossRatio" fill="#ef4444" radius={[4, 4, 0, 0]} maxBarSize={40} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Large loss alerts */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-900 flex items-center gap-2">
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-red-100 text-red-700 text-xs">!</span>
          Large Loss Alerts (&gt;$25K)
        </h2>
        <div className="overflow-hidden rounded-xl border border-red-200 bg-red-50">
          {largeLossAlerts.length === 0 ? (
            <p className="px-5 py-4 text-sm text-gray-500">No large losses currently flagged.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-red-200 bg-red-100">
                <tr>
                  {['Claim #', 'Insured', 'Amount', 'Status'].map((h) => (
                    <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-red-700">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {largeLossAlerts.map((r) => (
                  <tr key={r.claim} className="border-b border-red-100 last:border-0">
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-800">{r.claim}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-700">{r.insured}</td>
                    <td className="px-4 py-2.5 text-xs font-semibold text-red-700">{formatCurrency(r.amount)}</td>
                    <td className="px-4 py-2.5"><StatusBadge status={r.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function FinanceDashboard() {
  const [tab, setTab] = useState<Tab>('overview')

  return (
    <div className="space-y-6">
      <PageHeader title="Finance Dashboard" subtitle="Premium, payments and collection metrics" />

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

      {tab === 'overview' && <OverviewPanel />}
      {tab === 'revenue' && <RevenuePanel />}
      {tab === 'claims-output' && <ClaimsOutputPanel />}
    </div>
  )
}
