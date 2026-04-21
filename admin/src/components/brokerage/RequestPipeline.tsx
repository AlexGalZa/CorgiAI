import { useState, useCallback, useMemo } from 'react'
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  useDraggable,
  useDroppable,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core'
import type { BrokeredQuoteRequest } from '@/types'
import CoverageTags from '@/components/ui/CoverageTags'
import { formatCurrency, getAEName } from '@/lib/formatters'
import { cn } from '@/lib/utils'
import ConfirmDialog from '@/components/ui/ConfirmDialog'

// ─── Types ───────────────────────────────────────────────────────────────────

interface RequestPipelineProps {
  data: BrokeredQuoteRequest[]
  isLoading: boolean
  onCardClick: (request: BrokeredQuoteRequest) => void
  onStatusChange?: (requestId: number, newStatus: string) => Promise<void>
}

// ─── Pipeline Columns ────────────────────────────────────────────────────────

interface PipelineColumn {
  key: string
  label: string
  headerBg: string
  headerText: string
  borderColor: string
}

const PIPELINE_COLUMNS: PipelineColumn[] = [
  { key: 'received', label: 'Received',  headerBg: 'bg-orange-100',  headerText: 'text-orange-800',  borderColor: 'border-l-[#ff5c00]' },
  { key: 'stalled',  label: 'Stalled',   headerBg: 'bg-orange-100',  headerText: 'text-orange-800',  borderColor: 'border-l-orange-400' },
  { key: 'submitted',label: 'Submitted', headerBg: 'bg-yellow-100',  headerText: 'text-yellow-800',  borderColor: 'border-l-yellow-500' },
  { key: 'quoted',   label: 'Quoted',    headerBg: 'bg-green-100',   headerText: 'text-green-800',   borderColor: 'border-l-green-500' },
  { key: 'blocked',  label: 'Blocked',   headerBg: 'bg-red-100',     headerText: 'text-red-800',     borderColor: 'border-l-red-500' },
  { key: 'on_hold',  label: 'On Hold',   headerBg: 'bg-orange-100',  headerText: 'text-orange-800',  borderColor: 'border-l-orange-500' },
  { key: 'otm',      label: 'OTM',       headerBg: 'bg-purple-100',  headerText: 'text-purple-800',  borderColor: 'border-l-purple-500' },
  { key: 'bound',    label: 'Bound',     headerBg: 'bg-emerald-100', headerText: 'text-emerald-800', borderColor: 'border-l-emerald-500' },
  { key: 'denied',   label: 'Denied',    headerBg: 'bg-red-100',     headerText: 'text-red-800',     borderColor: 'border-l-red-400' },
  { key: 'recalled', label: 'Recalled',  headerBg: 'bg-gray-100',    headerText: 'text-gray-800',    borderColor: 'border-l-gray-400' },
]

const TERMINAL_STATUSES = new Set(['denied', 'cancelled', 'recalled'])

// ─── Skeleton ────────────────────────────────────────────────────────────────

function SkeletonColumn() {
  return (
    <div className="flex w-72 shrink-0 flex-col">
      <div className="mb-3 h-8 animate-pulse rounded-lg bg-gray-200" />
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-lg bg-gray-100" />
        ))}
      </div>
    </div>
  )
}

// ─── Draggable Pipeline Card ─────────────────────────────────────────────────

function DraggablePipelineCard({
  request,
  borderColor,
  onClick,
  isDragOverlay,
}: {
  request: BrokeredQuoteRequest
  borderColor: string
  onClick: () => void
  isDragOverlay?: boolean
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: String(request.id),
  })

  // If used as overlay, no need for draggable hooks
  if (isDragOverlay) {
    return (
      <div
        className={cn(
          'w-full rounded-lg border border-gray-200 bg-white p-3 text-left shadow-lg',
          'border-l-4',
          borderColor,
        )}
        style={{ transform: 'rotate(3deg)' }}
      >
        <CardContent request={request} />
      </div>
    )
  }

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={cn(
        'w-full cursor-grab rounded-lg border border-gray-200 bg-white p-3 text-left shadow-sm transition-shadow hover:shadow-md active:cursor-grabbing',
        'border-l-4',
        borderColor,
        isDragging && 'opacity-50',
      )}
      onClick={(e) => {
        // Only fire click if it wasn't a drag
        if (!isDragging) {
          e.stopPropagation()
          onClick()
        }
      }}
    >
      <CardContent request={request} />
    </div>
  )
}

function CardContent({ request }: { request: BrokeredQuoteRequest }) {
  return (
    <>
      <p className="truncate text-sm font-semibold text-gray-900">{request.company_name}</p>
      <div className="mt-1"><CoverageTags codes={request.coverage_types} max={2} /></div>
      {request.carrier && (
        <p className="mt-1 text-xs text-gray-500">{request.carrier}</p>
      )}
      <div className="mt-2 flex items-center justify-between">
        {request.premium_amount ? (
          <span className="text-xs font-medium text-gray-900">
            {formatCurrency(request.premium_amount)}
          </span>
        ) : (
          <span className="text-xs text-gray-400">No premium</span>
        )}
        <span className="truncate text-xs text-gray-400">{getAEName(request.requester_email)}</span>
      </div>
      {request.has_blocker && (
        <div className="mt-2 rounded bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
          {request.blocker_type?.replace(/_/g, ' ') ?? 'Blocker'}
        </div>
      )}
    </>
  )
}

