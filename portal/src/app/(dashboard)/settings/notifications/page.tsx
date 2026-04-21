'use client';

import { useState, useEffect } from 'react';
import { usePageTitle } from '@/hooks/use-page-title';

const STORAGE_KEY = 'corgi_notification_prefs';

interface NotificationPrefs {
  quote_updates: boolean;
  policy_renewals: boolean;
  claim_status: boolean;
  billing_reminders: boolean;
  product_announcements: boolean;
}

const DEFAULT_PREFS: NotificationPrefs = {
  quote_updates: true,
  policy_renewals: true,
  claim_status: true,
  billing_reminders: true,
  product_announcements: false,
};

const PREF_LABELS: { key: keyof NotificationPrefs; label: string; description: string }[] = [
  {
    key: 'quote_updates',
    label: 'Quote updates',
    description: 'When a quote is approved, declined, or requires action.',
  },
  {
    key: 'policy_renewals',
    label: 'Policy renewals',
    description: 'Reminders before your policies renew or expire.',
  },
  {
    key: 'claim_status',
    label: 'Claim status updates',
    description: 'When the status of a claim you filed changes.',
  },
  {
    key: 'billing_reminders',
    label: 'Billing reminders',
    description: 'Upcoming payments, failed charges, and invoices.',
  },
  {
    key: 'product_announcements',
    label: 'Product announcements',
    description: 'New features and updates from Corgi.',
  },
];

function Toggle({
  id,
  checked,
  onChange,
}: {
  id: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      id={id}
      onClick={() => onChange(!checked)}
      className={[
        'relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200',
        'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none',
        'cursor-pointer',
        checked ? 'bg-primary' : 'bg-border',
      ].join(' ')}
    >
      <span
        className={[
          'pointer-events-none block h-4 w-4 rounded-full bg-white shadow transition-transform duration-200',
          checked ? 'translate-x-4' : 'translate-x-0',
        ].join(' ')}
      />
    </button>
  );
}

export default function NotificationsSettingsPage() {
  usePageTitle('Notification Settings');

  const [prefs, setPrefs] = useState<NotificationPrefs>(DEFAULT_PREFS);
  const [saved, setSaved] = useState(false);

  // Load from localStorage
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        setPrefs({ ...DEFAULT_PREFS, ...JSON.parse(raw) });
      }
    } catch {
      // ignore parse errors
    }
  }, []);

  function handleToggle(key: keyof NotificationPrefs, value: boolean) {
    const next = { ...prefs, [key]: value };
    setPrefs(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore storage errors
    }
    setSaved(true);
    const t = setTimeout(() => setSaved(false), 2000);
    return () => clearTimeout(t);
  }

  return (
    <section className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-heading">Notifications</h2>
          <p className="text-[13px] text-muted mt-0.5">
            Choose which emails you want to receive from Corgi.
          </p>
        </div>
        {saved && (
          <span className="text-[11px] font-medium text-success shrink-0 mt-1 animate-enter">
            Saved
          </span>
        )}
      </div>

      <div className="bg-surface border border-border rounded-2xl overflow-hidden">
        {PREF_LABELS.map(({ key, label, description }, i) => (
          <div
            key={key}
            className={[
              'flex items-center justify-between gap-4 px-5 py-4',
              i < PREF_LABELS.length - 1 ? 'border-b border-border' : '',
            ].join(' ')}
          >
            <label htmlFor={`notif_${key}`} className="flex flex-col gap-0.5 cursor-pointer flex-1 min-w-0">
              <span className="text-sm font-medium text-heading">{label}</span>
              <span className="text-[12px] text-muted leading-[1.4]">{description}</span>
            </label>
            <Toggle
              id={`notif_${key}`}
              checked={prefs[key]}
              onChange={(v) => handleToggle(key, v)}
            />
          </div>
        ))}
      </div>

      <p className="text-[11px] text-muted">
        Preferences are stored locally. Backend sync coming soon.
      </p>
    </section>
  );
}
