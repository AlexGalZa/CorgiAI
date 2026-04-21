import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  X,
  CheckCircle2,
  XCircle,
  ExternalLink,
  FileText,
  AlertTriangle,
  Loader2,
  Pencil,
  Copy,
  LinkIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import type { BrokeredQuoteRequest } from '@/types'
import StatusBadge from '@/components/ui/StatusBadge'
import ActivityTimeline from '@/components/ui/ActivityTimeline'
import { useUpdateBrokeredRequest } from '@/hooks/useBrokeredRequests'
import { useAuditLog } from '@/hooks/useAuditLog'
import { usePermissions } from '@/lib/permissions'
import CoverageTags from '@/components/ui/CoverageTags'
import { formatCurrency, formatDate } from '@/lib/formatters'
import { cn } from '@/lib/utils'

const STATUS_OPTIONS = [
  'received', 'submitted', 'otm', 'quoted', 'on_hold',
  'denied', 'recalled', 'blocked', 'stalled', 'cancelled', 'bound',
]

// ─── Types ───────────────────────────────────────────────────────────────────

interface RequestDetailPanelProps {
  request: BrokeredQuoteRequest | null
  onClose: () => void
  onEdit?: (request: BrokeredQuoteRequest) => void
  onDuplicate?: (request: BrokeredQuoteRequest) => void
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-gray-100 py-4">
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-400">{title}</h4>
      {children}
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between py-1">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="ml-4 text-right text-sm font-medium text-gray-900">{value ?? '—'}</span>
    </div>
  )
}

function InteractiveChecklistItem({
  label,
  checked,
  fieldName,
  requestId,
}: {
  label: string
  checked: boolean
  fieldName: string
  requestId: number
}) {
  const [optimistic, setOptimistic] = useState<boolean | null>(null)
  const updateMutation = useUpdateBrokeredRequest()

  // When the server value catches up, clear the optimistic override
  useEffect(() => {
    if (optimistic !== null && checked === optimistic) {
      setOptimistic(null)
    }
  }, [checked, optimistic])

  const displayChecked = optimistic ?? checked

  const handleToggle = async () => {
    const newValue = !displayChecked
    setOptimistic(newValue)
    try {
      await updateMutation.mutateAsync({
        id: requestId,
        payload: { [fieldName]: newValue },
      })
      toast.success(`${label} ${newValue ? 'checked' : 'unchecked'}`)
    } catch {
      setOptimistic(null) // revert on failure
      toast.error(`Failed to update ${label}`)
    }
  }

  return (
    <button
      type="button"
      onClick={handleToggle}
      disabled={updateMutation.isPending}
      className="flex w-full items-center gap-2 py-1 text-left transition-colors hover:bg-gray-50 rounded -mx-1 px-1 disabled:opacity-50"
    >
      {displayChecked ? (
        <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500" />
      ) : (
        <XCircle className="h-4.5 w-4.5 text-gray-300" />
      )}
      <span className={cn('text-sm', displayChecked ? 'text-gray-900' : 'text-gray-400')}>{label}</span>
    </button>
  )
}

function StaticChecklistItem({ label, checked }: { label: string; checked: boolean }) {
  return (
    <div className="flex items-center gap-2 py-1">
      {checked ? (
        <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500" />
      ) : (
        <XCircle className="h-4.5 w-4.5 text-gray-300" />
      )}
      <span className={cn('text-sm', checked ? 'text-gray-900' : 'text-gray-400')}>{label}</span>
    </div>
  )
}

// ─── Component ───────────────────────────────────────────────────────────────

