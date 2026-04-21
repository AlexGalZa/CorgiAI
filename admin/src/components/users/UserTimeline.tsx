import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Clock, FileText, Shield, AlertTriangle, DollarSign,
  LogIn, ShoppingCart, CheckCircle,
} from 'lucide-react'
import api from '@/lib/api'
import { formatRelativeTime, formatDate, formatCurrency } from '@/lib/formatters'
import { cn } from '@/lib/utils'
import type { AuditEntry, PaginatedResponse } from '@/types'
import type { QuoteListItem } from '@/hooks/useQuotes'
import type { PolicyListItem } from '@/hooks/usePolicies'

// ─── Types ───────────────────────────────────────────────────────────────────

interface UserTimelineProps {
  userId: string
  userEmail?: string
}

interface TimelineEntry {
  id: string
  type: 'login' | 'quote_created' | 'quote_purchased' | 'policy_bound' | 'claim_filed' | 'payment_made' | 'activity'
  title: string
  description?: string
  timestamp: string
  link?: string
}

// ─── Hooks ───────────────────────────────────────────────────────────────────

function useUserAuditLog(userId: string) {
  return useQuery<AuditEntry[]>({
    queryKey: ['user-timeline-audit', userId],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.set('user_id', userId)
      params.set('limit', '50')
      const { data } = await api.get(`/admin/audit-log?${params}`)
      const entries = data?.entries ?? data?.results ?? data ?? []
      return entries.map((e: Record<string, unknown>) => ({
        id: e.id as number,
        user_email: (e.actor ?? e.user_email ?? '') as string,
        user_name: (e.actor ?? e.user_name ?? '') as string,
        action: e.action as string,
        entity_type: (e.content_type ?? e.entity_type ?? '') as string,
        entity_id: Number(e.object_id ?? e.entity_id ?? 0),
        entity_name: (e.entity_name ?? '') as string,
        field_changed: (e.field_changed ?? '') as string,
        old_value: (e.old_value ?? '') as string,
        new_value: (e.new_value ?? '') as string,
        timestamp: (e.timestamp ?? e.created_at ?? '') as string,
      }))
    },
    enabled: !!userId,
  })
}

function useUserQuotes(email: string | undefined) {
  return useQuery<PaginatedResponse<QuoteListItem>>({
    queryKey: ['user-timeline-quotes', email],
    queryFn: async () => {
      const { data } = await api.get(`/admin/quotes?search=${encodeURIComponent(email!)}&page_size=50`)
      return data
    },
    enabled: !!email,
  })
}

function useUserPolicies(email: string | undefined) {
  return useQuery<PaginatedResponse<PolicyListItem>>({
    queryKey: ['user-timeline-policies', email],
    queryFn: async () => {
      const { data } = await api.get(`/admin/policies?search=${encodeURIComponent(email!)}&page_size=50`)
      return data
    },
    enabled: !!email,
  })
}

// ─── Type Config ─────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<string, {
  icon: React.ComponentType<{ className?: string }>
  color: string
  bgColor: string
}> = {
  login: { icon: LogIn, color: 'text-gray-500', bgColor: 'bg-gray-100' },
  quote_created: { icon: FileText, color: 'text-blue-500', bgColor: 'bg-blue-50' },
  quote_purchased: { icon: ShoppingCart, color: 'text-green-500', bgColor: 'bg-green-50' },
  policy_bound: { icon: Shield, color: 'text-emerald-500', bgColor: 'bg-emerald-50' },
  claim_filed: { icon: AlertTriangle, color: 'text-red-500', bgColor: 'bg-red-50' },
  payment_made: { icon: DollarSign, color: 'text-amber-500', bgColor: 'bg-amber-50' },
  activity: { icon: Clock, color: 'text-gray-400', bgColor: 'bg-gray-50' },
}

