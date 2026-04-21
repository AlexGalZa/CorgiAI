'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { usePageTitle } from '@/hooks/use-page-title';
import { usePolicies } from '@/hooks/use-policies';
import { useCancelStore } from '@/stores/use-cancel-store';
import { DatePicker } from '@/components/ui/date-picker';
import { BtnPrimary, BtnSecondary } from '@/components/ui/button';
import { apiFetch } from '@/lib/api';
import { useAppStore } from '@/stores/use-app-store';

function todayYMD(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export default function CancelEffectiveDatePage() {
  usePageTitle('Cancel Policy — Effective Date');
  const router = useRouter();
  const { data: policies } = usePolicies();
  const { showToast } = useAppStore();

  const {
    formData,
    updateFormData,
    markStepCompleted,
    setSubmitStatus,
    setSubmitError,
    submitStatus,
    submitError,
  } = useCancelStore();

  const [submitting, setSubmitting] = useState(false);

  const activePolicy = useMemo(
    () => policies?.find((p) => p.id === formData.policy_id) ?? null,
    [policies, formData.policy_id],
  );

  // Guard: prior steps complete
  useEffect(() => {
    if (!formData.reason) {
      router.replace('/cancel/confirm');
    } else if (!formData.acknowledged_alternatives) {
      router.replace('/cancel/alternatives');
    }
  }, [formData.reason, formData.acknowledged_alternatives, router]);

  const minDate = todayYMD();
  const maxDate = activePolicy?.expiration_date ?? undefined;

  const canSubmit =
    !!formData.effective_date &&
    formData.effective_date >= minDate &&
    (!maxDate || formData.effective_date <= maxDate);

  const handleSubmit = async () => {
    if (!canSubmit || !formData.policy_id) return;
    setSubmitting(true);
    setSubmitStatus('submitting');
    setSubmitError(null);
    try {
      await apiFetch(`/api/v1/policies/${formData.policy_id}/cancel`, {
        method: 'POST',
        body: {
          effective_date: formData.effective_date,
          reason: formData.reason,
          reason_text: formData.reason_text,
        },
      });
      setSubmitStatus('success');
      markStepCompleted('effective-date');
      router.push('/cancel/success');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to submit cancellation';
      setSubmitStatus('error');
      setSubmitError(msg);
      showToast(msg, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleBack = () => {
    router.push('/cancel/alternatives');
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="bg-surface border border-border rounded-2xl p-6 flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-heading text-xl font-medium text-heading">
            When should coverage end?
          </h2>
          <p className="text-sm text-muted">
            Pick an effective date for the cancellation. It can&apos;t be in the past
            {activePolicy?.expiration_date
              ? `, and can't be later than your expiration date (${activePolicy.expiration_date}).`
              : '.'}
          </p>
        </div>

        <div className="flex flex-col gap-2 max-w-sm">
          <label className="text-sm font-medium text-heading">Cancellation effective date</label>
          <DatePicker
            value={formData.effective_date}
            onChange={(v) => updateFormData({ effective_date: v })}
            min={minDate}
            max={maxDate}
            placeholder="Select a date"
          />
        </div>

        <div className="text-xs text-muted bg-bg rounded-lg p-3">
          <strong className="text-heading">Note:</strong> Your Stripe subscription will be set to
          cancel at this date. Coverage remains active up to and including the effective date,
          and you&apos;ll receive a confirmation email once the cancellation is processed.
        </div>

        {submitStatus === 'error' && (
          <div className="text-xs text-danger bg-danger/10 rounded-lg p-3">
            {submitError ?? 'Something went wrong. Please try again.'}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between gap-3">
        <BtnSecondary onClick={handleBack} disabled={submitting}>
          Back
        </BtnSecondary>
        <BtnPrimary disabled={!canSubmit || submitting} onClick={handleSubmit}>
          {submitting ? 'Submitting…' : 'Confirm cancellation'}
        </BtnPrimary>
      </div>
    </div>
  );
}