function PanelHeader({ request, onClose }: { request: BrokeredQuoteRequest; onClose: () => void }) {
  const [editing, setEditing] = useState(false)
  const updateMutation = useUpdateBrokeredRequest()
  const { canEditBrokeredRequest } = usePermissions()

  const handleStatusChange = async (newStatus: string) => {
    try {
      await updateMutation.mutateAsync({ id: request.id, payload: { status: newStatus } })
      toast.success(`Status changed to ${newStatus.replace(/_/g, ' ')}`)
      setEditing(false)
    } catch {
      toast.error('Failed to update status')
    }
  }

  return (
    <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
      <div className="min-w-0 flex-1">
        <h2 className="truncate text-lg font-bold text-gray-900">{request.company_name}</h2>
        <div className="mt-1.5 flex items-center gap-2">
          {editing ? (
            <div className="flex flex-wrap gap-1.5">
              {STATUS_OPTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleStatusChange(s)}
                  disabled={updateMutation.isPending}
                  className={cn(
                    'rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
                    s === request.status
                      ? 'bg-[#ff5c00] text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
                  )}
                >
                  {s.replace(/_/g, ' ')}
                </button>
              ))}
              <button
                onClick={() => setEditing(false)}
                className="ml-1 text-xs text-gray-400 hover:text-gray-600"
              >
                Cancel
              </button>
            </div>
          ) : (
            <>
              <StatusBadge status={request.status} variant="brokerage" />
              {canEditBrokeredRequest && (
                <button
                  onClick={() => setEditing(true)}
                  className="text-[11px] text-gray-400 hover:text-[#ff5c00]"
                >
                  Change
                </button>
              )}
            </>
          )}
          {updateMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin text-gray-400" />}
        </div>
      </div>
      <button
        onClick={onClose}
        className="ml-4 rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        aria-label="Close"
      >
        <X className="h-5 w-5" />
      </button>
    </div>
  )
}

