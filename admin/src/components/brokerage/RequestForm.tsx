import { useEffect, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { X, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import type { BrokeredQuoteRequest } from '@/types'
import {
  useCreateBrokeredRequest,
  useUpdateBrokeredRequest,
} from '@/hooks/useBrokeredRequests'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import Select from '@/components/ui/Select'
import MultiSelect from '@/components/ui/MultiSelect'
import FormField from '@/components/ui/FormField'
import Checkbox from '@/components/ui/Checkbox'
import { useFocusTrap } from '@/hooks/useFocusTrap'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { useOrganizations } from '@/hooks/useOrganizations'
import { useConfigOptions } from '@/hooks/usePlatformConfig'

const CONFIRM_STATUSES = ['denied', 'cancelled', 'recalled']

// ─── Fallback Constants (used until PlatformConfig loads from DB) ────────────

const FALLBACK_STATUS_OPTIONS = [
  { value: 'received', label: 'Received' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'otm', label: 'Out to Market' },
  { value: 'quoted', label: 'Quoted' },
  { value: 'on_hold', label: 'On Hold' },
  { value: 'denied', label: 'Denied' },
  { value: 'recalled', label: 'Recalled' },
  { value: 'blocked', label: 'Blocked' },
  { value: 'stalled', label: 'Stalled' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'bound', label: 'Bound' },
]

const FALLBACK_COVERAGE_OPTIONS = [
  { value: 'cgl', label: 'Commercial General Liability' },
  { value: 'cul', label: 'Commercial Umbrella' },
  { value: 'cyber', label: 'Cyber Liability' },
  { value: 'tech_eo', label: 'Technology E&O' },
  { value: 'workers_comp', label: 'Workers Compensation' },
  { value: 'dno', label: 'Directors & Officers' },
  { value: 'bop', label: 'Business Owners Policy' },
  { value: 'crime', label: 'Crime' },
  { value: 'epl', label: 'Employment Practices Liability' },
  { value: 'med_malpractice', label: 'Medical Malpractice' },
  { value: 'comm_auto', label: 'Commercial Auto' },
  { value: 'hnoa', label: 'Hired & Non-Owned Auto' },
  { value: 'kidnap_ransom', label: 'Kidnap & Ransom' },
  { value: 'inland_marine', label: 'Inland Marine' },
  { value: 'aviation', label: 'Aviation' },
  { value: 'real_estate_eo', label: 'Real Estate E&O' },
  { value: 'misc_eo', label: 'Miscellaneous E&O' },
  { value: 'reps_warranties', label: 'Representations & Warranties' },
  { value: 'fiduciary', label: 'Fiduciary' },
  { value: 'erisa', label: 'ERISA 401(k)' },
  { value: 'pollution', label: 'Pollution/Environmental' },
  { value: 'international', label: 'International Package' },
  { value: 'media', label: 'Media Liability' },
  { value: 'crime_bond', label: 'Crime Bond' },
  { value: 'uas_aviation', label: 'UAS/Aviation Liability' },
  { value: 'other', label: 'Other' },
]

const FALLBACK_LIMIT_OPTIONS = [
  { value: '', label: 'Select limit...' },
  { value: '$500,000', label: '$500,000' },
  { value: '$1,000,000', label: '$1,000,000' },
  { value: '$2,000,000', label: '$2,000,000' },
  { value: '$3,000,000', label: '$3,000,000' },
  { value: '$4,000,000', label: '$4,000,000' },
  { value: '$5,000,000', label: '$5,000,000' },
  { value: '$10,000,000', label: '$10,000,000' },
]

const FALLBACK_RETENTION_OPTIONS = [
  { value: '', label: 'Select retention...' },
  { value: '$0', label: '$0' },
  { value: '$1,000', label: '$1,000' },
  { value: '$2,500', label: '$2,500' },
  { value: '$5,000', label: '$5,000' },
  { value: '$10,000', label: '$10,000' },
  { value: '$15,000', label: '$15,000' },
  { value: '$25,000', label: '$25,000' },
  { value: '$50,000', label: '$50,000' },
  { value: '$100,000', label: '$100,000' },
]

const FALLBACK_CARRIER_OPTIONS = [
  { value: '', label: 'Select carrier...' },
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


// ─── Schema ──────────────────────────────────────────────────────────────────

const requestSchema = z.object({
  company_name: z.string().min(1, 'Company name is required'),
  status: z.string().min(1, 'Status is required'),
  coverage_types: z.array(z.string()),
  carrier: z.string(),
  requested_coverage_detail: z.string(),
  aggregate_limit: z.string(),
  per_occurrence_limit: z.string(),
  retention: z.string(),
  blocker_type: z.string(),
  blocker_detail: z.string(),
  premium_amount: z.string(),
  requester_email: z.string().email('Invalid email').or(z.literal('')),
  notes: z.string(),
  client_contact_url: z.string(),
  client_email: z.string().email('Invalid email').or(z.literal('')),
  django_admin_url: z.string(),
  decline_reason: z.string(),
  missing_docs_note: z.string(),
  additional_notes: z.string(),
  // Fulfillment (edit mode only)
  is_bound: z.boolean(),
  custom_product_created: z.boolean(),
  docs_uploaded: z.boolean(),
  stripe_confirmed: z.boolean(),
})

type RequestFormData = z.infer<typeof requestSchema>

// ─── Props ───────────────────────────────────────────────────────────────────

interface RequestFormProps {
  request?: BrokeredQuoteRequest        // edit mode
  initialData?: Partial<BrokeredQuoteRequest>  // pre-fill for duplicate
  onClose: () => void
  onSaved: () => void
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const inputClasses =
  'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]'

function getDefaultValues(
  request?: BrokeredQuoteRequest,
  initialData?: Partial<BrokeredQuoteRequest>,
  currentUserEmail?: string,
): RequestFormData {
  // Edit mode
  if (request) {
    return {
      company_name: request.company_name || '',
      status: request.status || 'received',
      coverage_types: request.coverage_types || [],
      carrier: request.carrier || '',
      requested_coverage_detail: request.requested_coverage_detail || '',
      aggregate_limit: request.aggregate_limit || '',
      per_occurrence_limit: request.per_occurrence_limit || '',
      retention: request.retention || '',
      blocker_type: request.blocker_type || '',
      blocker_detail: request.blocker_detail || '',
      premium_amount: request.premium_amount ?? '',
      requester_email: request.requester_email || '',
      notes: request.notes || '',
      client_contact_url: request.client_contact_url || '',
      client_email: request.client_email || '',
      django_admin_url: request.django_admin_url || '',
      decline_reason: request.decline_reason || '',
      missing_docs_note: request.missing_docs_note || '',
      additional_notes: request.additional_notes || '',
      is_bound: request.is_bound ?? false,
      custom_product_created: request.custom_product_created ?? false,
      docs_uploaded: request.docs_uploaded ?? false,
      stripe_confirmed: request.stripe_confirmed ?? false,
    }
  }

  // Duplicate mode
  if (initialData) {
    return {
      company_name: initialData.company_name || '',
      status: 'received',
      coverage_types: initialData.coverage_types || [],
      carrier: initialData.carrier || '',
      requested_coverage_detail: initialData.requested_coverage_detail || '',
      aggregate_limit: initialData.aggregate_limit || '',
      per_occurrence_limit: initialData.per_occurrence_limit || '',
      retention: initialData.retention || '',
      blocker_type: '',
      blocker_detail: '',
      premium_amount: '',
      requester_email: initialData.requester_email || '',
      notes: initialData.notes || '',
      client_contact_url: initialData.client_contact_url || '',
      client_email: initialData.client_email || '',
      django_admin_url: '',
      decline_reason: '',
      missing_docs_note: '',
      additional_notes: '',
      is_bound: false,
      custom_product_created: false,
      docs_uploaded: false,
      stripe_confirmed: false,
    }
  }

  // New
  return {
    company_name: '',
    status: 'received',
    coverage_types: [],
    carrier: '',
    requested_coverage_detail: '',
    aggregate_limit: '',
    per_occurrence_limit: '',
    retention: '',
    blocker_type: '',
    blocker_detail: '',
    premium_amount: '',
    requester_email: currentUserEmail ?? '',
    notes: '',
    client_contact_url: '',
    client_email: '',
    django_admin_url: '',
    decline_reason: '',
    missing_docs_note: '',
    additional_notes: '',
    is_bound: false,
    custom_product_created: false,
    docs_uploaded: false,
    stripe_confirmed: false,
  }
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function RequestForm({ request, initialData, onClose, onSaved }: RequestFormProps) {
  const isEditMode = !!request
  const isDuplicateMode = !request && !!initialData
  const isNewMode = !isEditMode && !isDuplicateMode
  const createMutation = useCreateBrokeredRequest()
  const updateMutation = useUpdateBrokeredRequest()
  const currentUser = useAuthStore((s) => s.user)
  const [pendingSubmit, setPendingSubmit] = useState<RequestFormData | null>(null)
  const focusTrapRef = useFocusTrap(true)
  const orgsQ = useOrganizations({})
  const orgResults = orgsQ.data?.results ?? []

  // DB-driven options (fall back to hardcoded if config not loaded yet)
  const STATUS_OPTIONS = useConfigOptions('brokered_status_options', FALLBACK_STATUS_OPTIONS)
  const COVERAGE_TYPE_OPTIONS = useConfigOptions('brokered_coverage_type_options', FALLBACK_COVERAGE_OPTIONS)
  const AGG_LIMIT_OPTIONS = useConfigOptions('aggregate_limit_options', FALLBACK_LIMIT_OPTIONS)
  const OCC_LIMIT_OPTIONS = useConfigOptions('per_occurrence_limit_options', FALLBACK_LIMIT_OPTIONS)
  const RETENTION_OPTIONS = useConfigOptions('retention_options', FALLBACK_RETENTION_OPTIONS)
  const CARRIER_OPTIONS = useConfigOptions('carrier_options', FALLBACK_CARRIER_OPTIONS)

  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<RequestFormData>({
    resolver: zodResolver(requestSchema),
    defaultValues: getDefaultValues(request, initialData, currentUser?.email),
  })

  const watchStatus = watch('status')
  const watchDocsUploaded = watch('docs_uploaded')

  // Populate form when editing
  useEffect(() => {
    if (request) {
      reset(getDefaultValues(request))
    }
  }, [request, reset])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  // Lock body scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  const executeSubmit = async (data: RequestFormData) => {
    try {
      // Build payload - convert premium_amount to number or null
      const payload: Record<string, unknown> = {
        ...data,
        premium_amount: data.premium_amount ? parseFloat(data.premium_amount) : null,
      }

      if (isEditMode) {
        await updateMutation.mutateAsync({ id: request.id, payload })
        toast.success('Request updated successfully')
      } else {
        await createMutation.mutateAsync(payload as Partial<BrokeredQuoteRequest>)
        toast.success(isDuplicateMode ? 'Request duplicated successfully' : 'Request created successfully')
      }
      onSaved()
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Something went wrong'
      toast.error(message)
    }
  }

  const onSubmit = async (data: RequestFormData) => {
    // If changing to a terminal status in edit mode, require confirmation
    if (
      isEditMode &&
      CONFIRM_STATUSES.includes(data.status) &&
      data.status !== request.status
    ) {
      setPendingSubmit(data)
      return
    }
    await executeSubmit(data)
  }

  const isPending = createMutation.isPending || updateMutation.isPending || isSubmitting
  const mutationError = createMutation.error || updateMutation.error

  const formTitle = isEditMode
    ? 'Edit Request'
    : isDuplicateMode
      ? 'Duplicate Request'
      : 'New Brokered Quote Request'

  const submitLabel = isEditMode
    ? 'Save Changes'
    : isDuplicateMode
      ? 'Create Duplicate'
      : 'Create Request'

  const showDeclineReason = watchStatus === 'denied' || watchStatus === 'recalled'
  const showMissingDocsNote = !watchDocsUploaded

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 animate-in fade-in duration-150" onClick={onClose} />

      {/* Modal */}
      <div ref={focusTrapRef} className="relative z-10 flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-bold text-gray-900">{formTitle}</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <form onSubmit={handleSubmit(onSubmit)} className="flex-1 overflow-y-auto scrollbar-compact">
          <div className="space-y-6 px-6 py-5">
            {/* API Error */}
            {mutationError && (
              <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
                {mutationError instanceof Error
                  ? mutationError.message
                  : 'Failed to save request. Please try again.'}
              </div>
            )}

            {/* ── Core Fields ─────────────────────────────────────── */}
            <div className="grid grid-cols-2 gap-4">
              {/* Client Selector */}
              <FormField
                label="Select Client (optional)"
                className="col-span-2"
              >
                <Select
                  value=""
                  onChange={(clientName) => {
                    const client = orgResults.find((o) => o.name === clientName)
                    if (client) {
                      setValue('company_name', client.name)
                      if (client.owner_detail?.email) {
                        setValue('client_email', client.owner_detail.email)
                      }
                    }
                  }}
                  options={[
                    { value: '', label: 'Pick a client to pre-fill...' },
                    ...orgResults.map((o) => ({ value: o.name, label: o.name })),
                  ]}
                  placeholder="Pick a client to pre-fill..."
                />
              </FormField>

              {/* Company Name */}
              <FormField
                label="Company Name"
                htmlFor="company_name"
                required
                error={errors.company_name?.message}
                className="col-span-2"
              >
                <input
                  id="company_name"
                  type="text"
                  {...register('company_name')}
                  className={inputClasses}
                  placeholder="Enter company name"
                  autoFocus
                />
              </FormField>

              {/* Status: locked to "Received" on new requests, editable on edit */}
              <FormField label="Status" required error={errors.status?.message}>
                {isNewMode ? (
                  <div className={cn(inputClasses, 'bg-gray-50 text-gray-500 cursor-not-allowed select-none')}>
                    Received
                  </div>
                ) : (
                  <Controller
                    name="status"
                    control={control}
                    render={({ field }) => (
                      <Select
                        value={field.value}
                        onChange={field.onChange}
                        options={STATUS_OPTIONS}
                        placeholder="Select status..."
                      />
                    )}
                  />
                )}
              </FormField>

              {/* Carrier: only shown in edit mode */}
              {isEditMode && (
                <FormField label="Carrier">
                  <Controller
                    name="carrier"
                    control={control}
                    render={({ field }) => (
                      <Select
                        value={field.value}
                        onChange={field.onChange}
                        options={CARRIER_OPTIONS}
                        placeholder="Select carrier..."
                      />
                    )}
                  />
                </FormField>
              )}
            </div>

            {/* Coverage Types */}
            <FormField label="Coverage Types">
              <Controller
                name="coverage_types"
                control={control}
                render={({ field }) => (
                  <MultiSelect
                    value={field.value}
                    onChange={field.onChange}
                    options={COVERAGE_TYPE_OPTIONS}
                    placeholder="Select coverages..."
                    maxDisplay={4}
                  />
                )}
              />
            </FormField>

            {/* ── Coverage Details ─────────────────────────────────── */}
            <FormField label="Requested Coverage Detail" htmlFor="requested_coverage_detail">
              <textarea
                id="requested_coverage_detail"
                rows={3}
                {...register('requested_coverage_detail')}
                className={inputClasses}
                placeholder="AGG/OCC/Retention details..."
              />
            </FormField>

            <div className="grid grid-cols-3 gap-4">
              <FormField label="Aggregate Limit" htmlFor="aggregate_limit">
                <Controller
                  name="aggregate_limit"
                  control={control}
                  render={({ field }) => (
                    <Select
                      value={field.value}
                      onChange={field.onChange}
                      options={AGG_LIMIT_OPTIONS}
                      placeholder="Select limit..."
                    />
                  )}
                />
              </FormField>
              <FormField label="Per Occurrence Limit" htmlFor="per_occurrence_limit">
                <Controller
                  name="per_occurrence_limit"
                  control={control}
                  render={({ field }) => (
                    <Select
                      value={field.value}
                      onChange={field.onChange}
                      options={OCC_LIMIT_OPTIONS}
                      placeholder="Select limit..."
                    />
                  )}
                />
              </FormField>
              <FormField label="Retention" htmlFor="retention">
                <Controller
                  name="retention"
                  control={control}
                  render={({ field }) => (
                    <Select
                      value={field.value}
                      onChange={field.onChange}
                      options={RETENTION_OPTIONS}
                      placeholder="Select retention..."
                    />
                  )}
                />
              </FormField>
            </div>

            {/* ── Blocker ──────────────────────────────────────────── */}
                        {/* ── Blocker: free text only ────────────────────── */}
            <FormField label="Blocker" htmlFor="blocker_detail">
              <textarea
                id="blocker_detail"
                rows={2}
                {...register('blocker_detail')}
                className={inputClasses}
                placeholder="Describe any blocker or issue preventing progress..."
              />
            </FormField>

            {/* ── Requester Email (pre-filled) ──────────────── */}
            <FormField label="Requester Email" htmlFor="requester_email" error={errors.requester_email?.message}>
              <input
                id="requester_email"
                type="email"
                {...register('requester_email')}
                className={inputClasses}
                placeholder="ae@company.com"
              />
            </FormField>

            {/* ── Premium (edit mode only) ─────────────────── */}
            {isEditMode && (
              <FormField label="Premium Amount" htmlFor="premium_amount">
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">$</span>
                  <input
                    id="premium_amount"
                    type="number"
                    step="0.01"
                    min="0"
                    {...register('premium_amount')}
                    className={cn(inputClasses, 'pl-7')}
                    placeholder="0.00"
                  />
                </div>
              </FormField>
            )}

            {/* ── Client Info ──────────────────────────────────────── */}
            <div>
              <h3 className="mb-3 text-sm font-semibold text-gray-900">Client Info</h3>
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Client Email" htmlFor="client_email" error={errors.client_email?.message}>
                  <input
                    id="client_email"
                    type="email"
                    {...register('client_email')}
                    className={inputClasses}
                    placeholder="client@company.com"
                  />
                </FormField>
                <FormField label="Client Contact URL" htmlFor="client_contact_url">
                  <input
                    id="client_contact_url"
                    type="text"
                    {...register('client_contact_url')}
                    className={inputClasses}
                    placeholder="HubSpot link"
                  />
                </FormField>
              </div>
            </div>

            {/* Notes */}
            <FormField label="Notes" htmlFor="notes">
              <textarea
                id="notes"
                rows={3}
                {...register('notes')}
                className={inputClasses}
                placeholder="Additional notes..."
              />
            </FormField>

            {/* Additional Notes */}
            <FormField label="Additional Notes" htmlFor="additional_notes">
              <textarea
                id="additional_notes"
                rows={2}
                {...register('additional_notes')}
                className={inputClasses}
                placeholder="Any other relevant information..."
              />
            </FormField>

            {/* ── Conditional Fields ───────────────────────────────── */}

            {/* Decline Reason: only when status is denied or recalled */}
            {showDeclineReason && (
              <FormField label="Decline Reason" htmlFor="decline_reason">
                <textarea
                  id="decline_reason"
                  rows={3}
                  {...register('decline_reason')}
                  className={inputClasses}
                  placeholder="Reason for declining or recalling this request..."
                />
              </FormField>
            )}

            {/* Missing Docs Note: only when docs_uploaded is false */}
            {showMissingDocsNote && (
              <FormField label="Missing Documents Note" htmlFor="missing_docs_note">
                <textarea
                  id="missing_docs_note"
                  rows={2}
                  {...register('missing_docs_note')}
                  className={inputClasses}
                  placeholder="Note about missing documents..."
                />
              </FormField>
            )}

            {/* ── External Links ────────────────────────────────────── */}
            <FormField label="Django Admin URL" htmlFor="django_admin_url">
              <input
                id="django_admin_url"
                type="text"
                {...register('django_admin_url')}
                className={inputClasses}
                placeholder="Admin link"
              />
            </FormField>

            {/* ── Fulfillment (edit only) ───────────────────────────── */}
            {isEditMode && (
              <div>
                <h3 className="mb-3 text-sm font-semibold text-gray-900">
                  Fulfillment Checklist
                </h3>
                <div className="grid grid-cols-2 gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <Checkbox
                    checked={watch('is_bound')}
                    onChange={(v) => setValue('is_bound', v)}
                    label="Is Bound"
                  />
                  <Checkbox
                    checked={watch('custom_product_created')}
                    onChange={(v) => setValue('custom_product_created', v)}
                    label="Custom Product Created"
                  />
                  <Checkbox
                    checked={watch('docs_uploaded')}
                    onChange={(v) => setValue('docs_uploaded', v)}
                    label="Docs Uploaded"
                  />
                  <Checkbox
                    checked={watch('stripe_confirmed')}
                    onChange={(v) => setValue('stripe_confirmed', v)}
                    label="Stripe Confirmed"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-6 py-4">
            <button
              type="button"
              onClick={onClose}
              disabled={isPending}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-[#ea580c] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {submitLabel}
            </button>
          </div>
        </form>

        <ConfirmDialog
          open={!!pendingSubmit}
          title="Confirm Status Change"
          message={`Are you sure you want to set status to ${pendingSubmit?.status.replace(/_/g, ' ')}?`}
          confirmLabel="Confirm"
          variant="danger"
          isLoading={isPending}
          onConfirm={() => {
            if (pendingSubmit) {
              executeSubmit(pendingSubmit)
              setPendingSubmit(null)
            }
          }}
          onCancel={() => setPendingSubmit(null)}
        />
      </div>
    </div>
  )
}
