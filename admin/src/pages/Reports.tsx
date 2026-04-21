import { useState } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import MetricCard from '@/components/ui/MetricCard'
import ChartCard from '@/components/ui/ChartCard'
import ChartTooltip, { TOOLTIP_PROPS } from '@/components/ui/ChartTooltip'
import PageHeader from '@/components/ui/PageHeader'
import ExportButton from '@/components/ui/ExportButton'
import Select from '@/components/ui/Select'
import {
  usePipelineSummary,
  usePremiumByCarrier,
  useCoverageBreakdown,
  usePolicyStats,
  useRequesterStats,
  useClaimsSummary,
  useMonthlyPremium,
  useLossRatio,
  usePaymentSummary,
} from '@/hooks/useAnalytics'
import { formatCurrency } from '@/lib/formatters'

const DATE_RANGE_OPTIONS = [
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: '12m', label: 'Last 12 months' },
  { value: 'all', label: 'All time' },
]

// ── Shared palette ─────────────────────────────────────────────────────────

const COLORS = [
  '#ff5c00', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4',
  '#ec4899', '#84cc16', '#ef4444', '#6366f1', '#14b8a6',
]

const PAYMENT_COLORS: Record<string, string> = {
  Paid: '#10b981', Pending: '#f59e0b', Failed: '#ef4444', Refunded: '#8b5cf6',
}

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