export default function RequestDetailPanel({ request, onClose, onEdit, onDuplicate }: RequestDetailPanelProps) {
  const { canEditBrokeredRequest: canEditDetail } = usePermissions()
  // Fetch audit log for this request
  const auditLog = useAuditLog(
    request ? 'brokered_request' : undefined,
    request?.id,
  )

  // Lock body scroll when open
  useEffect(() => {
    if (request) {
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [request])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  if (!request) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30 animate-in fade-in duration-150" onClick={onClose} />

      {/* Panel */}
      <div className="relative z-10 flex w-full max-w-lg flex-col overflow-hidden bg-white shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Header with inline status edit */}
        <PanelHeader request={request} onClose={onClose} />

        {/* Action button bar */}
        {(onEdit || onDuplicate) && (
          <div className="flex items-center gap-2 border-b border-gray-100 px-6 py-2">
            {onEdit && (
              <button
                onClick={() => onEdit(request)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
              >
                <Pencil className="h-3.5 w-3.5" />
                Edit Request
              </button>
            )}
            {onDuplicate && (
              <button
                onClick={() => onDuplicate(request)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
              >
                <Copy className="h-3.5 w-3.5" />
                Duplicate
              </button>
            )}
          </div>
        )}

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 pb-6 scrollbar-compact">
          {/* Coverage Details */}
          <Section title="Coverage Details">
            <DetailRow label="Coverage Types" value={<CoverageTags codes={request.coverage_types} />} />
            {/* Additional coverage fields rendered if present in notes */}
            <DetailRow label="Notes" value={request.notes || '—'} />
          </Section>

          {/* Request Info */}
          <Section title="Request Info">
            <DetailRow label="Carrier" value={request.carrier} />
            <DetailRow label="Requester" value={request.requester_email} />
            <DetailRow label="Client Email" value={request.client_email || '—'} />
            <DetailRow label="Created" value={formatDate(request.created_at)} />
            <DetailRow label="Updated" value={formatDate(request.updated_at)} />
            <DetailRow label="Request ID" value={`#${request.id}`} />
            {request.quote && (
              <DetailRow
                label="Linked Quote"
                value={
                  <Link
                    to={`/quotes/${request.quote}`}
                    className="inline-flex items-center gap-1 text-[#ff5c00] hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <LinkIcon className="h-3 w-3" />
                    Quote #{request.quote}
                  </Link>
                }
              />
            )}
            {request.django_admin_url && (
              <DetailRow
                label="Django Admin"
                value={
                  <a
                    href={request.django_admin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[#ff5c00] hover:underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Open in Admin
                  </a>
                }
              />
            )}
            {request.client_contact_url && (
              <DetailRow
                label="HubSpot"
                value={
                  <a
                    href={request.client_contact_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[#ff5c00] hover:underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Open in HubSpot
                  </a>
                }
              />
            )}
          </Section>

          {/* Blocker */}
          {request.has_blocker && (
            <Section title="Blocker">
              <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                  <span className="text-sm font-semibold text-red-800">
                    {request.blocker_type?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) ??
                      'Unknown Blocker'}
                  </span>
                </div>
                {request.blocker_detail && (
                  <p className="mt-2 text-sm text-red-700">{request.blocker_detail}</p>
                )}
              </div>
            </Section>
          )}

          {/* Financials */}
          <Section title="Financials">
            <DetailRow label="Premium" value={formatCurrency(request.premium_amount)} />
          </Section>

          {/* Fulfillment Checklist (interactive for editors, static for others) */}
          <Section title="Fulfillment Checklist">
            <div className="space-y-0.5">
              {canEditDetail ? (
                <>
                  <InteractiveChecklistItem label="Bound" checked={request.is_bound} fieldName="is_bound" requestId={request.id} />
                  <InteractiveChecklistItem label="Custom Product Created" checked={request.custom_product_created} fieldName="custom_product_created" requestId={request.id} />
                  <InteractiveChecklistItem label="Docs Uploaded" checked={request.docs_uploaded} fieldName="docs_uploaded" requestId={request.id} />
                  <InteractiveChecklistItem label="Stripe Confirmed" checked={request.stripe_confirmed} fieldName="stripe_confirmed" requestId={request.id} />
                </>
              ) : (
                <>
                  <StaticChecklistItem label="Bound" checked={request.is_bound} />
                  <StaticChecklistItem label="Custom Product Created" checked={request.custom_product_created} />
                  <StaticChecklistItem label="Docs Uploaded" checked={request.docs_uploaded} />
                  <StaticChecklistItem label="Stripe Confirmed" checked={request.stripe_confirmed} />
                </>
              )}
            </div>
            {request.fulfillment_complete && (
              <div className="mt-2 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700">
                Fulfillment complete
              </div>
            )}
          </Section>

          {/* Documents */}
          {(request.quote_document_url || request.coi_document_url) ? (
            <Section title="Documents">
              <div className="space-y-2">
                {request.quote_document_url && (
                  <a
                    href={request.quote_document_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-[#ff5c00] hover:text-[#ea580c]"
                  >
                    <FileText className="h-4 w-4" />
                    Quote Document
                  </a>
                )}
                {request.coi_document_url && (
                  <a
                    href={request.coi_document_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-[#ff5c00] hover:text-[#ea580c]"
                  >
                    <FileText className="h-4 w-4" />
                    COI Document
                  </a>
                )}
              </div>
            </Section>
          ) : (
            <Section title="Documents">
              <p className="text-sm text-gray-400">No documents</p>
            </Section>
          )}

          {/* External Links */}
          {(request.client_contact_url || request.django_admin_url) ? (
            <Section title="External Links">
              <div className="space-y-2">
                {request.django_admin_url && (
                  <a
                    href={request.django_admin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-[#ff5c00] hover:text-[#ea580c]"
                  >
                    <ExternalLink className="h-4 w-4" />
                    Django Admin
                  </a>
                )}
                {request.client_contact_url && (
                  <a
                    href={request.client_contact_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-[#ff5c00] hover:text-[#ea580c]"
                  >
                    <ExternalLink className="h-4 w-4" />
                    HubSpot
                  </a>
                )}
              </div>
            </Section>
          ) : (
            <Section title="External Links">
              <p className="text-sm text-gray-400">No links</p>
            </Section>
          )}

          {/* Notes */}
          {request.notes && (
            <Section title="Notes">
              <p className="whitespace-pre-wrap text-sm text-gray-700">{request.notes}</p>
            </Section>
          )}

          {/* Decline Reason */}
          {request.decline_reason && (
            <Section title="Decline Reason">
              <p className="whitespace-pre-wrap text-sm text-gray-700">{request.decline_reason}</p>
            </Section>
          )}

          {/* Activity Timeline */}
          <Section title="Activity">
            <ActivityTimeline
              entries={auditLog.data?.entries ?? []}
              isLoading={auditLog.isLoading}
              maxEntries={20}
            />
          </Section>
        </div>
      </div>
    </div>
  )
}
