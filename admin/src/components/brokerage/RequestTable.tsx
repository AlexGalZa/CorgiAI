import { useState } from 'react'
import {
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Loader2,
} from 'lucide-react'
import { toast } from 'sonner'
import type { BrokeredQuoteRequest } from '@/types'
import Checkbox from '@/components/ui/Checkbox'
import InlineStatusEditor from '@/components/brokerage/InlineStatusEditor'
import InlineCarrierEditor from '@/components/brokerage/InlineCarrierEditor'
import StatusBadge from '@/components/ui/StatusBadge'
import { useUpdateBrokeredRequest } from '@/hooks/useBrokeredRequests'
import CoverageTags from '@/components/ui/CoverageTags'
import { formatCurrency, formatRelativeTime, getAEName } from '@/lib/formatters'
import { cn } from '@/lib/utils'

// ─── Types ───────────────────────────────────────────────────────────────────

type SortField =
  | 'company_name'
  | 'status'
  | 'coverage_types'
  | 'carrier'
  | 'premium_amount'
  | 'requester_email'
  | 'blocker_type'
  | 'updated_at'

type SortDirection = 'asc' | 'desc'

interface RequestTableProps {
  data: BrokeredQuoteRequest[]
  totalCount: number
  page: number
  pageSize: number
  isLoading: boolean
  onPageChange: (page: number) => void
  onRowClick: (request: BrokeredQuoteRequest) => void
  onSort: (field: string, direction: SortDirection) => void
  sortField?: string
  sortDirection?: SortDirection
  selectedIds?: number[]
  onSelectionChange?: (ids: number[]) => void
  readOnly?: boolean
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function FulfillmentIcon({ checked }: { checked: boolean }) {
  return checked ? (
    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
  ) : (
    <XCircle className="h-4 w-4 text-gray-300" />
  )
}

function ClickableFulfillmentIcon({
  checked,
  requestId,
  fieldName,
  title,
}: {
  checked: boolean
  requestId: number
  fieldName: string
  title: string
}) {
  const updateMutation = useUpdateBrokeredRequest()

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation() // prevent row click
    try {
      await updateMutation.mutateAsync({
        id: requestId,
        payload: { [fieldName]: !checked },
      })
      toast.success(`${title} ${!checked ? 'checked' : 'unchecked'}`)
    } catch {
      toast.error(`Failed to update ${title}`)
    }
  }

  if (updateMutation.isPending) {
    return <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      title={`${title}: ${checked ? 'Yes' : 'No'} (click to toggle)`}
      className="rounded p-0.5 transition-colors hover:bg-gray-100"
    >
      <FulfillmentIcon checked={checked} />
    </button>
  )
}

function SkeletonRow({ hasCheckbox }: { hasCheckbox: boolean }) {
  const colCount = hasCheckbox ? 10 : 9
  return (
    <tr className="animate-pulse">
      {Array.from({ length: colCount }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 rounded bg-gray-200" style={{ width: `${50 + Math.random() * 50}%` }} />
        </td>
      ))}
    </tr>
  )
}

// ─── Column Definitions ──────────────────────────────────────────────────────

const COLUMNS: { key: SortField; label: string; sortable: boolean; className?: string }[] = [
  { key: 'company_name', label: 'Company', sortable: true },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'coverage_types', label: 'Coverage', sortable: false },
  { key: 'carrier', label: 'Carrier', sortable: true },
  { key: 'premium_amount', label: 'Premium', sortable: true, className: 'text-right' },
  { key: 'requester_email', label: 'AE', sortable: true },
  { key: 'blocker_type', label: 'Blocker', sortable: true },
  { key: 'updated_at', label: 'Fulfillment', sortable: false },
  { key: 'updated_at', label: 'Updated', sortable: true },
]

// ─── Component ───────────────────────────────────────────────────────────────

