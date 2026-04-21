import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  LayoutDashboard,
  FileText,
  Shield,
  AlertTriangle,
  CreditCard,
  Users,
  Building2,
  BarChart3,
  UserCircle,
  Briefcase,
  FolderOpen,
  ArrowRight,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import api from '@/lib/api'
import StatusBadge from '@/components/ui/StatusBadge'
import { useAuthStore } from '@/stores/auth'

// ─── Types ──────────────────────────────────────────────────────────────────

interface CommandItem {
  id: string
  label: string
  sublabel?: string
  description?: string
  icon: React.ComponentType<{ className?: string }>
  action: () => void
  section: string
  keywords?: string
  status?: string
  statusVariant?: 'brokerage' | 'policy' | 'claim' | 'payment'
}

// ─── Component ──────────────────────────────────────────────────────────────

// ─── Role-based nav visibility ──────────────────────────────────────────────

/** Nav command IDs that each role should NOT see. Unlisted roles see everything. */
const HIDDEN_NAV_BY_ROLE: Record<string, Set<string>> = {
  bdr: new Set(['producers', 'orgs', 'users']),
  finance: new Set(['producers']),
  broker: new Set(['users', 'orgs', 'producers']),
}

function filterNavByRole(commands: CommandItem[], role: string): CommandItem[] {
  const hidden = HIDDEN_NAV_BY_ROLE[role]
  if (!hidden) return commands
  return commands.filter((c) => !hidden.has(c.id))
}

// ─── Component ──────────────────────────────────────────────────────────────

