import type { AuditEntry } from '@/types'
import { formatRelativeTime } from '@/lib/formatters'
import { cn } from '@/lib/utils'

// ─── Types ───────────────────────────────────────────────────────────────────

interface ActivityTimelineProps {
  entries: AuditEntry[]
  isLoading?: boolean
  maxEntries?: number
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const ACTION_COLORS: Record<string, string> = {
  created: 'bg-emerald-500',
  updated: 'bg-blue-500',
  status_changed: 'bg-orange-500',
  deleted: 'bg-red-500',
}

function getActionColor(action: string): string {
  return ACTION_COLORS[action] ?? 'bg-gray-400'
}

function formatFieldName(field: string): string {
  if (!field) return ''
  return field.replace(/_/g, ' ')
}

function formatEntryText(entry: AuditEntry): string {
  const name = entry.user_name || entry.user_email || 'System'

  if (entry.action === 'created') {
    return `${name} created ${entry.entity_name || 'this record'}`
  }

  if (entry.action === 'deleted') {
    return `${name} deleted ${entry.entity_name || 'this record'}`
  }

  if (entry.action === 'status_changed' && entry.field_changed === 'status') {
    const from = entry.old_value ? ` from ${entry.old_value.replace(/_/g, ' ')}` : ''
    const to = entry.new_value ? ` to ${entry.new_value.replace(/_/g, ' ')}` : ''
    return `${name} changed status${from}${to}`
  }

  if (entry.field_changed) {
    const field = formatFieldName(entry.field_changed)
    if (entry.old_value && entry.new_value) {
      return `${name} changed ${field} from "${entry.old_value}" to "${entry.new_value}"`
    }
    if (entry.new_value) {
      return `${name} set ${field} to "${entry.new_value}"`
    }
    return `${name} updated ${field}`
  }

  return `${name} ${entry.action.replace(/_/g, ' ')} ${entry.entity_name || ''}`
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

function SkeletonEntry() {
  return (
    <div className="flex gap-3 animate-pulse">
      <div className="flex flex-col items-center">
        <div className="h-2.5 w-2.5 rounded-full bg-gray-200" />
        <div className="mt-1 h-full w-0.5 bg-gray-100" />
      </div>
      <div className="flex-1 pb-4">
        <div className="h-3.5 w-3/4 rounded bg-gray-200" />
        <div className="mt-1.5 h-3 w-1/4 rounded bg-gray-100" />
      </div>
    </div>
  )
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function ActivityTimeline({ entries, isLoading, maxEntries }: ActivityTimelineProps) {
  if (isLoading) {
    return (
      <div className="space-y-0">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonEntry key={i} />
        ))}
      </div>
    )
  }

  if (!entries || entries.length === 0) {
    return <p className="text-sm text-gray-400">No activity yet</p>
  }

  const displayed = maxEntries ? entries.slice(0, maxEntries) : entries

  return (
    <div className="relative">
      {displayed.map((entry, idx) => {
        const isLast = idx === displayed.length - 1

        return (
          <div key={entry.id} className="flex gap-3">
            {/* Timeline dot + line */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'mt-1 h-2.5 w-2.5 shrink-0 rounded-full',
                  getActionColor(entry.action),
                )}
              />
              {!isLast && (
                <div className="mt-0.5 w-0.5 flex-1 bg-gray-200" />
              )}
            </div>

            {/* Content */}
            <div className={cn('flex-1 pb-4', isLast && 'pb-0')}>
              <p className="text-sm text-gray-700 leading-snug">
                {formatEntryText(entry)}
              </p>
              <p className="mt-0.5 text-xs text-gray-400">
                {formatRelativeTime(entry.timestamp)}
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
