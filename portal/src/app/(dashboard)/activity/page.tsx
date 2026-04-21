'use client';

import { useState, useEffect } from 'react';
import { usePageTitle } from '@/hooks/use-page-title';
import { apiFetch } from '@/lib/api';

// ─── Types ───────────────────────────────────────────────────────────────────

interface ActivityEvent {
  id: string;
  type:
    | 'policy_created'
    | 'policy_status_changed'
    | 'payment_received'
    | 'payment_refunded'
    | 'coverage_modification_requested'
    | 'certificate_requested'
    | 'member_joined';
  title: string;
  description: string;
  actor: string;
  metadata: Record<string, string | number | boolean | null | undefined>;
  timestamp: string;
}

interface ActivityLogResponse {
  events: ActivityEvent[];
  total: number;
  limit: number;
  offset: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const EVENT_ICON: Record<ActivityEvent['type'], React.ReactNode> = {
  policy_created: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
    </svg>
  ),
  policy_status_changed: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
    </svg>
  ),
  payment_received: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>
    </svg>
  ),
  payment_refunded: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 14 4 9 9 4"/><path d="M20 20v-7a4 4 0 0 0-4-4H4"/>
    </svg>
  ),
  coverage_modification_requested: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
    </svg>
  ),
  certificate_requested: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>
    </svg>
  ),
  member_joined: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
      <line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/>
    </svg>
  ),
};

