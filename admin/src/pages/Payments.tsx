import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { DollarSign, Clock, AlertTriangle, Search, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { usePermissions } from '@/lib/permissions'
import DataTable, { type Column, type SortState } from '@/components/ui/DataTable'
import ExportButton from '@/components/ui/ExportButton'
import ExportAllButton from '@/components/ui/ExportAllButton'
import StatusBadge from '@/components/ui/StatusBadge'
import InlineCellEditor from '@/components/ui/InlineCellEditor'
import Pagination from '@/components/ui/Pagination'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import QueryError from '@/components/ui/QueryError'
import Select from '@/components/ui/Select'
import PaymentDetailPanel from '@/components/payments/PaymentDetailPanel'
import { usePayments, useUpdatePayment } from '@/hooks/usePayments'
import { usePaymentSummary } from '@/hooks/useAnalytics'
import type { Payment } from '@/types'
import { formatCurrency, formatDate } from '@/lib/formatters'

// ─── Refresh Button ─────────────────────────────────────────────────────────

function RefreshButton({ onClick, isRefreshing }: { onClick: () => void; isRefreshing: boolean }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center justify-center rounded-lg border border-gray-300 bg-white p-2 text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-700"
      aria-label="Refresh data"
      title="Refresh data"
    >
      <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
    </button>
  )
}

const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'paid', label: 'Paid' },
  { value: 'failed', label: 'Failed' },
  { value: 'refunded', label: 'Refunded' },
]

const PAYMENT_STATUS_OPTIONS = [
  { value: 'pending', label: 'Pending' },
  { value: 'paid', label: 'Paid' },
  { value: 'failed', label: 'Failed' },
  { value: 'refunded', label: 'Refunded' },
]

const PAYMENT_CONFIRM_STATUSES = ['refunded']

// ─── Inline Payment Status Editor ────────────────────────────────────────────

function PaymentStatusCell({ row }: { row: Payment }) {
  const updateMutation = useUpdatePayment()

  const handleSave = async (newValue: string) => {
    try {
      await updateMutation.mutateAsync({
        id: row.id,
        payload: { status: newValue },
      })
      toast.success(`Payment status changed to ${newValue.replace(/_/g, ' ')}`)
    } catch {
      toast.error('Failed to update payment status')
      throw new Error('Failed to update payment status')
    }
  }

  return (
    <InlineCellEditor
      value={row.status}
      options={PAYMENT_STATUS_OPTIONS}
      onSave={handleSave}
      variant="badge"
      renderValue={(val) => <StatusBadge status={val} variant="payment" />}
      confirmValues={PAYMENT_CONFIRM_STATUSES}
    />
  )
}

// ─── Column Definitions ──────────────────────────────────────────────────────

