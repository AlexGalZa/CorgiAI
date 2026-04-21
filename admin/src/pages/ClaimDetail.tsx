import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  User,
  DollarSign,
  FileText,
  Shield,
  Download,
  Save,
  ChevronDown,
  Check,
  Folder,
  Paperclip,
  Clock,
} from 'lucide-react'
import { toast } from 'sonner'
import api from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/formatters'
import StatusBadge from '@/components/ui/StatusBadge'
import ActivityTimeline from '@/components/ui/ActivityTimeline'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import QueryError from '@/components/ui/QueryError'
import { SpinnerOverlay } from '@/components/ui/Spinner'
import Spinner from '@/components/ui/Spinner'
import DataTable, { type Column } from '@/components/ui/DataTable'
import { cn } from '@/lib/utils'
import { useAuditLog } from '@/hooks/useAuditLog'
import type { PaginatedResponse } from '@/types'

// ─── Types ──────────────────────────────────────────────────────────────────

interface ClaimDetail {
  id: number
  claim_number: string
  policy: number
  policy_number: string
  user: number
  organization_name: string
  first_name: string
  last_name: string
  email: string
  phone_number: string
  description: string
  admin_notes: string
  status: string
  loss_state: string
  paid_loss: string
  paid_lae: string
  case_reserve_loss: string
  case_reserve_lae: string
  total_incurred: string
  claim_report_date: string | null
  created_at: string
  updated_at: string
}

interface InternalDocument {
  id: number
  claim: number
  claim_number: string
  document_type: string
  filename: string
  status: string
  reviewed_by: string
  sent_date: string | null
  notes: string
  created_at: string
  updated_at: string
}

interface ClaimDocument {
  id: number
  claim: number
  filename: string
  file_type: string
  s3_url: string
  created_at: string
}

const CLAIM_STATUSES = ['filed', 'under_review', 'investigation', 'resolved', 'denied', 'closed']
const DOC_STATUSES = ['not_reviewed', 'reviewed', 'sent']

// ─── Hooks ──────────────────────────────────────────────────────────────────

function useClaim(id: string | undefined) {
  return useQuery<ClaimDetail>({
    queryKey: ['claim', id],
    queryFn: async () => {
      const { data } = await api.get(`/admin/claims/${id}`)
      return data
    },
    enabled: !!id,
  })
}

function useInternalDocuments(claimId: string | undefined) {
  return useQuery<PaginatedResponse<InternalDocument>>({
    queryKey: ['claim-internal-docs', claimId],
    queryFn: async () => {
      const { data } = await api.get(`/admin/internal-documents?claim=${claimId}`)
      return data
    },
    enabled: !!claimId,
  })
}

function useClaimDocuments(claimId: string | undefined) {
  return useQuery<PaginatedResponse<ClaimDocument>>({
    queryKey: ['claim-documents', claimId],
    queryFn: async () => {
      const { data } = await api.get(`/admin/claim-documents?claim=${claimId}`)
      return data
    },
    enabled: !!claimId,
  })
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between py-2.5 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="ml-4 text-right font-medium text-gray-900">{value ?? '—'}</span>
    </div>
  )
}

function FinancialCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className={cn('mt-1 text-lg font-bold', color)}>{formatCurrency(value)}</p>
    </div>
  )
}

