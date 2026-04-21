'use client';

import { useState, useEffect } from 'react';
import { usePageTitle } from '@/hooks/use-page-title';
import { apiFetch } from '@/lib/api';
import { useAppStore } from '@/stores/use-app-store';
import { Input, Textarea } from '@/components/ui/input';
import { BtnPrimary, BtnSecondary } from '@/components/ui/button';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ReviewSchedule {
  id: number;
  preferred_date: string;
  preferred_time: string;
  timezone: string;
  topics: string;
  notes: string;
  status: 'pending' | 'confirmed' | 'completed' | 'cancelled';
  confirmed_datetime: string | null;
  created_at: string;
}

const TOPIC_OPTIONS = [
  { value: 'coverage-review', label: 'Review current coverage' },
  { value: 'add-coverage', label: 'Add new coverage' },
  { value: 'adjust-limits', label: 'Adjust policy limits' },
  { value: 'claims-discussion', label: 'Discuss claims' },
  { value: 'pricing', label: 'Pricing & renewal' },
  { value: 'compliance', label: 'Compliance requirements' },
  { value: 'other', label: 'Other' },
];

const STATUS_BADGE: Record<ReviewSchedule['status'], { label: string; class: string }> = {
  pending: { label: 'Pending', class: 'bg-border text-muted' },
  confirmed: { label: 'Confirmed', class: 'bg-primary/10 text-primary' },
  completed: { label: 'Completed', class: 'bg-success-bg text-success-dark' },
  cancelled: { label: 'Cancelled', class: 'bg-danger/10 text-danger' },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

// Get tomorrow's date as the minimum allowed date
function getTomorrow() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().split('T')[0];
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ReviewPage() {
  usePageTitle('Schedule Review');
  const { showToast } = useAppStore();

  const [schedules, setSchedules] = useState<ReviewSchedule[]>([]);
  const [isLoadingSchedules, setIsLoadingSchedules] = useState(true);
  const [showForm, setShowForm] = useState(false);

  // Form state
  const [preferredDate, setPreferredDate] = useState('');
  const [preferredTime, setPreferredTime] = useState('');
  const [timezone, setTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/New_York'
  );
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const fetchSchedules = async () => {
    setIsLoadingSchedules(true);
    try {
      const data = await apiFetch<ReviewSchedule[]>('/api/v1/policies/schedule-review');
      setSchedules(data);
    } catch {
      // Silently fail — no schedules yet is fine
    } finally {
      setIsLoadingSchedules(false);
    }
  };

  useEffect(() => {
    fetchSchedules();
  }, []);

  const toggleTopic = (topic: string) => {
    setSelectedTopics((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!preferredDate) {
      showToast('Please select a preferred date');
      return;
    }

    setIsSubmitting(true);
    try {
      await apiFetch('/api/v1/policies/schedule-review', {
        method: 'POST',
        body: {
          preferred_date: preferredDate,
          preferred_time: preferredTime,
          timezone,
          topics: selectedTopics,
          notes,
        },
      });
      setSubmitted(true);
      showToast('Review scheduled! Your AE will be in touch to confirm.');
      fetchSchedules();
      // Reset form
      setPreferredDate('');
      setPreferredTime('');
      setSelectedTopics([]);
      setNotes('');
      setTimeout(() => {
        setSubmitted(false);
        setShowForm(false);
      }, 3000);
    } catch {
      showToast('Failed to schedule review. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeSchedules = schedules.filter((s) => !['completed', 'cancelled'].includes(s.status));
  const pastSchedules = schedules.filter((s) => ['completed', 'cancelled'].includes(s.status));

  return (
    <div className="max-w-[800px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10">
      {/* Header */}
      <div className="flex items-start justify-between mb-6 gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-semibold uppercase tracking-normal text-muted leading-[1.2]">Coverage</span>
          <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">Annual Review</h1>
          <p className="text-sm text-muted mt-1">
            Schedule a call with your Account Executive to review your coverage and make sure you&apos;re protected.
          </p>
        </div>
        {!showForm && (
          <BtnPrimary onClick={() => setShowForm(true)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            Schedule review
          </BtnPrimary>
        )}
      </div>

      {/* Scheduling form */}
      {showForm && (
        <div className="rounded-2xl border border-border bg-surface p-6 mb-6">
          {submitted ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <div className="w-14 h-14 rounded-full bg-success-bg flex items-center justify-center">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-success-dark">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
              <h3 className="text-lg font-bold text-heading">Review Scheduled!</h3>
              <p className="text-sm text-muted">Your AE will reach out to confirm the date and time.</p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-base font-semibold text-heading">Schedule a Review</h2>
                <button
                  onClick={() => setShowForm(false)}
                  className="text-muted hover:text-body transition-colors bg-transparent border-none cursor-pointer p-1 rounded focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>

              <form onSubmit={handleSubmit} className="flex flex-col gap-5">
                {/* Date & Time */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-medium text-heading" htmlFor="review-date">
                      Preferred date <span className="text-primary">*</span>
                    </label>
                    <Input
                      id="review-date"
                      type="date"
                      value={preferredDate}
                      min={getTomorrow()}
                      onChange={(e) => setPreferredDate(e.target.value)}
                      required
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-medium text-heading" htmlFor="review-time">
                      Preferred time
                    </label>
                    <Input
                      id="review-time"
                      type="time"
                      value={preferredTime}
                      onChange={(e) => setPreferredTime(e.target.value)}
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-heading" htmlFor="review-tz">
                    Your timezone
                  </label>
                  <Input
                    id="review-tz"
                    type="text"
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    placeholder="e.g. America/New_York"
                  />
                </div>

                {/* Topics */}
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-medium text-heading">
                    What would you like to discuss?
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {TOPIC_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => toggleTopic(opt.value)}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${
                          selectedTopics.includes(opt.value)
                            ? 'bg-primary text-white border-primary'
                            : 'bg-transparent text-muted border-border hover:border-primary hover:text-primary'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Notes */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-heading" htmlFor="review-notes">
                    Additional notes
                  </label>
                  <Textarea
                    id="review-notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Anything else you'd like us to know before the call?"
                    rows={3}
                    className="resize-none"
                  />
                </div>

                <div className="flex items-center gap-3">
                  <BtnPrimary
                    type="submit"
                    disabled={isSubmitting || !preferredDate}
                  >
                    {isSubmitting ? 'Scheduling…' : 'Confirm request'}
                  </BtnPrimary>
                  <BtnSecondary
                    type="button"
                    onClick={() => setShowForm(false)}
                  >
                    Cancel
                  </BtnSecondary>
                </div>
              </form>
            </>
          )}
        </div>
      )}

      {/* Active schedules */}
      {activeSchedules.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-heading mb-3">Upcoming Reviews</h2>
          <div className="flex flex-col gap-3">
            {activeSchedules.map((s) => (
              <div key={s.id} className="rounded-2xl border border-border bg-surface p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_BADGE[s.status].class}`}>
                        {STATUS_BADGE[s.status].label}
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-heading">{formatDate(s.preferred_date)}</p>
                    {s.preferred_time && (
                      <p className="text-xs text-muted mt-0.5">
                        {s.preferred_time} {s.timezone}
                      </p>
                    )}
                    {s.topics && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {s.topics.split(',').map((t) => (
                          <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-border text-muted">
                            {t.trim()}
                          </span>
                        ))}
                      </div>
                    )}
                    {s.confirmed_datetime && (
                      <p className="text-xs text-primary font-medium mt-2">
                        ✓ Confirmed for {new Date(s.confirmed_datetime).toLocaleString()}
                      </p>
                    )}
                  </div>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-muted shrink-0 mt-1">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                  </svg>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isLoadingSchedules && schedules.length === 0 && !showForm && (
        <div className="rounded-2xl border border-border bg-surface p-12 flex flex-col items-center gap-4 text-center">
          <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-heading">No reviews scheduled</p>
            <p className="text-xs text-muted mt-1">Schedule your annual coverage review to make sure you're fully protected.</p>
          </div>
          <BtnPrimary onClick={() => setShowForm(true)}>
            Schedule a review
          </BtnPrimary>
        </div>
      )}

      {/* Past schedules */}
      {pastSchedules.length > 0 && (
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-muted mb-3">Past Reviews</h2>
          <div className="flex flex-col gap-2">
            {pastSchedules.map((s) => (
              <div key={s.id} className="rounded-xl border border-border bg-surface/50 p-4 flex items-center justify-between gap-3 opacity-60">
                <div>
                  <p className="text-sm text-body">{formatDate(s.preferred_date)}</p>
                  {s.preferred_time && (
                    <p className="text-xs text-muted">{s.preferred_time} {s.timezone}</p>
                  )}
                </div>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_BADGE[s.status].class}`}>
                  {STATUS_BADGE[s.status].label}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
