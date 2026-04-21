import { useState, useRef, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { useUpdateInternalDocument } from '@/hooks/useClaims'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { cn } from '@/lib/utils'

// ─── Constants ───────────────────────────────────────────────────────────────

const DOC_STATUS_OPTIONS = [
  { value: 'not_reviewed', label: 'Not Reviewed' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'sent', label: 'Sent' },
] as const

const docStatusColors: Record<string, string> = {
  not_reviewed: 'bg-red-100 text-red-800',
  reviewed: 'bg-yellow-100 text-yellow-800',
  sent: 'bg-green-100 text-green-800',
}

// ─── Props ───────────────────────────────────────────────────────────────────

interface InternalDocStatusEditorProps {
  documentId: number
  currentStatus: string
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function InternalDocStatusEditor({
  documentId,
  currentStatus,
}: InternalDocStatusEditorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [confirmStatus, setConfirmStatus] = useState<string | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const updateMutation = useUpdateInternalDocument()

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [isOpen])

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen])

  const executeStatusChange = async (newStatus: string) => {
    try {
      await updateMutation.mutateAsync({
        id: documentId,
        payload: { status: newStatus },
      })
      toast.success(`Document status changed to ${newStatus.replace(/_/g, ' ')}`)
    } catch {
      toast.error('Failed to update document status')
    }
    setIsOpen(false)
    setConfirmStatus(null)
  }

  const handleStatusChange = (newStatus: string) => {
    if (newStatus === currentStatus) {
      setIsOpen(false)
      return
    }

    if (newStatus === 'sent') {
      setConfirmStatus(newStatus)
      return
    }

    executeStatusChange(newStatus)
  }

  const normalized = currentStatus.toLowerCase().replace(/\s+/g, '_')
  const colorClass = docStatusColors[normalized] ?? 'bg-gray-100 text-gray-800'
  const label = currentStatus.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

  if (updateMutation.isPending) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-500">
        <Loader2 className="h-3 w-3 animate-spin" />
        Saving...
      </span>
    )
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Current Status Badge (clickable) */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          setIsOpen(!isOpen)
        }}
        className={cn(
          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium cursor-pointer transition-shadow',
          colorClass,
          'hover:ring-2 hover:ring-gray-300',
        )}
      >
        {label}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute left-0 top-full z-30 mt-1 w-48 overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg scrollbar-compact animate-in fade-in slide-in-from-top-0.5">
          {DOC_STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                handleStatusChange(opt.value)
              }}
              className={cn(
                'flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors hover:bg-gray-50',
                opt.value === currentStatus
                  ? 'font-medium text-primary-500'
                  : 'text-gray-700',
              )}
            >
              <span className="inline-flex items-center gap-2">
                <span
                  className={cn(
                    'h-2 w-2 shrink-0 rounded-full',
                    docStatusColors[opt.value]?.split(' ')[0] ?? 'bg-gray-300',
                  )}
                />
                {opt.label}
              </span>
              {opt.value === currentStatus && (
                <svg className="ml-2 h-4 w-4 shrink-0 text-primary-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
              )}
            </button>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={!!confirmStatus}
        title="Confirm Status Change"
        message="Are you sure you want to mark this document as Sent? This indicates it has been delivered to the recipient."
        confirmLabel="Mark as Sent"
        variant="warning"
        isLoading={updateMutation.isPending}
        onConfirm={() => confirmStatus && executeStatusChange(confirmStatus)}
        onCancel={() => setConfirmStatus(null)}
      />
    </div>
  )
}