const EVENT_COLOR: Record<ActivityEvent['type'], string> = {
  policy_created: 'bg-success-bg text-success-dark',
  policy_status_changed: 'bg-border text-muted',
  payment_received: 'bg-primary/10 text-primary',
  payment_refunded: 'bg-border text-muted',
  coverage_modification_requested: 'bg-primary/10 text-primary',
  certificate_requested: 'bg-success-bg text-success-dark',
  member_joined: 'bg-border text-muted',
};

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours === 0) {
      const diffMin = Math.floor(diffMs / (1000 * 60));
      return diffMin <= 1 ? 'Just now' : `${diffMin} minutes ago`;
    }
    return diffHours === 1 ? '1 hour ago' : `${diffHours} hours ago`;
  }
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="max-w-[800px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 animate-pulse">
      <div className="flex flex-col gap-2 mb-8">
        <div className="h-3 w-16 bg-border rounded" />
        <div className="h-8 w-48 bg-border rounded" />
        <div className="h-4 w-72 bg-border rounded mt-1" />
      </div>
      <div className="flex flex-col gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="flex gap-4 items-start">
            <div className="w-8 h-8 rounded-full bg-border shrink-0 mt-1" />
            <div className="flex-1 flex flex-col gap-2">
              <div className="h-4 w-48 bg-border rounded" />
              <div className="h-3 w-72 bg-border rounded" />
              <div className="h-3 w-20 bg-border rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ActivityPage() {
  usePageTitle('Activity');
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [offset, setOffset] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [filterType, setFilterType] = useState<string>('all');

  const LIMIT = 25;

  const fetchActivity = async (newOffset = 0, append = false) => {
    if (newOffset === 0) setIsLoading(true);
    else setLoadingMore(true);

    try {
      const data = await apiFetch<ActivityLogResponse>(
        `/api/v1/policies/activity-log?limit=${LIMIT}&offset=${newOffset}`
      );
      if (append) {
        setEvents((prev) => [...prev, ...data.events]);
      } else {
        setEvents(data.events);
      }
      setTotal(data.total);
      setOffset(newOffset);
    } catch {
      setIsError(true);
    } finally {
      setIsLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    fetchActivity();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredEvents =
    filterType === 'all' ? events : events.filter((e) => e.type === filterType);

  const filterOptions = [
    { value: 'all', label: 'All activity' },
    { value: 'policy_created', label: 'Policies' },
    { value: 'payment_received', label: 'Payments' },
    { value: 'coverage_modification_requested', label: 'Modifications' },
    { value: 'certificate_requested', label: 'Certificates' },
    { value: 'member_joined', label: 'Team' },
  ];

  if (isLoading) return <LoadingSkeleton />;

  return (
    <div className="max-w-[800px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10">
      {/* Header */}
      <div className="flex flex-col gap-1 mb-6">
        <span className="text-[11px] font-semibold uppercase tracking-normal text-muted leading-[1.2]">Organization</span>
        <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">Activity</h1>
        <p className="text-sm text-muted mt-1">
          A timeline of all activity in your organization: policy changes, payments, team updates, and more.
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-6 flex-wrap">
        {filterOptions.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setFilterType(opt.value)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${
              filterType === opt.value
                ? 'bg-primary text-white border-primary'
                : 'bg-transparent text-muted border-border hover:border-primary hover:text-primary'
            }`}
          >
            {opt.label}
          </button>
        ))}
        <span className="ml-auto text-xs text-muted">{total} total events</span>
      </div>

      {isError && (
        <div className="rounded-2xl border border-border bg-surface p-8 text-center">
          <p className="text-sm text-muted mb-3">Failed to load activity.</p>
          <button
            onClick={() => fetchActivity()}
            className="text-sm font-medium text-primary bg-transparent border border-primary rounded-xl px-4 py-2 cursor-pointer hover:bg-primary hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
          >
            Retry
          </button>
        </div>
      )}

      {!isError && filteredEvents.length === 0 && (
        <div className="rounded-2xl border border-border bg-surface p-12 text-center flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-border flex items-center justify-center text-muted">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <p className="text-sm font-medium text-heading">No activity yet</p>
          <p className="text-xs text-muted">Activity will appear here as your team makes changes.</p>
        </div>
      )}

      {/* Timeline */}
      {filteredEvents.length > 0 && (
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />

          <div className="flex flex-col gap-0">
            {filteredEvents.map((event, idx) => (
              <div key={event.id} className={`relative flex gap-4 ${idx < filteredEvents.length - 1 ? 'pb-6' : ''}`}>
                {/* Icon bubble */}
                <div
                  className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${EVENT_COLOR[event.type]}`}
                >
                  {EVENT_ICON[event.type]}
                </div>

                {/* Content */}
                <div className="flex-1 pt-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-heading leading-snug">{event.title}</p>
                      <p className="text-sm text-muted mt-0.5">{event.description}</p>
                    </div>
                    <span className="text-xs text-muted shrink-0 pt-0.5">{formatTimestamp(event.timestamp)}</span>
                  </div>

                  {/* Actor + metadata */}
                  <div className="flex items-center gap-3 mt-2 flex-wrap">
                    <div className="flex items-center gap-1 text-xs text-muted">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                      </svg>
                      {event.actor}
                    </div>
                    {event.metadata.policy_number && (
                      <span className="text-xs text-muted font-mono bg-border/50 px-1.5 py-0.5 rounded">
                        #{event.metadata.policy_number as string}
                      </span>
                    )}
                    {event.metadata.amount && (
                      <span className="text-xs font-semibold text-heading">
                        ${parseFloat(event.metadata.amount as string).toLocaleString()}
                      </span>
                    )}
                    {event.type === 'coverage_modification_requested' && event.metadata.status && (
                      <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                        event.metadata.status === 'approved' ? 'bg-success-bg text-success-dark' :
                        event.metadata.status === 'denied' ? 'bg-danger/10 text-danger' :
                        'bg-border text-muted'
                      }`}>
                        {event.metadata.status as string}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Load more */}
          {offset + LIMIT < total && (
            <div className="mt-8 flex justify-center">
              <button
                onClick={() => fetchActivity(offset + LIMIT, true)}
                disabled={loadingMore}
                className="px-6 py-2 text-sm font-medium text-primary bg-transparent border border-primary rounded-xl cursor-pointer hover:bg-primary hover:text-white transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
              >
                {loadingMore ? 'Loading…' : 'Load more'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
