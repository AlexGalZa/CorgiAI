'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { usePageTitle } from '@/hooks/use-page-title';
import { usePolicies } from '@/hooks/use-policies';
import { useCancelStore, type CancelReason } from '@/stores/use-cancel-store';
import { CustomSelect } from '@/components/ui/custom-select';
import { BtnPrimary, BtnSecondary } from '@/components/ui/button';
import { Textarea } from '@/components/ui/input';

const REASON_OPTIONS: { value: CancelReason; label: string }[] = [
  { value: 'too_expensive', label: 'Too expensive' },
  { value: 'not_using', label: 'Not using the coverage' },
  { value: 'switching_carrier', label: 'Switching to another carrier' },
  { value: 'business_closed', label: 'Business closed or paused' },
  { value: 'coverage_not_needed', label: 'Coverage no longer needed' },
  { value: 'other', label: 'Other' },
];

export default function CancelConfirmPage() {
  usePageTitle('Cancel Policy');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: policies } = usePolicies();

  const { formData, updateFormData, markStepCompleted, setPolicy, reset } = useCancelStore();

  // Seed policy from query params on initial mount if absent
  useEffect(() => {
    const policyIdParam = searchParams?.get('policy_id');
    if (policyIdParam && !formData.policy_id && policies && policies.length > 0) {
      const pid = Number(policyIdParam);
      const match = policies.find((p) => p.id === pid);
      if (match) setPolicy(match.id, match.policy_number);
    } else if (!formData.policy_id && policies && policies.length > 0) {
      // Default to first active policy
      const firstActive = policies.find((p) => p.status === 'active') ?? policies[0];
      if (firstActive) setPolicy(firstActive.id, firstActive.policy_number);
    }
  }, [searchParams, policies, formData.policy_id, setPolicy]);

  const canContinue = !!formData.reason && (formData.reason !== 'other' || formData.reason_text.trim().length > 0);

  const handleContinue = () => {
    if (!canContinue) return;
    markStepCompleted('confirm');
    router.push('/cancel/alternatives');
  };

  const handleCancel = () => {
    reset();
    router.push('/');
  };

  const activePolicy = policies?.find((p) => p.id === formData.policy_id);

  return (
    <div className="flex flex-col gap-6">
      <div className="bg-surface border border-border rounded-2xl p-6 flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-heading text-xl font-medium text-heading">Confirm cancellation</h2>
          <p className="text-sm text-muted">
            Cancelling{activePolicy ? ` policy #${activePolicy.policy_number}` : ''} will stop
            your coverage at the effective date you choose. Please tell us why you&apos;re leaving.
          </p>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-heading">Reason for cancelling</label>
          <CustomSelect
            value={formData.reason}
            onChange={(v) => updateFormData({ reason: v as CancelReason })}
            options={REASON_OPTIONS}
            placeholder="Select a reason"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="reason_text" className="text-sm font-medium text-heading">
            Additional details {formData.reason === 'other' && <span className="text-danger">*</span>}
          </label>
          <Textarea
            id="reason_text"
            value={formData.reason_text}
            onChange={(e) => updateFormData({ reason_text: e.target.value })}
            placeholder="Tell us more so we can improve (optional)"
            rows={4}
          />
        </div>
      </div>

      <div className="flex items-center justify-between gap-3">
        <BtnSecondary onClick={handleCancel}>Never mind, keep my policy</BtnSecondary>
        <BtnPrimary disabled={!canContinue} onClick={handleContinue}>
          Continue
        </BtnPrimary>
      </div>
    </div>
  );
}
