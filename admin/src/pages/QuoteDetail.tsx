import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, FileText, DollarSign, Calendar, Shield, BarChart3, Layers, ClipboardList, Clock, ChevronDown, ChevronRight } from 'lucide-react'
import { useQuote, useQuotePolicies, useQuoteBrokeredRequests } from '@/hooks/useQuotes'
import { useAuditLog } from '@/hooks/useAuditLog'
import { usePermissions } from '@/lib/permissions'
import { formatCurrency, formatDate } from '@/lib/formatters'
import StatusBadge from '@/components/ui/StatusBadge'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import QueryError from '@/components/ui/QueryError'
import ActivityTimeline from '@/components/ui/ActivityTimeline'
import CustomerContextSidebar from '@/components/quotes/CustomerContextSidebar'
import { SpinnerOverlay } from '@/components/ui/Spinner'
import DataTable, { type Column } from '@/components/ui/DataTable'
import type { Policy } from '@/types'

// ─── Sub-components ─────────────────────────────────────────────────────────

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between py-2.5 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="ml-4 text-right font-medium text-gray-900">{value ?? '—'}</span>
    </div>
  )
}

function SectionHeader({ icon: Icon, label }: { icon: React.ComponentType<{ className?: string }>; label: string }) {
  return (
    <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-400">
      <Icon className="h-3.5 w-3.5" />
      {label}
    </div>
  )
}

