import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { X, Shield } from 'lucide-react'
import StatusBadge from '@/components/ui/StatusBadge'
import { formatCurrency, formatDate } from '@/lib/formatters'
import type { Payment } from '@/types'

interface PaymentDetailPanelProps {
  payment: Payment | null
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

export default function PaymentDetailPanel({ payment, onClose }: PaymentDetailPanelProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (payment) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [payment, onClose])

  if (!payment) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/20 animate-in fade-in duration-150" onClick={onClose} />

      {/* Panel */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md overflow-y-auto scrollbar-compact bg-white shadow-xl animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Payment Details</h2>
            <p className="text-xs text-gray-500">Invoice {payment.stripe_invoice_id || `#${payment.id}`}</p>
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
          {/* Amount + Status */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="mb-4 text-center">
              <p className="text-xs font-medium text-gray-500">Amount</p>
              <p className="mt-1 text-3xl font-bold text-gray-900">{formatCurrency(payment.amount)}</p>
              <div className="mt-2">
                <StatusBadge status={payment.status} variant="payment" />
              </div>
            </div>
          </div>

          {/* Details */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="divide-y divide-gray-100">
              <DetailRow label="Invoice ID" value={
                <span className="font-mono text-xs">{payment.stripe_invoice_id || '—'}</span>
              } />
              <DetailRow label="Status" value={<StatusBadge status={payment.status} variant="payment" />} />
              <DetailRow label="Amount" value={formatCurrency(payment.amount)} />
              <DetailRow label="Policy" value={
                <Link
                  to={`/policies/${payment.policy}`}
                  className="inline-flex items-center gap-1 text-sm font-medium text-[#ff5c00] hover:underline"
                  onClick={onClose}
                >
                  <Shield className="h-3.5 w-3.5" />
                  Policy #{payment.policy}
                </Link>
              } />
              <DetailRow label="Paid At" value={formatDate(payment.paid_at ?? '')} />
              <DetailRow label="Created" value={formatDate(payment.created_at)} />
              <DetailRow label="Last Updated" value={formatDate(payment.updated_at)} />
            </div>
          </div>

          {/* Stripe Info */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">Stripe Information</p>
            <div className="divide-y divide-gray-100">
              <DetailRow label="Stripe Invoice ID" value={
                <span className="font-mono text-xs">{payment.stripe_invoice_id || '—'}</span>
              } />
              <DetailRow label="Payment ID" value={
                <span className="font-mono text-xs">#{payment.id}</span>
              } />
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