function getColumns(canEdit: boolean): Column<Payment>[] {
  return [
    { key: 'stripe_invoice_id', header: 'Invoice ID' },
    {
      key: 'policy',
      header: 'Policy',
      render: (row) => (
        <Link
          to={`/policies/${row.policy}`}
          onClick={(e) => e.stopPropagation()}
          className="font-medium text-[#ff5c00] hover:underline"
        >
          {(row as any).policy_number || `#${row.policy}`}
        </Link>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      sortable: true,
      render: (row) => (
        <span className="font-medium">{formatCurrency(row.amount)}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => canEdit ? <PaymentStatusCell row={row} /> : <StatusBadge status={row.status} variant="payment" />,
    },
    {
      key: 'paid_at',
      header: 'Paid At',
      sortable: true,
      render: (row) => formatDate(row.paid_at ?? ''),
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (row) => formatDate(row.created_at),
    },
  ]
}

// ─── Summary Card ───────────────────────────────────────────────────────────

interface SummaryCardProps {
  title: string
  value: string
  icon: React.ReactNode
  colorClass: string
}

function SummaryCard({ title, value, icon, colorClass }: SummaryCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-4">
        <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${colorClass}`}>
          {icon}
        </div>
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  )
}

// ─── Component ──────────────────────────────────────────────────────────────

export default function PaymentsPage() {
  const { canEditPayments } = usePermissions()
  const columns = getColumns(canEditPayments)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [sort, setSort] = useState<SortState>({ key: 'created_at', direction: 'desc' })
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null)
  const [isManualRefreshing, setIsManualRefreshing] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const ordering = sort.direction === 'desc' ? `-${sort.key}` : sort.key

  const { data, isLoading, isError, refetch } = usePayments({ page, status: status || undefined, search: debouncedSearch || undefined, ordering })
  const { data: summary } = usePaymentSummary()

  const handleRefresh = useCallback(() => {
    setIsManualRefreshing(true)
    refetch().finally(() => {
      setTimeout(() => setIsManualRefreshing(false), 1000)
    })
  }, [refetch])

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Payments' }]} />
      <PageHeader
        title="Payments"
        subtitle="Track payment status and invoice history."
        count={data?.count}
        action={
          <div className="flex items-center gap-3">
            <RefreshButton onClick={handleRefresh} isRefreshing={isManualRefreshing} />
            <ExportButton
              data={(data?.results ?? []) as unknown as Record<string, unknown>[]}
              filename="payments"
              columns={[
                { key: 'stripe_invoice_id', header: 'Invoice ID' },
                { key: 'policy', header: 'Policy' },
                { key: 'amount', header: 'Amount' },
                { key: 'status', header: 'Status' },
                { key: 'paid_at', header: 'Paid At' },
                { key: 'created_at', header: 'Created' },
              ]}
            />
            <ExportAllButton
              endpoint="/admin/payments"
              filename="payments"
              columns={[
                { key: 'stripe_invoice_id', header: 'Invoice ID' },
                { key: 'policy', header: 'Policy' },
                { key: 'amount', header: 'Amount' },
                { key: 'status', header: 'Status' },
                { key: 'paid_at', header: 'Paid At' },
                { key: 'created_at', header: 'Created' },
              ]}
            />
          </div>
        }
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <SummaryCard
          title="Total Paid"
          value={formatCurrency(summary?.total_paid ?? 0)}
          icon={<DollarSign className="h-6 w-6 text-green-600" />}
          colorClass="bg-green-100"
        />
        <SummaryCard
          title="Total Pending"
          value={formatCurrency(summary?.total_pending ?? 0)}
          icon={<Clock className="h-6 w-6 text-yellow-600" />}
          colorClass="bg-yellow-100"
        />
        <SummaryCard
          title="Total Failed"
          value={formatCurrency(summary?.total_failed ?? 0)}
          icon={<AlertTriangle className="h-6 w-6 text-red-600" />}
          colorClass="bg-red-100"
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search invoice ID or policy..."
            value={searchInput}
            onChange={(e) => { setSearchInput(e.target.value); setPage(1) }}
            className="w-64 rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-3 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
          />
        </div>
        <Select
          value={status}
          onChange={(val) => { setStatus(val); setPage(1) }}
          options={STATUS_FILTER_OPTIONS}
          placeholder="All Statuses"
          size="sm"
          className="w-40"
        />
      </div>

      {isError && <QueryError onRetry={refetch} />}

      {!isError && (
        <DataTable
          columns={columns}
          data={data?.results ?? []}
          isLoading={isLoading}
          emptyMessage="No payments found"
          currentSort={sort}
          onSort={(key, direction) => { setSort({ key, direction }); setPage(1) }}
          onRowClick={(row) => setSelectedPayment(row)}
          footer={data && <Pagination page={page} totalCount={data.count} onPageChange={setPage} />}
        />
      )}

      <PaymentDetailPanel
        payment={selectedPayment}
        onClose={() => setSelectedPayment(null)}
      />
    </div>
  )
}
