'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { CoverageSelector } from '@/components/quote/CoverageSelector';
import { QuoteFormLayout } from '@/components/quote/QuoteFormLayout';
import { FormNavButtons } from '@/components/quote/FormNavButtons';
import { TrudyPanel } from '@/components/trudy/TrudyPanel';
import { useQuoteStore } from '@/stores/use-quote-store';
import { useSaveQuoteStep } from '@/hooks/use-quote';
import { buildStepPath, getNextStep, type AllCoverageType, type StepId } from '@/lib/quote-flow';

export default function ProductsPage() {
  const params = useParams<{ quoteNumber: string }>();
  const quoteNumber = params?.quoteNumber ?? '';
  const router = useRouter();
  const { formData, updateFormData, markStepCompleted, setCompletedSteps } = useQuoteStore();
  const { mutateAsync: saveStep, isPending } = useSaveQuoteStep(quoteNumber);
  const { setValue } = useForm();
  const [selectedCoverages, setSelectedCoverages] = useState<AllCoverageType[]>(
    formData.coverages ?? []
  );

  const handleToggle = (id: AllCoverageType) => {
    setSelectedCoverages((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const handleNext = async () => {
    const result = await saveStep({
      step_id: 'products',
      data: { coverages: selectedCoverages },
    });
    updateFormData({ coverages: selectedCoverages });
    markStepCompleted('products');
    if (result?.completed_steps) {
      setCompletedSteps(result.completed_steps as StepId[]);
    }
    const next = getNextStep('products', selectedCoverages);
    if (next) router.push(buildStepPath(next, quoteNumber));
  };

  return (
    <div className="fixed inset-0 overflow-hidden bg-bg flex">
      <div className="flex-1 overflow-y-auto p-6 lg:p-10">
        <QuoteFormLayout
          title="Choose your coverage"
          description="Select the policies you'd like to include in your quote. You can adjust later."
        >
          <CoverageSelector selectedCoverages={selectedCoverages} onToggle={handleToggle} />
          <div className="mt-8">
            <FormNavButtons
              onBack={() => router.push('/quote/get-started')}
              onNext={handleNext}
              nextType="button"
              loading={isPending}
              disableNext={selectedCoverages.length === 0}
              nextLabel="Continue"
            />
          </div>
        </QuoteFormLayout>
      </div>
      <div className="hidden lg:flex w-[340px] flex-col border-l border-border">
        <TrudyPanel step="products" setValue={setValue} isNewQuote={false} />
      </div>
    </div>
  );
}
