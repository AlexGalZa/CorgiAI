'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/use-app-store';
import type { User } from '@/stores/use-auth-store';
import { NotificationBell } from '@/components/ui/NotificationCenter';

interface HeaderProps {
  user?: User | null;
}

const SEARCH_ITEMS = [
  { label: 'Coverage', path: '/', keywords: 'coverage policies active' },
  { label: 'Certificates', path: '/certificates', keywords: 'certificates coi proof' },
  { label: 'Claims', path: '/claims', keywords: 'claims file incident' },
  { label: 'Documents', path: '/documents', keywords: 'documents files download' },
  { label: 'Billing', path: '/billing', keywords: 'billing invoices payment' },
  { label: 'Quotes', path: '/quotes', keywords: 'quotes get coverage explore' },
  { label: 'Organization', path: '/organization', keywords: 'organization team members' },
  { label: 'Get a Quote', path: '/quote/get-started', keywords: 'quote new start coverage' },
];

export default function Header({ user }: HeaderProps) {
  const { sidebarOpen, setSidebarOpen, toggleMobileSidebar } = useAppStore();
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = query.trim()
    ? SEARCH_ITEMS.filter(item =>
        item.label.toLowerCase().includes(query.toLowerCase()) ||
        item.keywords.toLowerCase().includes(query.toLowerCase())
      )
    : [];

  const showDropdown = focused && query.trim().length > 0 && filtered.length > 0;

  useEffect(() => {
    setSelectedIdx(0);
  }, [query]);

  // Keyboard shortcut: Cmd/Ctrl + K to focus search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
      if (e.key === 'Escape') {
        inputRef.current?.blur();
        setQuery('');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const navigate = (path: string) => {
    router.push(path);
    setQuery('');
    inputRef.current?.blur();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx(i => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIdx]) {
      navigate(filtered[selectedIdx].path);
    }
  };

  return (
    <header className="h-14 md:h-16 bg-[var(--color-surface-raw)] border-b border-[var(--color-border-raw)] flex items-center px-4 md:px-6 shrink-0 z-10">
      {/* Mobile hamburger */}
      <button
        onClick={toggleMobileSidebar}
        aria-label="Open menu"
        className="md:hidden w-9 h-9 rounded-lg flex items-center justify-center bg-transparent border-none cursor-pointer text-muted hover:text-heading hover:bg-black/[.04] transition-colors mr-2"
        title="Open menu"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 6h16" /><path d="M4 12h16" /><path d="M4 18h16" />
        </svg>
      </button>

      {/* Mobile logo (centered) */}
      <div className="md:hidden flex-1 flex justify-center">
        <img src="/corgi-icon.svg" alt="Corgi" className="h-7 w-7 object-contain" />
      </div>

      {/* Desktop sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        className="hidden md:flex w-9 h-9 rounded-lg items-center justify-center bg-transparent border-none cursor-pointer text-muted hover:text-heading hover:bg-black/[.04] transition-colors"
        title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <rect width="18" height="18" x="3" y="3" rx="2" />
          <path d="M9 3v18" />
        </svg>
      </button>

      {/* Search — hidden on mobile */}
      <div className="hidden md:block flex-1 max-w-[420px] mx-auto relative">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
          </svg>
          <input
            ref={inputRef}
            data-search-input
            type="text"
            placeholder="Search… (⌘K)"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => setFocused(false), 150)}
            onKeyDown={handleKeyDown}
            className="w-full bg-[var(--color-input-bg)] border border-transparent rounded-lg pl-9 pr-3 py-2 text-sm text-[var(--color-heading-raw)] placeholder:text-[var(--color-muted-raw)]/60 outline-none transition-colors focus:border-[var(--color-border-raw)] focus:bg-[var(--color-surface-raw)] focus:shadow-sm"
          />
        </div>

        {/* Search results dropdown */}
        {showDropdown && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-[var(--color-popup-bg)] border border-[var(--color-border-raw)] rounded-xl shadow-lg overflow-hidden z-50">
            {filtered.map((item, i) => (
              <button
                key={item.path}
                onMouseDown={() => navigate(item.path)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left border-none cursor-pointer font-sans transition-colors ${
                  i === selectedIdx ? 'bg-[var(--color-bg-hover)]' : 'bg-[var(--color-popup-bg)] hover:bg-[var(--color-bg-hover)]'
                } ${i > 0 ? 'border-t border-[var(--color-border-raw)]' : ''}`}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="text-muted" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m9 18 6-6-6-6" />
                </svg>
                <span className="text-sm font-medium text-[var(--color-heading-raw)]">{item.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Notification bell */}
      <div className="flex items-center gap-1 shrink-0">
        <NotificationBell />
      </div>
    </header>
  );
}
