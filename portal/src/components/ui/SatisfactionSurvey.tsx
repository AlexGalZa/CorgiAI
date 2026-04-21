'use client';

import { useState, useEffect, useCallback } from 'react';
import { CloseIcon } from '@/components/icons';

const STORAGE_KEY = 'corgi_survey_dismissed';
const COOLDOWN_DAYS = 30;
const SHOW_DELAY_MS = 60_000; // 60 seconds

const emojis = [
  { value: 1, emoji: '😞', label: 'Very Unhappy' },
  { value: 2, emoji: '😕', label: 'Unhappy' },
  { value: 3, emoji: '😐', label: 'Neutral' },
  { value: 4, emoji: '🙂', label: 'Happy' },
  { value: 5, emoji: '😍', label: 'Very Happy' },
];

function isInCooldown(): boolean {
  try {
    const dismissed = localStorage.getItem(STORAGE_KEY);
    if (!dismissed) return false;
    const dismissedAt = new Date(dismissed).getTime();
    const cooldownMs = COOLDOWN_DAYS * 24 * 60 * 60 * 1000;
    return Date.now() - dismissedAt < cooldownMs;
  } catch {
    return false;
  }
}

function setCooldown() {
  try {
    localStorage.setItem(STORAGE_KEY, new Date().toISOString());
  } catch {
    // localStorage unavailable
  }
}

export default function SatisfactionSurvey() {
  const [visible, setVisible] = useState(false);
  const [rating, setRating] = useState<number | null>(null);
  const [feedback, setFeedback] = useState('');
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (isInCooldown()) return;

    const timer = setTimeout(() => {
      // Re-check in case user dismissed via another tab
      if (!isInCooldown()) {
        setVisible(true);
      }
    }, SHOW_DELAY_MS);

    return () => clearTimeout(timer);
  }, []);

  const dismiss = useCallback(() => {
    setCooldown();
    setVisible(false);
  }, []);

  const handleSubmit = useCallback(() => {
    if (!rating) return;

    // Store feedback locally (placeholder — will POST to /api/v1/users/feedback later)
    try {
      const existingRaw = localStorage.getItem('corgi_survey_responses');
      const existing = existingRaw ? JSON.parse(existingRaw) : [];
      existing.push({
        rating,
        feedback: feedback.trim() || null,
        timestamp: new Date().toISOString(),
      });
      localStorage.setItem('corgi_survey_responses', JSON.stringify(existing));
    } catch {
      // localStorage unavailable
    }

    setCooldown();
    setSubmitted(true);

    // Auto-hide after showing thank you
    setTimeout(() => setVisible(false), 3000);
  }, [rating, feedback]);

  if (!visible) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 w-80 rounded-xl border border-border bg-surface p-5 shadow-lg animate-in slide-in-from-bottom-4 fade-in duration-300">
      {/* Close button */}
      <button
        onClick={dismiss}
        className="absolute right-3 top-3 text-muted hover:text-body transition-colors"
        aria-label="Dismiss survey"
      >
        <CloseIcon size={16} />
      </button>

      {submitted ? (
        <div className="text-center py-2">
          <p className="text-lg mb-1">🎉</p>
          <p className="text-sm font-medium text-heading">Thanks for your feedback!</p>
          <p className="text-xs text-muted mt-1">We appreciate it.</p>
        </div>
      ) : (
        <>
          <p className="text-sm font-medium text-heading mb-3 pr-4">
            How would you rate your experience?
          </p>

          {/* Emoji rating */}
          <div className="flex justify-between mb-4">
            {emojis.map(({ value, emoji, label }) => (
              <button
                key={value}
                onClick={() => setRating(value)}
                className={`flex flex-col items-center gap-1 rounded-lg p-2 transition-all ${
                  rating === value
                    ? 'bg-primary/10 ring-2 ring-primary scale-110'
                    : 'hover:bg-bg'
                }`}
                title={label}
              >
                <span className="text-2xl">{emoji}</span>
              </button>
            ))}
          </div>

          {/* Feedback text (appears after rating) */}
          {rating !== null && (
            <div className="space-y-3 animate-in fade-in duration-200">
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Any additional feedback? (optional)"
                rows={2}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm placeholder:text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none"
              />
              <button
                onClick={handleSubmit}
                className="w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-dark"
              >
                Submit
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
