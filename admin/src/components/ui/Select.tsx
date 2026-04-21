import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { ChevronDown, Check, Search } from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface SelectOption {
  value: string
  label: string
  icon?: React.ReactNode
}

export interface SelectProps {
  value: string
  onChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
  size?: 'sm' | 'md'
  className?: string
  id?: string
  name?: string
  error?: boolean
  /** Show the search input when options >= this count. Default 6. */
  searchThreshold?: number
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function Select({
  value,
  onChange,
  options,
  placeholder = 'Select...',
  disabled = false,
  size = 'md',
  className,
  id,
  name,
  error = false,
  searchThreshold = 6,
}: SelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [highlightIndex, setHighlightIndex] = useState(-1)
  const [search, setSearch] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  const showSearch = options.length >= searchThreshold

  const filtered = useMemo(() => {
    if (!search) return options
    const q = search.toLowerCase()
    return options.filter((o) => o.label.toLowerCase().includes(q))
  }, [options, search])

  const selectedOption = options.find((o) => o.value === value)

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [isOpen])

  // Focus search when opened, reset search when closed
  useEffect(() => {
    if (isOpen) {
      setSearch('')
      setHighlightIndex(filtered.findIndex((o) => o.value === value))
      // Delay focus so the dropdown has rendered
      requestAnimationFrame(() => searchRef.current?.focus())
    }
  }, [isOpen]) // eslint-disable-line react-hooks/exhaustive-deps

  // Reset highlight when filtered list changes
  useEffect(() => {
    if (!isOpen) return
    const idx = filtered.findIndex((o) => o.value === value)
    setHighlightIndex(idx >= 0 ? idx : 0)
  }, [filtered, isOpen, value])

  // Scroll highlighted item into view
  useEffect(() => {
    if (!isOpen || highlightIndex < 0 || !listRef.current) return
    const item = listRef.current.children[highlightIndex] as HTMLElement | undefined
    item?.scrollIntoView({ block: 'nearest' })
  }, [highlightIndex, isOpen])

  const handleSelect = useCallback(
    (optionValue: string) => {
      onChange(optionValue)
      setIsOpen(false)
    },
    [onChange],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (disabled) return

      switch (e.key) {
        case 'Escape':
          e.preventDefault()
          setIsOpen(false)
          break
        case 'Enter':
          e.preventDefault()
          if (!isOpen) {
            setIsOpen(true)
          } else if (highlightIndex >= 0 && highlightIndex < filtered.length) {
            handleSelect(filtered[highlightIndex].value)
          }
          break
        case ' ':
          if (!isOpen) {
            e.preventDefault()
            setIsOpen(true)
          }
          // When search is focused, allow space to type in search
          break
        case 'ArrowDown':
          e.preventDefault()
          if (!isOpen) {
            setIsOpen(true)
          } else {
            setHighlightIndex((prev) =>
              prev < filtered.length - 1 ? prev + 1 : 0,
            )
          }
          break
        case 'ArrowUp':
          e.preventDefault()
          if (!isOpen) {
            setIsOpen(true)
          } else {
            setHighlightIndex((prev) =>
              prev > 0 ? prev - 1 : filtered.length - 1,
            )
          }
          break
        case 'Tab':
          if (isOpen) setIsOpen(false)
          break
      }
    },
    [disabled, isOpen, highlightIndex, filtered, handleSelect],
  )

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      {name && <input type="hidden" name={name} value={value} />}

      {/* Trigger */}
      <button
        type="button"
        id={id}
        disabled={disabled}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        className={cn(
          'flex w-full items-center justify-between rounded-lg border bg-white text-left text-sm transition-colors',
          size === 'sm' ? 'px-3 py-1.5' : 'px-3 py-2',
          disabled && 'cursor-not-allowed opacity-50',
          error
            ? 'border-danger-500'
            : isOpen
              ? 'border-primary-500 ring-1 ring-primary-500/20'
              : 'border-gray-200 hover:border-gray-300',
        )}
      >
        <span className={cn('truncate', selectedOption ? 'text-gray-900' : 'text-gray-400')}>
          {selectedOption ? (
            <span className="inline-flex items-center gap-2">
              {selectedOption.icon}
              {selectedOption.label}
            </span>
          ) : (
            placeholder
          )}
        </span>
        <ChevronDown
          className={cn(
            'ml-2 h-4 w-4 shrink-0 text-gray-400 transition-transform',
            isOpen && 'rotate-180',
          )}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          className="absolute left-0 top-full z-30 mt-1 w-full overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg animate-in fade-in slide-in-from-top-0.5"
          role="listbox"
        >
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
                  onKeyDown={handleKeyDown}
                  placeholder="Search..."
                  className="w-full rounded-md border border-gray-200 bg-gray-50 py-1.5 pl-8 pr-3 text-sm text-gray-700 outline-none placeholder:text-gray-400 focus:border-primary-300 focus:bg-white focus:ring-1 focus:ring-primary-300/30"
                />
              </div>
            </div>
          )}

          {/* Options */}
          <div ref={listRef} className="max-h-56 overflow-auto py-1 scrollbar-compact">
            {filtered.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm text-gray-400">
                No results
              </div>
            ) : (
              filtered.map((opt, idx) => (
                <button
                  key={opt.value}
                  type="button"
                  role="option"
                  aria-selected={opt.value === value}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleSelect(opt.value)
                  }}
                  onMouseEnter={() => setHighlightIndex(idx)}
                  className={cn(
                    'flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors',
                    idx === highlightIndex && 'bg-gray-50',
                    opt.value === value
                      ? 'font-medium text-primary-500'
                      : 'text-gray-700',
                  )}
                >
                  <span className="inline-flex items-center gap-2 truncate">
                    {opt.icon}
                    {opt.label}
                  </span>
                  {opt.value === value && (
                    <Check className="ml-2 h-4 w-4 shrink-0 text-primary-500" />
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
