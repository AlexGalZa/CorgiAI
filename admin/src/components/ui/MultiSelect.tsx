import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { ChevronDown, X, Check, Search } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SelectOption } from './Select'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface MultiSelectProps {
  value: string[]
  onChange: (value: string[]) => void
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
  maxDisplay?: number
  className?: string
  error?: boolean
  /** Show the search input when options >= this count. Default 6. */
  searchThreshold?: number
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function MultiSelect({
  value,
  onChange,
  options,
  placeholder = 'Select...',
  disabled = false,
  maxDisplay = 3,
  className,
  error = false,
  searchThreshold = 6,
}: MultiSelectProps) {
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
      setHighlightIndex(-1)
      requestAnimationFrame(() => searchRef.current?.focus())
    }
  }, [isOpen])

  // Reset highlight when filtered list changes
  useEffect(() => {
    if (isOpen) setHighlightIndex(filtered.length > 0 ? 0 : -1)
  }, [filtered, isOpen])

  const toggleOption = useCallback(
    (optValue: string) => {
      if (value.includes(optValue)) {
        onChange(value.filter((v) => v !== optValue))
      } else {
        onChange([...value, optValue])
      }
    },
    [value, onChange],
  )

  const removeTag = (optValue: string, e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(value.filter((v) => v !== optValue))
  }

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
          }
          break
        case ' ':
          if (!isOpen) {
            e.preventDefault()
            setIsOpen(true)
          } else if (showSearch) {
            // Allow space to type in search
          } else if (highlightIndex >= 0 && highlightIndex < filtered.length) {
            e.preventDefault()
            toggleOption(filtered[highlightIndex].value)
          }
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
    [disabled, isOpen, highlightIndex, filtered, toggleOption, showSearch],
  )

  // Scroll highlighted item into view
  useEffect(() => {
    if (!isOpen || highlightIndex < 0 || !listRef.current) return
    const item = listRef.current.children[highlightIndex] as HTMLElement | undefined
    item?.scrollIntoView({ block: 'nearest' })
  }, [highlightIndex, isOpen])

  const selectedOptions = options.filter((o) => value.includes(o.value))
  const visibleTags = selectedOptions.slice(0, maxDisplay)
  const overflowCount = selectedOptions.length - maxDisplay

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      {/* Trigger */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        className={cn(
          'flex w-full min-h-[38px] items-center gap-1.5 rounded-lg border bg-white px-3 py-1.5 text-left text-sm transition-colors',
          disabled && 'cursor-not-allowed opacity-50',
          error
            ? 'border-danger-500'
            : isOpen
              ? 'border-primary-500 ring-1 ring-primary-500/20'
              : 'border-gray-200 hover:border-gray-300',
        )}
      >
        <div className="flex flex-1 flex-wrap items-center gap-1.5">
          {selectedOptions.length === 0 ? (
            <span className="text-gray-400">{placeholder}</span>
          ) : (
            <>
              {visibleTags.map((opt) => (
                <span
                  key={opt.value}
                  className="inline-flex items-center gap-1 rounded-md bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-700"
                >
                  {opt.label}
                  <button
                    type="button"
                    onClick={(e) => removeTag(opt.value, e)}
                    className="ml-0.5 rounded-md hover:bg-primary-100 hover:text-primary-900"
                    tabIndex={-1}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              {overflowCount > 0 && (
                <span className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
                  +{overflowCount} more
                </span>
              )}
            </>
          )}
        </div>
        <ChevronDown
          className={cn(
            'ml-1 h-4 w-4 shrink-0 text-gray-400 transition-transform',
            isOpen && 'rotate-180',
          )}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          className="absolute left-0 top-full z-30 mt-1 w-full overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg animate-in fade-in slide-in-from-top-0.5"
          role="listbox"
          aria-multiselectable="true"
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
              filtered.map((opt, idx) => {
                const isSelected = value.includes(opt.value)
                return (
                  <button
                    key={opt.value}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleOption(opt.value)
                    }}
                    onMouseEnter={() => setHighlightIndex(idx)}
                    className={cn(
                      'flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors',
                      idx === highlightIndex && 'bg-gray-50',
                      isSelected ? 'text-primary-700' : 'text-gray-700',
                    )}
                  >
                    <span
                      className={cn(
                        'flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-md border-[1.5px] transition-colors',
                        isSelected
                          ? 'border-primary-500 bg-primary-500'
                          : 'border-gray-300 bg-white',
                      )}
                    >
                      {isSelected && <Check className="h-3 w-3 text-white" strokeWidth={3} />}
                    </span>
                    <span className="truncate">{opt.label}</span>
                  </button>
                )
              })
            )}
          </div>

          {/* Clear all */}
          {value.length > 0 && (
            <div className="border-t border-gray-100 px-3 py-2">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onChange([])
                }}
                className="text-xs font-medium text-gray-500 transition-colors hover:text-primary-500"
              >
                Clear all
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
