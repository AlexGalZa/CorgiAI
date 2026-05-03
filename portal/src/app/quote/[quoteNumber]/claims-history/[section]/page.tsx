'use client';

import { useParams, useRouter, notFound } from 'next/navigation';
import { useForm, type UseFormSetValue, type FieldValues } from 'react-hook-form';
import { QuoteFormLayout } from '@/components/quote/QuoteFormLayout';
import { FormField } from '@/components/quote/FormField';
import { FormNavButtons } from '@/components/quote/FormNavButtons';
import { TrudyPanel } from '@/components/trudy/TrudyPanel';
import { Select, Textarea } from '@/components/ui/input';
import { useQuoteStore } from '@/stores/use-quote-store';
import { useSaveQuoteStep } from '@/hooks/use-quote';
import { buildStepPath, getNextStep, getPrevStep, type StepId } from '@/lib/quote-flow';

type ClaimsSection = 'loss-history' | 'insurance-history';
const SECTIONS: readonly ClaimsSection[] = ['loss-history', 'insurance-history'];

export default function ClaimsHistorySectionPage() {
  const params = useParams<{ quoteNumber: string; section: string }>();
  const section = params?.section as ClaimsSection | undefined;
  if (!section || !SECTIONS.includes(section as ClaimsSection)) {
    notFound();
  }

  switch (section) {
    case 'loss-history':
      return <LossHistoryForm />;
    case 'insurance-history':
      return <InsuranceHistoryForm />;
    default:
      notFound();
  }
}

interface ShellProps {
  title: string;
  description: string;
  setValue: UseFormSetValue<FieldValues>;
  quoteNumber: string;
  children: React.ReactNode;
}

