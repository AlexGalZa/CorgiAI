import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bell, AlertOctagon, Clock, Shield, FileText,
  ChevronRight, X,
} from 'lucide-react'
import api from '@/lib/api'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/lib/formatters'
import { useAuthStore } from '@/stores/auth'

// ─── Types ───────────────────────────────────────────────────────────────────

interface ActionItem {
  type: 'blocker' | 'pending' | 'expiring' | string
  title: string
  description?: string
  entity_type?: string
  entity_id?: number
  created_at?: string
  timestamp?: string
}

interface ActionItemsResponse {
  items: ActionItem[]
  total: number
}

// ─── Hook ────────────────────────────────────────────────────────────────────

function useActionItems() {
  return useQuery<ActionItemsResponse>({
    queryKey: ['staff-notifications'],
    queryFn: async () => {
      const { data } = await api.get('/admin/analytics/action-items')
      const items = data?.items ?? []
      return { items, total: data?.total ?? items.length }
    },
    refetchInterval: 60_000, // Poll every 60s
  })
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<string, {
  icon: React.ComponentType<{ className?: string }>
  color: string
  bgColor: string
  defaultPath: string
}> = {
  blocker: {
    icon: AlertOctagon,
    color: 'text-red-500',
    bgColor: 'bg-red-50',
    defaultPath: '/brokered-requests',
  },
  pending: {
    icon: Clock,
    color: 'text-amber-500',
    bgColor: 'bg-amber-50',
    defaultPath: '/quotes',
  },
  expiring: {
    icon: Shield,
    color: 'text-orange-500',
    bgColor: 'bg-orange-50',
    defaultPath: '/policies',
  },
}

function getItemConfig(item: ActionItem) {
  return TYPE_CONFIG[item.type] ?? {
    icon: FileText,
    color: 'text-gray-500',
    bgColor: 'bg-gray-50',
    defaultPath: '/',
  }
}

function getItemPath(item: ActionItem): string {
  const config = getItemConfig(item)

  // Try to derive path from entity_type and entity_id
  if (item.entity_type && item.entity_id) {
    const type = item.entity_type.toLowerCase()
    if (type.includes('quote')) return `/quotes/${item.entity_id}`
    if (type.includes('policy') || type.includes('policies')) return `/policies/${item.entity_id}`
    if (type.includes('claim')) return `/claims/${item.entity_id}`
    if (type.includes('brokered') || type.includes('request')) return `/brokered-requests?highlight=${item.entity_id}`
  }

  return config.defaultPath
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function StaffNotifications() {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const { data, isLoading } = useActionItems()
  const role = useAuthStore((s) => s.user?.role ?? '')

  // Filter notifications by role — finance shouldn't see quote reviews, BDR shouldn't see policy/payment items
  const allItems = data?.items ?? []
  const items = allItems.filter((item) => {
    if (role === 'finance') {
      // Finance only sees payment-related and expiring policy items
      return item.type === 'expiring' || item.title.toLowerCase().includes('payment')
    }
    if (role === 'bdr') {
      // BDR only sees quote-related items
      return item.title.toLowerCase().includes('quote') || item.title.toLowerCase().includes('demo')
    }
    // Admin, AE, AE+UW see everything
    return true
  })
  const unreadCount = items.length

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleItemClick = (item: ActionItem) => {
    const path = getItemPath(item)
    navigate(path)
    setOpen(false)
  }

  return (
    <div ref={containerRef} className="relative">
      {/* Bell Button */}
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          'relative rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-600',
          open && 'bg-gray-50 text-gray-600',
        )}
        title="Notifications"
        aria-label="Notifications"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-96 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <span className="rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-semibold text-red-600">
                  {unreadCount} items
                </span>
              )}
              <button
                onClick={() => setOpen(false)}
                className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Items */}
          <div className="max-h-80 overflow-y-auto scrollbar-compact">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-[#ff5c00]" />
              </div>
            ) : items.length === 0 ? (
              <div className="py-8 text-center">
                <Bell className="mx-auto h-8 w-8 text-gray-200" />
                <p className="mt-2 text-sm text-gray-400">All caught up!</p>
              </div>
            ) : (
              items.map((item, idx) => {
                const config = getItemConfig(item)
                const ItemIcon = config.icon
                const time = item.timestamp || item.created_at

                return (
                  <button
                    key={idx}
                    onClick={() => handleItemClick(item)}
                    className="flex w-full items-start gap-3 border-b border-gray-50 px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-gray-50"
                  >
                    <div className={cn('mt-0.5 rounded-lg p-1.5', config.bgColor)}>
                      <ItemIcon className={cn('h-3.5 w-3.5', config.color)} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {item.title || `${item.type} notification`}
                      </p>
                      {item.description && (
                        <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">
                          {item.description}
                        </p>
                      )}
                      {time && (
                        <p className="mt-1 text-[10px] text-gray-400">
                          {formatRelativeTime(time)}
                        </p>
                      )}
                    </div>
                    <ChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-gray-300" />
                  </button>
                )
              })
            )}
          </div>

          {/* Footer */}
          {items.length > 0 && (
            <div className="border-t border-gray-100 px-4 py-2">
              <button
                onClick={() => { navigate('/'); setOpen(false) }}
                className="w-full rounded-lg py-1.5 text-center text-xs font-medium text-[#ff5c00] transition-colors hover:bg-orange-50"
              >
                View Dashboard
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
