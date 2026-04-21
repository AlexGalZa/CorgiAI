import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Building2, FileText, Shield, AlertTriangle,
  ChevronDown, ChevronRight, X, PanelRightOpen, PanelRightClose,
  Users, MapPin, DollarSign, Hash,
} from 'lucide-react'
import { useQuotes } from '@/hooks/useQuotes'
import { usePolicies } from '@/hooks/usePolicies'
import { useClaims } from '@/hooks/useClaims'
import { formatCurrency, formatDate } from '@/lib/formatters'
import StatusBadge from '@/components/ui/StatusBadge'
import type { Quote } from '@/types'

// ─── Expandable Section ─────────────────────────────────────────────────────

function Section({
  icon: Icon,
  label,
  count,
  children,
  defaultOpen = false,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  count?: number
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 transition-colors hover:bg-gray-50"
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <Icon className="h-3.5 w-3.5 text-gray-400" />
        <span className="flex-1">{label}</span>
        {count !== undefined && (
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-semibold text-gray-500">
            {count}
          </span>
        )}
      </button>
      {open && <div className="px-4 pb-3">{children}</div>}
    </div>
  )
}

// ─── Info Row ────────────────────────────────────────────────────────────────

function InfoRow({ icon: Icon, label, value }: { icon: React.ComponentType<{ className?: string }>; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 py-1.5 text-xs">
      <Icon className="mt-0.5 h-3 w-3 shrink-0 text-gray-400" />
      <div className="min-w-0">
        <span className="text-gray-400">{label}: </span>
        <span className="font-medium text-gray-700">{value || '—'}</span>
      </div>
    </div>
  )
}

// ─── Main Component ─────────────────────────────────────────────────────────

interface CustomerContextSidebarProps {
  quote: Quote
}

