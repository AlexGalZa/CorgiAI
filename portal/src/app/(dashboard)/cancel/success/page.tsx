'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { usePageTitle } from '@/hooks/use-page-title';
import { useCancelStore } from '@/stores/use-cancel-store';
import { BtnPrimary, BtnSecondary } from '@/components/ui/button';

export default function CancelSuccessPage() {
  usePageTitle('Cancellation Submitted');
  const router = useRouter();
  const { formData, reset } = useCancelStore();

  // Guard: must have completed prior steps
  useEffect(() => {
    if (!formData.effective_date || !formData.policy_id) {
      router.replace('/');
    }
  }, [formData.effective_date, formData.policy_id, router]);

  const handleDone = () => {
    reset();
    router.push('/');
  };

  const handleBilling = () => {
    reset();
    router.push('/billing');
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="bg-surface border border-border rounded-2xl p-8 flex flex-col items-center text-center gap-4">
        <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor" className="text-primary"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M20 6 9 17l-5-5" />
          </svg>
        </div>

        <div className="flex flex-col gap-2 max-w-md">
          <h2 className="font-heading text-2xl font-medium text-heading">
            Cancellation submitted
          </h2>
          <p className="text-sm text-muted">
            Your policy
            {formData.policy_number ? (
              <>
                {' '}
                <strong className="text-heading">#{formData.policy_number}</strong>
              </>
            ) : null}{' '}
            is set to cancel on{' '}
            <strong className="text-heading">{formData.effective_date}</strong>. Coverage remains
            active through that date.
          </p>
        </div>

        <div className="bg-bg rounded-lg p-4 w-full max-w-md text-left text-sm text-body flex flex-col gap-2">
          <p>
            <strong className="text-heading">What happens next:</strong>
          </p>
          <ul className="list-disc pl-5 flex flex-col gap-1 text-muted">
            <li>
              We&apos;ve emailed you a cancellation confirmation with the effective date and final
              billing summary.
            </li>
            <li>Your Stripe subscription has been scheduled to cancel at the period end.</li>
            <li>
              Status shown as <em>Pending cancellation</em> until the effective date; then it
              switches to <em>Cancelled</em>.
            </li>
            <li>
              Changed your mind? Reply to the confirmation email within 24 hours and we&apos;ll
              reverse it.
            </li>
          </ul>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3">
        <BtnSecondary onClick={handleBilling}>View billing</BtnSecondary>
        <BtnPrimary onClick={handleDone}>Back to dashboard</BtnPrimary>
      </div>
    </div>
  );
}
