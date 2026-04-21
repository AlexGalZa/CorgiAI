import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import {
  FileText, CheckCircle, DollarSign, Clock, Users, Link2, Copy, Check,
  ArrowRight, Shield, Download,
} from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import ChartCard from '@/components/ui/ChartCard'
import ChartTooltip, { TOOLTIP_PROPS } from '@/components/ui/ChartTooltip'
import StatusBadge from '@/components/ui/StatusBadge'
import CoverageTags from '@/components/ui/CoverageTags'
import DataTable, { type Column } from '@/components/ui/DataTable'
import PageHeader from '@/components/ui/PageHeader'
import Pagination from '@/components/ui/Pagination'
import { cn } from '@/lib/utils'
import { useCoverageBreakdown } from '@/hooks/useAnalytics'
import { useBrokeredRequests } from '@/hooks/useBrokeredRequests'
import { useQuotes, type QuoteListItem } from '@/hooks/useQuotes'
import { usePolicies, type PolicyListItem } from '@/hooks/usePolicies'
import { useOrganizations, type OrganizationListItem } from '@/hooks/useOrganizations'
import { useAuthStore } from '@/stores/auth'
import { formatCurrency, formatDate, formatRelativeTime } from '@/lib/formatters'
import type { BrokeredQuoteRequest } from '@/types'

const PIE_COLORS = ['#ff5c00', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899']

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

type Tab = 'overview' | 'my-clients' | 'commissions'

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'my-clients', label: 'My Clients' },
  { id: 'commissions', label: 'Commissions' },
]

// ─── Referral Link Card ──────────────────────────────────────────────────────

function ReferralLinkCard({ referralCode }: { referralCode: string }) {
  const [copied, setCopied] = useState(false)
  const referralUrl = `${window.location.origin}/get-quote?ref=${referralCode}`

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(referralUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const input = document.createElement('input')
      input.value = referralUrl
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex items-center gap-2 mb-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-orange-50">
          <Link2 className="h-4 w-4 text-[#ff5c00]" />
        </div>
        <h3 className="text-sm font-semibold text-gray-900">My Referral Link</h3>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
          <p className="truncate text-xs font-mono text-gray-600">{referralUrl}</p>
        </div>
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50"
        >
          {copied ? <><Check className="h-3.5 w-3.5 text-emerald-500" />Copied</> : <><Copy className="h-3.5 w-3.5" />Copy</>}
        </button>
      </div>
      <p className="mt-2 text-[11px] text-gray-400">
        Referral code: <span className="font-mono font-medium text-gray-500">{referralCode}</span>
      </p>
    </div>
  )
}

// ─── Overview panel ───────────────────────────────────────────────────────────

