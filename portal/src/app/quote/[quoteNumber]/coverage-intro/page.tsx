'use client';

import { useParams, useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { QuoteFormLayout } from '@/components/quote/QuoteFormLayout';
import { FormNavButtons } from '@/components/quote/FormNavButtons';
import { TrudyPanel } from '@/components/trudy/TrudyPanel';
import { useQuoteStore } from '@/stores/use-quote-store';
import { useSaveQuoteStep } from '@/hooks/use-quote';
import { buildStepPath, getNextStep, getPrevStep, type StepId } from '@/lib/quote-flow';

export default function CoverageIntroPage() {
  const params = useParams<{ quoteNumber: string }>();
  const quoteNumber = params?.quoteNumber ?? '';
  const router = useRouter();
  const { formData, markStepCompleted, setCompletedSteps } = useQuoteStore();
  const { mutateAsync: saveStep, isPending } = useSaveQuoteStep(quoteNumber);
  const { setValue } = useForm();

  const handleNext = async () => {
    const result = await saveStep({ step_id: 'coverage-intro', data: {} });
    markStepCompleted('coverage-intro');
    if (result?.completed_steps) setCompletedSteps(result.completed_steps as StepId[]);
    const next = getNextStep('coverage-intro', formData.coverages ?? []);
    if (next) router.push(buildStepPath(next, quoteNumber));
  };

  const handleBack = () => {
    const prev = getPrevStep('coverage-intro', formData.coverages ?? []);
    if (prev) router.push(buildStepPath(prev, quoteNumber));
  };

  return (
    <div className="fixed inset-0 overflow-hidden bg-bg flex">
      <div className="flex-1 overflow-y-auto p-6 lg:p-10">
        <QuoteFormLayout
          title="Coverage questions"
          description="Next, we have a few questions specific to each coverage you've selected. These help us provide you with the most accurate quote."
        >
          <div className="mt-4 space-y-3">
            {(formData.coverages ?? []).map((c) => (
              <div key={c} className="flex items-center gap-2 text-sm text-body">
                <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                {c.split('-').map((w) => w[0].toUpperCase() + w.slice(1)).join(' ')}
              </div>
            ))}
          </div>
          <div className="mt-8">
            <FormNavButtons
              onBack={handleBack}
              onNext={handleNext}
              nextType="button"
              loading={isPending}
              nextLabel="Start questions"
            />
          </div>
        </QuoteFormLayout>
      </div>
      <div className="hidden lg:flex w-[340px] flex-col border-l border-border">
        <TrudyPanel step="coverage-intro" setValue={setValue} isNewQuote={false} quoteNumber={quoteNumber} />
      </div>
    </div>
  );
}