export default function CustomerContextSidebar({ quote }: CustomerContextSidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  const companyName = quote.company_detail?.entity_legal_name || ''

  // Fetch other quotes from same company
  const otherQuotes = useQuotes({ search: companyName || undefined })
  const otherQuotesList = (otherQuotes.data?.results ?? []).filter((q) => q.id !== quote.id)

  // Fetch policies from same company
  const policies = usePolicies({ search: companyName || undefined })
  const policiesList = policies.data?.results ?? []

  // Fetch claims from same company
  const claims = useClaims({ search: companyName || undefined })
  const claimsList = claims.data?.results ?? []

  if (collapsed) {
    return (
      <div className="flex flex-col items-center rounded-xl border border-gray-200 bg-white py-4 shadow-sm">
        <button
          onClick={() => setCollapsed(false)}
          className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          title="Expand sidebar"
        >
          <PanelRightOpen className="h-4 w-4" />
        </button>
      </div>
    )
  }

  return (
    <div className="w-[300px] shrink-0 rounded-xl border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          Customer Context
        </h3>
        <button
          onClick={() => setCollapsed(true)}
          className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          title="Collapse sidebar"
        >
          <PanelRightClose className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Company Info */}
      <Section icon={Building2} label="Company Info" defaultOpen>
        <div className="space-y-0.5">
          <InfoRow
            icon={Building2}
            label="Name"
            value={quote.company_detail?.entity_legal_name}
          />
          <InfoRow
            icon={Hash}
            label="Company ID"
            value={<span className="font-mono text-[10px]">#{quote.company ?? ""}</span>}
          />
          {/* Additional fields from company_detail if available */}
          {!!(quote as unknown as Record<string, unknown>).company_detail &&
            typeof (quote as unknown as Record<string, unknown>).company_detail === 'object' && (
              <>
                {((quote.company_detail as Record<string, unknown>)?.entity_type) && (
                  <InfoRow
                    icon={FileText}
                    label="Type"
                    value={String((quote.company_detail as Record<string, unknown>).entity_type)}
                  />
                )}
                {((quote.company_detail as Record<string, unknown>)?.revenue) && (
                  <InfoRow
                    icon={DollarSign}
                    label="Revenue"
                    value={formatCurrency(String((quote.company_detail as Record<string, unknown>).revenue))}
                  />
                )}
                {((quote.company_detail as Record<string, unknown>)?.employee_count) && (
                  <InfoRow
                    icon={Users}
                    label="Employees"
                    value={String((quote.company_detail as Record<string, unknown>).employee_count)}
                  />
                )}
                {((quote.company_detail as Record<string, unknown>)?.state) && (
                  <InfoRow
                    icon={MapPin}
                    label="State"
                    value={String((quote.company_detail as Record<string, unknown>).state)}
                  />
                )}
              </>
            )}
        </div>
      </Section>

      {/* Other Quotes */}
      <Section
        icon={FileText}
        label="Other Quotes"
        count={otherQuotesList.length}
      >
        {otherQuotes.isLoading ? (
          <p className="text-xs text-gray-400">Loading…</p>
        ) : otherQuotesList.length === 0 ? (
          <p className="text-xs text-gray-400">No other quotes</p>
        ) : (
          <div className="space-y-2">
            {otherQuotesList.slice(0, 10).map((q) => (
              <Link
                key={q.id}
                to={`/quotes/${q.id}`}
                className="block rounded-lg border border-gray-100 p-2 transition-colors hover:border-[#ff5c00]/30 hover:bg-orange-50/30"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-700">
                    {q.quote_number || `Q-${q.id}`}
                  </span>
                  <StatusBadge status={q.status} />
                </div>
                <div className="mt-0.5 flex items-center gap-2 text-[10px] text-gray-400">
                  <span>{formatCurrency(q.quote_amount)}</span>
                  <span>·</span>
                  <span>{formatDate(q.created_at)}</span>
                </div>
              </Link>
            ))}
            {otherQuotesList.length > 10 && (
              <p className="text-[10px] text-gray-400">
                +{otherQuotesList.length - 10} more
              </p>
            )}
          </div>
        )}
      </Section>

      {/* Active Policies */}
      <Section
        icon={Shield}
        label="Policies"
        count={policiesList.length}
      >
        {policies.isLoading ? (
          <p className="text-xs text-gray-400">Loading…</p>
        ) : policiesList.length === 0 ? (
          <p className="text-xs text-gray-400">No policies found</p>
        ) : (
          <div className="space-y-2">
            {policiesList.slice(0, 10).map((p) => (
              <Link
                key={p.id}
                to={`/policies/${p.id}`}
                className="block rounded-lg border border-gray-100 p-2 transition-colors hover:border-[#ff5c00]/30 hover:bg-orange-50/30"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-700">
                    {p.policy_number || `P-${p.id}`}
                  </span>
                  <StatusBadge status={p.status} variant="policy" />
                </div>
                <div className="mt-0.5 flex items-center gap-2 text-[10px] text-gray-400">
                  <span>{formatCurrency(p.premium)}</span>
                  <span>·</span>
                  <span>{p.coverage_type?.replace(/_/g, ' ') || '—'}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Section>

      {/* Claims History */}
      <Section
        icon={AlertTriangle}
        label="Claims"
        count={claimsList.length}
      >
        {claims.isLoading ? (
          <p className="text-xs text-gray-400">Loading…</p>
        ) : claimsList.length === 0 ? (
          <p className="text-xs text-gray-400">No claims found</p>
        ) : (
          <div className="space-y-2">
            {claimsList.slice(0, 10).map((c) => (
              <Link
                key={c.id}
                to={`/claims/${c.id}`}
                className="block rounded-lg border border-gray-100 p-2 transition-colors hover:border-[#ff5c00]/30 hover:bg-orange-50/30"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-700">
                    {c.claim_number || `C-${c.id}`}
                  </span>
                  <StatusBadge status={c.status} variant="claim" />
                </div>
                <div className="mt-0.5 text-[10px] text-gray-400">
                  {formatDate(c.created_at)}
                </div>
              </Link>
            ))}
          </div>
        )}
      </Section>
    </div>
  )
}
