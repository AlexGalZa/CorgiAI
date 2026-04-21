import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PaginationProps {
  page: number
  totalCount?: number
  /** Alias for totalCount */
  total?: number
  pageSize?: number
  onPageChange: (page: number) => void
}

export default function Pagination({
  page,
  totalCount,
  total,
  pageSize = 25,
  onPageChange,
}: PaginationProps) {
  const resolvedTotal = totalCount ?? total ?? 0
  // shadow totalCount with resolved value for the rest of the component
  totalCount = resolvedTotal
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))
  const hasPrev = page > 1
  const hasNext = page < totalPages

  return (
    <div className="flex items-center justify-between border-t border-gray-200 bg-white px-6 py-3">
      <p className="text-sm text-gray-500">
        Showing{' '}
        <span className="font-medium">{(page - 1) * pageSize + 1}</span>
        {' - '}
        <span className="font-medium">
          {Math.min(page * pageSize, totalCount)}
        </span>{' '}
        of <span className="font-medium">{totalCount}</span>
      </p>
      {totalPages > 1 && (
        <div className="flex items-center gap-1">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={!hasPrev}
            className={cn(
              'inline-flex items-center rounded-lg px-2 py-1.5 text-sm transition-colors',
              hasPrev
                ? 'text-gray-700 hover:bg-gray-100'
                : 'cursor-not-allowed text-gray-300',
            )}
          >
            <ChevronLeft className="h-4 w-4" />
            Prev
          </button>
          <span className="px-3 text-sm font-medium text-gray-700">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={!hasNext}
            className={cn(
              'inline-flex items-center rounded-lg px-2 py-1.5 text-sm transition-colors',
              hasNext
                ? 'text-gray-700 hover:bg-gray-100'
                : 'cursor-not-allowed text-gray-300',
            )}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )
}
