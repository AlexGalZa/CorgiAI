import { useEffect } from 'react'
import { X } from 'lucide-react'
import { formatDate } from '@/lib/formatters'
import type { CertificateListItem } from '@/hooks/useCertificates'

interface CertificateDetailPanelProps {
  certificate: CertificateListItem | null
  onClose: () => void
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between py-2.5 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="ml-4 text-right font-medium text-gray-900">{value ?? '—'}</span>
    </div>
  )
}

export default function CertificateDetailPanel({ certificate, onClose }: CertificateDetailPanelProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (certificate) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [certificate, onClose])

  if (!certificate) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/20 animate-in fade-in duration-150" onClick={onClose} />

      {/* Panel */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md overflow-y-auto scrollbar-compact bg-white shadow-xl animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Certificate Details</h2>
            <p className="text-xs text-gray-500">COI #{certificate.coi_number || certificate.id}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6 p-6">
          {/* COI Info */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">Certificate Information</p>
            <div className="divide-y divide-gray-100">
              <DetailRow label="COI Number" value={certificate.coi_number || '—'} />
              <DetailRow label="Custom COI Number" value={certificate.custom_coi_number || '—'} />
              <DetailRow label="Certificate ID" value={<span className="font-mono text-xs">#{certificate.id}</span>} />
            </div>
          </div>

          {/* Holder Info */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">Holder Information</p>
            <div className="divide-y divide-gray-100">
              <DetailRow label="Holder Name" value={certificate.holder_name || '—'} />
              <DetailRow label="City" value={certificate.holder_city || '—'} />
              <DetailRow label="State" value={certificate.holder_state || '—'} />
              <DetailRow
                label="Service Location"
                value={
                  certificate.holder_city && certificate.holder_state
                    ? `${certificate.holder_city}, ${certificate.holder_state}`
                    : certificate.holder_city || certificate.holder_state || '—'
                }
              />
            </div>
          </div>

          {/* Additional Info */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">Additional Details</p>
            <div className="divide-y divide-gray-100">
              <DetailRow
                label="Additional Insured"
                value={
                  certificate.is_additional_insured ? (
                    <span className="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-[#ff5c00]">
                      Yes
                    </span>
                  ) : (
                    <span className="text-xs text-gray-400">No</span>
                  )
                }
              />
              <DetailRow label="User ID" value={<span className="font-mono text-xs">#{certificate.user}</span>} />
              <DetailRow
                label="Organization"
                value={certificate.organization ? <span className="font-mono text-xs">#{certificate.organization}</span> : '—'}
              />
            </div>
          </div>

          {/* Dates */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">Dates</p>
            <div className="divide-y divide-gray-100">
              <DetailRow label="Created" value={formatDate(certificate.created_at)} />
              <DetailRow label="Last Updated" value={formatDate(certificate.updated_at)} />
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
