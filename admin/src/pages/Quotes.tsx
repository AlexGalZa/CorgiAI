import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, RefreshCw, Download, ChevronDown, X } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { usePermissions } from '@/lib/permissions'
import DataTable, { type Column, type SortState } from '@/components/ui/DataTable'
import ExportButton from '@/components/ui/ExportButton'
import StatusBadge from '@/components/ui/StatusBadge'
import InlineCellEditor from '@/components/ui/InlineCellEditor'
import Pagination from '@/components/ui/Pagination'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import QueryError from '@/components/ui/QueryError'
import Select from '@/components/ui/Select'
import { useQuotes, useUpdateQuote, type QuoteListItem } from '@/hooks/useQuotes'
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
  { value: 'draft', label: 'Draft' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'quoted', label: 'Quoted' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'declined', label: 'Declined' },
  { value: 'expired', label: 'Expired' },
  { value: 'bound', label: 'Bound' },
]

const QUOTE_STATUS_OPTIONS = [
  { value: 'draft', label: 'Draft' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'quoted', label: 'Quoted' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'declined', label: 'Declined' },
  { value: 'expired', label: 'Expired' },
  { value: 'bound', label: 'Bound' },
]

const QUOTE_CONFIRM_STATUSES = ['declined', 'expired']

const BULK_STATUS_OPTIONS = [
  { value: 'draft', label: 'Draft' },
  { value: 'quoted', label: 'Quoted' },
  { value: 'needs_review', label: 'Needs Review' },
  { value: 'declined', label: 'Declined' },
]

// ─── CSV Export Helper ───────────────────────────────────────────────────────

