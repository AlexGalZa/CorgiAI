'use client';

import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import naicsData from '@/data/naics-codes.json';

interface NAICSEntry {
  /** NAICS code */
  c: string;
  /** Short title */
  t: string;
}

interface NAICSSelectorProps {
  code: string;
  description: string;
  onSelect: (code: string, description: string) => void;
  error?: boolean;
}

const entries = naicsData as NAICSEntry[];

/**
 * NAICS code autocomplete selector.
 * User can search by code or industry name. Selecting an entry fills both
 * the NAICS code and description fields.
 */
export function NAICSSelector({ code, description, onSelect, error }: NAICSSelectorProps) {
  const [query, setQuery] = useState(code ? `${code} — ${description}` : '');
  const [open, setOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Filter entries by query (code prefix or title substring)
  const filtered = useMemo(() => {
    if (!query.trim()) return entries.slice(0, 50); // show first 50 when empty
    const q = query.toLowerCase().replace(/\s*—\s*.*$/, '').trim(); // strip description after —
    return entries
      .filter((e) => e.c.startsWith(q) || e.t.toLowerCase().includes(q))
      .slice(0, 80);
  }, [query]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightIndex >= 0 && listRef.current) {
      const el = listRef.current.children[highlightIndex] as HTMLElement;
      el?.scrollIntoView({ block: 'nearest' });
    }
  }, [highlightIndex]);

  const handleSelect = useCallback(
    (entry: NAICSEntry) => {
      setQuery(`${entry.c} — ${entry.t}`);
      onSelect(entry.c, entry.t);
      setOpen(false);
      setHighlightIndex(-1);
    },
    [onSelect],
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setOpen(true);
        e.preventDefault();
      }
      return;
    }
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightIndex((i) => Math.min(i + 1, filtered.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightIndex((i) => Math.max(i - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightIndex >= 0 && filtered[highlightIndex]) {
          handleSelect(filtered[highlightIndex]);
        }
        break;
      case 'Escape':
        setOpen(false);
        setHighlightIndex(-1);
        break;
    }
  };

  if (entries.length === 0) {
    // Fallback: plain text inputs when NAICS data hasn't been generated
    return (
      <Input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          onSelect(e.target.value, '');
        }}
        placeholder="e.g. 541512"
        error={error}
      />
    );
  }

  return (
    <div ref={wrapperRef} className="relative">
      <Input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setHighlightIndex(-1);
          // If they clear the field, clear the selection
          if (!e.target.value.trim()) {
            onSelect('', '');
          }
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder="Search by code or industry name…"
        error={error}
        autoComplete="off"
      />
      {open && filtered.length > 0 && (
        <ul
          ref={listRef}
          className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-xl border border-border bg-white shadow-lg"
          role="listbox"
        >
          {filtered.map((entry, i) => (
            <li
              key={entry.c}
              role="option"
              aria-selected={i === highlightIndex}
              className={`cursor-pointer px-3 py-2 text-sm transition-colors ${
                i === highlightIndex
                  ? 'bg-primary/10 text-primary'
                  : 'text-body hover:bg-surface'
              }`}
              onMouseDown={(e) => {
                e.preventDefault(); // prevent blur
                handleSelect(entry);
              }}
              onMouseEnter={() => setHighlightIndex(i)}
            >
              <span className="font-mono text-xs text-muted mr-2">{entry.c}</span>
              <span>{entry.t}</span>
            </li>
          ))}
        </ul>
      )}
      {open && filtered.length === 0 && query.trim() && (
        <div className="absolute z-50 mt-1 w-full rounded-xl border border-border bg-white px-3 py-3 text-sm text-muted shadow-lg">
          No matching NAICS codes found
        </div>
      )}
    </div>
  );
}
