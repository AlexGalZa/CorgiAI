import { useState } from 'react'
import { X, Loader2, Info } from 'lucide-react'
import { toast } from 'sonner'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import Label from '@/components/ui/Label'
import Checkbox from '@/components/ui/Checkbox'
import { useFocusTrap } from '@/hooks/useFocusTrap'

interface CertificateFormProps {
  open: boolean
  onClose: () => void
}

const STEPS = [
  { number: 1, label: 'Certificate Info' },
  { number: 2, label: 'Holder Details' },
  { number: 3, label: 'Service Info' },
]

export default function CertificateForm({ open, onClose }: CertificateFormProps) {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({
    coi_number: '',
    custom_coi_number: '',
    holder_name: '',
    holder_second_line: '',
    holder_street_address: '',
    holder_suite: '',
    holder_city: '',
    holder_state: '',
    holder_zip: '',
    is_additional_insured: false,
    service_location_job: '',
    service_location_address: '',
    service_you_provide_job: '',
    service_you_provide_service: '',
  })

  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: async (data: typeof form) => {
      const resp = await api.post('/certificates/', data)
      return resp.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      toast.success('Certificate created')
      handleClose()
    },
    onError: () => {
      toast.error('Failed to create certificate')
    },
  })

  const handleClose = () => {
    setStep(1)
    setForm({
      coi_number: '', custom_coi_number: '', holder_name: '', holder_second_line: '',
      holder_street_address: '', holder_suite: '', holder_city: '', holder_state: '',
      holder_zip: '', is_additional_insured: false, service_location_job: '',
      service_location_address: '', service_you_provide_job: '', service_you_provide_service: '',
    })
    onClose()
  }

  const update = (field: string, value: string | boolean) =>
    setForm((f) => ({ ...f, [field]: value }))

  const canProceed = () => {
    if (step === 1) return form.coi_number.trim().length > 0
    if (step === 2) return form.holder_name.trim().length > 0
    return true
  }

  const handleSubmit = () => {
    if (step < 3) {
      setStep(step + 1)
      return
    }
    mutation.mutate(form)
  }

  const focusTrapRef = useFocusTrap(open)

  if (!open) return null

  const inputCls =
    'w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 transition-colors focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]'

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20 animate-in fade-in duration-150" onClick={handleClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          ref={focusTrapRef}
          className="flex w-full max-w-lg flex-col rounded-xl border border-gray-200 bg-white shadow-xl animate-in fade-in zoom-in-95 duration-150"
          style={{ maxHeight: 'calc(100vh - 4rem)' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900">New Certificate</h2>
            <button onClick={handleClose} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600" aria-label="Close">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Step indicator */}
          <div className="border-b border-gray-100 px-6 py-3">
            <div className="flex items-center gap-2">
              {STEPS.map((s) => (
                <div key={s.number} className="flex items-center gap-2">
                  {s.number > 1 && <div className={`h-px w-6 ${step >= s.number ? 'bg-[#ff5c00]' : 'bg-gray-200'}`} />}
                  <div className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                    step === s.number ? 'bg-orange-50 text-[#ff5c00]' : step > s.number ? 'bg-emerald-50 text-emerald-600' : 'bg-gray-100 text-gray-400'
                  }`}>
                    <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                      step === s.number ? 'bg-[#ff5c00] text-white' : step > s.number ? 'bg-emerald-500 text-white' : 'bg-gray-300 text-white'
                    }`}>
                      {step > s.number ? '✓' : s.number}
                    </span>
                    {s.label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5 scrollbar-compact">
            {step === 1 && (
              <div className="space-y-4">
                <div>
                  <Label required>COI Number</Label>
                  <input type="text" value={form.coi_number} onChange={(e) => update('coi_number', e.target.value)} className={inputCls} placeholder="e.g. COI-2026-0001" autoFocus />
                </div>
                <div>
                  <Label hint="Optional">Custom COI Number</Label>
                  <input type="text" value={form.custom_coi_number} onChange={(e) => update('custom_coi_number', e.target.value)} className={inputCls} placeholder="Client-specific reference" />
                </div>
                <Checkbox
                  checked={form.is_additional_insured}
                  onChange={(v) => update('is_additional_insured', v)}
                  label="Additional Insured"
                />
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                {/* Info callout */}
                <div className="flex gap-3 rounded-lg border border-blue-100 bg-blue-50 p-3">
                  <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
                  <p className="text-sm text-blue-700">
                    Each certificate is issued to a specific holder. If you need to cover multiple people or entities, create a separate certificate for each one.
                  </p>
                </div>

                <div>
                  <Label required>Holder Name</Label>
                  <input type="text" value={form.holder_name} onChange={(e) => update('holder_name', e.target.value)} className={inputCls} placeholder="Full name of the certificate holder" autoFocus />
                </div>
                <div>
                  <Label hint="Optional">Second Line</Label>
                  <input type="text" value={form.holder_second_line} onChange={(e) => update('holder_second_line', e.target.value)} className={inputCls} placeholder="DBA, department, attention line" />
                </div>
                <div>
                  <Label>Street Address</Label>
                  <input type="text" value={form.holder_street_address} onChange={(e) => update('holder_street_address', e.target.value)} className={inputCls} placeholder="123 Main St" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Suite / Unit</Label>
                    <input type="text" value={form.holder_suite} onChange={(e) => update('holder_suite', e.target.value)} className={inputCls} placeholder="Suite 100" />
                  </div>
                  <div>
                    <Label>City</Label>
                    <input type="text" value={form.holder_city} onChange={(e) => update('holder_city', e.target.value)} className={inputCls} placeholder="San Francisco" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>State</Label>
                    <input type="text" value={form.holder_state} onChange={(e) => update('holder_state', e.target.value)} className={inputCls} placeholder="CA" maxLength={2} />
                  </div>
                  <div>
                    <Label>ZIP</Label>
                    <input type="text" value={form.holder_zip} onChange={(e) => update('holder_zip', e.target.value)} className={inputCls} placeholder="94105" />
                  </div>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-4">
                <div>
                  <Label hint="Optional">Service Location / Job</Label>
                  <input type="text" value={form.service_location_job} onChange={(e) => update('service_location_job', e.target.value)} className={inputCls} placeholder="Job site or project name" autoFocus />
                </div>
                <div>
                  <Label hint="Optional">Service Location Address</Label>
                  <input type="text" value={form.service_location_address} onChange={(e) => update('service_location_address', e.target.value)} className={inputCls} placeholder="Full address of the service location" />
                </div>
                <div>
                  <Label hint="Optional">Service You Provide - Job</Label>
                  <input type="text" value={form.service_you_provide_job} onChange={(e) => update('service_you_provide_job', e.target.value)} className={inputCls} placeholder="Job title or role" />
                </div>
                <div>
                  <Label hint="Optional">Service Description</Label>
                  <textarea value={form.service_you_provide_service} onChange={(e) => update('service_you_provide_service', e.target.value)} className={`${inputCls} resize-none`} rows={3} placeholder="Describe the services you provide" />
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-gray-200 px-6 py-4">
            <button
              type="button"
              onClick={step > 1 ? () => setStep(step - 1) : handleClose}
              className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {step > 1 ? 'Back' : 'Cancel'}
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canProceed() || mutation.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-[#ea580c] disabled:opacity-50"
            >
              {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {step < 3 ? 'Continue' : 'Create Certificate'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
