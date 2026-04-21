import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, LayoutList, Columns3, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import DataTable, { type Column, type SortState } from '@/components/ui/DataTable'
import ExportButton from '@/components/ui/ExportButton'
import ExportAllButton from '@/components/ui/ExportAllButton'
import StatusBadge from '@/components/ui/StatusBadge'
import Pagination from '@/components/ui/Pagination'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import QueryError from '@/components/ui/QueryError'
import Select from '@/components/ui/Select'
import { usePermissions } from '@/lib/permissions'
import { useClaims, useUpdateInternalDocument, type ClaimListItem } from '@/hooks/useClaims'
import { formatCurrency, formatDate } from '@/lib/formatters'
import { cn } from '@/lib/utils'
import api from '@/lib/api'
import type { InternalDocument, PaginatedResponse } from '@/types'
import ClaimStatusEditor from '@/components/claims/ClaimStatusEditor'
import InternalDocStatusEditor from '@/components/claims/InternalDocStatusEditor'
import InternalDocsKanban from '@/components/claims/InternalDocsKanban'

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

const DOC_STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'not_reviewed', label: 'Not Reviewed' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'sent', label: 'Sent' },
]

// ─── Claims Status Options ──────────────────────────────────────────────────

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'filed', label: 'Filed' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'investigation', label: 'Investigation' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'denied', label: 'Denied' },
  { value: 'closed', label: 'Closed' },
]

// ─── Claims Columns ─────────────────────────────────────────────────────────

function getClaimColumns(canEdit: boolean): Column<ClaimListItem>[] {
  return [
    { key: 'claim_number', header: 'Claim #', sortable: true },
    { key: 'organization_name', header: 'Organization' },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => canEdit ? <ClaimStatusEditor claimId={row.id} currentStatus={row.status} /> : <StatusBadge status={row.status} variant="claim" />,
    },
    { key: 'loss_state', header: 'Loss State' },
    {
      key: 'claim_report_date',
      header: 'Report Date',
      sortable: true,
      render: (row) => formatDate(row.claim_report_date ?? ''),
    },
    {
      key: 'paid_loss',
      header: 'Paid Loss',
      sortable: true,
      render: (row) => formatCurrency(row.paid_loss),
    },
    {
      key: 'total_incurred',
      header: 'Total Incurred',
      render: (row) => (
        <span className="font-medium">{formatCurrency(row.total_incurred)}</span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (row) => formatDate(row.created_at),
    },
  ]
}

// ─── Internal Document Columns ──────────────────────────────────────────────

function getDocColumns(canEdit: boolean): Column<InternalDocument>[] {
  return [
    {
      key: 'document_type',
      header: 'Document Type',
      sortable: true,
      render: (row) => {
        if (!row.document_type) return '—'
        return row.document_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
      },
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => canEdit
        ? <InternalDocStatusEditor documentId={row.id} currentStatus={row.status} />
        : <StatusBadge status={row.status} />,
    },
    { key: 'claim_number', header: 'Claim #' },
    {
      key: 'reviewed_by',
      header: 'Reviewed By',
      render: (row) => row.reviewed_by || '—',
    },
    {
      key: 'notes',
      header: 'Notes',
      render: (row) => (
        <span className="max-w-xs truncate" title={row.notes}>
          {row.notes || '—'}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (row) => formatDate(row.created_at),
    },
  ]
}

// ─── Internal Documents Hook ────────────────────────────────────────────────

function useInternalDocuments(filters: { page?: number; search?: string; status?: string; ordering?: string }) {
  return useQuery<PaginatedResponse<InternalDocument>>({
    queryKey: ['internal-documents', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.search) params.set('search', filters.search)
      if (filters.status) params.set('status', filters.status)
      if (filters.ordering) params.set('ordering', filters.ordering)
      const { data } = await api.get(`/admin/internal-documents?${params.toString()}`)
      return data
    },
  })
}

// ─── Component ──────────────────────────────────────────────────────────────

