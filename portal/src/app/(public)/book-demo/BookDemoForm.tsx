'use client';

import { useState } from 'react';
import type { FormEvent } from 'react';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function BookDemoForm() {
  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [preferredTime, setPreferredTime] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<
    { ok: true; message: string } | { ok: false; message: string } | null
  >(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/demos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: customerName,
          customer_email: customerEmail,
          preferred_time: new Date(preferredTime).toISOString(),
        }),
      });
      const body = await res.json();
      if (res.ok && body.success) {
        setResult({ ok: true, message: body.message || 'Demo scheduled' });
        setCustomerName('');
        setCustomerEmail('');
        setPreferredTime('');
      } else {
        setResult({
          ok: false,
          message: body.message || 'Unable to schedule demo',
        });
      }
    } catch {
      setResult({ ok: false, message: 'Network error. Please try again.' });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-5 bg-surface border border-border rounded-2xl p-6"
    >
      <div className="flex flex-col gap-2">
        <label
          htmlFor="customer_name"
          className="text-sm font-medium text-heading"
        >
          Full name
        </label>
        <input
          id="customer_name"
          type="text"
          required
          value={customerName}
          onChange={(e) => setCustomerName(e.target.value)}
          className="border border-border rounded-lg px-3 py-2 text-sm"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label
          htmlFor="customer_email"
          className="text-sm font-medium text-heading"
        >
          Work email
        </label>
        <input
          id="customer_email"
          type="email"
          required
          value={customerEmail}
          onChange={(e) => setCustomerEmail(e.target.value)}
          className="border border-border rounded-lg px-3 py-2 text-sm"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label
          htmlFor="preferred_time"
          className="text-sm font-medium text-heading"
        >
          Preferred time
        </label>
        <input
          id="preferred_time"
          type="datetime-local"
          required
          value={preferredTime}
          onChange={(e) => setPreferredTime(e.target.value)}
          className="border border-border rounded-lg px-3 py-2 text-sm"
        />
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="bg-primary text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-60"
      >
        {submitting ? 'Scheduling…' : 'Book demo'}
      </button>

      {result && (
        <div
          role="status"
          className={`text-sm ${
            result.ok ? 'text-success' : 'text-danger'
          }`}
        >
          {result.message}
        </div>
      )}
    </form>
  );
}
