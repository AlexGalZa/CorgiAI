import { cn } from '@/lib/utils'
import EmptyState from '@/components/ui/EmptyState'
import Checkbox from '@/components/ui/Checkbox'
import { type LucideIcon, Inbox, ChevronUp, ChevronDown } from 'lucide-react'

export interface Column<T> {
  key: string
  header: string
  align?: 'left' | 'right' | 'center'
  sortable?: boolean
  sortKey?: string
  render?: (row: T) => React.ReactNode
}

export interface SortState {
  key: string
  direction: 'asc' | 'desc'
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  isLoading?: boolean
  onRowClick?: (row: T) => void
  emptyMessage?: string
  emptyIcon?: LucideIcon
  emptyAction?: { label: string; onClick: () => void }
  onSort?: (key: string, direction: 'asc' | 'desc') => void
  currentSort?: SortState
  footer?: React.ReactNode
  /** Enable row selection with checkboxes */
  selectable?: boolean
  /** Set of selected row IDs (controlled) */
  selectedIds?: Set<string | number>
  /** Called when selection changes */
  onSelectionChange?: (selectedIds: Set<string | number>) => void
}

const skeletonWidths = [65, 45, 80, 55, 70, 40, 60, 50, 75, 85]

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <tr className="animate-pulse">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3.5">
          <div
            className="h-4 rounded bg-gray-100"
            style={{ width: `${skeletonWidths[i % skeletonWidths.length]}%` }}
          />
        </td>
      ))}
    </tr>
  )
}

const alignClass = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function DataTable<T extends Record<string, any>>({
  columns,
  data,
  isLoading = false,
  onRowClick,
  emptyMessage = 'No data available',
  emptyIcon = Inbox,
  emptyAction,
  onSort,
  currentSort,
  footer,
  selectable = false,
  selectedIds,
  onSelectionChange,
}: DataTableProps<T>) {
  const handleHeaderClick = (col: Column<T>) => {
    if (!col.sortable || !onSort) return
    const sortField = col.sortKey ?? col.key
    const newDirection: 'asc' | 'desc' =
      currentSort?.key === sortField && currentSort.direction === 'asc'
        ? 'desc'
        : 'asc'
    onSort(sortField, newDirection)
  }

  const allSelected = selectable && data.length > 0 && data.every((row) => selectedIds?.has(row.id))
  const someSelected = selectable && data.some((row) => selectedIds?.has(row.id))

  const handleSelectAll = () => {
    if (!onSelectionChange) return
    if (allSelected) {
      onSelectionChange(new Set())
    } else {
      onSelectionChange(new Set(data.map((row) => row.id as string | number)))
    }
  }

  const handleSelectRow = (rowId: string | number, e?: React.MouseEvent) => {
    if (!onSelectionChange || !selectedIds) return
    e?.stopPropagation()
    const next = new Set(selectedIds)
    if (next.has(rowId)) {
      next.delete(rowId)
    } else {
      next.add(rowId)
    }
    onSelectionChange(next)
  }

  const totalCols = selectable ? columns.length + 1 : columns.length

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="overflow-x-auto overflow-y-visible">
        <table className="min-w-full">
          <thead className="sticky top-0 z-10">
            <tr className="border-b border-gray-200 bg-gray-50/80 shadow-[0_1px_3px_0_rgba(0,0,0,0.05)]">
              {selectable && (
                <th className="w-10 px-3 py-3">
                  <Checkbox
                    checked={allSelected}
                    indeterminate={someSelected && !allSelected}
                    onChange={handleSelectAll}
                  />
                </th>
              )}
              {columns.map((col) => {
                const sortField = col.sortKey ?? col.key
                const isActive = currentSort?.key === sortField
                return (
                  <th
                    key={col.key}
                    onClick={() => handleHeaderClick(col)}
                    className={cn(
                      'px-4 py-3 text-xs font-semibold uppercase tracking-wider',
                      alignClass[col.align ?? 'left'],
                      col.sortable && onSort
                        ? 'cursor-pointer select-none transition-colors hover:bg-gray-100'
                        : '',
                      isActive && col.sortable
                        ? 'text-[#ff5c00]'
                        : 'text-gray-500',
                    )}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.header}
                      {col.sortable && onSort && (
                        <span className="inline-flex flex-col">
                          {isActive ? (
                            currentSort?.direction === 'asc' ? (
                              <ChevronUp className="h-3.5 w-3.5" />
                            ) : (
                              <ChevronDown className="h-3.5 w-3.5" />
                            )
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5 text-gray-300" />
                          )}
                        </span>
                      )}
                    </span>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <SkeletonRow key={i} cols={totalCols} />
              ))
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={totalCols}>
                  <EmptyState
                    icon={emptyIcon}
                    title={emptyMessage}
                    className="py-12"
                    action={
                      emptyAction ? (
                        <button
                          onClick={emptyAction.onClick}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-[#ff5c00] px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#ea580c]"
                        >
                          {emptyAction.label}
                        </button>
                      ) : undefined
                    }
                  />
                </td>
              </tr>
            ) : (
              data.map((row, idx) => {
                const rowId = (row.id as string | number) ?? idx
                const isSelected = selectable && selectedIds?.has(rowId)
                return (
                  <tr
                    key={rowId}
                    onClick={() => onRowClick?.(row)}
                    className={cn(
                      'transition-colors',
                      onRowClick && 'cursor-pointer hover:bg-gray-50',
                      isSelected && 'bg-orange-50/50',
                    )}
                  >
                    {selectable && (
                      <td className="w-10 px-3 py-3">
                        <Checkbox
                          checked={isSelected}
                          onChange={() => handleSelectRow(rowId)}
                        />
                      </td>
                    )}
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={cn(
                          'whitespace-nowrap px-4 py-3 text-sm text-gray-700',
                          alignClass[col.align ?? 'left'],
                        )}
                      >
                        {col.render
                          ? col.render(row)
                          : (row[col.key] as React.ReactNode) ?? '—'}
                      </td>
                    ))}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
      {footer}
    </div>
  )
}
