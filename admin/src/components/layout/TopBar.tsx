import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, Search, Loader2, ArrowRight, FileText, Shield, AlertTriangle, Menu, HelpCircle } from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { cn } from '@/lib/utils'
import api from '@/lib/api'
import StatusBadge from '@/components/ui/StatusBadge'
import ShortcutsHelp from '@/components/ui/ShortcutsHelp'
import StaffNotifications from '@/components/ui/StaffNotifications'

// ─── Role badge colors ──────────────────────────────────────────────────────

const roleBadgeColors: Record<string, string> = {
  admin: 'bg-red-50 text-red-700',
  broker: 'bg-emerald-50 text-emerald-700',
  finance: 'bg-amber-50 text-amber-700',
  account_executive: 'bg-sky-50 text-sky-700',
  customer_support: 'bg-purple-50 text-purple-700',
  account_manager: 'bg-violet-50 text-violet-700',
}

function formatRole(role: string): string {
  return role
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

// ─── Search result types ────────────────────────────────────────────────────

interface SearchResult {
  id: number
  label: string
  sublabel?: string
  status?: string
  statusVariant?: 'brokerage' | 'policy' | 'claim' | 'payment'
  path: string
}

interface SearchCategory {
  name: string
  icon: React.ComponentType<{ className?: string }>
  results: SearchResult[]
}

// ─── Inline Search Dropdown ─────────────────────────────────────────────────

function InlineSearch() {
  const [focused, setFocused] = useState(false)
  const [query, setQuery] = useState('')
  const [categories, setCategories] = useState<SearchCategory[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const [mobileExpanded, setMobileExpanded] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const navigate = useNavigate()

  const allResults = categories.flatMap((c) => c.results)
  const showDropdown = focused && query.trim().length > 0

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setFocused(false)
        setMobileExpanded(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Debounced search
  const performSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setCategories([])
      setIsSearching(false)
      return
    }

    setIsSearching(true)
    try {
      const [brokeredRes, quotesRes, policiesRes, claimsRes] = await Promise.allSettled([
        api.get(`/brokered-requests/?search=${encodeURIComponent(q)}&page_size=5`),
        api.get(`/quotes/?search=${encodeURIComponent(q)}&page_size=5`),
        api.get(`/policies/?search=${encodeURIComponent(q)}&page_size=5`),
        api.get(`/claims/?search=${encodeURIComponent(q)}&page_size=5`),
      ])

      const cats: SearchCategory[] = []

      if (brokeredRes.status === 'fulfilled') {
        const items = (brokeredRes.value.data.results ?? []).slice(0, 5)
        if (items.length > 0) {
          cats.push({
            name: 'Brokered Requests',
            icon: FileText,
            results: items.map((r: { id: number; company_name: string; status: string }) => ({
              id: r.id,
              label: r.company_name || `Request #${r.id}`,
              status: r.status,
              statusVariant: 'brokerage' as const,
              path: `/brokered-requests?highlight=${r.id}`,
            })),
          })
        }
      }

      if (quotesRes.status === 'fulfilled') {
        const items = (quotesRes.value.data.results ?? []).slice(0, 5)
        if (items.length > 0) {
          cats.push({
            name: 'Quotes',
            icon: FileText,
            results: items.map((r: { id: number; quote_number: string; status: string; company_detail?: { entity_legal_name: string } }) => ({
              id: r.id,
              label: r.quote_number || `Quote #${r.id}`,
              sublabel: r.company_detail?.entity_legal_name,
              status: r.status,
              path: `/quotes/${r.id}`,
            })),
          })
        }
      }

      if (policiesRes.status === 'fulfilled') {
        const items = (policiesRes.value.data.results ?? []).slice(0, 5)
        if (items.length > 0) {
          cats.push({
            name: 'Policies',
            icon: Shield,
            results: items.map((r: { id: number; policy_number: string; insured_legal_name: string; status: string }) => ({
              id: r.id,
              label: r.policy_number || `Policy #${r.id}`,
              sublabel: r.insured_legal_name,
              status: r.status,
              statusVariant: 'policy' as const,
              path: `/policies/${r.id}`,
            })),
          })
        }
      }

      if (claimsRes.status === 'fulfilled') {
        const items = (claimsRes.value.data.results ?? []).slice(0, 5)
        if (items.length > 0) {
          cats.push({
            name: 'Claims',
            icon: AlertTriangle,
            results: items.map((r: { id: number; claim_number: string; organization_name: string; status: string }) => ({
              id: r.id,
              label: r.claim_number || `Claim #${r.id}`,
              sublabel: r.organization_name,
              status: r.status,
              statusVariant: 'claim' as const,
              path: `/claims/${r.id}`,
            })),
          })
        }
      }

      setCategories(cats)
      setActiveIndex(0)
    } catch {
      // Silently fail
    } finally {
      setIsSearching(false)
    }
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!query.trim()) {
      setCategories([])
      setIsSearching(false)
      return
    }
    setIsSearching(true)
    debounceRef.current = setTimeout(() => performSearch(query), 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query, performSearch])

  const goToResult = (result: SearchResult) => {
    navigate(result.path)
    setFocused(false)
    setQuery('')
    setCategories([])
    setMobileExpanded(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setFocused(false)
      setMobileExpanded(false)
      inputRef.current?.blur()
      return
    }
    if (!showDropdown) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => Math.min(i + 1, allResults.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && allResults[activeIndex]) {
      e.preventDefault()
      goToResult(allResults[activeIndex])
    }
  }

  let flatIndex = -1

  return (
    <div ref={containerRef} className="relative">
      {/* Mobile: search icon button */}
      <button
        onClick={() => {
          setMobileExpanded(true)
          setTimeout(() => inputRef.current?.focus(), 100)
        }}
        className="sm:hidden rounded-lg p-1.5 text-gray-400 hover:text-gray-600"
      >
        <Search className="h-5 w-5" />
      </button>

      {/* Desktop: always visible input / Mobile: expanded input */}
      <div className={cn(
        'relative',
        // On mobile, only show when expanded (as a fixed overlay)
        mobileExpanded
          ? 'fixed inset-x-0 top-0 z-50 bg-white p-3 shadow-md sm:relative sm:inset-auto sm:p-0 sm:shadow-none'
          : 'hidden sm:block',
      )}>
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 sm:left-3" />
        <input
          ref={inputRef}
          type="text"
          placeholder="Search... (Ctrl+K)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onKeyDown={handleKeyDown}
          className={cn(
            'rounded-lg border border-gray-200 bg-gray-50 py-1.5 pl-9 pr-3 text-sm text-gray-700 transition-colors placeholder:text-gray-400 focus:border-[#ff5c00] focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#ff5c00]',
            mobileExpanded ? 'w-full' : 'w-72',
          )}
        />
        {isSearching && (
          <Loader2 className="absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 animate-spin text-gray-400" />
        )}
      </div>

      {/* Dropdown */}
      {showDropdown && (
        <div className={cn(
          'absolute top-full z-40 mt-1 w-96 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg',
          mobileExpanded ? 'left-3 sm:left-0' : 'left-0',
        )}>
          <div className="max-h-80 overflow-y-auto px-2 py-2 scrollbar-compact">
            {isSearching && categories.length === 0 ? (
              <div className="flex items-center justify-center gap-2 py-6">
                <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                <span className="text-sm text-gray-400">Searching...</span>
              </div>
            ) : categories.length === 0 && !isSearching ? (
              <p className="py-6 text-center text-sm text-gray-400">No results found</p>
            ) : (
              categories.map((cat) => (
                <div key={cat.name}>
                  <div className="mb-1 mt-2 flex items-center gap-1.5 px-2">
                    <cat.icon className="h-3 w-3 text-gray-400" />
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400">
                      {cat.name}
                    </p>
                  </div>
                  {cat.results.map((result) => {
                    flatIndex++
                    const idx = flatIndex
                    return (
                      <button
                        key={`${cat.name}-${result.id}`}
                        onClick={() => goToResult(result)}
                        onMouseEnter={() => setActiveIndex(idx)}
                        className={cn(
                          'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors',
                          idx === activeIndex
                            ? 'bg-gray-100 text-gray-900'
                            : 'text-gray-600 hover:bg-gray-50',
                        )}
                      >
                        <div className="min-w-0 flex-1">
                          <span className="font-medium">{result.label}</span>
                          {result.sublabel && (
                            <span className="ml-2 text-xs text-gray-400">{result.sublabel}</span>
                          )}
                        </div>
                        {result.status && (
                          <StatusBadge
                            status={result.status}
                            variant={result.statusVariant}
                            className="shrink-0"
                          />
                        )}
                        <ArrowRight className="h-3 w-3 shrink-0 text-gray-300" />
                      </button>
                    )
                  })}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── TopBar ─────────────────────────────────────────────────────────────────

export default function TopBar() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()
  const openMobileSidebar = useUIStore((s) => s.openMobileSidebar)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const badgeColor =
    roleBadgeColors[user?.role ?? ''] ?? 'bg-gray-100 text-gray-700'

  return (
    <header className="flex h-14 items-center justify-between gap-4 border-b border-gray-100 bg-white px-4 sm:px-6">
      <div className="flex items-center gap-3">
        {/* Hamburger menu - mobile only */}
        <button
          onClick={openMobileSidebar}
          className="lg:hidden rounded-lg p-1.5 text-gray-500 hover:bg-gray-50 hover:text-gray-700"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Global search */}
        <InlineSearch />
      </div>

      {/* User info */}
      <div className="flex items-center gap-3">
        {/* Staff Notifications */}
        <StaffNotifications />
        {/* Shortcuts help button */}
        <button
          onClick={() => setShortcutsOpen(true)}
          className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-600"
          title="Keyboard shortcuts"
          aria-label="Keyboard shortcuts"
        >
          <HelpCircle className="h-4 w-4" />
        </button>
        {/* Avatar circle */}
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-600">
          {user?.first_name?.[0] ?? ''}{user?.last_name?.[0] ?? ''}
        </div>
        <div className="hidden md:block">
          <p className="text-sm font-medium leading-none text-gray-900">
            {user?.full_name ?? 'User'}
          </p>
          <span
            className={cn(
              'mt-0.5 inline-block rounded px-1.5 py-px text-[10px] font-medium',
              badgeColor,
            )}
          >
            {user?.role ? formatRole(user.role) : 'Unknown'}
          </span>
        </div>
        {/* Role badge only on small screens (no full name) */}
        <span
          className={cn(
            'md:hidden inline-block rounded px-1.5 py-px text-[10px] font-medium',
            badgeColor,
          )}
        >
          {user?.role ? formatRole(user.role) : ''}
        </span>
        <button
          onClick={handleLogout}
          className="ml-1 rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-600"
          title="Sign out"
          aria-label="Sign out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>

      <ShortcutsHelp open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </header>
  )
}
