import { useState } from 'react'
import { X, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import Select from '@/components/ui/Select'
import { useUpdateBrokeredRequest } from '@/hooks/useBrokeredRequests'

// ─── Types ───────────────────────────────────────────────────────────────────

interface BulkActionBarProps {
  selectedIds: number[]
  onClearSelection: () => void
  onComplete: () => void
}

// ─── Constants ───────────────────────────────────────────────────────────────

const STATUS_OPTIONS = [
  { value: '', label: 'Change Status...' },
  { value: 'received', label: 'Received' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'otm', label: 'OTM' },
  { value: 'quoted', label: 'Quoted' },
  { value: 'on_hold', label: 'On Hold' },
  { value: 'denied', label: 'Denied' },
  { value: 'recalled', label: 'Recalled' },
  { value: 'blocked', label: 'Blocked' },
  { value: 'stalled', label: 'Stalled' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'bound', label: 'Bound' },
]

const CARRIER_OPTIONS = [
  { value: '', label: 'Change Carrier...' },
  { value: 'limit', label: 'Limit' },
  { value: 'am_trust', label: 'AM Trust' },
  { value: 'coterie', label: 'Coterie' },
  { value: 'rts', label: 'RTS / Nautilus' },
  { value: 'ergo_next', label: 'Ergo / NEXT' },
  { value: 'hiscox', label: 'Hiscox' },
  { value: 'zane', label: 'Zane' },
  { value: 'novella', label: 'Novella' },
  { value: 'wesure', label: 'weSure' },
  { value: 'rli', label: 'RLI' },
  { value: 'other', label: 'Other' },
]

// ─── Component ───────────────────────────────────────────────────────────────

export default function BulkActionBar({ selectedIds, onClearSelection, onComplete }: BulkActionBarProps) {
  const updateMutation = useUpdateBrokeredRequest()
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0 })

  const executeBulk = async (payload: Record<string, unknown>) => {
    setIsProcessing(true)
    const total = selectedIds.length
    setProgress({ current: 0, total })

    let succeeded = 0
    for (let i = 0; i < total; i++) {
      try {
        await updateMutation.mutateAsync({ id: selectedIds[i], payload })
        succeeded++
      } catch {
        // continue processing remaining
      }
      setProgress({ current: i + 1, total })
    }

    setIsProcessing(false)
    setProgress({ current: 0, total: 0 })

    if (succeeded === total) {
      toast.success(`${total} request${total !== 1 ? 's' : ''} updated`)
    } else {
      toast.warning(`${succeeded} of ${total} requests updated`)
    }
    onComplete()
  }

  const handleStatusChange = (status: string) => {
    if (!status) return
    executeBulk({ status })
  }

  const handleCarrierChange = (carrier: string) => {
    if (!carrier) return
    executeBulk({ carrier })
  }

  const handleToggle = (field: string, label: string) => {
    executeBulk({ [field]: true })
    // Note: toggling "true" for bulk since we don't know individual states.
    // A smarter approach could be added later.
    toast.info(`Setting ${label} to checked for ${selectedIds.length} request${selectedIds.length !== 1 ? 's' : ''}`)
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-gray-200 bg-white px-6 py-3 shadow-lg">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
        {/* Left: count + clear */}
        <div className="flex items-center gap-3">
          {isProcessing ? (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Loader2 className="h-4 w-4 animate-spin text-[#ff5c00]" />
              <span>
                Updating {progress.current} of {progress.total}...
              </span>
            </div>
          ) : (
            <>
              <span className="text-sm font-semibold text-gray-900">
                {selectedIds.length} selected
              </span>
              <button
                onClick={onClearSelection}
                className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
              >
                <X className="h-3.5 w-3.5" />
                Clear
              </button>
            </>
          )}
        </div>

        {/* Right: bulk actions */}
        {!isProcessing && (
          <div className="flex items-center gap-3">
            <Select
              value=""
              onChange={handleStatusChange}
              options={STATUS_OPTIONS}
              placeholder="Change Status..."
              size="sm"
              className="w-44"
            />
            <Select
              value=""
              onChange={handleCarrierChange}
              options={CARRIER_OPTIONS}
              placeholder="Change Carrier..."
              size="sm"
              className="w-44"
            />
            <button
              onClick={() => handleToggle('is_bound', 'Bound')}
              className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
            >
              Toggle Bound
            </button>
            <button
              onClick={() => handleToggle('docs_uploaded', 'Docs Uploaded')}
              className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
            >
              Toggle Docs
            </button>
            <button
              onClick={() => handleToggle('stripe_confirmed', 'Stripe')}
              className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
            >
              Toggle Stripe
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