function OverviewPanel() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const coverageQ = useCoverageBreakdown()
  const allQ = useBrokeredRequests({ page_size: 100, ordering: '-created_at' })
  const recentQ = useBrokeredRequests({ page_size: 8, ordering: '-created_at' })
  const quotesQ = useQuotes({ ordering: '-created_at' })
  const policiesQ = usePolicies({ ordering: '-created_at' })

  const referralCode = user?.email?.split('@')[0]?.toLowerCase().replace(/[^a-z0-9]/g, '') || `broker-${user?.id ?? 0}`

  const all = allQ.data?.results ?? []
  const quotes = quotesQ.data?.results ?? []
  const policies = policiesQ.data?.results ?? []

  const totalClients = new Set([
    ...all.map((r) => r.company_name),
    ...quotes.map((q) => q.company_detail?.entity_legal_name),
  ]).size

  const pending = all.filter((r) => r.status === 'received' || r.status === 'submitted').length
  const quoted = all.filter((r) => r.status === 'quoted')
  const quotedPrem = quoted.reduce((s, r) => s + (parseFloat(r.premium_amount ?? '0') || 0), 0)
  const bound = all.filter((r) => r.status === 'bound' || r.is_bound)
  const boundPrem = bound.reduce((s, r) => s + (parseFloat(r.premium_amount ?? '0') || 0), 0)
  const totalPremium = policies.reduce((s, p) => s + (parseFloat(p.premium ?? '0') || 0), 0) + boundPrem
  const commission = boundPrem * 0.1
  const pendingCommission = quotedPrem * 0.1

  const statusCounts: Record<string, number> = {}
  for (const r of all) statusCounts[r.status] = (statusCounts[r.status] ?? 0) + 1
  const barData = Object.entries(statusCounts).map(([s, c]) => ({ name: fmtStatus(s), count: c }))

  const pieData = consolidate(
    (coverageQ.data ?? []).map((c) => ({ name: c.coverage_type_display, value: c.count })),
  )

  const clientCols: Column<BrokeredQuoteRequest>[] = [
    { key: 'company_name', header: 'Company' },
    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} variant="brokerage" /> },
    { key: 'carrier', header: 'Broker / Carrier', render: (r) => r.carrier_display || r.carrier || <span className="text-gray-400">—</span> },
    { key: 'blocker_detail', header: 'Blocker', render: (r) => r.blocker_detail ? (
      <span className="text-xs text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">{r.blocker_detail}</span>
    ) : <span className="text-gray-300">—</span> },
    { key: 'premium_amount', header: 'Premium', align: 'right', render: (r) => formatCurrency(r.premium_amount) },
    { key: 'is_bound', header: 'Bound', align: 'center', render: (r) => (
      <span className={r.is_bound ? 'text-emerald-600 font-semibold' : 'text-gray-400'}>{r.is_bound ? '✓' : '✗'}</span>
    ) },
    { key: 'quote', header: 'Quote', render: (r) => r.quote ? (
      <a href={`/quotes?id=${r.quote}`} onClick={(e) => e.stopPropagation()} className="text-[#ff5c00] hover:underline text-xs font-mono">#{r.quote}</a>
    ) : <span className="text-gray-300">—</span> },
    { key: 'created_at', header: 'Date', render: (r) => formatDate(r.created_at) },
  ]

  const policyCols: Column<PolicyListItem>[] = [
    { key: 'policy_number', header: 'Policy #' },
    { key: 'insured_legal_name', header: 'Insured' },
    { key: 'coverage_type', header: 'Coverage', render: (r) => fmtStatus(r.coverage_type) },
    { key: 'premium', header: 'Premium', align: 'right', render: (r) => formatCurrency(r.premium) },
    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
    { key: 'effective_date', header: 'Effective', render: (r) => formatDate(r.effective_date ?? '') },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard title="Referred Clients" value={totalClients} subtitle={`${all.length} total requests`} isLoading={allQ.isLoading} />
        <MetricCard title="Pending" value={pending} subtitle="Awaiting action" accent="amber" isLoading={allQ.isLoading} />
        <MetricCard title="Total Premium" value={formatCurrency(totalPremium)} subtitle={`${bound.length + policies.length} active`} isLoading={allQ.isLoading && policiesQ.isLoading} />
        <MetricCard title="Est. Commission" value={formatCurrency(commission)} subtitle="10% earned" accent="emerald" isLoading={allQ.isLoading} />
        <MetricCard title="Pending Commission" value={formatCurrency(pendingCommission)} subtitle="Awaiting bind" accent="sky" isLoading={allQ.isLoading} />
      </div>

      <ReferralLinkCard referralCode={referralCode} />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartCard title="Pipeline by Status" isLoading={allQ.isLoading} isEmpty={barData.length === 0}>
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

        <ChartCard title="Coverage Breakdown" isLoading={coverageQ.isLoading} isEmpty={pieData.length === 0}>
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

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-900">Pipeline (Brokered Requests)</h2>
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/brokered-requests?new=true')} className="inline-flex items-center gap-1.5 rounded-lg bg-[#ff5c00] px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-[#ea580c] transition-colors">
              + Add Manual Request
            </button>
            <button onClick={() => navigate('/brokered-requests')} className="inline-flex items-center gap-1 text-xs font-medium text-[#ff5c00] hover:text-[#ea580c] transition-colors">
              View all <ArrowRight className="h-3 w-3" />
            </button>
          </div>
        </div>
        <DataTable columns={clientCols} data={recentQ.data?.results ?? []} isLoading={recentQ.isLoading} onRowClick={(r) => navigate(`/brokered-requests?highlight=${r.id}`)} emptyMessage="No quotes assigned yet" />
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-900">My Quotes</h2>
          <button onClick={() => navigate('/quotes')} className="inline-flex items-center gap-1 text-xs font-medium text-[#ff5c00] hover:text-[#ea580c] transition-colors">
            View all <ArrowRight className="h-3 w-3" />
          </button>
        </div>
        <DataTable
          columns={[
            { key: 'quote_number', header: 'Quote #', render: (r) => (
              <a href={`/quotes?id=${r.id}`} onClick={(e) => e.stopPropagation()} className="text-[#ff5c00] hover:underline font-mono text-xs">{r.quote_number}</a>
            )},
            { key: 'company_detail', header: 'Client', render: (r) => r.company_detail?.entity_legal_name ?? '-' },
            { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
            { key: 'referral_partner', header: 'Assigned Broker', render: (r) => (r as unknown as { referral_partner_name?: string }).referral_partner_name ?? <span className="text-gray-400">—</span> },
            { key: 'coverage_types', header: 'Coverage', render: (r) => {
              const covs = (r as unknown as { coverages?: string[] }).coverages;
              return covs?.length ? <CoverageTags codes={covs} max={2} /> : <span className="text-gray-400">—</span>;
            }},
            { key: 'quote_amount', header: 'Premium', align: 'right' as const, render: (r) => formatCurrency(r.quote_amount) },
            { key: 'created_at', header: 'Date', render: (r) => formatDate(r.created_at) },
          ]}
          data={quotesQ.data?.results ?? []}
          isLoading={quotesQ.isLoading}
          onRowClick={(r) => navigate(`/quotes/${r.id}`)}
          emptyMessage="No quotes yet"
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-900">My Policies</h2>
          <button onClick={() => navigate('/policies')} className="inline-flex items-center gap-1 text-xs font-medium text-[#ff5c00] hover:text-[#ea580c] transition-colors">
            View all <ArrowRight className="h-3 w-3" />
          </button>
        </div>
        <DataTable columns={policyCols} data={policies.slice(0, 8)} isLoading={policiesQ.isLoading} onRowClick={(r) => navigate(`/policies/${r.id}`)} emptyMessage="No policies yet" />
      </div>
    </div>
  )
}

