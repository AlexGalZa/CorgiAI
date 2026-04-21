import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import MetricCard from '@/components/ui/MetricCard'
import DataTable, { type Column } from '@/components/ui/DataTable'
import PageHeader from '@/components/ui/PageHeader'
import StatusBadge from '@/components/ui/StatusBadge'
import Select from '@/components/ui/Select'
import Pagination from '@/components/ui/Pagination'
import { cn } from '@/lib/utils'
import { formatDate } from '@/lib/formatters'
import { useOrganizations, type OrganizationListItem } from '@/hooks/useOrganizations'
import { usePolicies, type PolicyListItem } from '@/hooks/usePolicies'
import { useClaims } from '@/hooks/useClaims'

// ─── Types ───────────────────────────────────────────────────────────────────

interface Ticket {
  id: string
  subject: string
  requester: string
  status: 'open' | 'in_progress' | 'resolved'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  assigned_agent: string
  created_at: string
  updated_at: string
}

interface EndorsementRequest {
  id: string
  type: 'coverage_change' | 'additional_insured' | 'name_change' | 'other'
  policy_number: string
  requester: string
  description: string
  status: 'pending' | 'in_review' | 'approved' | 'rejected'
  created_at: string
}

// ─── Mock data generators (until dedicated endpoints exist) ───────────────────

function mockTickets(): Ticket[] {
  return [
    { id: 'TKT-001', subject: 'Policy document request', requester: 'Acme Corp', status: 'open', priority: 'medium', assigned_agent: 'Support Team', created_at: new Date(Date.now() - 3600000).toISOString(), updated_at: new Date().toISOString() },
    { id: 'TKT-002', subject: 'Certificate of insurance needed', requester: 'Tech Startup LLC', status: 'in_progress', priority: 'high', assigned_agent: 'Support Team', created_at: new Date(Date.now() - 7200000).toISOString(), updated_at: new Date().toISOString() },
    { id: 'TKT-003', subject: 'Billing question on renewal', requester: 'Global Services Inc', status: 'open', priority: 'low', assigned_agent: 'Unassigned', created_at: new Date(Date.now() - 86400000).toISOString(), updated_at: new Date().toISOString() },
    { id: 'TKT-004', subject: 'How to add additional insured?', requester: 'Retail Co', status: 'resolved', priority: 'low', assigned_agent: 'Support Team', created_at: new Date(Date.now() - 172800000).toISOString(), updated_at: new Date().toISOString() },
  ]
}

function mockEndorsements(): EndorsementRequest[] {
  return [
    { id: 'END-001', type: 'additional_insured', policy_number: 'CGL-CA-26-000001-01', requester: 'Acme Corp', description: 'Add landlord as additional insured', status: 'pending', created_at: new Date(Date.now() - 86400000).toISOString() },
    { id: 'END-002', type: 'coverage_change', policy_number: 'DO-NY-26-000005-01', requester: 'Tech Startup LLC', description: 'Increase D&O limit to $2M', status: 'in_review', created_at: new Date(Date.now() - 172800000).toISOString() },
    { id: 'END-003', type: 'name_change', policy_number: 'TEO-TX-26-000010-01', requester: 'Rebranded Co', description: 'Company name change to NewBrand Inc', status: 'pending', created_at: new Date(Date.now() - 259200000).toISOString() },
  ]
}

// ─── Tab definitions ─────────────────────────────────────────────────────────

type Tab = 'dashboard' | 'tickets' | 'endorsements' | 'policyholders'

const TABS: { id: Tab; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'tickets', label: 'Tickets' },
  { id: 'endorsements', label: 'Endorsements' },
  { id: 'policyholders', label: 'Policyholders' },
]

const PRIORITY_COLORS: Record<string, string> = {
  low: 'bg-gray-100 text-gray-600',
  medium: 'bg-amber-100 text-amber-700',
  high: 'bg-orange-100 text-orange-700',
  urgent: 'bg-red-100 text-red-700',
}

const ENDORSEMENT_TYPE_LABELS: Record<string, string> = {
  coverage_change: 'Coverage Change',
  additional_insured: 'Additional Insured',
  name_change: 'Name Change',
  other: 'Other',
}

// ─── Sub-panels ───────────────────────────────────────────────────────────────

function DashboardPanel() {
  const claimsQ = useClaims({ status: 'submitted' })
  const policiesQ = usePolicies({ status: 'active' })

  const openClaimsCount = claimsQ.data?.count ?? 0
  const pendingEndorsements = mockEndorsements().filter((e) => e.status === 'pending').length
  const openTickets = mockTickets().filter((t) => t.status !== 'resolved').length

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        title="Open Tickets"
        value={openTickets}
        subtitle="Awaiting resolution"
        isLoading={false}
      />
      <MetricCard
        title="Avg Response Time"
        value="2.4h"
        subtitle="Target: 4h"
        accent="sky"
        progress={60}
        isLoading={false}
      />
      <MetricCard
        title="CSAT Score"
        value="—"
        subtitle="Score coming soon"
        accent="emerald"
        isLoading={false}
      />
      <MetricCard
        title="Pending Endorsements"
        value={pendingEndorsements}
        subtitle="Awaiting review"
        accent="amber"
        isLoading={false}
      />
    </div>
  )
}

