import { useCallback, useEffect, useRef, useState } from 'react'
import { Search, X } from 'lucide-react'
import Select from '@/components/ui/Select'
import { useUsers } from '@/hooks/useUsers'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface RequestFiltersState {
  status: string
  carrier: string
  blocker: string
  search: string
  created_after: string
  created_before: string
  requester: string
}

interface RequestFiltersProps {
  filters: RequestFiltersState
  onChange: (filters: RequestFiltersState) => void
}

// ─── Constants ───────────────────────────────────────────────────────────────

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'received', label: 'Received' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'otm', label: 'OTM' },
  { value: 'quoted', label: 'Quoted' },
  { value: 'on_hold', label: 'On Hold' },
  { value: 'denied', label: 'Denied' },
  { value: 'recalled', label: 'Recalled' },
  { value: 'blocked', label: 'Blocked' },
  { value: 'stalled', label: 'Stalled' },
  { value: 'bound', label: 'Bound' },
  { value: 'cancelled', label: 'Cancelled' },
]

const CARRIER_OPTIONS = [
  { value: '', label: 'All Carriers' },
  { value: 'coalition', label: 'Coalition' },
  { value: 'cowbell', label: 'Cowbell' },
  { value: 'cfc', label: 'CFC' },
  { value: 'corvus', label: 'Corvus' },
  { value: 'attune', label: 'Attune' },
  { value: 'coterie', label: 'Coterie' },
  { value: 'hiscox', label: 'Hiscox' },
  { value: 'next', label: 'Next' },
  { value: 'pie', label: 'Pie' },
  { value: 'other', label: 'Other' },
]

const BLOCKER_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'has_blocker', label: 'Has Blocker' },
  { value: 'no_blocker', label: 'No Blocker' },
  { value: 'missing_info', label: 'Missing Info' },
  { value: 'pending_client', label: 'Pending Client' },
  { value: 'underwriting', label: 'Underwriting' },
  { value: 'carrier_delay', label: 'Carrier Delay' },
  { value: 'other', label: 'Other' },
]

const DEFAULT_FILTERS: RequestFiltersState = {
  status: '',
  carrier: '',
  blocker: '',
  search: '',
  created_after: '',
  created_before: '',
  requester: '',
}

// ─── Date Range Helpers ──────────────────────────────────────────────────────

type DatePreset = 'today' | '7d' | '30d' | '90d' | 'all'

function getDatePresetValue(preset: DatePreset): string {
  if (preset === 'all') return ''
  const d = new Date()
  switch (preset) {
    case 'today':
      break // today
    case '7d':
      d.setDate(d.getDate() - 7)
      break
    case '30d':
      d.setDate(d.getDate() - 30)
      break
    case '90d':
      d.setDate(d.getDate() - 90)
      break
  }
  return d.toISOString().split('T')[0]
}

function getActivePreset(createdAfter: string): DatePreset | null {
  if (!createdAfter) return 'all'
  const now = new Date()
  const after = new Date(createdAfter)
  const diffDays = Math.round((now.getTime() - after.getTime()) / (1000 * 60 * 60 * 24))
  if (diffDays <= 1) return 'today'
  if (diffDays >= 6 && diffDays <= 8) return '7d'
  if (diffDays >= 29 && diffDays <= 31) return '30d'
  if (diffDays >= 89 && diffDays <= 91) return '90d'
  return null
}

const DATE_PRESETS: { key: DatePreset; label: string }[] = [
  { key: 'today', label: 'Today' },
  { key: '7d', label: '7d' },
  { key: '30d', label: '30d' },
  { key: '90d', label: '90d' },
  { key: 'all', label: 'All' },
]

// ─── Component ───────────────────────────────────────────────────────────────

export default function RequestFilters({ filters, onChange }: RequestFiltersProps) {
  const [searchInput, setSearchInput] = useState(filters.search)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Fetch AE users
  const { data: usersData } = useUsers({ role: 'account_executive' })
  const aeOptions = [
    { value: '', label: 'All AEs' },
    ...(usersData?.results ?? []).map((u) => ({
      value: String(u.id),
      label: u.full_name || `${u.first_name} ${u.last_name}`.trim() || u.email,
    })),
  ]

  // Debounced search
  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchInput(value)
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => {
        onChange({ ...filters, search: value })
      }, 300)
    },
    [filters, onChange],
  )

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  const handleSelectChange = (key: keyof RequestFiltersState, value: string) => {
    onChange({ ...filters, [key]: value })
  }

  const handleDatePreset = (preset: DatePreset) => {
    const created_after = getDatePresetValue(preset)
    onChange({ ...filters, created_after, created_before: '' })
  }

  const activePreset = getActivePreset(filters.created_after)

  const hasActiveFilters =
    filters.status !== '' ||
    filters.carrier !== '' ||
    filters.blocker !== '' ||
    filters.search !== '' ||
    filters.created_after !== '' ||
    filters.created_before !== '' ||
    filters.requester !== ''

  const handleClear = () => {
    setSearchInput('')
    onChange(DEFAULT_FILTERS)
  }

  return (
    <div className="space-y-3">
      {/* Row 1: Dropdowns + Search */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Status */}
        <Select
          value={filters.status}
          onChange={(val) => handleSelectChange('status', val)}
          options={STATUS_OPTIONS}
          placeholder="All Statuses"
          size="sm"
          className="w-44"
        />

        {/* Carrier */}
        <Select
          value={filters.carrier}
          onChange={(val) => handleSelectChange('carrier', val)}
          options={CARRIER_OPTIONS}
          placeholder="All Carriers"
          size="sm"
          className="w-40"
        />

        {/* Blocker */}
        <Select
          value={filters.blocker}
          onChange={(val) => handleSelectChange('blocker', val)}
          options={BLOCKER_OPTIONS}
          placeholder="All"
          size="sm"
          className="w-40"
        />

        {/* AE / Requester */}
        <Select
          value={filters.requester}
          onChange={(val) => handleSelectChange('requester', val)}
          options={aeOptions}
          placeholder="All AEs"
          size="sm"
          className="w-44"
        />

        {/* Search */}
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search company, carrier..."
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm text-gray-700 shadow-sm placeholder:text-gray-400 focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
          />
        </div>

        {/* Clear */}
        {hasActiveFilters && (
          <button
            onClick={handleClear}
            className="inline-flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-600 shadow-sm hover:bg-gray-50"
          >
            <X className="h-3.5 w-3.5" />
            Clear Filters
          </button>
        )}
      </div>

      {/* Row 2: Date range presets */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-gray-500">Date:</span>
        <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-0.5">
          {DATE_PRESETS.map((p) => (
            <button
              key={p.key}
              onClick={() => handleDatePreset(p.key)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                activePreset === p.key
                  ? 'bg-white text-[#ff5c00] shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