// ── Component ──────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const [dateRange, setDateRange] = useState('all')
  const pipelineQ = usePipelineSummary()
  const carrierQ = usePremiumByCarrier()
  const coverageQ = useCoverageBreakdown()
  const policyQ = usePolicyStats()
  const requesterQ = useRequesterStats()
  const claimsQ = useClaimsSummary()
  const monthlyQ = useMonthlyPremium()
  const lossQ = useLossRatio()
  const paymentQ = usePaymentSummary()

  // ── derived ────────────────────────────────────────────────────────────

  const pipeline = pipelineQ.data ?? []
  const totalQuoted = pipeline
    .filter((s) => ['quoted', 'bound'].includes(s.status))
    .reduce((a, s) => a + s.count, 0)
  const totalBound = pipeline
    .filter((s) => s.status === 'bound')
    .reduce((a, s) => a + s.count, 0)
  const bindRatio = totalQuoted > 0 ? Math.round((totalBound / totalQuoted) * 100) : 0

  const lossRatioPercent = lossQ.data ? Math.round(lossQ.data.loss_ratio * 100) : 0
  const totalPaid = paymentQ.data?.total_paid ?? 0
  const totalPending = paymentQ.data?.total_pending ?? 0
  const collectionDenom = totalPaid + totalPending
  const collectionRate = collectionDenom > 0 ? Math.round((totalPaid / collectionDenom) * 100) : 0

  const monthlyChart = (monthlyQ.data ?? []).map((m) => ({
    month:
      m.month.length > 4
        ? new Date(m.month + '-01').toLocaleDateString('en-US', { month: 'short' })
        : m.month,
    premium: m.premium,
  }))

  const barData = pipeline.map((s) => ({ name: fmtStatus(s.status), count: s.count }))

  const pieData = consolidate(
    (coverageQ.data ?? []).map((c) => ({ name: c.coverage_type_display, value: c.count })),
  )

  const carrierData = (carrierQ.data ?? []).slice(0, 8).map((c) => ({
    carrier: (c.carrier || 'Unknown').replace(/_/g, ' ').replace(/\b\w/g, (ch: string) => ch.toUpperCase()),
    premium: c.total_premium,
  }))

  const paymentDonut = paymentQ.data
    ? [
        { name: 'Paid', value: paymentQ.data.total_paid },
        { name: 'Pending', value: paymentQ.data.total_pending },
        { name: 'Failed', value: paymentQ.data.total_failed },
        { name: 'Refunded', value: paymentQ.data.total_refunded },
      ].filter((d) => d.value > 0)
    : []

  const aeRows = requesterQ.data ?? []
  const totalRequests = aeRows.reduce((a, r) => a + r.request_count, 0)
  const totalAEPremium = aeRows.reduce((a, r) => a + r.total_premium, 0)
  const totalQuotedAE = aeRows.reduce((a, r) => a + r.quoted_count, 0)
  const totalBoundAE = aeRows.reduce((a, r) => a + r.bound_count, 0)

  // ── render ─────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Reports' }]} />
      <PageHeader
        title="Reports & Analytics"
        subtitle="Platform performance metrics, trends, and producer insights."
        action={
          <Select
            value={dateRange}
            onChange={setDateRange}
            options={DATE_RANGE_OPTIONS}
            size="sm"
            className="w-44"
          />
        }
      />

      {/* KPI row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Quote-to-Bind"
          value={`${bindRatio}%`}
          subtitle={`${totalBound} bound / ${totalQuoted} quoted`}
          isLoading={pipelineQ.isLoading}
          progress={bindRatio}
        />
        <MetricCard
          title="Loss Ratio"
          value={`${lossRatioPercent}%`}
          subtitle={
            lossQ.data
              ? `${formatCurrency(lossQ.data.total_paid_losses + lossQ.data.total_paid_lae)} losses`
              : undefined
          }
          accent={lossRatioPercent > 70 ? 'red' : lossRatioPercent > 50 ? 'amber' : 'emerald'}
          isLoading={lossQ.isLoading}
          progress={lossRatioPercent}
        />
        <MetricCard
          title="Written Premium"
          value={formatCurrency(policyQ.data?.total_premium ?? 0)}
          subtitle={`${policyQ.data?.active_count ?? 0} active policies`}
          isLoading={policyQ.isLoading}
        />
        <MetricCard
          title="Collection Rate"
          value={`${collectionRate}%`}
          subtitle={paymentQ.data ? `${formatCurrency(totalPaid)} of ${formatCurrency(collectionDenom)}` : undefined}
          accent={collectionRate >= 80 ? 'emerald' : collectionRate >= 50 ? 'amber' : 'red'}
          isLoading={paymentQ.isLoading}
          progress={collectionRate}
        />
      </div>

      {/* ── Premium Volume (full width, tall) ─────────────────────────── */}
      <ChartCard
        title="Premium Volume"
        subtitle="Monthly gross written premium from policy transactions"
        isLoading={monthlyQ.isLoading}
        isEmpty={monthlyChart.length === 0}
        height="h-80"
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={monthlyChart} margin={{ top: 4, right: 4, bottom: 0, left: -12 }}>
            <defs>
              <linearGradient id="reportPremiumGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ff5c00" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#ff5c00" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="#f3f4f6" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              content={<ChartTooltip formatter={(v) => formatCurrency(Number(v))} />}
              {...TOOLTIP_PROPS}
              cursor={{ stroke: '#ff5c00', strokeWidth: 1, strokeDasharray: '4 4' }}
            />
            <Area
              type="monotone"
              dataKey="premium"
              stroke="#ff5c00"
              fill="url(#reportPremiumGrad)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#ff5c00', strokeWidth: 0 }}
              name="Premium"
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ── Row 1: Pipeline + Coverage ────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartCard
          title="Quote Pipeline"
          subtitle="Brokered requests by current status"
          isLoading={pipelineQ.isLoading}
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
          title="Coverage Distribution"
          subtitle="Request volume by coverage type"
          isLoading={coverageQ.isLoading}
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
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
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
                    style={{ backgroundColor: COLORS[i % COLORS.length] }}
                  />
                  <span className="text-xs text-gray-600">{e.name}</span>
                  <span className="ml-auto text-xs font-semibold text-gray-900">{e.value}</span>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
      </div>

      {/* ── Claims Summary ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Open Claims"
          value={
            claimsQ.data
              ? String(
                  claimsQ.data.by_status
                    .filter((s) => s.status === 'open')
                    .reduce((a, s) => a + s.count, 0),
                )
              : '—'
          }
          subtitle="Currently open"
          isLoading={claimsQ.isLoading}
        />
        <MetricCard
          title="Total Reserves"
          value={formatCurrency(claimsQ.data?.total_reserves ?? 0)}
          subtitle="Case reserves (loss)"
          isLoading={claimsQ.isLoading}
        />
        <MetricCard
          title="Paid Losses"
          value={formatCurrency(claimsQ.data?.total_paid_loss ?? 0)}
          subtitle="Total paid to date"
          isLoading={claimsQ.isLoading}
        />
        <MetricCard
          title="Claim Statuses"
          value={
            claimsQ.data
              ? String(claimsQ.data.by_status.reduce((a, s) => a + s.count, 0))
              : '—'
          }
          subtitle="All claims total"
          isLoading={claimsQ.isLoading}
        />
      </div>

      {/* ── Row 2: Carrier + Payment donut ────────────────────────────── */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartCard
          title="Carrier Performance"
          subtitle="Total premium placed by carrier"
          isLoading={carrierQ.isLoading}
          isEmpty={carrierData.length === 0}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={carrierData} layout="vertical" margin={{ top: 0, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid horizontal={false} stroke="#f3f4f6" />
              <XAxis
                type="number"
                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="carrier"
                width={90}
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                content={<ChartTooltip formatter={(v) => formatCurrency(Number(v))} />}
                {...TOOLTIP_PROPS}
                cursor={{ fill: 'rgba(0,0,0,.03)' }}
              />
              <Bar dataKey="premium" fill="#10b981" radius={[0, 4, 4, 0]} maxBarSize={28} name="Premium" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Payment Breakdown"
          subtitle="Distribution of payment statuses"
          isLoading={paymentQ.isLoading}
          isEmpty={paymentDonut.length === 0}
        >
          <div className="flex h-full items-center gap-6">
            <div className="w-[55%]">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={paymentDonut}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={88}
                    paddingAngle={3}
                    stroke="none"
                  >
                    {paymentDonut.map((entry) => (
                      <Cell key={entry.name} fill={PAYMENT_COLORS[entry.name] ?? '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={<ChartTooltip formatter={(v) => formatCurrency(Number(v))} />}
                    {...TOOLTIP_PROPS}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col gap-2.5">
              {paymentDonut.map((e) => (
                <div key={e.name} className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: PAYMENT_COLORS[e.name] ?? '#94a3b8' }}
                  />
                  <span className="text-xs text-gray-600">{e.name}</span>
                  <span className="ml-auto text-xs font-semibold text-gray-900">{formatCurrency(e.value)}</span>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
      </div>

      {/* ── AE Performance ────────────────────────────────────────────── */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">AE / Producer Performance</h3>
            <p className="mt-0.5 text-xs text-gray-500">
              Account executive production volume, conversion, and premium placed.
            </p>
          </div>
          <ExportButton
            data={aeRows.map((r) => ({
              name: `${r.first_name} ${r.last_name}`,
              email: r.email,
              request_count: r.request_count,
              quoted_count: r.quoted_count,
              bound_count: r.bound_count,
              bind_rate: `${r.bind_rate.toFixed(0)}%`,
              total_premium: r.total_premium,
            })) as unknown as Record<string, unknown>[]}
            filename="ae-performance"
            columns={[
              { key: 'name', header: 'Account Executive' },
              { key: 'email', header: 'Email' },
              { key: 'request_count', header: 'Requests' },
              { key: 'quoted_count', header: 'Quoted' },
              { key: 'bound_count', header: 'Bound' },
              { key: 'bind_rate', header: 'Bind Rate' },
              { key: 'total_premium', header: 'Total Premium' },
            ]}
          />
        </div>

        {requesterQ.isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <div className="h-7 w-7 animate-spin rounded-full border-2 border-[#ff5c00] border-t-transparent" />
          </div>
        ) : aeRows.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50/80">
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Account Executive
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Email
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Requests
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Quoted
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Bound
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Bind Rate
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Total Premium
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {aeRows.map((r) => {
                  const rateColor =
                    r.bind_rate > 50
                      ? 'bg-emerald-50 text-emerald-700'
                      : r.bind_rate >= 20
                        ? 'bg-amber-50 text-amber-700'
                        : 'bg-gray-100 text-gray-600'
                  return (
                    <tr key={r.requester} className="transition-colors hover:bg-gray-50/60">
                      <td className="whitespace-nowrap px-5 py-3.5 text-sm font-medium text-gray-900">
                        {r.first_name} {r.last_name}
                      </td>
                      <td className="whitespace-nowrap px-5 py-3.5 text-sm text-gray-500">
                        {r.email}
                      </td>
                      <td className="whitespace-nowrap px-5 py-3.5 text-right text-sm">
                        <span className="inline-flex min-w-[28px] items-center justify-center rounded-full bg-purple-50 px-2 py-0.5 text-xs font-semibold text-purple-700">
                          {r.request_count}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-5 py-3.5 text-right text-sm text-gray-700">
                        {r.quoted_count}
                      </td>
                      <td className="whitespace-nowrap px-5 py-3.5 text-right text-sm text-gray-700">
                        {r.bound_count}
                      </td>
                      <td className="whitespace-nowrap px-5 py-3.5 text-right text-sm">
                        <span
                          className={`inline-flex min-w-[40px] items-center justify-center rounded-full px-2 py-0.5 text-xs font-semibold ${rateColor}`}
                        >
                          {r.bind_rate.toFixed(0)}%
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-5 py-3.5 text-right text-sm font-semibold text-gray-900">
                        {formatCurrency(r.total_premium)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
              <tfoot>
                <tr className="border-t border-gray-200 bg-gray-50/80">
                  <td className="px-5 py-3 text-sm font-semibold text-gray-900" colSpan={2}>
                    Totals
                  </td>
                  <td className="px-5 py-3 text-right text-sm font-semibold text-gray-900">{totalRequests}</td>
                  <td className="px-5 py-3 text-right text-sm font-semibold text-gray-900">{totalQuotedAE}</td>
                  <td className="px-5 py-3 text-right text-sm font-semibold text-gray-900">{totalBoundAE}</td>
                  <td className="px-5 py-3 text-right text-sm text-gray-400">-</td>
                  <td className="px-5 py-3 text-right text-sm font-semibold text-gray-900">
                    {formatCurrency(totalAEPremium)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        ) : (
          <div className="flex h-48 items-center justify-center text-sm text-gray-400">
            No AE data available
          </div>
        )}
      </div>
    </div>
  )
}
