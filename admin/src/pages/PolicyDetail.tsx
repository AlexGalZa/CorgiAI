import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, FileText, DollarSign, MapPin, Calendar, Shield, AlertTriangle, CreditCard, Clock, ChevronDown, ChevronRight } from 'lucide-react'
import api from '@/lib/api'
import { usePermissions } from '@/lib/permissions'
import { useAuditLog } from '@/hooks/useAuditLog'
import { formatCurrency, formatDate, getCoverageLabel } from '@/lib/formatters'
import StatusBadge from '@/components/ui/StatusBadge'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import QueryError from '@/components/ui/QueryError'
import ActivityTimeline from '@/components/ui/ActivityTimeline'
import { SpinnerOverlay } from '@/components/ui/Spinner'
import DataTable, { type Column } from '@/components/ui/DataTable'
import type { PaginatedResponse, Claim, Payment } from '@/types'

// ─── Types ──────────────────────────────────────────────────────────────────

interface PolicyDetail {
  id: number
  policy_number: string
  quote: number | null
  coverage_type: string
  carrier: string
  is_brokered: boolean
  premium: string
  monthly_premium: string
  effective_date: string | null
  expiration_date: string | null
  status: string
  insured_legal_name: string
  insured_fein: string
  principal_state: string
  billing_frequency: string
  paid_to_date: string | null
  coi_number: string
  discount: string
  limits_and_retentions: Record<string, unknown> | null
  transaction_count: number
  created_at: string
  updated_at: string
}

interface Transaction {
  id: number
  transaction_type: string
  effective_date: string
  gross_written_premium: string
  tax_amount: string
  commission_amount: string
  total_billed_delta: string
  collected_amount: string
  description: string
  created_at: string
}

// ─── Hooks ──────────────────────────────────────────────────────────────────

function usePolicy(id: string | undefined) {
  return useQuery<PolicyDetail>({
    queryKey: ['policy', id],
    queryFn: async () => {
      const { data } = await api.get(`/admin/policies/${id}`)
      return data
    },
    enabled: !!id,
  })
}

function useTransactions(policyId: string | undefined) {
  return useQuery<PaginatedResponse<Transaction>>({
    queryKey: ['policy-transactions', policyId],
    queryFn: async () => {
      const { data } = await api.get(`/admin/policy-transactions?policy=${policyId}`)
      return data
    },
    enabled: !!policyId,
  })
}

function usePolicyClaims(policyId: string | undefined) {
  return useQuery<PaginatedResponse<Claim>>({
    queryKey: ['policy-claims', policyId],
    queryFn: async () => {
      const { data } = await api.get(`/admin/claims?policy=${policyId}`)
      return data
    },
    enabled: !!policyId,
  })
}

function usePolicyPayments(policyId: string | undefined) {
  return useQuery<PaginatedResponse<Payment>>({
    queryKey: ['policy-payments', policyId],
    queryFn: async () => {
      const { data } = await api.get(`/admin/payments?policy=${policyId}`)
      return data
    },
    enabled: !!policyId,
  })
}

// ─── Table Columns ──────────────────────────────────────────────────────────

