'use client';

import { useState, useRef, useEffect, useCallback, useMemo, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';

export interface DatePickerProps {
  value: string; // YYYY-MM-DD
  onChange: (value: string) => void;
  min?: string;
  max?: string;
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
  className?: string;
}

const DAYS_OF_WEEK = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function parseDate(s: string): Date | null {
  if (!s) return null;
  const [y, m, d] = s.split('-').map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d);
}

function formatYMD(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function formatDisplay(s: string): string {
  const d = parseDate(s);
  if (!d) return '';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

export function DatePicker({
  value,
  onChange,
  min,
  max,
  placeholder = 'Select date',
  disabled = false,
  error = false,
  className = '',
}: DatePickerProps) {
  const parsed = parseDate(value);
  const today = useMemo(() => new Date(), []);

  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState(parsed?.getFullYear() ?? today.getFullYear());
  const [viewMonth, setViewMonth] = useState(parsed?.getMonth() ?? today.getMonth());
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [rect, setRect] = useState<DOMRect | null>(null);

  const minDate = parseDate(min ?? '');
  const maxDate = parseDate(max ?? '');

  const openCalendar = useCallback(() => {
    if (disabled) return;
    const r = triggerRef.current?.getBoundingClientRect();
    if (r) setRect(r);
    const d = parsed ?? today;
    setViewYear(d.getFullYear());
    setViewMonth(d.getMonth());
    setOpen(true);
  }, [disabled, parsed, today]);

  const closeCalendar = useCallback(() => {
    setOpen(false);
    triggerRef.current?.focus();
  }, []);

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
        closeCalendar();
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open, closeCalendar]);

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

  // Escape to close
  useEffect(() => {
    if (!open) return;
    const handler = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') closeCalendar();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, closeCalendar]);

  const prevMonth = useCallback(() => {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear((y) => y - 1);
    } else {
      setViewMonth((m) => m - 1);
    }
  }, [viewMonth]);

  const nextMonth = useCallback(() => {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear((y) => y + 1);
    } else {
      setViewMonth((m) => m + 1);
    }
  }, [viewMonth]);

  const selectDay = useCallback(
    (date: Date) => {
      onChange(formatYMD(date));
      closeCalendar();
    },
    [onChange, closeCalendar],
  );

  const isDisabled = useCallback(
    (date: Date) => {
      if (minDate && date < minDate) return true;
      if (maxDate && date > maxDate) return true;
      return false;
    },
    [minDate, maxDate],
  );

  // Build the calendar grid
  const calendarDays = useMemo(() => {
    const firstDay = new Date(viewYear, viewMonth, 1);
    const startOffset = firstDay.getDay(); // 0=Sun
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

    const days: Array<{ date: Date; inMonth: boolean }> = [];

    // Previous month filler
    for (let i = startOffset - 1; i >= 0; i--) {
      const d = new Date(viewYear, viewMonth, -i);
      days.push({ date: d, inMonth: false });
    }
    // Current month
    for (let i = 1; i <= daysInMonth; i++) {
      days.push({ date: new Date(viewYear, viewMonth, i), inMonth: true });
    }
    // Next month filler (pad to 42 = 6 rows)
    const remaining = 42 - days.length;
    for (let i = 1; i <= remaining; i++) {
      days.push({ date: new Date(viewYear, viewMonth + 1, i), inMonth: false });
    }

    return days;
  }, [viewYear, viewMonth]);

  const handleTriggerKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault();
        openCalendar();
      }
    },
    [openCalendar],
  );

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={() => (open ? closeCalendar() : openCalendar())}
        onKeyDown={handleTriggerKeyDown}
        className={`
          w-full bg-surface border rounded-lg px-3 py-2.5 text-sm font-sans text-left
          flex items-center justify-between gap-2 outline-none transition-all cursor-pointer
          disabled:opacity-50 disabled:cursor-not-allowed
          ${error ? 'border-danger' : open ? 'border-primary ring-1 ring-primary' : 'border-border'}
          focus:border-primary focus:ring-1 focus:ring-primary
          ${className}
        `}
      >
        <span className={value ? 'text-heading' : 'text-muted'}>
          {value ? formatDisplay(value) : placeholder}
        </span>
        {/* Calendar icon */}
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="shrink-0 text-muted"
        >
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <path d="M16 2v4" />
          <path d="M8 2v4" />
          <path d="M3 10h18" />
        </svg>
      </button>

      {open &&
        rect &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            ref={panelRef}
            style={{
              position: 'fixed',
              top: rect.bottom + 4,
              left: rect.left,
              width: 288,
              zIndex: 9999,
            }}
            className="bg-surface border border-border rounded-lg shadow-lg p-3"
          >
            {/* Header: prev / month year / next */}
            <div className="flex items-center justify-between mb-2">
              <button
                type="button"
                onClick={prevMonth}
                className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-bg transition-colors bg-transparent border-none cursor-pointer"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m15 18-6-6 6-6" />
                </svg>
              </button>
              <span className="text-sm font-semibold text-heading">
                {MONTH_NAMES[viewMonth]} {viewYear}
              </span>
              <button
                type="button"
                onClick={nextMonth}
                className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-bg transition-colors bg-transparent border-none cursor-pointer"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m9 18 6-6-6-6" />
                </svg>
              </button>
            </div>

            {/* Day-of-week headers */}
            <div className="grid grid-cols-7 gap-0 mb-1">
              {DAYS_OF_WEEK.map((d) => (
                <div key={d} className="text-center text-[10px] font-semibold text-muted py-1">
                  {d}
                </div>
              ))}
            </div>

            {/* Day grid */}
            <div className="grid grid-cols-7 gap-0">
              {calendarDays.map(({ date, inMonth }, i) => {
                const isSelected = parsed && isSameDay(date, parsed);
                const isToday = isSameDay(date, today);
                const dayDisabled = !inMonth || isDisabled(date);

                return (
                  <button
                    key={i}
                    type="button"
                    disabled={dayDisabled}
                    onClick={() => !dayDisabled && selectDay(date)}
                    className={`
                      w-full aspect-square flex items-center justify-center text-xs rounded-full
                      transition-colors border-none cursor-pointer font-sans
                      ${dayDisabled ? 'text-muted/40 cursor-default bg-transparent' : ''}
                      ${!dayDisabled && !isSelected ? 'hover:bg-bg bg-transparent' : ''}
                      ${isSelected ? 'bg-primary text-white font-semibold' : ''}
                      ${!isSelected && isToday && inMonth ? 'ring-1 ring-primary text-heading font-medium' : ''}
                      ${!isSelected && !isToday && inMonth && !dayDisabled ? 'text-heading' : ''}
                    `}
                  >
                    {date.getDate()}
                  </button>
                );
              })}
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