function TicketsPanel() {
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const tickets = mockTickets()

  const filtered = tickets.filter((t) => {
    if (statusFilter && t.status !== statusFilter) return false
    if (priorityFilter && t.priority !== priorityFilter) return false
    return true
  })

  const cols: Column<Ticket>[] = [
    { key: 'id', header: 'Ticket #' },
    { key: 'subject', header: 'Subject' },
    { key: 'requester', header: 'Customer' },
    { key: 'status', header: 'Status', render: (r) => (
      <span className={cn(
        'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
        r.status === 'resolved' ? 'bg-emerald-100 text-emerald-700' :
        r.status === 'in_progress' ? 'bg-sky-100 text-sky-700' :
        'bg-amber-100 text-amber-700'
      )}>
        {r.status.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
      </span>
    )},
    { key: 'priority', header: 'Priority', render: (r) => (
      <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', PRIORITY_COLORS[r.priority])}>
        {r.priority.charAt(0).toUpperCase() + r.priority.slice(1)}
      </span>
    )},
    { key: 'assigned_agent', header: 'Assigned To' },
    { key: 'created_at', header: 'Created', render: (r) => formatDate(r.created_at) },
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <Select
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { value: '', label: 'All Statuses' },
            { value: 'open', label: 'Open' },
            { value: 'in_progress', label: 'In Progress' },
            { value: 'resolved', label: 'Resolved' },
          ]}
        />
        <Select
          value={priorityFilter}
          onChange={setPriorityFilter}
          options={[
            { value: '', label: 'All Priorities' },
            { value: 'urgent', label: 'Urgent' },
            { value: 'high', label: 'High' },
            { value: 'medium', label: 'Medium' },
            { value: 'low', label: 'Low' },
          ]}
        />
      </div>
      <DataTable columns={cols} data={filtered} isLoading={false} emptyMessage="No tickets found" />
    </div>
  )
}

function EndorsementsPanel() {
  const endorsements = mockEndorsements()

  const cols: Column<EndorsementRequest>[] = [
    { key: 'id', header: 'Request #' },
    { key: 'type', header: 'Type', render: (r) => ENDORSEMENT_TYPE_LABELS[r.type] ?? r.type },
    { key: 'policy_number', header: 'Policy' },
    { key: 'requester', header: 'Customer' },
    { key: 'description', header: 'Details' },
    { key: 'status', header: 'Status', render: (r) => (
      <span className={cn(
        'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
        r.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
        r.status === 'rejected' ? 'bg-red-100 text-red-700' :
        r.status === 'in_review' ? 'bg-sky-100 text-sky-700' :
        'bg-amber-100 text-amber-700'
      )}>
        {r.status.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
      </span>
    )},
    { key: 'created_at', header: 'Requested', render: (r) => formatDate(r.created_at) },
  ]

  return (
    <div className="space-y-4">
      <div className="text-xs text-gray-500 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
        Endorsement requests submitted by customers via the portal. Route to underwriting for approval.
      </div>
      <DataTable columns={cols} data={endorsements} isLoading={false} emptyMessage="No pending endorsements" />
    </div>
  )
}

function PolicyholdersPanel() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')

  const { data, isLoading } = useOrganizations({ page, search })

  const cols: Column<OrganizationListItem>[] = [
    { key: 'name', header: 'Organization' },
    { key: 'owner_detail', header: 'Contact', render: (r) => r.owner_detail?.email ?? '—' },
    { key: 'is_personal', header: 'Type', render: (r) => (
      <span className={cn(
        'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
        r.is_personal ? 'bg-gray-100 text-gray-600' : 'bg-sky-100 text-sky-700'
      )}>
        {r.is_personal ? 'Personal' : 'Business'}
      </span>
    )},
    { key: 'created_at', header: 'Customer Since', render: (r) => formatDate(r.created_at) },
    { key: 'id', header: 'Quick Links', render: (r) => (
      <div className="flex gap-2">
        <button
          onClick={(e) => { e.stopPropagation(); navigate(`/policies?organization=${r.id}`) }}
          className="text-xs text-[#ff5c00] hover:underline"
        >
          Policies
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); navigate(`/payments?organization=${r.id}`) }}
          className="text-xs text-[#ff5c00] hover:underline"
        >
          Billing
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); navigate(`/claims?organization=${r.id}`) }}
          className="text-xs text-[#ff5c00] hover:underline"
        >
          Claims
        </button>
      </div>
    )},
  ]

  return (
    <div className="space-y-4">
      <input
        className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#ff5c00] focus:ring-1 focus:ring-[#ff5c00]"
        placeholder="Search policyholders…"
        value={search}
        onChange={(e) => { setSearch(e.target.value); setPage(1) }}
      />
      <DataTable
        columns={cols}
        data={data?.results ?? []}
        isLoading={isLoading}
        emptyMessage="No policyholders found"
      />
      {data && (
        <Pagination page={page} pageSize={25} total={data.count} onPageChange={setPage} />
      )}
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function CustomerSupportDashboard() {
  const [tab, setTab] = useState<Tab>('dashboard')

  return (
    <div className="space-y-6">
      <PageHeader title="Customer Support" subtitle="Tickets, endorsement requests, and policyholder management" />

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

      {tab === 'dashboard' && <DashboardPanel />}
      {tab === 'tickets' && <TicketsPanel />}
      {tab === 'endorsements' && <EndorsementsPanel />}
      {tab === 'policyholders' && <PolicyholdersPanel />}
    </div>
  )
}
