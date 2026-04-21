/**
 * AE + Underwriting Dashboard
 * Wraps the base OperationsDashboard with extra tabs:
 * - Risk Assessment (ae_underwriting only)
 * - Renewals
 * - Pipeline (kanban summary)
 *
 * The AE role gets Renewals + Pipeline.
 * The AE + Underwriting role gets Risk Assessment too.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import OperationsDashboard from './OperationsDashboard'
import MetricCard from '@/components/ui/MetricCard'
import DataTable, { type Column } from '@/components/ui/DataTable'
import PageHeader from '@/components/ui/PageHeader'
import StatusBadge from '@/components/ui/StatusBadge'
import Select from '@/components/ui/Select'
import Pagination from '@/components/ui/Pagination'
import ChartCard from '@/components/ui/ChartCard'
import ChartTooltip, { TOOLTIP_PROPS } from '@/components/ui/ChartTooltip'
import { cn } from '@/lib/utils'
import api from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/formatters'
import { useAuthStore } from '@/stores/auth'
import { usePolicies, type PolicyListItem } from '@/hooks/usePolicies'
import { useQuotes, type QuoteListItem } from '@/hooks/useQuotes'
import { useBrokeredRequests } from '@/hooks/useBrokeredRequests'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts'

// ─── Types ───────────────────────────────────────────────────────────────────

type Tab = 'dashboard' | 'risk-assessment' | 'renewals' | 'pipeline'
type AETab = 'dashboard' | 'renewals' | 'pipeline'

// ─── Risk Assessment panel ────────────────────────────────────────────────────

function RiskAssessmentPanel() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)

  const quotesQ = useQuotes({ status: 'needs_review', ordering: '-created_at', page })

  const cols: Column<QuoteListItem>[] = [
    { key: 'quote_number', header: 'Quote #' },
    { key: 'company_detail', header: 'Company', render: (r) => r.company_detail?.entity_legal_name ?? '—' },
    { key: 'quote_amount', header: 'Est. Premium', align: 'right', render: (r) => formatCurrency(r.quote_amount) },
    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
    { key: 'created_at', header: 'Submitted', render: (r) => formatDate(r.created_at) },
    { key: 'id', header: 'Actions', render: (r) => (
      <div className="flex gap-2">
        <button
          onClick={(e) => { e.stopPropagation(); navigate(`/quotes/${r.id}`) }}
          className="text-xs font-medium text-[#ff5c00] hover:underline"
        >
          Review
        </button>
      </div>
    )},
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard
          title="Pending UW Review"
          value={quotesQ.data?.count ?? 0}
          subtitle="Quotes needing review"
          accent="amber"
          isLoading={quotesQ.isLoading}
        />
        <MetricCard
          title="Risk Factors"
          value="—"
          subtitle="AI risk scoring coming soon"
          accent="sky"
          isLoading={false}
        />
        <MetricCard
          title="Avg Review Time"
          value="—"
          subtitle="Time to decision"
          accent="emerald"
          isLoading={false}
        />
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-900">Quotes Pending Underwriting Review</h2>
        <DataTable
          columns={cols}
          data={quotesQ.data?.results ?? []}
          isLoading={quotesQ.isLoading}
          onRowClick={(r) => navigate(`/quotes/${r.id}`)}
          emptyMessage="No quotes pending review"
        />
        {quotesQ.data && (
          <Pagination page={page} pageSize={25} total={quotesQ.data.count} onPageChange={setPage} />
        )}
      </div>

      <div className="rounded-lg border border-sky-200 bg-sky-50 p-4 text-sm text-sky-800">
        <p className="font-semibold mb-1">Research Links</p>
        <ul className="space-y-1 text-xs">
          <li>• <a href="https://opencorporates.com" target="_blank" rel="noreferrer" className="underline hover:text-sky-900">OpenCorporates</a> — Company research</li>
          <li>• <a href="https://www.dnb.com" target="_blank" rel="noreferrer" className="underline hover:text-sky-900">Dun &amp; Bradstreet</a> — Business credit</li>
          <li>• <a href="https://www.secretary.state.mn.us/businesses" target="_blank" rel="noreferrer" className="underline hover:text-sky-900">Secretary of State</a> — Entity verification</li>
        </ul>
      </div>
    </div>
  )
}

// ─── Renewals panel ───────────────────────────────────────────────────────────

function RenewalsPanel() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('active')

  // Policies expiring in next 90 days
  const today = new Date()
  const in90Days = new Date(today)
  in90Days.setDate(today.getDate() + 90)

  const policiesQ = usePolicies({
    status: statusFilter || 'active',
    effective_date_after: today.toISOString().split('T')[0],
    page,
  })

  // For renewals we need expiring policies — use expiration_date filter if available
  // Fall back to all active policies sorted by expiration
  const allActiveQ = usePolicies({ status: 'active', ordering: 'expiration_date', page })

  const policies = allActiveQ.data?.results ?? []
  const today_ts = Date.now()
  const expiringPolicies = policies.filter((p) => {
    if (!p.expiration_date) return false
    const expTs = new Date(p.expiration_date).getTime()
    return expTs >= today_ts && expTs <= today_ts + 90 * 86400 * 1000
  })

  const expiringSoon = expiringPolicies.filter((p) => {
    const expTs = new Date(p.expiration_date!).getTime()
    return expTs <= today_ts + 30 * 86400 * 1000
  }).length

  const cols: Column<PolicyListItem>[] = [
    { key: 'policy_number', header: 'Policy #' },
    { key: 'insured_legal_name', header: 'Insured' },
    { key: 'coverage_type', header: 'Coverage', render: (r) => r.coverage_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) },
    { key: 'premium', header: 'Premium', align: 'right', render: (r) => formatCurrency(r.premium) },
    { key: 'expiration_date', header: 'Expires', render: (r) => {
      if (!r.expiration_date) return '—'
      const daysLeft = Math.round((new Date(r.expiration_date).getTime() - today_ts) / 86400000)
      const color = daysLeft <= 30 ? 'text-red-600' : daysLeft <= 60 ? 'text-amber-600' : 'text-gray-700'
      return <span className={color}>{formatDate(r.expiration_date)} ({daysLeft}d)</span>
    }},
    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard title="Expiring ≤30d" value={expiringSoon} subtitle="Needs immediate action" accent="red" isLoading={allActiveQ.isLoading} />
        <MetricCard title="Expiring 31–60d" value={expiringPolicies.filter(p => {
          const d = Math.round((new Date(p.expiration_date!).getTime() - today_ts) / 86400000)
          return d > 30 && d <= 60
        }).length} subtitle="Action soon" accent="amber" isLoading={allActiveQ.isLoading} />
        <MetricCard title="Expiring 61–90d" value={expiringPolicies.filter(p => {
          const d = Math.round((new Date(p.expiration_date!).getTime() - today_ts) / 86400000)
          return d > 60 && d <= 90
        }).length} subtitle="Plan ahead" accent="sky" isLoading={allActiveQ.isLoading} />
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-900">Policies Approaching Renewal (90 days)</h2>
        <DataTable
          columns={cols}
          data={expiringPolicies}
          isLoading={allActiveQ.isLoading}
          onRowClick={(r) => navigate(`/policies/${r.id}`)}
          emptyMessage="No policies expiring in next 90 days"
        />
      </div>
    </div>
  )
}

// ─── Pipeline panel ───────────────────────────────────────────────────────────

function PipelinePanel() {
  const navigate = useNavigate()
  const allQ = useBrokeredRequests({ page_size: 100, ordering: '-created_at' })
  const quotesQ = useQuotes({ ordering: '-created_at' })

  const all = allQ.data?.results ?? []
  const quotes = quotesQ.data?.results ?? []

  // Kanban columns: submitted → quoted → purchased
  const stages = [
    { id: 'submitted', label: 'Submitted', color: 'bg-amber-50 border-amber-200' },
    { id: 'quoted', label: 'Quoted', color: 'bg-sky-50 border-sky-200' },
    { id: 'purchased', label: 'Purchased', color: 'bg-emerald-50 border-emerald-200' },
    { id: 'needs_review', label: 'Needs Review', color: 'bg-orange-50 border-orange-200' },
    { id: 'declined', label: 'Declined', color: 'bg-red-50 border-red-200' },
  ]

  const statusCounts: Record<string, number> = {}
  const statusPremium: Record<string, number> = {}
  for (const q of quotes) {
    statusCounts[q.status] = (statusCounts[q.status] ?? 0) + 1
    statusPremium[q.status] = (statusPremium[q.status] ?? 0) + parseFloat(q.quote_amount || '0')
  }

  const barData = stages.map((s) => ({
    name: s.label,
    count: statusCounts[s.id] ?? 0,
    premium: statusPremium[s.id] ?? 0,
  }))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {stages.map((s) => (
          <MetricCard
            key={s.id}
            title={s.label}
            value={statusCounts[s.id] ?? 0}
            subtitle={formatCurrency(statusPremium[s.id] ?? 0)}
            isLoading={quotesQ.isLoading}
          />
        ))}
      </div>

      <ChartCard title="Pipeline by Stage" isLoading={quotesQ.isLoading} isEmpty={barData.every(d => d.count === 0)}>
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

      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-900">All Quotes</h2>
        <DataTable
          columns={[
            { key: 'quote_number', header: 'Quote #' },
            { key: 'company_detail', header: 'Company', render: (r) => r.company_detail?.entity_legal_name ?? '—' },
            { key: 'quote_amount', header: 'Premium', align: 'right', render: (r) => formatCurrency(r.quote_amount) },
            { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
            { key: 'created_at', header: 'Created', render: (r) => formatDate(r.created_at) },
          ] as Column<QuoteListItem>[]}
          data={(quotesQ.data?.results ?? []).slice(0, 20)}
          isLoading={quotesQ.isLoading}
          onRowClick={(r) => navigate(`/quotes/${r.id}`)}
          emptyMessage="No quotes found"
        />
      </div>
    </div>
  )
}

// ─── AE + UW Dashboard (full tabs) ───────────────────────────────────────────

const AE_UW_TABS: { id: Tab; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'risk-assessment', label: 'Risk Assessment' },
  { id: 'renewals', label: 'Renewals' },
  { id: 'pipeline', label: 'Pipeline' },
]

export function AEUnderwritingDashboard() {
  const [tab, setTab] = useState<Tab>('dashboard')

  return (
    <div className="space-y-6">
      {tab !== 'dashboard' && (
        <PageHeader
          title="Operations"
          subtitle="Underwriting, renewals, and pipeline management"
        />
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-1 -mb-px">
          {AE_UW_TABS.map((t) => (
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

      {tab === 'dashboard' && <OperationsDashboard />}
      {tab === 'risk-assessment' && <RiskAssessmentPanel />}
      {tab === 'renewals' && <RenewalsPanel />}
      {tab === 'pipeline' && <PipelinePanel />}
    </div>
  )
}

// ─── AE Dashboard (no risk assessment) ───────────────────────────────────────

const AE_TABS: { id: AETab; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'renewals', label: 'Renewals' },
  { id: 'pipeline', label: 'Pipeline' },
]

export function AEDashboard() {
  const [tab, setTab] = useState<AETab>('dashboard')

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-1 -mb-px">
          {AE_TABS.map((t) => (
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

      {tab === 'dashboard' && <OperationsDashboard />}
      {tab === 'renewals' && <RenewalsPanel />}
      {tab === 'pipeline' && <PipelinePanel />}
    </div>
  )
}

export default AEUnderwritingDashboard