function getTxnCols(showCommissions: boolean): Column<Transaction>[] {
  const cols: Column<Transaction>[] = [
    {
      key: 'transaction_type',
      header: 'Type',
      render: (r) => (
        <span className="font-medium">
          {r.transaction_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
        </span>
      ),
    },
    { key: 'effective_date', header: 'Effective', render: (r) => formatDate(r.effective_date ?? '') },
    { key: 'gross_written_premium', header: 'GWP', align: 'right', render: (r) => formatCurrency(r.gross_written_premium) },
    { key: 'tax_amount', header: 'Tax', align: 'right', render: (r) => formatCurrency(r.tax_amount) },
  ]

  if (showCommissions) {
    cols.push({ key: 'commission_amount', header: 'Commission', align: 'right', render: (r) => formatCurrency(r.commission_amount) })
  }

  cols.push(
    { key: 'total_billed_delta', header: 'Total Billed', align: 'right', render: (r) => formatCurrency(r.total_billed_delta) },
    { key: 'collected_amount', header: 'Collected', align: 'right', render: (r) => formatCurrency(r.collected_amount) },
    {
      key: 'description',
      header: 'Description',
      render: (r) => (
        <span className="max-w-[200px] truncate" title={r.description}>
          {r.description || '—'}
        </span>
      ),
    },
  )

  return cols
}

const claimCols: Column<Claim>[] = [
  {
    key: 'claim_number',
    header: 'Claim #',
    render: (r) => (
      <Link to={`/claims/${r.id}`} className="font-medium text-[#ff5c00] hover:underline" onClick={(e) => e.stopPropagation()}>
        {r.claim_number}
      </Link>
    ),
  },
  { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} variant="claim" /> },
  { key: 'organization_name', header: 'Organization' },
  { key: 'total_incurred', header: 'Total Incurred', align: 'right', render: (r) => formatCurrency(r.total_incurred) },
  { key: 'claim_report_date', header: 'Report Date', render: (r) => formatDate(r.claim_report_date ?? '') },
]

const paymentCols: Column<Payment>[] = [
  { key: 'stripe_invoice_id', header: 'Invoice ID', render: (r) => <span className="font-mono text-xs">{r.stripe_invoice_id || '—'}</span> },
  { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} variant="payment" /> },
  { key: 'amount', header: 'Amount', align: 'right', render: (r) => formatCurrency(r.amount) },
  { key: 'paid_at', header: 'Paid At', render: (r) => formatDate(r.paid_at ?? '') },
  { key: 'created_at', header: 'Created', render: (r) => formatDate(r.created_at) },
]

// ─── Sub-components ─────────────────────────────────────────────────────────

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between py-2.5 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="ml-4 text-right font-medium text-gray-900">{value ?? '—'}</span>
    </div>
  )
}

function CarrierBadge({ carrier }: { carrier: string }) {
  if (!carrier) return <span className="text-gray-400">—</span>
  const label = carrier.charAt(0).toUpperCase() + carrier.slice(1)
  return (
    <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
      {label}
    </span>
  )
}