function exportSelectedCsv(rows: QuoteListItem[]) {
  const cols = [
    { key: 'quote_number', header: 'Quote #' },
    { key: 'status', header: 'Status' },
    { key: 'current_step', header: 'Coverage' },
    { key: 'quote_amount', header: 'Amount' },
    { key: 'billing_frequency', header: 'Billing Freq' },
    { key: 'created_at', header: 'Created' },
  ]
  const header = cols.map((c) => `"${c.header}"`).join(',')
  const csvRows = rows.map((row) =>
    cols
      .map((c) => {
        const val = (row as unknown as Record<string, unknown>)[c.key]
        if (val === null || val === undefined) return '""'
        return `"${String(val).replace(/"/g, '""')}"`
      })
      .join(','),
  )
  const csv = [header, ...csvRows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'quotes-selected.csv'
  a.click()
  URL.revokeObjectURL(url)
}

// ─── Bulk Action Bar ─────────────────────────────────────────────────────────

function BulkActionBar({
  count,
  onChangeStatus,
  onExport,
  onClear,
  isUpdating,
}: {
  count: number
  onChangeStatus: (status: string) => void
  onExport: () => void
  onClear: () => void
  isUpdating: boolean
}) {
  const [statusOpen, setStatusOpen] = useState(false)

  return (
    <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 animate-in slide-in-from-bottom-4 fade-in duration-200">
      <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-lg">
        {/* Selection count */}
        <span className="inline-flex items-center gap-1.5 rounded-full bg-[#ff5c00] px-2.5 py-1 text-xs font-semibold text-white">
          {count} selected
        </span>

        {/* Change Status dropdown */}
        <div className="relative">
          <button
            onClick={() => setStatusOpen(!statusOpen)}
            disabled={isUpdating}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
          >
            {isUpdating ? 'Updating...' : 'Change Status'}
            <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
          </button>
          {statusOpen && (
            <div className="absolute bottom-full left-0 mb-1 w-44 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
              {BULK_STATUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => {
                    setStatusOpen(false)
                    onChangeStatus(opt.value)
                  }}
                  className="flex w-full items-center px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-50"
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Export Selected */}
        <button
          onClick={onExport}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
        >
          <Download className="h-3.5 w-3.5" />
          Export Selected
        </button>

        {/* Clear selection */}
        <button
          onClick={onClear}
          className="inline-flex items-center justify-center rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          aria-label="Clear selection"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}

// ─── Inline Quote Status Editor ──────────────────────────────────────────────

function QuoteStatusCell({ row }: { row: QuoteListItem }) {
  const updateMutation = useUpdateQuote()

  const handleSave = async (newValue: string) => {
    try {
      await updateMutation.mutateAsync({
        id: row.id,
        payload: { status: newValue },
      })
      toast.success(`Quote status changed to ${newValue.replace(/_/g, ' ')}`)
    } catch {
      toast.error('Failed to update quote status')
      throw new Error('Failed to update quote status')
    }
  }

  return (
    <InlineCellEditor
      value={row.status}
      options={QUOTE_STATUS_OPTIONS}
      onSave={handleSave}
      variant="badge"
      renderValue={(val) => <StatusBadge status={val} />}
      confirmValues={QUOTE_CONFIRM_STATUSES}
    />
  )
}

// ─── Column Definitions ──────────────────────────────────────────────────────

function getColumns(canEdit: boolean): Column<QuoteListItem>[] {
  return [
    { key: 'quote_number', header: 'Quote #', sortable: true },
    {
      key: 'company_detail',
      header: 'Company',
      render: (row) => row.company_detail?.entity_legal_name ?? '—',
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => canEdit ? <QuoteStatusCell row={row} /> : <StatusBadge status={row.status} />,
    },
    {
      key: 'current_step',
      header: 'Coverage',
      render: (row) => getCoverageLabel(row.current_step),
    },
    {
      key: 'quote_amount',
      header: 'Amount',
      sortable: true,
      render: (row) => formatCurrency(row.quote_amount),
    },
    {
      key: 'billing_frequency',
      header: 'Billing Freq',
      render: (row) => {
        const freq = row.billing_frequency
        if (!freq) return '—'
        return freq.charAt(0).toUpperCase() + freq.slice(1).replace(/_/g, ' ')
      },
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (row) => formatDate(row.created_at),
    },
  ]
}

export default function QuotesPage() {
  const navigate = useNavigate()
  const { canEditQuotes } = usePermissions()
  const columns = getColumns(canEditQuotes)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [sort, setSort] = useState<SortState>({ key: 'created_at', direction: 'desc' })
  const [isManualRefreshing, setIsManualRefreshing] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string | number>>(new Set())
  const [isBulkUpdating, setIsBulkUpdating] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const ordering = sort.direction === 'desc' ? `-${sort.key}` : sort.key

  const { data, isLoading, isError, refetch } = useQuotes({
    page,
    status: status || undefined,
    search: debouncedSearch || undefined,
    ordering,
  })

  const handleRefresh = useCallback(() => {
    setIsManualRefreshing(true)
    refetch().finally(() => {
      setTimeout(() => setIsManualRefreshing(false), 1000)
    })
  }, [refetch])

  const updateQuoteMutation = useUpdateQuote()

  // Get the selected row objects for export
  const selectedRows = useMemo(
    () => (data?.results ?? []).filter((r) => selectedIds.has(r.id)),
    [data?.results, selectedIds],
  )

  const handleBulkStatusChange = useCallback(
    async (newStatus: string) => {
      if (selectedIds.size === 0) return
      setIsBulkUpdating(true)
      const ids = Array.from(selectedIds)
      let successCount = 0
      let failCount = 0
      for (const id of ids) {
        try {
          await updateQuoteMutation.mutateAsync({ id: id as number, payload: { status: newStatus } })
          successCount++
        } catch {
          failCount++
        }
      }
      setIsBulkUpdating(false)
      if (failCount === 0) {
        toast.success(`Updated ${successCount} quote${successCount !== 1 ? 's' : ''} to ${newStatus.replace(/_/g, ' ')}`)
      } else {
        toast.error(`Updated ${successCount}, failed ${failCount}`)
      }
      setSelectedIds(new Set())
    },
    [selectedIds, updateQuoteMutation],
  )

  const handleExportSelected = useCallback(() => {
    if (selectedRows.length === 0) return
    exportSelectedCsv(selectedRows)
    toast.success(`Exported ${selectedRows.length} quote${selectedRows.length !== 1 ? 's' : ''}`)
  }, [selectedRows])

  // Clear selection when page/filters change
  useEffect(() => {
    setSelectedIds(new Set())
  }, [page, status, debouncedSearch, sort])

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Quotes' }]} />
      <PageHeader
        title="Quotes"
        subtitle="Manage and track insurance quotes across all companies."
        count={data?.count}
        action={
          <div className="flex items-center gap-3">
            <RefreshButton onClick={handleRefresh} isRefreshing={isManualRefreshing} />
            <ExportButton
              data={(data?.results ?? []) as unknown as Record<string, unknown>[]}
              filename="quotes"
              columns={[
                { key: 'quote_number', header: 'Quote #' },
                { key: 'status', header: 'Status' },
                { key: 'current_step', header: 'Coverage' },
                { key: 'quote_amount', header: 'Amount' },
                { key: 'billing_frequency', header: 'Billing Freq' },
                { key: 'created_at', header: 'Created' },
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
            placeholder="Search quote # or company..."
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
        <>
          <DataTable
            columns={columns}
            data={data?.results ?? []}
            isLoading={isLoading}
            emptyMessage="No quotes found"
            emptyAction={{ label: 'View Brokered Requests', onClick: () => navigate('/brokered-requests') }}
            currentSort={sort}
            onSort={(key, direction) => { setSort({ key, direction }); setPage(1) }}
            onRowClick={(row) => navigate(`/quotes/${row.id}`)}
            footer={data && <Pagination page={page} totalCount={data.count} onPageChange={setPage} />}
            selectable={canEditQuotes}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
          />
          {selectedIds.size > 0 && (
            <BulkActionBar
              count={selectedIds.size}
              onChangeStatus={handleBulkStatusChange}
              onExport={handleExportSelected}
              onClear={() => setSelectedIds(new Set())}
              isUpdating={isBulkUpdating}
            />
          )}
        </>
      )}
    </div>
  )
}