function Shell({ title, description, setValue, quoteNumber, children }: ShellProps) {
  return (
    <div className="fixed inset-0 overflow-hidden bg-bg flex">
      <div className="flex-1 overflow-y-auto p-6 lg:p-10">
        <QuoteFormLayout title={title} description={description}>
          {children}
        </QuoteFormLayout>
      </div>
      <div className="hidden lg:flex w-[340px] flex-col border-l border-border">
        <TrudyPanel step="claims-history" setValue={setValue} isNewQuote={false} quoteNumber={quoteNumber} />
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// Loss History
// ────────────────────────────────────────────────────────────────

interface LossHistoryValues {
  has_past_claims: string;
  claim_details?: string;
  has_known_circumstances: string;
  known_circumstances_details?: string;
}

function LossHistoryForm() {
  const params = useParams<{ quoteNumber: string }>();
  const quoteNumber = params?.quoteNumber ?? '';
  const router = useRouter();
  const { formData, updateFormData, markStepCompleted, setCompletedSteps } = useQuoteStore();
  const { mutateAsync: saveStep, isPending } = useSaveQuoteStep(quoteNumber);
  const stepId: StepId = 'loss-history';

  const existing = formData.claims_history?.loss_history;
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<LossHistoryValues>({
    defaultValues: {
      has_past_claims: existing?.has_past_claims === true ? 'Yes' : existing?.has_past_claims === false ? 'No' : '',
      claim_details: existing?.claim_details ?? '',
      has_known_circumstances: existing?.has_known_circumstances === true ? 'Yes' : existing?.has_known_circumstances === false ? 'No' : '',
      known_circumstances_details: existing?.known_circumstances_details ?? '',
    },
  });

  const hasPastClaims = watch('has_past_claims');
  const hasKnownCircumstances = watch('has_known_circumstances');

  const onSubmit = async (values: LossHistoryValues) => {
    const result = await saveStep({ step_id: stepId, data: values as unknown as Record<string, unknown> });
    updateFormData({
      claims_history: {
        ...formData.claims_history,
        loss_history: {
          ...formData.claims_history?.loss_history,
          has_past_claims: values.has_past_claims === 'Yes',
          claim_details: values.claim_details,
          has_known_circumstances: values.has_known_circumstances === 'Yes',
          known_circumstances_details: values.known_circumstances_details,
        },
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
    <Shell
      title="Loss history"
      description="Tell us about any past claims or known circumstances that could lead to a claim."
      setValue={setValue as unknown as UseFormSetValue<FieldValues>}
      quoteNumber={quoteNumber}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <FormField label="Have you had any claims in the past 5 years?" error={errors.has_past_claims?.message} required>
          <Select {...register('has_past_claims', { required: 'Please select an option' })}>
            <option value="">Select...</option>
            <option value="No">No</option>
            <option value="Yes">Yes</option>
          </Select>
        </FormField>

        {hasPastClaims === 'Yes' && (
          <FormField label="Claim details" error={errors.claim_details?.message} helper="Briefly describe each claim and its outcome">
            <Textarea rows={4} {...register('claim_details')} />
          </FormField>
        )}

        <FormField label="Are you aware of any circumstances that could lead to a claim?" error={errors.has_known_circumstances?.message}>
          <Select {...register('has_known_circumstances')}>
            <option value="">Select...</option>
            <option value="No">No</option>
            <option value="Yes">Yes</option>
          </Select>
        </FormField>

        {hasKnownCircumstances === 'Yes' && (
          <FormField label="Describe the circumstances" error={errors.known_circumstances_details?.message}>
            <Textarea rows={4} {...register('known_circumstances_details')} />
          </FormField>
        )}

        <FormNavButtons onBack={handleBack} loading={isPending} />
      </form>
    </Shell>
  );
}

// ────────────────────────────────────────────────────────────────
// Insurance History
// ────────────────────────────────────────────────────────────────

interface InsuranceHistoryValues {
  existing_insurance: string;
  prior_coverage_details?: string;
  has_refused_insurance: string;
}

function InsuranceHistoryForm() {
  const params = useParams<{ quoteNumber: string }>();
  const quoteNumber = params?.quoteNumber ?? '';
  const router = useRouter();
  const { formData, updateFormData, markStepCompleted, setCompletedSteps } = useQuoteStore();
  const { mutateAsync: saveStep, isPending } = useSaveQuoteStep(quoteNumber);
  const stepId: StepId = 'insurance-history';

  const existing = formData.claims_history?.insurance_history;
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<InsuranceHistoryValues>({
    defaultValues: {
      existing_insurance: existing?.has_prior_coverage === true ? 'Yes' : existing?.has_prior_coverage === false ? 'No' : '',
      prior_coverage_details: existing?.prior_coverage_details ?? '',
      has_refused_insurance: existing?.has_refused_insurance === true ? 'Yes' : existing?.has_refused_insurance === false ? 'No' : '',
    },
  });

  const existingInsurance = watch('existing_insurance');

  const onSubmit = async (values: InsuranceHistoryValues) => {
    const result = await saveStep({ step_id: stepId, data: values as unknown as Record<string, unknown> });
    updateFormData({
      claims_history: {
        ...formData.claims_history,
        insurance_history: {
          ...formData.claims_history?.insurance_history,
          has_prior_coverage: values.existing_insurance === 'Yes',
          prior_coverage_details: values.prior_coverage_details,
          has_refused_insurance: values.has_refused_insurance === 'Yes',
        },
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
    <Shell
      title="Insurance history"
      description="Let us know about your current or past business insurance."
      setValue={setValue as unknown as UseFormSetValue<FieldValues>}
      quoteNumber={quoteNumber}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <FormField label="Do you currently have this type of insurance?" error={errors.existing_insurance?.message} required>
          <Select {...register('existing_insurance', { required: 'Please select an option' })}>
            <option value="">Select...</option>
            <option value="No">No</option>
            <option value="Yes">Yes</option>
          </Select>
        </FormField>

        {existingInsurance === 'Yes' && (
          <FormField label="Prior coverage details" error={errors.prior_coverage_details?.message} helper="Carrier, policy dates, limits">
            <Textarea rows={4} {...register('prior_coverage_details')} />
          </FormField>
        )}

        <FormField label="Has any insurer ever declined or refused to renew coverage?" error={errors.has_refused_insurance?.message}>
          <Select {...register('has_refused_insurance')}>
            <option value="">Select...</option>
            <option value="No">No</option>
            <option value="Yes">Yes</option>
          </Select>
        </FormField>

        <FormNavButtons onBack={handleBack} loading={isPending} />
      </form>
    </Shell>
  );
}
