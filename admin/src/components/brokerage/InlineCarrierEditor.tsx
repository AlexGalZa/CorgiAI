import { toast } from 'sonner'
import InlineCellEditor from '@/components/ui/InlineCellEditor'
import { useUpdateBrokeredRequest } from '@/hooks/useBrokeredRequests'

// ─── Constants ───────────────────────────────────────────────────────────────

const CARRIER_OPTIONS = [
  { value: '', label: '— None —' },
  { value: 'Limit', label: 'Limit' },
  { value: 'AM Trust', label: 'AM Trust' },
  { value: 'Coterie', label: 'Coterie' },
  { value: 'RTS', label: 'RTS' },
  { value: 'Ergo/NEXT', label: 'Ergo/NEXT' },
  { value: 'Hiscox', label: 'Hiscox' },
  { value: 'Zane', label: 'Zane' },
  { value: 'Other', label: 'Other' },
]

// ─── Props ───────────────────────────────────────────────────────────────────

interface InlineCarrierEditorProps {
  requestId: number
  currentCarrier: string | null
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function InlineCarrierEditor({
  requestId,
  currentCarrier,
}: InlineCarrierEditorProps) {
  const updateMutation = useUpdateBrokeredRequest()

  const handleSave = async (newValue: string) => {
    try {
      await updateMutation.mutateAsync({
        id: requestId,
        payload: { carrier: newValue || '' },
      })
      toast.success(
        newValue
          ? `Carrier changed to ${newValue}`
          : 'Carrier cleared',
      )
    } catch {
      toast.error('Failed to update carrier')
      throw new Error('Failed to update carrier')
    }
  }

  return (
    <InlineCellEditor
      value={currentCarrier ?? ''}
      options={CARRIER_OPTIONS}
      onSave={handleSave}
      variant="text"
    />
  )
}
