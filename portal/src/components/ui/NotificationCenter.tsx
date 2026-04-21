'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';

/* ── Types ─────────────────────────────────────────────────── */

type NotificationType = 'success' | 'warning' | 'info' | 'error';

interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  createdAt: string; // ISO
  read: boolean;
}

// No mock data — notifications come from the API when the endpoint is implemented

/* ── Helpers ───────────────────────────────────────────────── */

const TYPE_STYLES: Record<NotificationType, { dot: string; icon: string }> = {
  success: { dot: 'bg-success', icon: 'var(--color-success)' },
  warning: { dot: 'bg-amber-500', icon: 'var(--color-warning-text)' },
  info: { dot: 'bg-primary', icon: 'var(--color-primary)' },
  error: { dot: 'bg-danger', icon: 'var(--color-danger)' },
};

function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/* ── Component ─────────────────────────────────────────────── */

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const bellRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; right: number } | null>(null);

  const unreadCount = notifications.filter((n) => !n.read).length;

  // Position the dropdown when opening
  useEffect(() => {
    if (open && bellRef.current) {
      const rect = bellRef.current.getBoundingClientRect();
      setPos({
        top: rect.bottom + 8,
        right: window.innerWidth - rect.right,
      });
    }
  }, [open]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        bellRef.current &&
        !bellRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open]);

  const markRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const markAllRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  return (
    <>
      {/* Bell button */}
      <button
        ref={bellRef}
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
        className="relative w-9 h-9 rounded-lg flex items-center justify-center bg-transparent border-none cursor-pointer text-muted hover:text-heading hover:bg-black/[.04] transition-colors"
        title="Notifications"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-[18px] h-[18px] rounded-full bg-primary text-white text-[10px] font-bold flex items-center justify-center leading-none">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel via Portal */}
      {open &&
        pos &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            ref={panelRef}
            className="fixed z-[9998] w-[360px] max-h-[420px] bg-surface border border-border rounded-2xl shadow-xl overflow-hidden flex flex-col animate-enter"
            style={{ top: pos.top, right: pos.right }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <span className="text-sm font-semibold text-heading">Notifications</span>
              {unreadCount > 0 && (
                <button
                  onClick={markAllRead}
                  className="text-[11px] font-medium text-primary bg-transparent border-none cursor-pointer font-sans p-0 hover:underline"
                >
                  Mark all as read
                </button>
              )}
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm text-muted">
                  No notifications yet
                </div>
              ) : (
                notifications.map((n) => {
                  const style = TYPE_STYLES[n.type];
                  return (
                    <button
                      key={n.id}
                      onClick={() => markRead(n.id)}
                      className={`w-full flex items-start gap-3 px-4 py-3 text-left border-none cursor-pointer font-sans transition-colors ${
                        n.read
                          ? 'bg-surface hover:bg-bg'
                          : 'bg-primary/5 hover:bg-primary/10'
                      } border-b border-border last:border-b-0`}
                    >
                      {/* Type dot */}
                      <span
                        className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${style.dot}`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className={`text-sm leading-tight truncate ${
                              n.read
                                ? 'font-normal text-muted'
                                : 'font-semibold text-heading'
                            }`}
                          >
                            {n.title}
                          </span>
                          <span className="text-[10px] text-muted whitespace-nowrap shrink-0">
                            {timeAgo(n.createdAt)}
                          </span>
                        </div>
                        <p className="text-xs text-muted leading-relaxed mt-0.5 m-0 line-clamp-2">
                          {n.message}
                        </p>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>,
          document.body
        )}
    </>
  );
}
