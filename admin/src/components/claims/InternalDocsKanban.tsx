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
import type { InternalDocument } from '@/types'
import { cn } from '@/lib/utils'
import ConfirmDialog from '@/components/ui/ConfirmDialog'

// ─── Types ───────────────────────────────────────────────────────────────────

interface InternalDocsKanbanProps {
  documents: InternalDocument[]
  isLoading: boolean
  onStatusChange: (docId: number, newStatus: string) => Promise<void>
  onCardClick?: (doc: InternalDocument) => void
}

// ─── Kanban Columns ──────────────────────────────────────────────────────────

interface KanbanColumn {
  key: string
  label: string
  headerBg: string
  headerText: string
  borderColor: string
}

const KANBAN_COLUMNS: KanbanColumn[] = [
  { key: 'not_reviewed', label: 'Not Reviewed', headerBg: 'bg-red-100', headerText: 'text-red-800', borderColor: 'border-l-red-500' },
  { key: 'reviewed', label: 'Reviewed', headerBg: 'bg-amber-100', headerText: 'text-amber-800', borderColor: 'border-l-amber-500' },
  { key: 'sent', label: 'Sent', headerBg: 'bg-green-100', headerText: 'text-green-800', borderColor: 'border-l-green-500' },
]

// ─── Skeleton ────────────────────────────────────────────────────────────────

function SkeletonColumn() {
  return (
    <div className="flex flex-1 flex-col">
      <div className="mb-3 h-8 animate-pulse rounded-lg bg-gray-200" />
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-lg bg-gray-100" />
        ))}
      </div>
    </div>
  )
}

// ─── Card Content ────────────────────────────────────────────────────────────

function formatDocType(docType: string) {
  if (!docType) return '—'
  return docType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function DocCardContent({ doc }: { doc: InternalDocument }) {
  return (
    <>
      <p className="truncate text-sm font-semibold text-gray-900">{formatDocType(doc.document_type)}</p>
      <p className="mt-1 text-xs text-gray-500">Claim #{doc.claim_number}</p>
      {doc.original_filename && (
        <p className="mt-1 truncate text-xs text-gray-400" title={doc.original_filename}>
          {doc.original_filename}
        </p>
      )}
      {doc.notes && (
        <p className="mt-2 line-clamp-2 text-xs text-gray-500" title={doc.notes}>
          {doc.notes}
        </p>
      )}
    </>
  )
}

// ─── Draggable Card ──────────────────────────────────────────────────────────

function DraggableDocCard({
  doc,
  borderColor,
  onClick,
  isDragOverlay,
}: {
  doc: InternalDocument
  borderColor: string
  onClick?: () => void
  isDragOverlay?: boolean
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: String(doc.id),
  })

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
        <DocCardContent doc={doc} />
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
        if (!isDragging && onClick) {
          e.stopPropagation()
          onClick()
        }
      }}
    >
      <DocCardContent doc={doc} />
    </div>
  )
}

// ─── Droppable Column ────────────────────────────────────────────────────────

function DroppableColumn({
  column,
  items,
  onCardClick,
}: {
  column: KanbanColumn
  items: InternalDocument[]
  onCardClick?: (doc: InternalDocument) => void
}) {
  const { isOver, setNodeRef } = useDroppable({
    id: column.key,
  })

  return (
    <div ref={setNodeRef} className="flex flex-1 flex-col">
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
            No documents
          </div>
        ) : (
          items.map((doc) => (
            <DraggableDocCard
              key={doc.id}
              doc={doc}
              borderColor={column.borderColor}
              onClick={onCardClick ? () => onCardClick(doc) : undefined}
            />
          ))
        )}
      </div>
    </div>
  )
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function InternalDocsKanban({ documents, isLoading, onStatusChange, onCardClick }: InternalDocsKanbanProps) {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [confirmMove, setConfirmMove] = useState<{ docId: number; newStatus: string } | null>(null)
  const [isConfirmLoading, setIsConfirmLoading] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
  )

  // Group documents by status
  const grouped = useMemo(() => {
    const result: Record<string, InternalDocument[]> = {}
    for (const col of KANBAN_COLUMNS) {
      result[col.key] = []
    }
    for (const doc of documents) {
      const status = doc.status.toLowerCase()
      if (result[status]) {
        result[status].push(doc)
      }
    }
    return result
  }, [documents])

  // Find the active document for the overlay
  const activeDoc = useMemo(() => {
    if (!activeId) return null
    return documents.find((d) => String(d.id) === activeId) ?? null
  }, [activeId, documents])

  const activeColumn = useMemo(() => {
    if (!activeDoc) return null
    const status = activeDoc.status.toLowerCase()
    return KANBAN_COLUMNS.find((col) => col.key === status) ?? null
  }, [activeDoc])

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(String(event.active.id))
  }, [])

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveId(null)

      const { active, over } = event
      if (!over) return

      const docId = Number(active.id)
      const newStatus = String(over.id)

      // Find current status
      const doc = documents.find((d) => d.id === docId)
      if (!doc) return
      const currentStatus = doc.status.toLowerCase()

      // No change
      if (currentStatus === newStatus) return

      // "Sent" requires confirmation
      if (newStatus === 'sent') {
        setConfirmMove({ docId, newStatus })
        return
      }

      onStatusChange(docId, newStatus)
    },
    [documents, onStatusChange],
  )

  const handleDragCancel = useCallback(() => {
    setActiveId(null)
  }, [])

  const handleConfirm = useCallback(async () => {
    if (!confirmMove) return
    setIsConfirmLoading(true)
    try {
      await onStatusChange(confirmMove.docId, confirmMove.newStatus)
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
      <div className="flex gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
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
        <div className="flex gap-4">
          {KANBAN_COLUMNS.map((col) => (
            <DroppableColumn
              key={col.key}
              column={col}
              items={grouped[col.key] ?? []}
              onCardClick={onCardClick}
            />
          ))}
        </div>

        <DragOverlay>
          {activeDoc && activeColumn ? (
            <div className="w-72">
              <DraggableDocCard
                doc={activeDoc}
                borderColor={activeColumn.borderColor}
                isDragOverlay
              />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      <ConfirmDialog
        open={!!confirmMove}
        title="Mark as Sent"
        message="Are you sure you want to mark this document as sent? This indicates the document has been delivered."
        confirmLabel="Mark Sent"
        variant="warning"
        isLoading={isConfirmLoading}
        onConfirm={handleConfirm}
        onCancel={handleCancelConfirm}
      />
    </>
  )
}
