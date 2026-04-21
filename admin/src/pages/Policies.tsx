import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search, RefreshCw } from 'lucide-react'
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
import { usePolicies, useUpdatePolicy, type PolicyListItem } from '@/hooks/usePolicies'
import { formatCurrency, formatDate, getCoverageLabel } from '@/lib/formatters'

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
  { value: 'active', label: 'Active' },
  { value: 'expired', label: 'Expired' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'pending', label: 'Pending' },
]

const POLICY_STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'expired', label: 'Expired' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'pending', label: 'Pending' },
]

const POLICY_CONFIRM_STATUSES = ['cancelled', 'expired']

const COVERAGE_OPTIONS = [
  { value: '', label: 'All Coverages' },
  { value: 'gl', label: 'General Liability' },
  { value: 'pl', label: 'Tech E&O' },
  { value: 'wc', label: 'Workers Comp' },
  { value: 'bop', label: 'Business Owners Policy' },
  { value: 'cyber', label: 'Cyber Liability' },
  { value: 'epli', label: 'EPLI' },
  { value: 'do', label: 'D&O' },
  { value: 'auto', label: 'Commercial Auto' },
  { value: 'umbrella', label: 'Umbrella' },
  { value: 'property', label: 'Property' },
]

const CARRIER_OPTIONS = [
  { value: '', label: 'All Carriers' },
  { value: 'coterie', label: 'Coterie' },
  { value: 'hiscox', label: 'Hiscox' },
  { value: 'employers', label: 'Employers' },
  { value: 'pie', label: 'Pie Insurance' },
  { value: 'next', label: 'NEXT' },
  { value: 'coalition', label: 'Coalition' },
  { value: 'cna', label: 'CNA' },
  { value: 'amtrust', label: 'AmTrust' },
  { value: 'guard', label: 'Guard' },
]

// ─── Inline Policy Status Editor ─────────────────────────────────────────────

function PolicyStatusCell({ row }: { row: PolicyListItem }) {
  const updateMutation = useUpdatePolicy()

  const handleSave = async (newValue: string) => {
    try {
      await updateMutation.mutateAsync({
        id: row.id,
        payload: { status: newValue },
      })
      toast.success(`Policy status changed to ${newValue.replace(/_/g, ' ')}`)
    } catch {
      toast.error('Failed to update policy status')
      throw new Error('Failed to update policy status')
    }
  }

  return (
    <InlineCellEditor
      value={row.status}
      options={POLICY_STATUS_OPTIONS}
      onSave={handleSave}
      variant="badge"
      renderValue={(val) => <StatusBadge status={val} variant="policy" />}
      confirmValues={POLICY_CONFIRM_STATUSES}
    />
  )
}

// ─── Column Definitions ──────────────────────────────────────────────────────

function getColumns(canEdit: boolean): Column<PolicyListItem>[] {
  return [
    { key: 'policy_number', header: 'Policy #', sortable: true },
    {
      key: 'coverage_type',
      header: 'Coverage Type',
      sortable: true,
      render: (row) => getCoverageLabel(row.coverage_type),
    },
    {
      key: 'carrier',
      header: 'Carrier',
      sortable: true,
      render: (row) => {
        if (!row.carrier) return '—'
        return row.carrier.charAt(0).toUpperCase() + row.carrier.slice(1)
      },
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => canEdit ? <PolicyStatusCell row={row} /> : <StatusBadge status={row.status} variant="policy" />,
    },
    {
      key: 'premium',
      header: 'Premium',
      sortable: true,
      render: (row) => formatCurrency(row.premium),
    },
    {
      key: 'effective_date',
      header: 'Effective Date',
      sortable: true,
      render: (row) => formatDate(row.effective_date ?? ''),
    },
    {
      key: 'expiration_date',
      header: 'Expiration Date',
      sortable: true,
      render: (row) => formatDate(row.expiration_date ?? ''),
    },
    {
      key: 'is_brokered',
      header: 'Brokered',
      render: (row) =>
        row.is_brokered ? (
          <span className="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-[#ff5c00]">
            Yes
          </span>
        ) : (
          <span className="text-xs text-gray-400">No</span>
        ),
    },
  ]
}

export default function PoliciesPage() {
  const navigate = useNavigate()
  const { canEditPolicies } = usePermissions()
  const columns = getColumns(canEditPolicies)
  const [urlSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState(() => urlSearchParams.get('status') || '')
  const [coverageType, setCoverageType] = useState('')
  const [carrier, setCarrier] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [sort, setSort] = useState<SortState>({ key: 'created_at', direction: 'desc' })
  const [isManualRefreshing, setIsManualRefreshing] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const ordering = sort.direction === 'desc' ? `-${sort.key}` : sort.key

  const { data, isLoading, isError, refetch } = usePolicies({
    page,
    status: status || undefined,
    coverage_type: coverageType || undefined,
    carrier: carrier || undefined,
    search: debouncedSearch || undefined,
    ordering,
  })

  const handleRefresh = useCallback(() => {
    setIsManualRefreshing(true)
    refetch().finally(() => {
      setTimeout(() => setIsManualRefreshing(false), 1000)
    })
  }, [refetch])

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Policies' }]} />
      <PageHeader
        title="Policies"
        subtitle="Active and historical insurance policies."
        count={data?.count}
        action={
          <div className="flex items-center gap-3">
            <RefreshButton onClick={handleRefresh} isRefreshing={isManualRefreshing} />
            <ExportButton
              data={(data?.results ?? []) as unknown as Record<string, unknown>[]}
              filename="policies"
              columns={[
                { key: 'policy_number', header: 'Policy #' },
                { key: 'coverage_type', header: 'Coverage' },
                { key: 'carrier', header: 'Carrier' },
                { key: 'status', header: 'Status' },
                { key: 'premium', header: 'Premium' },
                { key: 'effective_date', header: 'Effective' },
                { key: 'expiration_date', header: 'Expiration' },
              ]}
            />
            <ExportAllButton
              endpoint="/admin/policies"
              filename="policies"
              columns={[
                { key: 'policy_number', header: 'Policy #' },
                { key: 'coverage_type', header: 'Coverage' },
                { key: 'carrier', header: 'Carrier' },
                { key: 'status', header: 'Status' },
                { key: 'premium', header: 'Premium' },
                { key: 'effective_date', header: 'Effective' },
                { key: 'expiration_date', header: 'Expiration' },
              ]}
            />
          </div>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search policy # or insured..."
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
        <Select
          value={coverageType}
          onChange={(val) => { setCoverageType(val); setPage(1) }}
          options={COVERAGE_OPTIONS}
          placeholder="All Coverages"
          size="sm"
          className="w-48"
        />
        <Select
          value={carrier}
          onChange={(val) => { setCarrier(val); setPage(1) }}
          options={CARRIER_OPTIONS}
          placeholder="All Carriers"
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
          onRowClick={(row) => navigate(`/policies/${row.id}`)}
          emptyMessage="No policies found"
          currentSort={sort}
          onSort={(key, direction) => { setSort({ key, direction }); setPage(1) }}
          footer={data && <Pagination page={page} totalCount={data.count} onPageChange={setPage} />}
        />
      )}
    </div>
  )
}