function getConfig(type: string) {
  return TYPE_CONFIG[type] ?? TYPE_CONFIG.activity
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function UserTimeline({ userId, userEmail }: UserTimelineProps) {
  const auditLog = useUserAuditLog(userId)
  const quotes = useUserQuotes(userEmail)
  const policies = useUserPolicies(userEmail)

  const isLoading = auditLog.isLoading || (userEmail && (quotes.isLoading || policies.isLoading))

  // Merge all sources into a single timeline
  const timeline = useMemo(() => {
    const entries: TimelineEntry[] = []

    // Add audit log entries
    for (const entry of auditLog.data ?? []) {
      let type: TimelineEntry['type'] = 'activity'
      const action = entry.action?.toLowerCase() ?? ''
      const entityType = entry.entity_type?.toLowerCase() ?? ''

      if (action.includes('login')) type = 'login'
      else if (action === 'created' && entityType.includes('quote')) type = 'quote_created'
      else if (action.includes('purchased') || action.includes('bound')) type = 'policy_bound'
      else if (action === 'created' && entityType.includes('claim')) type = 'claim_filed'
      else if (action.includes('payment')) type = 'payment_made'

      let title = `${entry.action?.replace(/_/g, ' ')} ${entry.entity_name || entry.entity_type || ''}`.trim()
      if (entry.field_changed) {
        title = `Updated ${entry.field_changed.replace(/_/g, ' ')}`
        if (entry.new_value) title += ` to "${entry.new_value}"`
      }

      let link: string | undefined
      if (entityType.includes('quote') && entry.entity_id) link = `/quotes/${entry.entity_id}`
      else if (entityType.includes('polic') && entry.entity_id) link = `/policies/${entry.entity_id}`
      else if (entityType.includes('claim') && entry.entity_id) link = `/claims/${entry.entity_id}`

      entries.push({
        id: `audit-${entry.id}`,
        type,
        title,
        description: entry.user_name || entry.user_email || undefined,
        timestamp: entry.timestamp,
        link,
      })
    }

    // Add quotes as timeline entries
    for (const q of quotes.data?.results ?? []) {
      entries.push({
        id: `quote-${q.id}`,
        type: q.status === 'purchased' ? 'quote_purchased' : 'quote_created',
        title: `Quote ${q.quote_number || `#${q.id}`} — ${q.status.replace(/_/g, ' ')}`,
        description: `${q.company_detail?.entity_legal_name ?? ''} · ${formatCurrency(q.quote_amount)}`,
        timestamp: q.created_at,
        link: `/quotes/${q.id}`,
      })
    }

    // Add policies as timeline entries
    for (const p of policies.data?.results ?? []) {
      entries.push({
        id: `policy-${p.id}`,
        type: 'policy_bound',
        title: `Policy ${p.policy_number || `#${p.id}`} — ${p.status.replace(/_/g, ' ')}`,
        description: `${p.coverage_type?.replace(/_/g, ' ') ?? ''} · ${formatCurrency(p.premium)}`,
        timestamp: p.created_at,
        link: `/policies/${p.id}`,
      })
    }

    // Deduplicate by rough matching (same type + same entity within same minute)
    const seen = new Set<string>()
    const deduped = entries.filter((e) => {
      const key = `${e.type}-${e.link ?? ''}-${e.timestamp?.slice(0, 16) ?? ''}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })

    // Sort by timestamp descending
    return deduped.sort((a, b) => {
      const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0
      const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0
      return tb - ta
    })
  }, [auditLog.data, quotes.data, policies.data])

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex gap-3 animate-pulse">
            <div className="h-8 w-8 rounded-lg bg-gray-100" />
            <div className="flex-1 space-y-1.5 py-1">
              <div className="h-3.5 w-3/4 rounded bg-gray-100" />
              <div className="h-3 w-1/2 rounded bg-gray-50" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Empty state
  if (timeline.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6">
        <div className="flex items-center gap-3 text-gray-500">
          <Clock className="h-5 w-5" />
          <div>
            <p className="text-sm font-medium text-gray-700">No activity yet</p>
            <p className="text-xs text-gray-500 mt-0.5">
              Activity for user <code className="text-xs bg-gray-200 px-1 rounded">{userId}</code> will appear here.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="relative">
      {timeline.map((entry, idx) => {
        const config = getConfig(entry.type)
        const Icon = config.icon
        const isLast = idx === timeline.length - 1

        const content = (
          <div className="flex gap-3">
            {/* Icon */}
            <div className="flex flex-col items-center">
              <div className={cn('rounded-lg p-1.5', config.bgColor)}>
                <Icon className={cn('h-3.5 w-3.5', config.color)} />
              </div>
              {!isLast && <div className="mt-1 w-0.5 flex-1 bg-gray-100" />}
            </div>

            {/* Content */}
            <div className={cn('flex-1 min-w-0 pb-4', isLast && 'pb-0')}>
              <p className="text-sm font-medium text-gray-900 leading-snug truncate">
                {entry.title}
              </p>
              {entry.description && (
                <p className="mt-0.5 text-xs text-gray-500 truncate">{entry.description}</p>
              )}
              <p className="mt-0.5 text-[10px] text-gray-400">
                {entry.timestamp ? formatRelativeTime(entry.timestamp) : '—'}
                {entry.timestamp && (
                  <span className="ml-2">{formatDate(entry.timestamp)}</span>
                )}
              </p>
            </div>
          </div>
        )

        if (entry.link) {
          return (
            <Link
              key={entry.id}
              to={entry.link}
              className="block rounded-lg transition-colors hover:bg-gray-50 -mx-2 px-2"
            >
              {content}
            </Link>
          )
        }

        return <div key={entry.id}>{content}</div>
      })}
    </div>
  )
}