export default function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const [apiResults, setApiResults] = useState<CommandItem[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const navigate = useNavigate()
  const userRole = useAuthStore((s) => s.user?.role ?? '')

  const go = useCallback(
    (path: string) => {
      navigate(path)
      setOpen(false)
    },
    [navigate],
  )

  // Static navigation commands
  const navCommands: CommandItem[] = [
    { id: 'dash', label: 'Dashboard', icon: LayoutDashboard, action: () => go('/dashboard'), section: 'Navigate', keywords: 'home overview' },
    { id: 'bqr', label: 'Brokered Requests', icon: FileText, action: () => go('/brokered-requests'), section: 'Navigate', keywords: 'brokerage pipeline quotes' },
    { id: 'quotes', label: 'Quotes', icon: FileText, action: () => go('/quotes'), section: 'Navigate', keywords: 'quote applications' },
    { id: 'policies', label: 'Policies', icon: Shield, action: () => go('/policies'), section: 'Navigate', keywords: 'policy active coverage' },
    { id: 'claims', label: 'Claims', icon: AlertTriangle, action: () => go('/claims'), section: 'Navigate', keywords: 'claim loss incurred' },
    { id: 'payments', label: 'Payments', icon: CreditCard, action: () => go('/payments'), section: 'Navigate', keywords: 'payment invoice stripe' },
    { id: 'certs', label: 'Certificates', icon: FolderOpen, action: () => go('/certificates'), section: 'Navigate', keywords: 'coi certificate holder' },
    { id: 'users', label: 'Users', icon: Users, action: () => go('/users'), section: 'Navigate', keywords: 'user accounts people' },
    { id: 'orgs', label: 'Organizations', icon: Building2, action: () => go('/organizations'), section: 'Navigate', keywords: 'organization company team' },
    { id: 'producers', label: 'Producers', icon: Briefcase, action: () => go('/producers'), section: 'Navigate', keywords: 'producer broker agent' },
    { id: 'reports', label: 'Reports', icon: BarChart3, action: () => go('/reports'), section: 'Navigate', keywords: 'analytics charts' },
    { id: 'profile', label: 'Profile', icon: UserCircle, action: () => go('/profile'), section: 'Navigate', keywords: 'settings account' },
  ]

  // Filter static commands — first by role visibility, then by query match
  const roleFilteredNav = filterNavByRole(navCommands, userRole)
  const filteredNav = query.trim()
    ? roleFilteredNav.filter((c) => {
        const q = query.toLowerCase()
        return (
          c.label.toLowerCase().includes(q) ||
          c.description?.toLowerCase().includes(q) ||
          c.keywords?.toLowerCase().includes(q)
        )
      })
    : roleFilteredNav

  // All items: static nav + API results
  const allItems = [...filteredNav, ...apiResults]

  // Group by section
  const sections = new Map<string, CommandItem[]>()
  for (const item of allItems) {
    const arr = sections.get(item.section) ?? []
    arr.push(item)
    sections.set(item.section, arr)
  }

  // API search
  const performApiSearch = useCallback(
    async (q: string) => {
      if (!q.trim() || q.trim().length < 2) {
        setApiResults([])
        setIsSearching(false)
        return
      }

      setIsSearching(true)
      try {
        const [brokeredRes, quotesRes, policiesRes, claimsRes] = await Promise.allSettled([
          api.get(`/admin/brokered-requests?search=${encodeURIComponent(q)}&page_size=5`),
          api.get(`/admin/quotes?search=${encodeURIComponent(q)}&page_size=5`),
          api.get(`/admin/policies?search=${encodeURIComponent(q)}&page_size=5`),
          api.get(`/admin/claims?search=${encodeURIComponent(q)}&page_size=5`),
        ])

        const results: CommandItem[] = []

        if (brokeredRes.status === 'fulfilled') {
          const items = (brokeredRes.value.data.results ?? []).slice(0, 5)
          for (const r of items) {
            results.push({
              id: `br-${r.id}`,
              label: r.company_name || `Request #${r.id}`,
              icon: FileText,
              action: () => go(`/brokered-requests?highlight=${r.id}`),
              section: 'Brokered Requests',
              status: r.status,
              statusVariant: 'brokerage',
            })
          }
        }

        if (quotesRes.status === 'fulfilled') {
          const items = (quotesRes.value.data.results ?? []).slice(0, 5)
          for (const r of items) {
            results.push({
              id: `q-${r.id}`,
              label: r.quote_number || `Quote #${r.id}`,
              sublabel: r.company_detail?.entity_legal_name,
              icon: FileText,
              action: () => go(`/quotes/${r.id}`),
              section: 'Quotes',
              status: r.status,
            })
          }
        }

        if (policiesRes.status === 'fulfilled') {
          const items = (policiesRes.value.data.results ?? []).slice(0, 5)
          for (const r of items) {
            results.push({
              id: `p-${r.id}`,
              label: r.policy_number || `Policy #${r.id}`,
              sublabel: r.insured_legal_name,
              icon: Shield,
              action: () => go(`/policies/${r.id}`),
              section: 'Policies',
              status: r.status,
              statusVariant: 'policy',
            })
          }
        }

        if (claimsRes.status === 'fulfilled') {
          const items = (claimsRes.value.data.results ?? []).slice(0, 5)
          for (const r of items) {
            results.push({
              id: `c-${r.id}`,
              label: r.claim_number || `Claim #${r.id}`,
              sublabel: r.organization_name,
              icon: AlertTriangle,
              action: () => go(`/claims/${r.id}`),
              section: 'Claims',
              status: r.status,
              statusVariant: 'claim',
            })
          }
        }

        setApiResults(results)
      } catch {
        // Silently fail
      } finally {
        setIsSearching(false)
      }
    },
    [go],
  )

  // Debounced API search on query change
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!query.trim() || query.trim().length < 2) {
      setApiResults([])
      setIsSearching(false)
      return
    }
    setIsSearching(true)
    debounceRef.current = setTimeout(() => performApiSearch(query), 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query, performApiSearch])

  // Keyboard handler
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((o) => !o)
        setQuery('')
        setActiveIndex(0)
        setApiResults([])
      }
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  // Focus input when opened
  useEffect(() => {
    if (open) {
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [open])

  // Arrow keys + Enter
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => Math.min(i + 1, allItems.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && allItems[activeIndex]) {
      allItems[activeIndex].action()
    }
  }

  // Scroll active item into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-index="${activeIndex}"]`)
    el?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  if (!open) return null

  let flatIndex = -1

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[20vh]">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />

      {/* Dialog */}
      <div className="relative w-full max-w-lg overflow-hidden rounded-xl border border-gray-200 bg-white shadow-2xl">
        {/* Search input */}
        <div className="flex items-center gap-3 border-b border-gray-100 px-4 py-3">
          <Search className="h-4 w-4 shrink-0 text-gray-400" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command or search..."
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActiveIndex(0) }}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none"
          />
          {isSearching && <Loader2 className="h-4 w-4 animate-spin text-gray-400" />}
          <kbd className="hidden rounded border border-gray-200 px-1.5 py-0.5 text-[10px] font-medium text-gray-400 sm:inline-block">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-80 overflow-y-auto px-2 py-2 scrollbar-compact">
          {allItems.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">
              {isSearching ? 'Searching...' : 'No results found'}
            </p>
          ) : (
            Array.from(sections.entries()).map(([section, items]) => (
              <div key={section}>
                <p className="mb-1 mt-2 px-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
                  {section}
                </p>
                {items.map((item) => {
                  flatIndex++
                  const idx = flatIndex
                  return (
                    <button
                      key={item.id}
                      data-index={idx}
                      onClick={item.action}
                      onMouseEnter={() => setActiveIndex(idx)}
                      className={cn(
                        'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors',
                        idx === activeIndex
                          ? 'bg-gray-100 text-gray-900'
                          : 'text-gray-600 hover:bg-gray-50',
                      )}
                    >
                      <item.icon className="h-4 w-4 shrink-0 text-gray-400" />
                      <div className="min-w-0 flex-1">
                        <span className="font-medium">{item.label}</span>
                        {item.sublabel && (
                          <span className="ml-2 text-xs text-gray-400">{item.sublabel}</span>
                        )}
                      </div>
                      {item.status && (
                        <StatusBadge
                          status={item.status}
                          variant={item.statusVariant}
                          className="shrink-0"
                        />
                      )}
                      <ArrowRight className="h-3.5 w-3.5 shrink-0 text-gray-300" />
                    </button>
                  )
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer hint */}
        <div className="flex items-center gap-4 border-t border-gray-100 px-4 py-2 text-[10px] text-gray-400">
          <span className="flex items-center gap-1">
            <kbd className="rounded border border-gray-200 px-1 py-px font-medium">↑↓</kbd> Navigate
          </span>
          <span className="flex items-center gap-1">
            <kbd className="rounded border border-gray-200 px-1 py-px font-medium">↵</kbd> Open
          </span>
          <span className="flex items-center gap-1">
            <kbd className="rounded border border-gray-200 px-1 py-px font-medium">Esc</kbd> Close
          </span>
        </div>
      </div>
    </div>
  )
}