export default function RequestTable({
  data,
  totalCount,
  page,
  pageSize,
  isLoading,
  onPageChange,
  onRowClick,
  onSort,
  sortField,
  sortDirection,
  selectedIds = [],
  onSelectionChange,
  readOnly = false,
}: RequestTableProps) {
  const [hoveredSort, setHoveredSort] = useState<string | null>(null)
  const hasCheckbox = !!onSelectionChange

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))
  const startItem = totalCount === 0 ? 0 : (page - 1) * pageSize + 1
  const endItem = Math.min(page * pageSize, totalCount)

  const allOnPageSelected = data.length > 0 && data.every((r) => selectedIds.includes(r.id))
  const someOnPageSelected = data.some((r) => selectedIds.includes(r.id))

  const handleSelectAll = () => {
    if (!onSelectionChange) return
    if (allOnPageSelected) {
      // Deselect all on this page
      onSelectionChange(selectedIds.filter((id) => !data.some((r) => r.id === id)))
    } else {
      // Select all on this page (merge with existing)
      const pageIds = data.map((r) => r.id)
      const merged = Array.from(new Set([...selectedIds, ...pageIds]))
      onSelectionChange(merged)
    }
  }

  const handleSelectRow = (id: number, e?: React.MouseEvent) => {
    e?.stopPropagation()
    if (!onSelectionChange) return
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter((sid) => sid !== id))
    } else {
      onSelectionChange([...selectedIds, id])
    }
  }

  const handleSort = (field: SortField, sortable: boolean) => {
    if (!sortable) return
    const newDirection: SortDirection =
      sortField === field && sortDirection === 'asc' ? 'desc' : 'asc'
    onSort(field, newDirection)
  }

  const getSortIcon = (field: string, sortable: boolean) => {
    if (!sortable) return null
    if (sortField === field) {
      return sortDirection === 'asc' ? (
        <ChevronUp className="h-3.5 w-3.5" />
      ) : (
        <ChevronDown className="h-3.5 w-3.5" />
      )
    }
    return <ChevronsUpDown className="h-3.5 w-3.5 text-gray-400" />
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {/* Checkbox header */}
              {hasCheckbox && (
                <th scope="col" className="sticky left-0 z-10 bg-gray-50 px-3 py-3">
                  <Checkbox
                    checked={allOnPageSelected}
                    indeterminate={someOnPageSelected && !allOnPageSelected}
                    onChange={handleSelectAll}
                  />
                </th>
              )}
              {COLUMNS.map((col, idx) => (
                <th
                  key={`${col.key}-${idx}`}
                  scope="col"
                  onClick={() => handleSort(col.key, col.sortable)}
                  onMouseEnter={() => col.sortable && setHoveredSort(`${col.key}-${idx}`)}
                  onMouseLeave={() => setHoveredSort(null)}
                  className={cn(
                    'px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500',
                    col.sortable && 'cursor-pointer select-none hover:text-gray-700',
                    col.className,
                  )}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {col.sortable && (
                      <span
                        className={cn(
                          'transition-opacity',
                          hoveredSort === `${col.key}-${idx}` || sortField === col.key
                            ? 'opacity-100'
                            : 'opacity-0',
                        )}
                      >
                        {getSortIcon(col.key, col.sortable)}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {isLoading ? (
              Array.from({ length: pageSize }).map((_, i) => <SkeletonRow key={i} hasCheckbox={hasCheckbox} />)
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={COLUMNS.length + (hasCheckbox ? 1 : 0)} className="px-4 py-12 text-center text-sm text-gray-500">
                  No brokered requests found.
                </td>
              </tr>
            ) : (
              data.map((req) => (
                <tr
                  key={req.id}
                  onClick={() => onRowClick(req)}
                  className={cn(
                    'cursor-pointer transition-colors hover:bg-gray-50',
                    selectedIds.includes(req.id) && 'bg-orange-50',
                  )}
                >
                  {/* Checkbox */}
                  {hasCheckbox && (
                    <td className="sticky left-0 z-10 bg-inherit px-3 py-3">
                      <Checkbox
                        checked={selectedIds.includes(req.id)}
                        onChange={() => handleSelectRow(req.id)}
                      />
                    </td>
                  )}

                  {/* Company */}
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {req.company_name}
                  </td>

                  {/* Status */}
                  <td className="whitespace-nowrap px-4 py-3">
                    {readOnly ? (
                      <StatusBadge status={req.status} variant="brokerage" />
                    ) : (
                      <InlineStatusEditor requestId={req.id} currentStatus={req.status} />
                    )}
                  </td>

                  {/* Coverage */}
                  <td className="max-w-[200px] truncate px-4 py-3 text-sm text-gray-600">
                    <CoverageTags codes={req.coverage_types} max={2} />
                  </td>

                  {/* Carrier */}
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                    {readOnly ? (
                      <span>{req.carrier_display || req.carrier || '—'}</span>
                    ) : (
                      <InlineCarrierEditor requestId={req.id} currentCarrier={req.carrier} />
                    )}
                  </td>

                  {/* Premium */}
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-medium text-gray-900">
                    {formatCurrency(req.premium_amount)}
                  </td>

                  {/* AE */}
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                    {getAEName(req.requester_email)}
                  </td>

                  {/* Blocker */}
                  <td className="whitespace-nowrap px-4 py-3">
                    {req.has_blocker ? (
                      <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                        {req.blocker_type?.replace(/_/g, ' ') ?? 'Blocker'}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">&mdash;</span>
                    )}
                  </td>

                  {/* Fulfillment (clickable if not readOnly) */}
                  <td className="whitespace-nowrap px-4 py-3">
                    <div className="flex items-center gap-1">
                      {readOnly ? (
                        <>
                          <FulfillmentIcon checked={req.is_bound} />
                          <FulfillmentIcon checked={req.custom_product_created} />
                          <FulfillmentIcon checked={req.docs_uploaded} />
                          <FulfillmentIcon checked={req.stripe_confirmed} />
                        </>
                      ) : (
                        <>
                          <ClickableFulfillmentIcon checked={req.is_bound} requestId={req.id} fieldName="is_bound" title="Bound" />
                          <ClickableFulfillmentIcon checked={req.custom_product_created} requestId={req.id} fieldName="custom_product_created" title="Custom Product" />
                          <ClickableFulfillmentIcon checked={req.docs_uploaded} requestId={req.id} fieldName="docs_uploaded" title="Docs Uploaded" />
                          <ClickableFulfillmentIcon checked={req.stripe_confirmed} requestId={req.id} fieldName="stripe_confirmed" title="Stripe Confirmed" />
                        </>
                      )}
                    </div>
                  </td>

                  {/* Updated */}
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                    {formatRelativeTime(req.updated_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3">
        <p className="text-sm text-gray-600">
          {totalCount === 0 ? (
            'No results'
          ) : (
            <>
              Showing <span className="font-medium">{startItem}</span>&ndash;
              <span className="font-medium">{endItem}</span> of{' '}
              <span className="font-medium">{totalCount}</span>
            </>
          )}
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="inline-flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ChevronLeft className="h-4 w-4" />
            Prev
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="inline-flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
