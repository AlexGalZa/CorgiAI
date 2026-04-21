import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, LayoutList, Columns3, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { usePermissions } from '@/lib/permissions'
import type { BrokeredQuoteRequest } from '@/types'
import { useBrokeredRequests, useUpdateBrokeredRequest, type BrokeredRequestFilters } from '@/hooks/useBrokeredRequests'
import RequestFilters, { type RequestFiltersState } from '@/components/brokerage/RequestFilters'
import RequestTable from '@/components/brokerage/RequestTable'
import RequestPipeline from '@/components/brokerage/RequestPipeline'
import RequestDetailPanel from '@/components/brokerage/RequestDetailPanel'
import RequestForm from '@/components/brokerage/RequestForm'
import BulkActionBar from '@/components/brokerage/BulkActionBar'
import ExportButton from '@/components/ui/ExportButton'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import QueryError from '@/components/ui/QueryError'


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

// ─── Types ───────────────────────────────────────────────────────────────────

type ViewMode = 'table' | 'pipeline'

// ─── Component ───────────────────────────────────────────────────────────────

export default function BrokeredRequestsPage() {
  const { canCreateBrokeredRequest, canEditBrokeredRequest } = usePermissions()
  const [searchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(25)

  // Initialize filters from URL params
  const [filters, setFilters] = useState<RequestFiltersState>(() => ({
    status: searchParams.get('status') || '',
    carrier: searchParams.get('carrier') || '',
    blocker: searchParams.get('has_blocker') === 'true' ? 'has_blocker' : searchParams.get('blocker') || '',
    search: searchParams.get('search') || '',
    created_after: '',
    created_before: '',
    requester: '',
  }))

  const [sortField, setSortField] = useState<string | undefined>('updated_at')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [selectedRequest, setSelectedRequest] = useState<BrokeredQuoteRequest | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editingRequest, setEditingRequest] = useState<BrokeredQuoteRequest | undefined>(undefined)
  const [duplicateData, setDuplicateData] = useState<Partial<BrokeredQuoteRequest> | undefined>(undefined)
  const [isManualRefreshing, setIsManualRefreshing] = useState(false)
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  // Build hook filters from local state
  const hookFilters = useMemo<BrokeredRequestFilters>(() => {
    const ordering = sortField
      ? `${sortDirection === 'desc' ? '-' : ''}${sortField}`
      : undefined

    const base: BrokeredRequestFilters = {
      page: viewMode === 'table' ? page : undefined,
      page_size: viewMode === 'table' ? pageSize : 500,
      ordering,
    }

    if (filters.status) base.status = filters.status
    if (filters.carrier) base.carrier = filters.carrier
    if (filters.search) base.search = filters.search
    if (filters.created_after) base.created_after = filters.created_after
    if (filters.created_before) base.created_before = filters.created_before
    if (filters.requester) base.requester = filters.requester

    // Blocker handling
    if (filters.blocker === 'has_blocker') base.has_blocker = 'true'
    else if (filters.blocker === 'no_blocker') base.has_blocker = 'false'
    else if (filters.blocker) base.blocker_type = filters.blocker

    return base
  }, [viewMode, page, pageSize, filters, sortField, sortDirection])

  // Query via the shared hook
  const { data, isLoading, isError, refetch } = useBrokeredRequests(hookFilters)
  const updateMutation = useUpdateBrokeredRequest()

  // Handle highlight param: auto-open detail panel for that request ID
  const highlightId = searchParams.get('highlight')
  useEffect(() => {
    if (highlightId && data?.results) {
      const found = data.results.find((r) => r.id === Number(highlightId))
      if (found) setSelectedRequest(found)
    }
  }, [highlightId, data?.results])

  // Keep the selected request in sync with fresh query data.
  const selectedRequestId = useRef<number | null>(null)
  selectedRequestId.current = selectedRequest?.id ?? null

  const displayedRequest = useMemo(() => {
    if (selectedRequestId.current == null || !data?.results) return selectedRequest
    return data.results.find((r) => r.id === selectedRequestId.current) ?? selectedRequest
  }, [data?.results, selectedRequest])

  // Manual refresh handler
  const handleRefresh = useCallback(() => {
    setIsManualRefreshing(true)
    refetch().finally(() => {
      setTimeout(() => setIsManualRefreshing(false), 1000)
    })
  }, [refetch])

  // Handlers
  const handleFilterChange = useCallback((newFilters: RequestFiltersState) => {
    setFilters(newFilters)
    setPage(1)
  }, [])

  const handleSort = useCallback((field: string, direction: 'asc' | 'desc') => {
    setSortField(field)
    setSortDirection(direction)
    setPage(1)
  }, [])

  const handleRowClick = useCallback((request: BrokeredQuoteRequest) => {
    setSelectedRequest(request)
  }, [])

  const handleCloseDetail = useCallback(() => {
    setSelectedRequest(null)
  }, [])

  const handleOpenCreate = useCallback(() => {
    setEditingRequest(undefined)
    setDuplicateData(undefined)
    setFormOpen(true)
  }, [])

  const handleOpenEdit = useCallback((request: BrokeredQuoteRequest) => {
    setEditingRequest(request)
    setDuplicateData(undefined)
    setFormOpen(true)
    setSelectedRequest(null)
  }, [])

  const handleDuplicate = useCallback((request: BrokeredQuoteRequest) => {
    setEditingRequest(undefined)
    setDuplicateData({
      company_name: request.company_name,
      coverage_types: request.coverage_types,
      coverage_type_display: request.coverage_type_display,
      carrier: request.carrier,
      carrier_display: request.carrier_display,
      requested_coverage_detail: request.requested_coverage_detail,
      aggregate_limit: request.aggregate_limit,
      per_occurrence_limit: request.per_occurrence_limit,
      retention: request.retention,
      requester_email: request.requester_email,
      client_contact_url: request.client_contact_url,
      client_email: request.client_email,
      notes: request.notes,
    })
    setFormOpen(true)
    setSelectedRequest(null)
  }, [])

  const handleFormClose = useCallback(() => {
    setFormOpen(false)
    setEditingRequest(undefined)
    setDuplicateData(undefined)
  }, [])

  const handleFormSaved = useCallback(() => {
    setFormOpen(false)
    setEditingRequest(undefined)
    setDuplicateData(undefined)
  }, [])

  const handleStatusChange = useCallback(async (requestId: number, newStatus: string) => {
    try {
      await updateMutation.mutateAsync({ id: requestId, payload: { status: newStatus } })
      toast.success(`Status changed to ${newStatus.replace(/_/g, ' ')}`)
    } catch {
      toast.error('Failed to update request status')
    }
  }, [updateMutation])

  const handleBulkComplete = useCallback(() => {
    setSelectedIds([])
  }, [])

  const tabClasses = (active: boolean) =>
    cn(
      'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
      active
        ? 'bg-orange-100 text-[#ff5c00]'
        : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700',
    )

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Brokered Requests' }]} />

      {/* Page Header */}
      <PageHeader
        title="Brokered Quote Requests"
        subtitle="Manage and track brokered insurance quote requests across carriers."
        count={data?.count}
        action={
          <div className="flex items-center gap-3">
            <RefreshButton onClick={handleRefresh} isRefreshing={isManualRefreshing} />
            <ExportButton
              data={(data?.results ?? []) as unknown as Record<string, unknown>[]}
              filename="brokered-requests"
              columns={[
                { key: 'company_name', header: 'Company' },
                { key: 'status', header: 'Status' },
                { key: 'carrier', header: 'Carrier' },
                { key: 'coverage_type_display', header: 'Coverage Types' },
                { key: 'premium_amount', header: 'Premium' },
                { key: 'blocker_type', header: 'Blocker' },
                { key: 'created_at', header: 'Created' },
                { key: 'updated_at', header: 'Updated' },
              ]}
            />
            {canCreateBrokeredRequest && (
              <button
                onClick={handleOpenCreate}
                className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-[#ea580c] focus:outline-none focus:ring-2 focus:ring-[#ff5c00] focus:ring-offset-2"
              >
                <Plus className="h-4 w-4" />
                New Request
              </button>
            )}
          </div>
        }
      />

      {/* Filters */}
      <RequestFilters filters={filters} onChange={handleFilterChange} />

      {/* View Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-1">
          <button className={tabClasses(viewMode === 'table')} onClick={() => setViewMode('table')}>
            <LayoutList className="h-4 w-4" />
            Table View
          </button>
          <button
            className={tabClasses(viewMode === 'pipeline')}
            onClick={() => setViewMode('pipeline')}
          >
            <Columns3 className="h-4 w-4" />
            Pipeline View
          </button>
        </div>
      </div>

      {/* Error State */}
      {isError && <QueryError onRetry={refetch} />}

      {/* Content */}
      {!isError && (viewMode === 'table' ? (
        <RequestTable
          data={data?.results ?? []}
          totalCount={data?.count ?? 0}
          page={page}
          pageSize={pageSize}
          isLoading={isLoading}
          onPageChange={setPage}
          onRowClick={handleRowClick}
          onSort={handleSort}
          sortField={sortField}
          sortDirection={sortDirection}
          selectedIds={canEditBrokeredRequest ? selectedIds : []}
          onSelectionChange={canEditBrokeredRequest ? setSelectedIds : undefined}
          readOnly={!canEditBrokeredRequest}
        />
      ) : (
        <RequestPipeline
          data={data?.results ?? []}
          isLoading={isLoading}
          onCardClick={handleRowClick}
          onStatusChange={handleStatusChange}
        />
      ))}

      {/* Bulk Action Bar */}
      {canEditBrokeredRequest && selectedIds.length > 0 && (
        <BulkActionBar
          selectedIds={selectedIds}
          onClearSelection={() => setSelectedIds([])}
          onComplete={handleBulkComplete}
        />
      )}

      {/* Detail Panel */}
      <RequestDetailPanel
        request={displayedRequest}
        onClose={handleCloseDetail}
        onEdit={canEditBrokeredRequest ? handleOpenEdit : undefined}
        onDuplicate={canEditBrokeredRequest ? handleDuplicate : undefined}
      />

      {/* Create / Edit / Duplicate Form Modal */}
      {formOpen && (
        <RequestForm
          request={editingRequest}
          initialData={duplicateData}
          onClose={handleFormClose}
          onSaved={handleFormSaved}
        />
      )}
    </div>
  )
}
