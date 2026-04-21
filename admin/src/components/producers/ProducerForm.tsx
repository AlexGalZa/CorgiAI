import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { toast } from 'sonner'
import {
  useCreateProducer,
  useUpdateProducer,
  type ProducerListItem,
} from '@/hooks/useProducers'
import Spinner from '@/components/ui/Spinner'
import Checkbox from '@/components/ui/Checkbox'
import Select from '@/components/ui/Select'
import Label from '@/components/ui/Label'
import { useFocusTrap } from '@/hooks/useFocusTrap'

const TYPE_OPTIONS = [
  { value: 'broker', label: 'Broker' },
  { value: 'agent', label: 'Agent' },
  { value: 'mga', label: 'MGA' },
]

interface ProducerFormProps {
  producer?: ProducerListItem
  onClose: () => void
  onSaved: () => void
}

export default function ProducerForm({ producer, onClose, onSaved }: ProducerFormProps) {
  const isEditing = !!producer
  const createMutation = useCreateProducer()
  const updateMutation = useUpdateProducer()
  const focusTrapRef = useFocusTrap(true)

  const [form, setForm] = useState({
    name: '',
    producer_type: 'broker',
    email: '',
    license_number: '',
    is_active: true,
  })

  const [error, setError] = useState('')

  useEffect(() => {
    if (producer) {
      setForm({
        name: producer.name,
        producer_type: producer.producer_type,
        email: producer.email,
        license_number: producer.license_number || '',
        is_active: producer.is_active,
      })
    }
  }, [producer])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    try {
      if (isEditing && producer) {
        await updateMutation.mutateAsync({ id: producer.id, payload: form })
        toast.success('Producer updated successfully')
      } else {
        await createMutation.mutateAsync(form)
        toast.success('Producer created successfully')
      }
      onSaved()
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? JSON.stringify((err as { response: { data: unknown } }).response.data)
          : 'An error occurred'
      setError(msg)
      toast.error('Failed to save producer')
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  const inputClass =
    'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 animate-in fade-in duration-150">
      <div ref={focusTrapRef} className="w-full max-w-lg rounded-xl border border-gray-200 bg-white shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEditing ? 'Edit Producer' : 'New Producer'}
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          {error && (
            <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div>
            <Label required>Name</Label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className={inputClass}
              required
              autoFocus
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Producer Type</Label>
              <Select
                value={form.producer_type}
                onChange={(val) => setForm((f) => ({ ...f, producer_type: val }))}
                options={TYPE_OPTIONS}
              />
            </div>
            <div>
              <Label>License Number</Label>
              <input
                type="text"
                value={form.license_number}
                onChange={(e) => setForm((f) => ({ ...f, license_number: e.target.value }))}
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <Label required>Email</Label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              className={inputClass}
              required
            />
          </div>

          <div>
            <Checkbox
              checked={form.is_active}
              onChange={(v) => setForm((f) => ({ ...f, is_active: v }))}
              label="Active"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#ea580c] disabled:opacity-50"
            >
              {isPending && <Spinner size="sm" />}
              {isEditing ? 'Save Changes' : 'Create Producer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