function LimitsTable({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data)
  if (entries.length === 0) return <p className="text-sm text-gray-400">No limits data</p>

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

function SectionHeader({ icon: Icon, label }: { icon: React.ComponentType<{ className?: string }>; label: string }) {
  return (
    <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-400">
      <Icon className="h-3.5 w-3.5" />
      {label}
    </div>
  )
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function PolicyDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { canViewCommissions } = usePermissions()
  const txnCols = getTxnCols(canViewCommissions)
  const policy = usePolicy(id)
  const txns = useTransactions(id)
  const claims = usePolicyClaims(id)
  const payments = usePolicyPayments(id)
  const auditLog = useAuditLog('Policy', id)
  const [auditOpen, setAuditOpen] = useState(false)

  if (policy.isLoading) return <SpinnerOverlay height="h-96" />
  if (policy.isError) return <QueryError message="Failed to load policy details" onRetry={policy.refetch} />

  const p = policy.data
  if (!p) return <div className="py-16 text-center text-sm text-gray-500">Policy not found</div>

  return (
    <div className="space-y-6">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: 'Policies', href: '/policies' },
          { label: p.policy_number || `Policy #${p.id}` },
        ]}
      />

      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/policies')}
          className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          aria-label="Go back"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-gray-900">
              {p.policy_number || `Policy #${p.id}`}
            </h1>
            <StatusBadge status={p.status} variant="policy" />
            <CarrierBadge carrier={p.carrier} />
          </div>
          <p className="text-sm text-gray-500">{p.insured_legal_name}</p>
        </div>
      </div>

      {/* Info Grid (2 columns) */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Coverage & Carrier */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <SectionHeader icon={Shield} label="Coverage & Carrier" />
          <div className="divide-y divide-gray-100">
            <DetailRow label="Coverage Type" value={getCoverageLabel(p.coverage_type)} />
            <DetailRow label="Carrier" value={p.carrier ? p.carrier.charAt(0).toUpperCase() + p.carrier.slice(1) : undefined} />
            <DetailRow label="Premium" value={formatCurrency(p.premium)} />
            <DetailRow label="Monthly Premium" value={formatCurrency(p.monthly_premium)} />
          </div>
        </div>

        {/* Dates */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <SectionHeader icon={Calendar} label="Dates & Billing" />
          <div className="divide-y divide-gray-100">
            <DetailRow label="Effective Date" value={formatDate(p.effective_date ?? '')} />
            <DetailRow label="Expiration Date" value={formatDate(p.expiration_date ?? '')} />
            <DetailRow label="Billing Frequency" value={p.billing_frequency ? p.billing_frequency.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : undefined} />
            <DetailRow label="Paid To Date" value={formatDate(p.paid_to_date ?? '')} />
          </div>
        </div>

        {/* Insured Info */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <SectionHeader icon={FileText} label="Insured Information" />
          <div className="divide-y divide-gray-100">
            <DetailRow label="Legal Name" value={p.insured_legal_name} />
            <DetailRow label="FEIN" value={p.insured_fein || '—'} />
            <DetailRow label="Principal State" value={p.principal_state} />
          </div>
        </div>

        {/* Additional Details */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <SectionHeader icon={DollarSign} label="Additional Details" />
          <div className="divide-y divide-gray-100">
            <DetailRow
              label="Brokered"
              value={
                p.is_brokered ? (
                  <span className="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-[#ff5c00]">
                    Yes
                  </span>
                ) : (
                  <span className="text-xs text-gray-400">No</span>
                )
              }
            />
            <DetailRow label="COI Number" value={p.coi_number || '—'} />
            <DetailRow label="Discount" value={p.discount != null && p.discount !== '' ? `${p.discount}%` : '—'} />
            <DetailRow label="Transactions" value={p.transaction_count} />
          </div>
        </div>
      </div>

      {/* Limits & Retentions */}
      {p.limits_and_retentions && Object.keys(p.limits_and_retentions).length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-gray-900">Limits & Retentions</h2>
          <LimitsTable data={p.limits_and_retentions} />
        </div>
      )}

      {/* Linked Transactions */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
          <MapPin className="h-4 w-4 text-gray-400" />
          Linked Transactions
          {txns.data && (
            <span className="text-xs font-normal text-gray-400">({txns.data.results.length})</span>
          )}
        </h2>
        <DataTable
          columns={txnCols}
          data={txns.data?.results ?? []}
          isLoading={txns.isLoading}
          emptyMessage="No transactions recorded"
        />
      </div>

      {/* Linked Claims */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
          <AlertTriangle className="h-4 w-4 text-gray-400" />
          Linked Claims
          {claims.data && (
            <span className="text-xs font-normal text-gray-400">({claims.data.results.length})</span>
          )}
        </h2>
        <DataTable
          columns={claimCols}
          data={claims.data?.results ?? []}
          isLoading={claims.isLoading}
          emptyMessage="No claims for this policy"
        />
      </div>

      {/* Linked Payments */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
          <CreditCard className="h-4 w-4 text-gray-400" />
          Linked Payments
          {payments.data && (
            <span className="text-xs font-normal text-gray-400">({payments.data.results.length})</span>
          )}
        </h2>
        <DataTable
          columns={paymentCols}
          data={payments.data?.results ?? []}
          isLoading={payments.isLoading}
          emptyMessage="No payments for this policy"
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
        <span>Created {formatDate(p.created_at)}</span>
        <span>Updated {formatDate(p.updated_at)}</span>
      </div>
    </div>
  )
}