function JsonTable({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data)
  if (entries.length === 0) return <p className="text-sm text-gray-400">No data</p>

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      <table className="min-w-full">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50/80">
            <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Field</th>
            <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Value</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {entries.map(([key, value]) => (
            <tr key={key}>
              <td className="whitespace-nowrap px-4 py-2.5 text-sm font-medium text-gray-700">
                {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </td>
              <td className="px-4 py-2.5 text-sm text-gray-600">
                {typeof value === 'object' && value !== null
                  ? JSON.stringify(value, null, 2)
                  : String(value ?? '—')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Table Columns ──────────────────────────────────────────────────────────

const policyCols: Column<Policy>[] = [
  {
    key: 'policy_number',
    header: 'Policy #',
    render: (r) => (
      <Link to={`/policies/${r.id}`} className="font-medium text-[#ff5c00] hover:underline" onClick={(e) => e.stopPropagation()}>
        {r.policy_number || `Policy #${r.id}`}
      </Link>
    ),
  },
  { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} variant="policy" /> },
  { key: 'coverage_type', header: 'Coverage', render: (r) => r.coverage_type?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) || '—' },
  { key: 'premium', header: 'Premium', align: 'right', render: (r) => formatCurrency(r.premium) },
  { key: 'effective_date', header: 'Effective', render: (r) => formatDate(r.effective_date ?? '') },
]

const brokeredCols: Column<Record<string, unknown>>[] = [
  {
    key: 'id',
    header: 'ID',
    render: (r) => (
      <Link to="/brokered-requests" className="font-medium text-[#ff5c00] hover:underline" onClick={(e) => e.stopPropagation()}>
        #{String(r.id)}
      </Link>
    ),
  },
  { key: 'company_name', header: 'Company', render: (r) => String(r.company_name ?? '—') },
  { key: 'status', header: 'Status', render: (r) => <StatusBadge status={String(r.status ?? '')} variant="brokerage" /> },
  { key: 'carrier', header: 'Carrier', render: (r) => String(r.carrier_display ?? r.carrier ?? '—') },
  { key: 'created_at', header: 'Created', render: (r) => formatDate(String(r.created_at ?? '')) },
]

// ─── Main Component ─────────────────────────────────────────────────────────

export default function QuoteDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { canDoUnderwriterOverrides } = usePermissions()
  const quote = useQuote(id)
  const policies = useQuotePolicies(id)
  const brokeredRequests = useQuoteBrokeredRequests(id)
  const auditLog = useAuditLog('Quote', id)
  const [auditOpen, setAuditOpen] = useState(false)

  if (quote.isLoading) return <SpinnerOverlay height="h-96" />
  if (quote.isError) return <QueryError message="Failed to load quote details" onRetry={quote.refetch} />

  const q = quote.data
  if (!q) return <div className="py-16 text-center text-sm text-gray-500">Quote not found</div>

  return (
    <div className="flex items-start gap-6">
      {/* Main content */}
      <div className="min-w-0 flex-1 space-y-6">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: 'Quotes', href: '/quotes' },
          { label: q.quote_number || `Q-${q.id}` },
        ]}
      />

      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/quotes')}
          className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          aria-label="Go back"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-gray-900">
              {q.quote_number || `Q-${q.id}`}
            </h1>
            <StatusBadge status={q.status} />
          </div>
          <p className="text-sm text-gray-500">{q.company_detail?.entity_legal_name}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">Quote Amount</p>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(q.quote_amount)}</p>
        </div>
      </div>

      {/* Info Grid (2 columns) */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Company & Quote Info */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <SectionHeader icon={FileText} label="Quote Information" />
          <div className="divide-y divide-gray-100">
            <DetailRow label="Company" value={q.company_detail?.entity_legal_name} />
            <DetailRow label="Quote Number" value={q.quote_number} />
            <DetailRow label="Status" value={<StatusBadge status={q.status} />} />
            <DetailRow label="Quote Amount" value={formatCurrency(q.quote_amount)} />
          </div>
        </div>

        {/* Billing & Details */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <SectionHeader icon={DollarSign} label="Billing & Details" />
          <div className="divide-y divide-gray-100">
            <DetailRow
              label="Billing Frequency"
              value={
                q.billing_frequency
                  ? q.billing_frequency.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
                  : undefined
              }
            />
            <DetailRow label="Promo Code" value={q.promo_code || '—'} />
            <DetailRow
              label="Current Step"
              value={
                q.current_step
                  ? q.current_step.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
                  : undefined
              }
            />
            <DetailRow label="Referral Partner" value={q.referral_partner || '—'} />
          </div>
        </div>

        {/* Dates */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <SectionHeader icon={Calendar} label="Dates" />
          <div className="divide-y divide-gray-100">
            <DetailRow label="Quoted At" value={formatDate(q.quoted_at ?? '')} />
            <DetailRow label="Created" value={formatDate(q.created_at)} />
            <DetailRow label="Last Updated" value={formatDate(q.updated_at)} />
          </div>
        </div>

        {/* IDs */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <SectionHeader icon={Shield} label="References" />
          <div className="divide-y divide-gray-100">
            <DetailRow label="Quote ID" value={<span className="font-mono text-xs">#{q.id}</span>} />
            <DetailRow label="Company ID" value={<span className="font-mono text-xs">#{q.company}</span>} />
            <DetailRow label="User ID" value={<span className="font-mono text-xs">#{q.user}</span>} />
            <DetailRow
              label="Organization"
              value={q.organization ? <span className="font-mono text-xs">#{q.organization}</span> : '—'}
            />
          </div>
        </div>
      </div>

      {/* Coverage Data */}
      {q.coverages && Object.keys(q.coverages).length > 0 && (
        <div>
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
            <Layers className="h-4 w-4 text-gray-400" />
            Coverage Data
          </h2>
          <JsonTable data={q.coverages} />
        </div>
      )}

      {q.coverage_data && Object.keys(q.coverage_data).length > 0 && (
        <div>
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
            <Layers className="h-4 w-4 text-gray-400" />
            Coverage Details
          </h2>
          <JsonTable data={q.coverage_data} />
        </div>
      )}

      {/* Limits & Retentions */}
      {q.limits_retentions && Object.keys(q.limits_retentions).length > 0 && (
        <div>
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
            <Shield className="h-4 w-4 text-gray-400" />
            Limits & Retentions
          </h2>
          <JsonTable data={q.limits_retentions} />
        </div>
      )}

      {/* Rating Result / Underwriter Overrides - only visible to ae_underwriting and admin */}
      {canDoUnderwriterOverrides && q.rating_result && Object.keys(q.rating_result).length > 0 && (
        <div>
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
            <BarChart3 className="h-4 w-4 text-gray-400" />
            Rating Result / Underwriter Overrides
          </h2>
          <JsonTable data={q.rating_result} />
        </div>
      )}

      {/* Associated Policies */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
          <ClipboardList className="h-4 w-4 text-gray-400" />
          Associated Policies
          {policies.data && (
            <span className="text-xs font-normal text-gray-400">({policies.data.results.length})</span>
          )}
        </h2>
        <DataTable
          columns={policyCols}
          data={policies.data?.results ?? []}
          isLoading={policies.isLoading}
          emptyMessage="No policies linked to this quote"
        />
      </div>

      {/* Associated Brokered Requests */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
          <FileText className="h-4 w-4 text-gray-400" />
          Associated Brokered Requests
          {brokeredRequests.data && (
            <span className="text-xs font-normal text-gray-400">({brokeredRequests.data.results.length})</span>
          )}
        </h2>
        <DataTable
          columns={brokeredCols}
          data={brokeredRequests.data?.results ?? []}
          isLoading={brokeredRequests.isLoading}
          emptyMessage="No brokered requests linked to this quote"
        />
      </div>

      {/* Activity Log (collapsible) */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <button
          onClick={() => setAuditOpen(!auditOpen)}
          className="flex w-full items-center gap-2 px-5 py-4 text-left text-sm font-semibold text-gray-900 transition-colors hover:bg-gray-50"
        >
          {auditOpen ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronRight className="h-4 w-4 text-gray-400" />}
          <Clock className="h-4 w-4 text-gray-400" />
          Activity Log
          {auditLog.data?.entries && (
            <span className="text-xs font-normal text-gray-400">({auditLog.data?.entries?.length ?? 0})</span>
          )}
        </button>
        {auditOpen && (
          <div className="border-t border-gray-100 px-5 py-4">
            <ActivityTimeline
              entries={auditLog.data?.entries ?? []}
              isLoading={auditLog.isLoading}
            />
          </div>
        )}
      </div>

      {/* Timestamps */}
      <div className="flex gap-6 text-xs text-gray-400">
        <span>Created {formatDate(q.created_at)}</span>
        <span>Updated {formatDate(q.updated_at)}</span>
      </div>
      </div>

      {/* Customer Context Sidebar */}
      <div className="hidden xl:block sticky top-6">
        <CustomerContextSidebar quote={q} />
      </div>
    </div>
  )
}
