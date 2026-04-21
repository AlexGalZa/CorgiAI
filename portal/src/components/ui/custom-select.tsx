'use client';

import { useState, useRef, useEffect, useCallback, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';

export interface CustomSelectOption {
  value: string;
  label: string;
  description?: string;
}

export interface CustomSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: CustomSelectOption[];
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
  className?: string;
}

export function CustomSelect({
  value,
  onChange,
  options,
  placeholder = 'Select…',
  disabled = false,
  error = false,
  className = '',
}: CustomSelectProps) {
  const [open, setOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [rect, setRect] = useState<DOMRect | null>(null);

  const selectedOption = options.find((o) => o.value === value);

  const openDropdown = useCallback(() => {
    if (disabled) return;
    const r = triggerRef.current?.getBoundingClientRect();
    if (r) setRect(r);
    setFocusedIndex(options.findIndex((o) => o.value === value));
    setOpen(true);
  }, [disabled, options, value]);

  const closeDropdown = useCallback(() => {
    setOpen(false);
    setFocusedIndex(-1);
    triggerRef.current?.focus();
  }, []);

  const selectOption = useCallback(
    (val: string) => {
      onChange(val);
      closeDropdown();
    },
    [onChange, closeDropdown],
  );

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node)
      ) {
        closeDropdown();
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open, closeDropdown]);

  // Reposition on scroll/resize
  useEffect(() => {
    if (!open) return;
    const reposition = () => {
      const r = triggerRef.current?.getBoundingClientRect();
      if (r) setRect(r);
    };
    window.addEventListener('scroll', reposition, true);
    window.addEventListener('resize', reposition);
    return () => {
      window.removeEventListener('scroll', reposition, true);
      window.removeEventListener('resize', reposition);
    };
  }, [open]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!open) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          openDropdown();
        }
        return;
      }
      switch (e.key) {
        case 'Escape':
          e.preventDefault();
          closeDropdown();
          break;
        case 'ArrowDown':
          e.preventDefault();
          setFocusedIndex((prev) => (prev < options.length - 1 ? prev + 1 : 0));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setFocusedIndex((prev) => (prev > 0 ? prev - 1 : options.length - 1));
          break;
        case 'Enter':
        case ' ':
          e.preventDefault();
          if (focusedIndex >= 0 && focusedIndex < options.length) {
            selectOption(options[focusedIndex].value);
          }
          break;
      }
    },
    [open, focusedIndex, options, openDropdown, closeDropdown, selectOption],
  );

  // Scroll focused item into view
  useEffect(() => {
    if (!open || focusedIndex < 0) return;
    const panel = panelRef.current;
    if (!panel) return;
    const item = panel.children[focusedIndex] as HTMLElement | undefined;
    item?.scrollIntoView({ block: 'nearest' });
  }, [focusedIndex, open]);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        role="combobox"
        aria-expanded={open}
        aria-haspopup="listbox"
        disabled={disabled}
        onClick={() => (open ? closeDropdown() : openDropdown())}
        onKeyDown={handleKeyDown}
        className={`
          w-full bg-surface border rounded-lg px-3 py-2.5 text-sm font-sans text-left
          flex items-center justify-between gap-2 outline-none transition-all cursor-pointer
          disabled:opacity-50 disabled:cursor-not-allowed
          ${error ? 'border-danger' : open ? 'border-primary ring-1 ring-primary' : 'border-border'}
          focus:border-primary focus:ring-1 focus:ring-primary
          ${className}
        `}
      >
        <span className={selectedOption ? 'text-heading truncate' : 'text-muted truncate'}>
          {selectedOption?.label ?? placeholder}
        </span>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`shrink-0 text-muted transition-transform ${open ? 'rotate-180' : ''}`}
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open &&
        rect &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            ref={panelRef}
            role="listbox"
            style={{
              position: 'fixed',
              top: rect.bottom + 4,
              left: rect.left,
              width: rect.width,
              zIndex: 9999,
            }}
            className="bg-surface border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto py-1"
          >
            {options.map((opt, i) => {
              const isSelected = opt.value === value;
              const isFocused = i === focusedIndex;
              return (
                <div
                  key={opt.value}
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => selectOption(opt.value)}
                  onMouseEnter={() => setFocusedIndex(i)}
                  className={`
                    px-3 py-2 flex items-center justify-between gap-2 cursor-pointer text-sm transition-colors
                    ${isFocused ? 'bg-bg' : ''}
                    ${isSelected ? 'font-medium text-heading' : 'text-body'}
                  `}
                >
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <span className="truncate">{opt.label}</span>
                    {opt.description && (
                      <span className="text-[11px] text-muted truncate">{opt.description}</span>
                    )}
                  </div>
                  {isSelected && (
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="shrink-0 text-primary"
                    >
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                  )}
                </div>
              );
            })}
          </div>,
          document.body,
        )}
    </>
  );
}