function StatusDropdown({
  currentStatus,
  onStatusChange,
  isUpdating,
}: {
  currentStatus: string
  onStatusChange: (status: string) => void
  isUpdating: boolean
}) {
  const [open, setOpen] = useState(false)

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open])

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={isUpdating}
        className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
      >
        {isUpdating ? <Spinner size="sm" /> : <ChevronDown className="h-3.5 w-3.5" />}
        Edit Status
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-1 w-48 overflow-hidden rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
            {CLAIM_STATUSES.map((s) => (
              <button
                key={s}
                onClick={() => {
                  onStatusChange(s)
                  setOpen(false)
                }}
                className={cn(
                  'flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-gray-50',
                  s === currentStatus && 'bg-gray-50 font-medium',
                )}
              >
                {s === currentStatus && <Check className="h-3.5 w-3.5 text-[#ff5c00]" />}
                <span className={s === currentStatus ? 'text-[#ff5c00]' : 'text-gray-700'}>
                  {s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function InlineDocStatusEditor({
  doc,
  onUpdate,
}: {
  doc: InternalDocument
  onUpdate: (docId: number, status: string) => void
}) {
  const currentIdx = DOC_STATUSES.indexOf(doc.status.toLowerCase().replace(/\s+/g, '_'))
  const nextStatus = currentIdx < DOC_STATUSES.length - 1 ? DOC_STATUSES[currentIdx + 1] : null

  const statusColors: Record<string, string> = {
    not_reviewed: 'bg-red-100 text-red-800',
    reviewed: 'bg-yellow-100 text-yellow-800',
    sent: 'bg-green-100 text-green-800',
  }

  const normalized = doc.status.toLowerCase().replace(/\s+/g, '_')
  const colorClass = statusColors[normalized] ?? 'bg-gray-100 text-gray-800'

  return (
    <div className="flex items-center gap-2">
      <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', colorClass)}>
        {doc.status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
      </span>
      {nextStatus && (
        <button
          onClick={() => onUpdate(doc.id, nextStatus)}
          className="rounded border border-gray-200 px-2 py-0.5 text-[10px] font-medium text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-700"
        >
          Mark {nextStatus.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
        </button>
      )}
    </div>
  )
}

function SectionHeader({ icon: Icon, label }: { icon: React.ComponentType<{ className?: string }>; label: string }) {
  return (
    <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-400">
      <Icon className="h-3.5 w-3.5" />
      {label}
    </div>
  )
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function ClaimDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const claim = useClaim(id)
  const internalDocs = useInternalDocuments(id)
  const claimDocs = useClaimDocuments(id)

  const [adminNotes, setAdminNotes] = useState<string | null>(null)
  const [notesSaving, setNotesSaving] = useState(false)

  // Status mutation
  const statusMutation = useMutation({
    mutationFn: async (newStatus: string) => {
      await api.patch(`/admin/claims/${id}`, { status: newStatus })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claim', id] })
      toast.success('Claim status updated')
    },
    onError: () => {
      toast.error('Failed to update claim status')
    },
  })

  // Admin notes save
  const saveAdminNotes = async () => {
    setNotesSaving(true)
    try {
      await api.patch(`/admin/claims/${id}`, { admin_notes: adminNotes })
      queryClient.invalidateQueries({ queryKey: ['claim', id] })
      toast.success('Notes saved')
    } catch {
      toast.error('Failed to save notes')
    } finally {
      setNotesSaving(false)
    }
  }

  // Doc status mutation
  const docStatusMutation = useMutation({
    mutationFn: async ({ docId, status }: { docId: number; status: string }) => {
      await api.patch(`/admin/internal-documents/${docId}`, { status })
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['claim-internal-docs', id] })
      toast.success(`Document status changed to ${variables.status.replace(/_/g, ' ')}`)
    },
    onError: () => {
      toast.error('Failed to update document status')
    },
  })

  if (claim.isLoading) return <SpinnerOverlay height="h-96" />
  if (claim.isError) return <QueryError message="Failed to load claim details" onRetry={claim.refetch} />

  const c = claim.data
  if (!c) return <div className="py-16 text-center text-sm text-gray-500">Claim not found</div>

  const notesValue = adminNotes ?? c.admin_notes ?? ''

  // Internal doc columns with inline editor
  const internalDocCols: Column<InternalDocument>[] = [
    {
      key: 'document_type',
      header: 'Type',
      render: (r) =>
        r.document_type
          ? r.document_type.replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase())
          : '—',
    },
    { key: 'filename', header: 'Filename', render: (r) => r.filename || '—' },
    {
      key: 'status',
      header: 'Status',
      render: (r) => (
        <InlineDocStatusEditor
          doc={r}
          onUpdate={(docId, status) => docStatusMutation.mutate({ docId, status })}
        />
      ),
    },
    { key: 'reviewed_by', header: 'Reviewed By', render: (r) => r.reviewed_by || '—' },
    { key: 'sent_date', header: 'Sent Date', render: (r) => formatDate(r.sent_date ?? '') },
    { key: 'created_at', header: 'Generated', render: (r) => formatDate(r.created_at) },
  ]

  // Claim doc columns
  const claimDocCols: Column<ClaimDocument>[] = [
    { key: 'filename', header: 'Filename', render: (r) => <span className="font-medium">{r.filename}</span> },
    {
      key: 'file_type',
      header: 'File Type',
      render: (r) => (
        <span className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
          {r.file_type || '—'}
        </span>
      ),
    },
    { key: 'created_at', header: 'Uploaded', render: (r) => formatDate(r.created_at) },
    {
      key: 's3_url',
      header: 'Download',
      render: (r) =>
        r.s3_url ? (
          <a
            href={r.s3_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-[#ff5c00] hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            <Download className="h-3.5 w-3.5" />
            Download
          </a>
        ) : (
          <span className="text-gray-400">—</span>
        ),
    },
  ]

  const totalIncurred = parseFloat(c.total_incurred) || 0

  return (
    <div className="space-y-6">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: 'Claims', href: '/claims' },
          { label: c.claim_number || `Claim #${c.id}` },
        ]}
      />

      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/claims')}
          className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          aria-label="Go back"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-gray-900">
              {c.claim_number || `Claim #${c.id}`}
            </h1>
            <StatusBadge status={c.status} variant="claim" />
          </div>
          <p className="text-sm text-gray-500">{c.organization_name}</p>
        </div>
        <div className="flex items-center gap-4">
          <StatusDropdown
            currentStatus={c.status}
            onStatusChange={(s) => statusMutation.mutate(s)}
            isUpdating={statusMutation.isPending}
          />
          <div className="text-right">
            <p className="text-xs text-gray-500">Total Incurred</p>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalIncurred)}</p>
          </div>
        </div>
      </div>

      {/* Claimant Info + Description */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <SectionHeader icon={User} label="Claimant Information" />
          <div className="divide-y divide-gray-100">
            <DetailRow label="First Name" value={c.first_name} />
            <DetailRow label="Last Name" value={c.last_name} />
            <DetailRow label="Email" value={c.email} />
            <DetailRow label="Phone" value={c.phone_number || '—'} />
            <DetailRow label="Organization" value={c.organization_name} />
            <DetailRow label="Loss State" value={c.loss_state} />
            <DetailRow label="Report Date" value={formatDate(c.claim_report_date ?? '')} />
          </div>
        </div>

        <div className="space-y-5">
          {/* Description */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <SectionHeader icon={FileText} label="Description" />
            <p className="whitespace-pre-wrap text-sm text-gray-700">
              {c.description || 'No description provided.'}
            </p>
          </div>

          {/* Admin Notes */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <SectionHeader icon={FileText} label="Admin Notes" />
            <textarea
              value={notesValue}
              onChange={(e) => setAdminNotes(e.target.value)}
              rows={4}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
              placeholder="Add internal notes about this claim..."
            />
            <div className="mt-2 flex items-center gap-2">
              <button
                onClick={saveAdminNotes}
                disabled={notesSaving || adminNotes === null}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[#ff5c00] px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-[#ea580c] disabled:opacity-50"
              >
                {notesSaving ? <Spinner size="sm" /> : <Save className="h-3.5 w-3.5" />}
                Save Notes
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Financial Summary */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
          <DollarSign className="h-4 w-4 text-gray-400" />
          Financial Summary
        </h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <FinancialCard label="Paid Loss" value={c.paid_loss} color="text-gray-900" />
          <FinancialCard label="Paid LAE" value={c.paid_lae} color="text-gray-900" />
          <FinancialCard label="Case Reserve (Loss)" value={c.case_reserve_loss} color="text-amber-700" />
          <FinancialCard label="Case Reserve (LAE)" value={c.case_reserve_lae} color="text-amber-700" />
          <FinancialCard label="Total Incurred" value={c.total_incurred} color="text-[#ff5c00]" />
        </div>
      </div>

      {/* Linked Policy */}
      {c.policy && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <SectionHeader icon={Shield} label="Linked Policy" />
          <Link
            to={`/policies/${c.policy}`}
            className="inline-flex items-center gap-2 text-sm font-medium text-[#ff5c00] hover:underline"
          >
            <Shield className="h-4 w-4" />
            {c.policy_number || `Policy #${c.policy}`}
          </Link>
        </div>
      )}

      {/* Internal Documents */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
          <Folder className="h-4 w-4 text-gray-400" />
          Internal Documents
          {internalDocs.data && (
            <span className="text-xs font-normal text-gray-400">
              ({internalDocs.data.results.length})
            </span>
          )}
        </h2>
        <DataTable
          columns={internalDocCols}
          data={internalDocs.data?.results ?? []}
          isLoading={internalDocs.isLoading}
          emptyMessage="No internal documents"
        />
      </div>

      {/* Claim Documents */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
          <Paperclip className="h-4 w-4 text-gray-400" />
          Claim Documents
          {claimDocs.data && (
            <span className="text-xs font-normal text-gray-400">
              ({claimDocs.data.results.length})
            </span>
          )}
        </h2>
        <DataTable
          columns={claimDocCols}
          data={claimDocs.data?.results ?? []}
          isLoading={claimDocs.isLoading}
          emptyMessage="No claim documents uploaded"
        />
      </div>

      {/* Activity Timeline */}
      <ClaimActivitySection claimId={c.id} />

      {/* Timestamps */}
      <div className="flex gap-6 text-xs text-gray-400">
        <span>Created {formatDate(c.created_at)}</span>
        <span>Updated {formatDate(c.updated_at)}</span>
      </div>
    </div>
  )
}

// ─── Activity Section ────────────────────────────────────────────────────────

function ClaimActivitySection({ claimId }: { claimId: number }) {
  const auditLog = useAuditLog('claim', claimId)

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
        <Clock className="h-4 w-4 text-gray-400" />
        Activity
      </h2>
      <ActivityTimeline
        entries={auditLog.data?.entries ?? []}
        isLoading={auditLog.isLoading}
        maxEntries={20}
      />
    </div>
  )
}
