import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { Loader2, Search } from 'lucide-react'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { cn } from '@/lib/utils'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface CellOption {
  value: string
  label: string
  color?: string
}

export interface InlineCellEditorProps {
  value: string
  options: CellOption[]
  onSave: (newValue: string) => Promise<void>
  renderValue?: (value: string) => React.ReactNode
  variant?: 'badge' | 'text'
  confirmValues?: string[]
  confirmMessage?: string
  disabled?: boolean
  /** Show search when options >= this count. Default 8. */
  searchThreshold?: number
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function InlineCellEditor({
  value,
  options,
  onSave,
  renderValue,
  variant = 'text',
  confirmValues = [],
  confirmMessage,
  disabled = false,
  searchThreshold = 8,
}: InlineCellEditorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  const showSearch = options.length >= searchThreshold

  const filtered = useMemo(() => {
    if (!search) return options
    const q = search.toLowerCase()
    return options.filter((o) => o.label.toLowerCase().includes(q))
  }, [options, search])

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [isOpen])

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen])

  // Focus search and reset on open
  useEffect(() => {
    if (isOpen) {
      setSearch('')
      requestAnimationFrame(() => searchRef.current?.focus())
    }
  }, [isOpen])

  const executeSave = useCallback(
    async (newValue: string) => {
      setIsSaving(true)
      try {
        await onSave(newValue)
      } finally {
        setIsSaving(false)
        setIsOpen(false)
        setConfirmTarget(null)
      }
    },
    [onSave],
  )

  const handleOptionClick = (newValue: string) => {
    if (newValue === value) {
      setIsOpen(false)
      return
    }
    if (confirmValues.includes(newValue)) {
      setConfirmTarget(newValue)
      return
    }
    executeSave(newValue)
  }

  // Loading
  if (isSaving) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-500">
        <Loader2 className="h-3 w-3 animate-spin" />
        Saving...
      </span>
    )
  }

  // Current value display
  const currentLabel = options.find((o) => o.value === value)?.label ?? value
  const displayNode = renderValue ? (
    renderValue(value)
  ) : variant === 'badge' ? (
    <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
      {currentLabel}
    </span>
  ) : (
    <span className="text-sm text-gray-700">{currentLabel || '—'}</span>
  )

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Clickable trigger */}
      <button
        type="button"
        disabled={disabled}
        onClick={(e) => {
          e.stopPropagation()
          setIsOpen(!isOpen)
        }}
        className={cn(
          'cursor-pointer transition-shadow',
          variant === 'badge'
            ? 'inline-flex rounded-full hover:ring-2 hover:ring-gray-300'
            : 'rounded-md px-0.5 -mx-0.5 hover:ring-2 hover:ring-gray-300',
          disabled && 'cursor-not-allowed opacity-50',
        )}
      >
        {displayNode}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute left-0 top-full z-30 mt-1 w-52 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg animate-in fade-in slide-in-from-top-0.5">
          {/* Search input */}
          {showSearch && (
            <div className="border-b border-gray-100 px-2 py-2">
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
                <input
                  ref={searchRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  onKeyDown={(e) => {
                    if (e.key === 'Escape') {
                      e.stopPropagation()
                      setIsOpen(false)
                    }
                  }}
                  placeholder="Search..."
                  className="w-full rounded-md border border-gray-200 bg-gray-50 py-1.5 pl-8 pr-3 text-sm text-gray-700 outline-none placeholder:text-gray-400 focus:border-primary-300 focus:bg-white focus:ring-1 focus:ring-primary-300/30"
                />
              </div>
            </div>
          )}

          {/* Options */}
          <div className="max-h-56 overflow-auto py-1 scrollbar-compact">
            {filtered.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm text-gray-400">
                No results
              </div>
            ) : (
              filtered.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleOptionClick(opt.value)
                  }}
                  className={cn(
                    'flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors hover:bg-gray-50',
                    opt.value === value
                      ? 'font-medium text-primary-500'
                      : 'text-gray-700',
                  )}
                >
                  <span className="inline-flex items-center gap-2">
                    {opt.color && (
                      <span className={cn('h-2 w-2 shrink-0 rounded-full', opt.color)} />
                    )}
                    {opt.label}
                  </span>
                  {opt.value === value && (
                    <svg className="ml-2 h-4 w-4 shrink-0 text-primary-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* Confirmation dialog */}
      <ConfirmDialog
        open={!!confirmTarget}
        title="Confirm Change"
        message={
          confirmMessage ??
          `Are you sure you want to change this to "${options.find((o) => o.value === confirmTarget)?.label ?? confirmTarget}"? This action may be difficult to reverse.`
        }
        confirmLabel="Change"
        variant="danger"
        isLoading={isSaving}
        onConfirm={() => confirmTarget && executeSave(confirmTarget)}
        onCancel={() => setConfirmTarget(null)}
      />
    </div>
  )
}