// ─── My Clients panel ────────────────────────────────────────────────────────

function MyClientsPanel() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')

  const orgsQ = useOrganizations({ page, search })
  const policiesQ = usePolicies({ ordering: '-created_at' })
  const policies = policiesQ.data?.results ?? []

  // Group policies by insured
  const policyCountByOrg: Record<string, number> = {}
  const premiumByOrg: Record<string, number> = {}
  for (const p of policies) {
    const key = p.insured_legal_name
    policyCountByOrg[key] = (policyCountByOrg[key] ?? 0) + 1
    premiumByOrg[key] = (premiumByOrg[key] ?? 0) + parseFloat(p.premium || '0')
  }

  const cols: Column<OrganizationListItem>[] = [
    { key: 'name', header: 'Client' },
    { key: 'owner_detail', header: 'Contact', render: (r) => r.owner_detail?.email ?? '—' },
    { key: 'id', header: 'Policies', align: 'right', render: (r) => policyCountByOrg[r.name] ?? 0 },
    { key: 'id', header: 'Total Premium', align: 'right', render: (r) => formatCurrency(premiumByOrg[r.name] ?? 0) },
    { key: 'created_at', header: 'Last Activity', render: (r) => formatDate(r.updated_at) },
    { key: 'id', header: 'Actions', render: (r) => (
      <div className="flex gap-2">
        <button onClick={(e) => { e.stopPropagation(); navigate(`/policies?search=${encodeURIComponent(r.name)}`) }} className="text-xs text-[#ff5c00] hover:underline">Policies</button>
        <button onClick={(e) => { e.stopPropagation(); navigate(`/claims?search=${encodeURIComponent(r.name)}`) }} className="text-xs text-[#ff5c00] hover:underline">Claims</button>
      </div>
    )},
  ]

  return (
    <div className="space-y-4">
      <input
        className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#ff5c00] focus:ring-1 focus:ring-[#ff5c00]"
        placeholder="Search clients…"
        value={search}
        onChange={(e) => { setSearch(e.target.value); setPage(1) }}
      />
      <DataTable columns={cols} data={orgsQ.data?.results ?? []} isLoading={orgsQ.isLoading} emptyMessage="No clients found" />
      {orgsQ.data && <Pagination page={page} pageSize={25} total={orgsQ.data.count} onPageChange={setPage} />}
    </div>
  )
}

// ─── Commissions panel ────────────────────────────────────────────────────────