export default function ClaimsPage() {
  const navigate = useNavigate()
  const { canEditClaims } = usePermissions()
  const claimColumns = getClaimColumns(canEditClaims)
  const docColumns = getDocColumns(canEditClaims)
  const [urlSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState(() => urlSearchParams.get('status') || '')
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [sort, setSort] = useState<SortState>({ key: 'created_at', direction: 'desc' })
  const [isManualRefreshing, setIsManualRefreshing] = useState(false)

  const [docPage, setDocPage] = useState(1)
  const [docSearchInput, setDocSearchInput] = useState('')
  const [debouncedDocSearch, setDebouncedDocSearch] = useState('')
  const [docStatus, setDocStatus] = useState('')
  const [docSort, setDocSort] = useState<SortState>({ key: 'created_at', direction: 'desc' })
  const [docViewMode, setDocViewMode] = useState<'table' | 'kanban'>('table')

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedDocSearch(docSearchInput), 300)
    return () => clearTimeout(timer)
  }, [docSearchInput])

  const ordering = sort.direction === 'desc' ? `-${sort.key}` : sort.key

  const { data, isLoading, isError, refetch } = useClaims({
    page,
    status: status || undefined,
    search: debouncedSearch || undefined,
    ordering,
  })

  const docOrdering = docSort.direction === 'desc' ? `-${docSort.key}` : docSort.key

  const { data: docData, isLoading: docLoading, isError: docIsError, refetch: docRefetch } = useInternalDocuments({
    page: docViewMode === 'table' ? docPage : undefined,
    search: debouncedDocSearch || undefined,
    status: docViewMode === 'table' ? (docStatus || undefined) : undefined,
    ordering: docViewMode === 'table' ? docOrdering : undefined,
  })

  const updateDocMutation = useUpdateInternalDocument()

  const handleDocStatusChange = useCallback(async (docId: number, newStatus: string) => {
    try {
      await updateDocMutation.mutateAsync({ id: docId, payload: { status: newStatus } })
      toast.success(`Document status changed to ${newStatus.replace(/_/g, ' ')}`)
    } catch {
      toast.error('Failed to update document status')
    }
  }, [updateDocMutation])

  const handleRefresh = useCallback(() => {
    setIsManualRefreshing(true)
    refetch().finally(() => {
      setTimeout(() => setIsManualRefreshing(false), 1000)
    })
  }, [refetch])

  const docTabClasses = (active: boolean) =>
    cn(
      'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
      active
        ? 'bg-orange-100 text-[#ff5c00]'
        : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700',
    )

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Claims' }]} />

      {/* ── Claims Section ──────────────────────────────────────────────── */}
      <div className="space-y-4">
        <PageHeader
          title="Claims"
          subtitle="Track and manage insurance claims and incurred losses."
          count={data?.count}
          action={
            <div className="flex items-center gap-3">
              <RefreshButton onClick={handleRefresh} isRefreshing={isManualRefreshing} />
              <ExportButton
                data={(data?.results ?? []) as unknown as Record<string, unknown>[]}
                filename="claims"
                columns={[
                  { key: 'claim_number', header: 'Claim #' },
                  { key: 'organization_name', header: 'Organization' },
                  { key: 'status', header: 'Status' },
                  { key: 'loss_state', header: 'Loss State' },
                  { key: 'claim_report_date', header: 'Report Date' },
                  { key: 'paid_loss', header: 'Paid Loss' },
                  { key: 'total_incurred', header: 'Total Incurred' },
                  { key: 'created_at', header: 'Created' },
                ]}
              />
              <ExportAllButton
                endpoint="/admin/claims"
                filename="claims"
                columns={[
                  { key: 'claim_number', header: 'Claim #' },
                  { key: 'organization_name', header: 'Organization' },
                  { key: 'status', header: 'Status' },
                  { key: 'loss_state', header: 'Loss State' },
                  { key: 'claim_report_date', header: 'Report Date' },
                  { key: 'paid_loss', header: 'Paid Loss' },
                  { key: 'total_incurred', header: 'Total Incurred' },
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
              placeholder="Search claim # or organization..."
              value={searchInput}
              onChange={(e) => { setSearchInput(e.target.value); setPage(1) }}
              className="w-64 rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-3 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
            />
          </div>
          <Select
            value={status}
            onChange={(val) => { setStatus(val); setPage(1) }}
            options={STATUS_OPTIONS}
            placeholder="All Statuses"
            size="sm"
            className="w-44"
          />
        </div>

        {isError && <QueryError onRetry={refetch} />}

        {!isError && (
          <DataTable
            columns={claimColumns}
            data={data?.results ?? []}
            isLoading={isLoading}
            onRowClick={(row) => navigate(`/claims/${row.id}`)}
            emptyMessage="No claims found"
            currentSort={sort}
            onSort={(key, direction) => { setSort({ key, direction }); setPage(1) }}
            footer={data && <Pagination page={page} totalCount={data.count} onPageChange={setPage} />}
          />
        )}
      </div>

      {/* ── Internal Documents Section ──────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Internal Documents</h2>
            <p className="mt-1 text-sm text-gray-500">
              Review and manage internal claim documentation.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">{docData?.count ?? 0} documents</span>
            <ExportButton
              data={(docData?.results ?? []) as unknown as Record<string, unknown>[]}
              filename="internal-documents"
              columns={[
                { key: 'document_type', header: 'Document Type' },
                { key: 'status', header: 'Status' },
                { key: 'claim_number', header: 'Claim #' },
                { key: 'reviewed_by', header: 'Reviewed By' },
                { key: 'notes', header: 'Notes' },
                { key: 'created_at', header: 'Created' },
              ]}
            />
            <ExportAllButton
              endpoint="/admin/internal-documents"
              filename="internal-documents"
              columns={[
                { key: 'document_type', header: 'Document Type' },
                { key: 'status', header: 'Status' },
                { key: 'claim_number', header: 'Claim #' },
                { key: 'reviewed_by', header: 'Reviewed By' },
                { key: 'notes', header: 'Notes' },
                { key: 'created_at', header: 'Created' },
              ]}
            />
          </div>
        </div>

        {/* Filters + View Toggle */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search documents..."
                value={docSearchInput}
                onChange={(e) => { setDocSearchInput(e.target.value); setDocPage(1) }}
                className="w-64 rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-3 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
              />
            </div>
            {docViewMode === 'table' && (
              <Select
                value={docStatus}
                onChange={(val) => { setDocStatus(val); setDocPage(1) }}
                options={DOC_STATUS_OPTIONS}
                placeholder="All Statuses"
                size="sm"
                className="w-40"
              />
            )}
          </div>

          <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-1">
            <button className={docTabClasses(docViewMode === 'table')} onClick={() => setDocViewMode('table')}>
              <LayoutList className="h-4 w-4" />
              Table View
            </button>
            <button className={docTabClasses(docViewMode === 'kanban')} onClick={() => setDocViewMode('kanban')}>
              <Columns3 className="h-4 w-4" />
              Kanban View
            </button>
          </div>
        </div>

        {/* Error State for docs */}
        {docIsError && <QueryError onRetry={docRefetch} />}

        {/* Content */}
        {!docIsError && (docViewMode === 'table' ? (
          <>
            <DataTable
              columns={docColumns}
              data={docData?.results ?? []}
              isLoading={docLoading}
              onRowClick={(row) => navigate(`/claims/${row.claim}`)}
              emptyMessage="No internal documents found"
              currentSort={docSort}
              onSort={(key, direction) => { setDocSort({ key, direction }); setDocPage(1) }}
              footer={docData && <Pagination page={docPage} totalCount={docData.count} onPageChange={setDocPage} />}
            />
          </>
        ) : (
          <InternalDocsKanban
            documents={docData?.results ?? []}
            isLoading={docLoading}
            onStatusChange={handleDocStatusChange}
            onCardClick={(doc) => navigate(`/claims/${doc.claim}`)}
          />
        ))}
      </div>
    </div>
  )
}
