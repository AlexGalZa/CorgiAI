import { useState, useRef, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { useUpdateClaim } from '@/hooks/useClaims'
import StatusBadge from '@/components/ui/StatusBadge'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { cn } from '@/lib/utils'

const TERMINAL_STATUSES = ['denied', 'closed']

// ─── Constants ───────────────────────────────────────────────────────────────

const CLAIM_STATUS_OPTIONS = [
  { value: 'filed', label: 'Filed' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'investigation', label: 'Investigation' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'denied', label: 'Denied' },
  { value: 'closed', label: 'Closed' },
] as const

// ─── Props ───────────────────────────────────────────────────────────────────

interface ClaimStatusEditorProps {
  claimId: number
  currentStatus: string
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function ClaimStatusEditor({
  claimId,
  currentStatus,
}: ClaimStatusEditorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [confirmStatus, setConfirmStatus] = useState<string | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const updateMutation = useUpdateClaim()

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
        id: claimId,
        payload: { status: newStatus },
      })
      toast.success(`Claim status changed to ${newStatus.replace(/_/g, ' ')}`)
    } catch {
      toast.error('Failed to update claim status')
    }
    setIsOpen(false)
    setConfirmStatus(null)
  }

  const handleStatusChange = (newStatus: string) => {
    if (newStatus === currentStatus) {
      setIsOpen(false)
      return
    }

    if (TERMINAL_STATUSES.includes(newStatus)) {
      setConfirmStatus(newStatus)
      return
    }

    executeStatusChange(newStatus)
  }

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
        className="inline-flex cursor-pointer rounded-full transition-shadow hover:ring-2 hover:ring-gray-300"
      >
        <StatusBadge status={currentStatus} variant="claim" />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute left-0 top-full z-30 mt-1 w-48 overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg scrollbar-compact animate-in fade-in slide-in-from-top-0.5">
          {CLAIM_STATUS_OPTIONS.map((opt) => (
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
              <StatusBadge status={opt.value} variant="claim" />
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
        message={`Are you sure you want to mark this claim as ${confirmStatus?.replace(/_/g, ' ')}? This action may be difficult to reverse.`}
        confirmLabel="Change Status"
        variant="danger"
        isLoading={updateMutation.isPending}
        onConfirm={() => confirmStatus && executeStatusChange(confirmStatus)}
        onCancel={() => setConfirmStatus(null)}
      />
    </div>
  )
}