// ─── Droppable Column ────────────────────────────────────────────────────────

function DroppableColumn({
  column,
  items,
  onCardClick,
}: {
  column: PipelineColumn
  items: BrokeredQuoteRequest[]
  onCardClick: (request: BrokeredQuoteRequest) => void
}) {
  const { isOver, setNodeRef } = useDroppable({
    id: column.key,
  })

  return (
    <div ref={setNodeRef} className="flex w-72 shrink-0 flex-col">
      {/* Column header */}
      <div
        className={cn(
          'mb-3 flex items-center justify-between rounded-lg px-3 py-2',
          column.headerBg,
        )}
      >
        <span className={cn('text-sm font-semibold', column.headerText)}>{column.label}</span>
        <span
          className={cn(
            'inline-flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-xs font-bold',
            column.headerBg,
            column.headerText,
          )}
        >
          {items.length}
        </span>
      </div>

      {/* Cards */}
      <div
        className={cn(
          'flex flex-1 flex-col gap-2 rounded-lg p-1 transition-all',
          isOver && 'ring-2 ring-[#ff5c00] bg-orange-50/50',
        )}
      >
        {items.length === 0 ? (
          <div className={cn(
            'rounded-lg border-2 border-dashed py-8 text-center text-xs text-gray-400',
            isOver ? 'border-[#ff5c00] bg-orange-50' : 'border-gray-200',
          )}>
            No requests
          </div>
        ) : (
          items.map((req) => (
            <DraggablePipelineCard
              key={req.id}
              request={req}
              borderColor={column.borderColor}
              onClick={() => onCardClick(req)}
            />
          ))
        )}
      </div>
    </div>
  )
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function RequestPipeline({ data, isLoading, onCardClick, onStatusChange }: RequestPipelineProps) {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [confirmMove, setConfirmMove] = useState<{ requestId: number; newStatus: string } | null>(null)
  const [isConfirmLoading, setIsConfirmLoading] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
  )

  // Group requests by status
  const grouped = useMemo(() => {
    const result: Record<string, BrokeredQuoteRequest[]> = {}
    for (const col of PIPELINE_COLUMNS) {
      result[col.key] = []
    }
    for (const req of data) {
      const status = req.status.toLowerCase()
      if (result[status]) {
        result[status].push(req)
      }
    }
    return result
  }, [data])

  // Find the active request for the overlay
  const activeRequest = useMemo(() => {
    if (!activeId) return null
    return data.find((r) => String(r.id) === activeId) ?? null
  }, [activeId, data])

  // Find the column for the active request (for border color in overlay)
  const activeColumn = useMemo(() => {
    if (!activeRequest) return null
    const status = activeRequest.status.toLowerCase()
    return PIPELINE_COLUMNS.find((col) => col.key === status) ?? null
  }, [activeRequest])

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(String(event.active.id))
  }, [])

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveId(null)

      const { active, over } = event
      if (!over || !onStatusChange) return

      const requestId = Number(active.id)
      const newStatus = String(over.id)

      // Find current status
      const request = data.find((r) => r.id === requestId)
      if (!request) return
      const currentStatus = request.status.toLowerCase()

      // No change
      if (currentStatus === newStatus) return

      // Terminal statuses require confirmation
      if (TERMINAL_STATUSES.has(newStatus)) {
        setConfirmMove({ requestId, newStatus })
        return
      }

      // Perform the change
      onStatusChange(requestId, newStatus)
    },
    [data, onStatusChange],
  )

  const handleDragCancel = useCallback(() => {
    setActiveId(null)
  }, [])

  const handleConfirm = useCallback(async () => {
    if (!confirmMove || !onStatusChange) return
    setIsConfirmLoading(true)
    try {
      await onStatusChange(confirmMove.requestId, confirmMove.newStatus)
    } finally {
      setIsConfirmLoading(false)
      setConfirmMove(null)
    }
  }, [confirmMove, onStatusChange])

  const handleCancelConfirm = useCallback(() => {
    setConfirmMove(null)
  }, [])

  if (isLoading) {
    return (
      <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-compact">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonColumn key={i} />
        ))}
      </div>
    )
  }

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-compact">
          {PIPELINE_COLUMNS.map((col) => (
            <DroppableColumn
              key={col.key}
              column={col}
              items={grouped[col.key] ?? []}
              onCardClick={onCardClick}
            />
          ))}
        </div>

        <DragOverlay>
          {activeRequest && activeColumn ? (
            <div className="w-72">
              <DraggablePipelineCard
                request={activeRequest}
                borderColor={activeColumn.borderColor}
                onClick={() => {}}
                isDragOverlay
              />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      <ConfirmDialog
        open={!!confirmMove}
        title="Move to terminal status"
        message={`Are you sure you want to move this request to "${confirmMove?.newStatus.replace(/_/g, ' ')}"? This is typically a final status.`}
        confirmLabel="Move"
        variant="warning"
        isLoading={isConfirmLoading}
        onConfirm={handleConfirm}
        onCancel={handleCancelConfirm}
      />
    </>
  )
}
