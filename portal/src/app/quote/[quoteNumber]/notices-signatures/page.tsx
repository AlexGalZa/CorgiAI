'use client';

import { useParams, useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { QuoteFormLayout } from '@/components/quote/QuoteFormLayout';
import { FormField } from '@/components/quote/FormField';
import { FormNavButtons } from '@/components/quote/FormNavButtons';
import { TrudyPanel } from '@/components/trudy/TrudyPanel';
import { Input } from '@/components/ui/input';
import { useQuoteStore } from '@/stores/use-quote-store';
import { useSaveQuoteStep } from '@/hooks/use-quote';
import { buildStepPath, getNextStep, getPrevStep, type StepId } from '@/lib/quote-flow';

interface NoticesSignaturesValues {
  applicant_name: string;
  agreed_to_terms: boolean;
}

export default function NoticesSignaturesPage() {
  const params = useParams<{ quoteNumber: string }>();
  const quoteNumber = params?.quoteNumber ?? '';
  const router = useRouter();
  const { formData, updateFormData, markStepCompleted, setCompletedSteps } = useQuoteStore();
  const { mutateAsync: saveStep, isPending } = useSaveQuoteStep(quoteNumber);
  const stepId: StepId = 'notices-signatures';

  const existing = formData.notices_signatures;
  const defaultApplicantName =
    existing?.applicant_name ??
    [formData.first_name, formData.last_name].filter(Boolean).join(' ') ??
    '';

  const { register, handleSubmit, setValue, formState: { errors } } = useForm<NoticesSignaturesValues>({
    defaultValues: {
      applicant_name: defaultApplicantName,
      agreed_to_terms: existing?.agreed_to_terms ?? false,
    },
  });

  const onSubmit = async (values: NoticesSignaturesValues) => {
    const result = await saveStep({ step_id: stepId, data: values as unknown as Record<string, unknown> });
    updateFormData({
      notices_signatures: {
        agreed_to_terms: true,
        applicant_name: values.applicant_name,
      },
    });
    markStepCompleted(stepId);
    if (result?.completed_steps) setCompletedSteps(result.completed_steps as StepId[]);
    const next = getNextStep(stepId, formData.coverages ?? []);
    if (next) router.push(buildStepPath(next, quoteNumber));
  };

  const handleBack = () => {
    const prev = getPrevStep(stepId, formData.coverages ?? []);
    if (prev) router.push(buildStepPath(prev, quoteNumber));
  };

  return (
    <div className="fixed inset-0 overflow-hidden bg-bg flex">
      <div className="flex-1 overflow-y-auto p-6 lg:p-10">
        <QuoteFormLayout
          title="Notices & signatures"
          description="One last step — please review the notices below and sign to confirm your application."
        >
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div className="rounded-xl border border-border bg-surface p-4 text-[12px] leading-[1.6] text-body space-y-2 max-h-60 overflow-y-auto">
              <p className="font-semibold text-heading">Applicant representations</p>
              <p>
                By signing below, you represent that the information provided in this application is true and
                complete to the best of your knowledge. You understand that any material misrepresentation or
                omission may void coverage or void the policy.
              </p>
              <p>
                You authorize Corgi Insurance and its underwriting partners to verify the information provided
                and to obtain additional information as needed, including loss history and public records, to
                evaluate this application.
              </p>
              <p>
                No coverage is bound or in force until a policy is issued and the first premium is paid. This
                application does not constitute an offer of insurance.
              </p>
            </div>

            <FormField label="Full legal name of applicant" error={errors.applicant_name?.message} required>
              <Input
                placeholder="Jane A. Doe"
                autoComplete="name"
                {...register('applicant_name', { required: 'Please enter your full name' })}
                error={!!errors.applicant_name}
              />
            </FormField>

            <label className="flex items-start gap-3 p-3 border border-border rounded-xl cursor-pointer hover:bg-surface/50 transition-colors">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 rounded border-border accent-primary"
                {...register('agreed_to_terms', { required: 'You must agree to continue' })}
              />
              <span className="text-sm text-heading">
                I have read and agree to the representations above and to Corgi&apos;s{' '}
                <a href="/terms" className="text-primary underline" target="_blank" rel="noreferrer">Terms of Service</a>{' '}
                and{' '}
                <a href="/privacy" className="text-primary underline" target="_blank" rel="noreferrer">Privacy Policy</a>.
              </span>
            </label>
            {errors.agreed_to_terms && (
              <p className="text-[11px] text-danger">{errors.agreed_to_terms.message}</p>
            )}

            <FormNavButtons onBack={handleBack} loading={isPending} nextLabel="Review quote" />
          </form>
        </QuoteFormLayout>
      </div>
      <div className="hidden lg:flex w-[340px] flex-col border-l border-border">
        <TrudyPanel step="notices-signatures" setValue={setValue} isNewQuote={false} quoteNumber={quoteNumber} />
      </div>
    </div>
  );
}
