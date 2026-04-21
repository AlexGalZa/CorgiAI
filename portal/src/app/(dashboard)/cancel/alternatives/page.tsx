'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { usePageTitle } from '@/hooks/use-page-title';
import { useCancelStore } from '@/stores/use-cancel-store';
import { BtnPrimary, BtnSecondary, BtnLink } from '@/components/ui/button';

interface Alternative {
  id: string;
  title: string;
  description: string;
  badge: string;
}

const ALTERNATIVES: Alternative[] = [
  {
    id: 'pause',
    title: 'Pause your policy for up to 90 days',
    description:
      'Keep your coverage history intact while you sort things out. You won\'t be billed during the pause.',
    badge: 'Most popular',
  },
  {
    id: 'downgrade',
    title: 'Downgrade to a lighter plan',
    description:
      'Reduce your aggregate limit and monthly premium by up to 40% while keeping essential protection.',
    badge: 'Save up to 40%',
  },
  {
    id: 'talk',
    title: 'Talk to your account executive',
    description:
      'We\'ll review your coverage together and find a better fit. Most calls resolve in 15 minutes.',
    badge: 'Free review',
  },
];

export default function CancelAlternativesPage() {
  usePageTitle('Cancel Policy — Alternatives');
  const router = useRouter();
  const { formData, markStepCompleted, updateFormData } = useCancelStore();

  // Guard: make sure step 1 has been completed
  useEffect(() => {
    if (!formData.reason) {
      router.replace('/cancel/confirm');
    }
  }, [formData.reason, router]);

  const handleAlternative = (altId: string) => {
    // Stubs — in a real flow these would open a pause/downgrade/scheduling modal.
    // For 5.1 they're informational: clicking dismisses this step.
    markStepCompleted('alternatives');
    updateFormData({ acknowledged_alternatives: true });
    // Go back home; user effectively cancels the cancellation.
    router.push(`/?saved_via=${altId}`);
  };

  const handleContinue = () => {
    updateFormData({ acknowledged_alternatives: true });
    markStepCompleted('alternatives');
    router.push('/cancel/effective-date');
  };

  const handleBack = () => {
    router.push('/cancel/confirm');
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="bg-surface border border-border rounded-2xl p-6 flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-heading text-xl font-medium text-heading">
            Before you cancel — have you considered these?
          </h2>
          <p className="text-sm text-muted">
            You can resolve most concerns without losing your coverage history or your
            claims-made retroactive date. Here are a few options.
          </p>
        </div>

        <div className="flex flex-col gap-3">
          {ALTERNATIVES.map((alt) => (
            <button
              key={alt.id}
              type="button"
              onClick={() => handleAlternative(alt.id)}
              className="text-left bg-white border border-border rounded-xl p-4 flex items-start gap-4 cursor-pointer hover:border-primary transition-colors"
            >
              <div className="flex-1 flex flex-col gap-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-heading text-base font-medium text-heading">
                    {alt.title}
                  </span>
                  <span className="text-[11px] font-semibold text-primary bg-primary/10 rounded-full px-2 py-0.5">
                    {alt.badge}
                  </span>
                </div>
                <span className="text-sm text-muted">{alt.description}</span>
              </div>
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="shrink-0 text-muted mt-1"
              >
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between gap-3">
        <BtnSecondary onClick={handleBack}>Back</BtnSecondary>
        <div className="flex items-center gap-4">
          <BtnLink onClick={handleContinue}>No thanks, keep cancelling</BtnLink>
          <BtnPrimary onClick={() => handleAlternative('talk')}>Talk to my AE</BtnPrimary>
        </div>
      </div>
    </div>
  );
}