function CommissionsPanel() {
  const navigate = useNavigate()
  const allQ = useBrokeredRequests({ page_size: 100, ordering: '-created_at' })
  const policiesQ = usePolicies({ ordering: '-created_at' })

  const all = allQ.data?.results ?? []
  const policies = policiesQ.data?.results ?? []

  const bound = all.filter((r) => r.status === 'bound' || r.is_bound)
  const quoted = all.filter((r) => r.status === 'quoted')

  const earnedCommission = bound.reduce((s, r) => s + (parseFloat(r.premium_amount ?? '0') || 0) * 0.1, 0)
  const pendingCommission = quoted.reduce((s, r) => s + (parseFloat(r.premium_amount ?? '0') || 0) * 0.1, 0)
  const totalProduction = policies.reduce((s, p) => s + (parseFloat(p.premium ?? '0') || 0), 0)

  interface CommRow {
    id: string | number
    policy_number: string
    insured: string
    premium: number
    commission_rate: number
    commission_amount: number
    status: string
    effective_date: string
  }

  const commRows: CommRow[] = policies.slice(0, 20).map((p) => ({
    id: p.id,
    policy_number: p.policy_number,
    insured: p.insured_legal_name,
    premium: parseFloat(p.premium ?? '0'),
    commission_rate: 10,
    commission_amount: parseFloat(p.premium ?? '0') * 0.1,
    status: p.status === 'active' ? 'earned' : 'pending',
    effective_date: p.effective_date ?? '',
  }))

  const cols: Column<CommRow>[] = [
    { key: 'policy_number', header: 'Policy #' },
    { key: 'insured', header: 'Insured' },
    { key: 'premium', header: 'Premium', align: 'right', render: (r) => formatCurrency(r.premium) },
    { key: 'commission_rate', header: 'Rate', align: 'right', render: (r) => `${r.commission_rate}%` },
    { key: 'commission_amount', header: 'Commission', align: 'right', render: (r) => (
      <span className="font-semibold text-emerald-700">{formatCurrency(r.commission_amount)}</span>
    )},
    { key: 'status', header: 'Status', render: (r) => (
      <span className={cn(
        'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
        r.status === 'earned' ? 'bg-emerald-100 text-emerald-700' :
        r.status === 'paid' ? 'bg-sky-100 text-sky-700' :
        'bg-amber-100 text-amber-700'
      )}>
        {r.status.charAt(0).toUpperCase() + r.status.slice(1)}
      </span>
    )},
    { key: 'effective_date', header: 'Effective', render: (r) => formatDate(r.effective_date) },
  ]

  const handleDownload = () => {
    const csv = [
      ['Policy #', 'Insured', 'Premium', 'Rate', 'Commission', 'Status', 'Effective Date'],
      ...commRows.map((r) => [r.policy_number, r.insured, r.premium, `${r.commission_rate}%`, r.commission_amount, r.status, r.effective_date]),
    ].map((row) => row.join(',')).join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'commission-statement.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard title="Earned Commission" value={formatCurrency(earnedCommission)} subtitle="From bound policies" accent="emerald" isLoading={allQ.isLoading} />
        <MetricCard title="Pending Payouts" value={formatCurrency(pendingCommission)} subtitle="Awaiting bind" accent="amber" isLoading={allQ.isLoading} />
        <MetricCard title="Total Production" value={formatCurrency(totalProduction)} subtitle="GWP managed" accent="sky" isLoading={policiesQ.isLoading} />
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-900">Commission by Policy</h2>
          <button
            onClick={handleDownload}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 shadow-sm hover:bg-gray-50"
          >
            <Download className="h-3.5 w-3.5" />
            Download Statement
          </button>
        </div>
        <DataTable
          columns={cols}
          data={commRows}
          isLoading={policiesQ.isLoading}
          onRowClick={(r) => navigate(`/policies/${r.id}`)}
          emptyMessage="No commission data found"
        />
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function BrokerDashboard() {
  const [tab, setTab] = useState<Tab>('overview')

  return (
    <div className="space-y-6">
      <PageHeader title="Broker Dashboard" subtitle="Your referrals, quotes, policies and commissions at a glance" />

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
      {tab === 'my-clients' && <MyClientsPanel />}
      {tab === 'commissions' && <CommissionsPanel />}
    </div>
  )
}
