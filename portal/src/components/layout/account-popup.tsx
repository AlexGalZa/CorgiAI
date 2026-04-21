'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/use-app-store';
import { useLogout } from '@/hooks/use-auth';

export default function AccountPopup() {
  const { accountPopupOpen, setAccountPopupOpen } = useAppStore();
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const logout = useLogout();

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        ref.current &&
        !ref.current.contains(e.target as Node) &&
        !(e.target as HTMLElement).closest('.profile-row-trigger')
      ) {
        setAccountPopupOpen(false);
      }
    }
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, [setAccountPopupOpen]);

  if (!accountPopupOpen) return null;

  return (
    <div
      ref={ref}
      className="fixed bottom-[70px] left-4 w-[248px] bg-[var(--color-popup-bg)] border border-[var(--color-border-raw)] rounded-xl shadow-[0_8px_24px_rgba(0,0,0,.1)] dark:shadow-[0_8px_24px_rgba(0,0,0,.4)] z-[1001] animate-enter p-1.5"
    >
      <div
        className="py-2.5 px-3 text-[13px] text-[var(--color-heading-raw)] cursor-pointer rounded-lg transition-colors flex items-center gap-2 hover:bg-[var(--color-popup-hover)]"
        onClick={() => {
          setAccountPopupOpen(false);
          router.push('/settings');
        }}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
          <circle cx="7" cy="5" r="3" /><path d="M1 13c0-3 3-5 6-5s6 2 6 5" />
        </svg>
        Account settings
      </div>
      <div
        className="py-2.5 px-3 text-[13px] text-[var(--color-heading-raw)] cursor-pointer rounded-lg transition-colors flex items-center gap-2 hover:bg-[var(--color-popup-hover)]"
        onClick={() => {
          setAccountPopupOpen(false);
          router.push('/billing');
        }}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
          <rect x="1" y="4" width="12" height="8" rx="1.5" /><path d="M4 4V3a3 3 0 0 1 6 0v1" />
        </svg>
        Billing
      </div>
      <div className="h-px bg-[var(--color-border-raw)] my-1" />
      <div
        className="py-2.5 px-3 text-[13px] text-danger cursor-pointer rounded-lg transition-colors flex items-center gap-2 hover:bg-danger-bg"
        onClick={() => {
          setAccountPopupOpen(false);
          logout();
        }}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" className="text-danger" strokeWidth="1.4" strokeLinecap="round">
          <path d="M5 1H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h2" /><path d="M9 10l3-3-3-3" /><line x1="5" y1="7" x2="12" y2="7" />
        </svg>
        Sign out
      </div>
    </div>
  );
}
