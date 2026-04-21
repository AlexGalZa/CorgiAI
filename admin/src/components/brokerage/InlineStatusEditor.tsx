import { toast } from 'sonner'
import InlineCellEditor from '@/components/ui/InlineCellEditor'
import StatusBadge from '@/components/ui/StatusBadge'
import { useUpdateBrokeredRequest } from '@/hooks/useBrokeredRequests'

// ─── Constants ───────────────────────────────────────────────────────────────

const STATUS_OPTIONS = [
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

const CONFIRM_STATUSES = ['denied', 'cancelled', 'recalled']

// ─── Props ───────────────────────────────────────────────────────────────────

interface InlineStatusEditorProps {
  requestId: number
  currentStatus: string
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function InlineStatusEditor({
  requestId,
  currentStatus,
}: InlineStatusEditorProps) {
  const updateMutation = useUpdateBrokeredRequest()

  const handleSave = async (newValue: string) => {
    try {
      await updateMutation.mutateAsync({
        id: requestId,
        payload: { status: newValue },
      })
      toast.success(`Status changed to ${newValue.replace(/_/g, ' ')}`)
    } catch {
      toast.error('Failed to update status')
      throw new Error('Failed to update status')
    }
  }

  return (
    <InlineCellEditor
      value={currentStatus}
      options={STATUS_OPTIONS}
      onSave={handleSave}
      variant="badge"
      renderValue={(val) => <StatusBadge status={val} variant="brokerage" />}
      confirmValues={CONFIRM_STATUSES}
      confirmMessage="Are you sure you want to change to this status? This action may be difficult to reverse."
    />
  )
}
