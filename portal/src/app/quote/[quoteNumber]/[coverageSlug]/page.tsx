'use client';

import { useParams, useRouter, notFound } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { QuoteFormLayout } from '@/components/quote/QuoteFormLayout';
import { FormField } from '@/components/quote/FormField';
import { FormNavButtons } from '@/components/quote/FormNavButtons';
import { TrudyPanel } from '@/components/trudy/TrudyPanel';
import { Input, Select } from '@/components/ui/input';
import { useQuoteStore } from '@/stores/use-quote-store';
import { useSaveQuoteStep } from '@/hooks/use-quote';
import {
  buildStepPath,
  getNextStep,
  getPrevStep,
  getStepBySlug,
  type StepId,
} from '@/lib/quote-flow';

interface CoverageQuestion {
  field: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'checkbox';
  required?: boolean;
  options?: string[];
  helper?: string;
}

interface CoverageConfig {
  title: string;
  description: string;
  questions: CoverageQuestion[];
}

const COVERAGE_QUESTIONS: Record<string, CoverageConfig> = {
  'directors-and-officers': {
    title: 'Directors & Officers',
    description: 'Help us understand your governance structure.',
    questions: [
      { field: 'num_directors', label: 'Total directors and officers', type: 'number', required: true },
      { field: 'has_do_claims', label: 'Any D&O claims in the past 5 years?', type: 'select', options: ['No', 'Yes'] },
      { field: 'desired_limit', label: 'Desired coverage limit ($)', type: 'number' },
    ],
  },
  'technology-errors-omissions': {
    title: 'Tech E&O',
    description: 'A few questions about your technology products and services.',
    questions: [
      { field: 'tech_revenue', label: 'Annual technology revenue ($)', type: 'number', required: true },
      { field: 'has_eo_claims', label: 'Any E&O claims in the past 5 years?', type: 'select', options: ['No', 'Yes'] },
      { field: 'desired_limit', label: 'Desired coverage limit ($)', type: 'number' },
    ],
  },
  'cyber-liability': {
    title: 'Cyber Liability',
    description: 'Tell us about your data security practices.',
    questions: [
      { field: 'stores_pii', label: 'Do you store sensitive customer data (PII)?', type: 'select', options: ['No', 'Yes'], required: true },
      { field: 'prior_incidents', label: 'Have you experienced a data breach?', type: 'select', options: ['No', 'Yes'] },
      { field: 'desired_limit', label: 'Desired coverage limit ($)', type: 'number' },
    ],
  },
  'commercial-general-liability': {
    title: 'Commercial General Liability',
    description: 'Help us understand your business operations.',
    questions: [
      { field: 'has_physical_location', label: 'Do customers visit your location?', type: 'select', options: ['No', 'Yes'], required: true },
      { field: 'has_cgl_claims', label: 'Any CGL claims in the past 5 years?', type: 'select', options: ['No', 'Yes'] },
      { field: 'desired_limit', label: 'Desired coverage limit ($)', type: 'number' },
    ],
  },
  'fiduciary-liability': {
    title: 'Fiduciary Liability',
    description: 'Questions about your employee benefit plans.',
    questions: [
      { field: 'plan_assets', label: 'Total plan assets under management ($)', type: 'number', required: true },
      { field: 'has_fid_claims', label: 'Any fiduciary claims in the past 5 years?', type: 'select', options: ['No', 'Yes'] },
      { field: 'desired_limit', label: 'Desired coverage limit ($)', type: 'number' },
    ],
  },
  'hired-non-owned-auto': {
    title: 'Hired & Non-Owned Auto',
    description: 'Questions about vehicle use for business.',
    questions: [
      { field: 'employees_drive_for_work', label: 'Do employees drive personal vehicles for work?', type: 'select', options: ['No', 'Yes'], required: true },
      { field: 'annual_miles', label: 'Estimated annual business miles', type: 'number' },
      { field: 'desired_limit', label: 'Desired coverage limit ($)', type: 'number' },
    ],
  },
  'media-liability': {
    title: 'Media Liability',
    description: 'Questions about your media and content production.',
    questions: [
      { field: 'media_type', label: 'Type of content produced', type: 'select', options: ['Digital', 'Print', 'Broadcast', 'Social Media', 'Multiple'], required: true },
      { field: 'has_media_claims', label: 'Any media-related claims in the past 5 years?', type: 'select', options: ['No', 'Yes'] },
      { field: 'desired_limit', label: 'Desired coverage limit ($)', type: 'number' },
    ],
  },
  'employment-practices-liability': {
    title: 'Employment Practices Liability',
    description: 'Questions about your employment practices.',
    questions: [
      { field: 'prior_incidents', label: 'Any EPL claims in the past 5 years?', type: 'select', options: ['No', 'Yes'], required: true },
      { field: 'has_hr_policies', label: 'Do you have written HR policies?', type: 'select', options: ['No', 'Yes'] },
      { field: 'desired_limit', label: 'Desired coverage limit ($)', type: 'number' },
    ],
  },
};

export default function CoverageQuestionnairePage() {
  const params = useParams<{ quoteNumber: string; coverageSlug: string }>();
  const quoteNumber = params?.quoteNumber ?? '';
  const slug = params?.coverageSlug ?? '';
  const router = useRouter();

  const stepBySlug = getStepBySlug(slug);
  const config = COVERAGE_QUESTIONS[slug];
  if (!stepBySlug || !config) {
    notFound();
  }

  return (
    <CoverageForm
      quoteNumber={quoteNumber}
      slug={slug}
      stepId={stepBySlug.id}
      config={config}
      router={router}
    />
  );
}

interface CoverageFormProps {
  quoteNumber: string;
  slug: string;
  stepId: StepId;
  config: CoverageConfig;
  router: ReturnType<typeof useRouter>;
}

function CoverageForm({ quoteNumber, slug, stepId, config, router }: CoverageFormProps) {
  const { formData, updateFormData, markStepCompleted, setCompletedSteps } = useQuoteStore();
  const { mutateAsync: saveStep, isPending } = useSaveQuoteStep(quoteNumber);

  const existingAnswers = (formData.coverage_answers?.[slug] ?? {}) as Record<string, unknown>;

  const defaultValues: Record<string, unknown> = {};
  for (const q of config.questions) {
    defaultValues[q.field] = existingAnswers[q.field] ?? (q.type === 'checkbox' ? false : '');
  }

  const { register, handleSubmit, setValue, formState: { errors } } = useForm<Record<string, unknown>>({
    defaultValues,
  });

  const onSubmit = async (values: Record<string, unknown>) => {
    const result = await saveStep({ step_id: stepId, data: values });
    updateFormData({
      coverage_answers: {
        ...(formData.coverage_answers ?? {}),
        [slug]: values,
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
        <QuoteFormLayout title={config.title} description={config.description}>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {config.questions.map((q) => {
              const err = errors[q.field];
              const errorMessage = err && typeof err === 'object' && 'message' in err
                ? (err as { message?: string }).message
                : undefined;

              if (q.type === 'checkbox') {
                return (
                  <label key={q.field} className="flex items-start gap-3 p-3 border border-border rounded-xl cursor-pointer hover:bg-surface/50 transition-colors">
                    <input
                      type="checkbox"
                      className="mt-0.5 h-4 w-4 rounded border-border accent-primary"
                      {...register(q.field, { required: q.required ? `${q.label} is required` : false })}
                    />
                    <span className="text-sm font-semibold text-heading">{q.label}</span>
                  </label>
                );
              }

              if (q.type === 'select') {
                return (
                  <FormField key={q.field} label={q.label} error={errorMessage} required={q.required} helper={q.helper}>
                    <Select
                      {...register(q.field, { required: q.required ? `${q.label} is required` : false })}
                    >
                      <option value="">Select...</option>
                      {(q.options ?? []).map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </Select>
                  </FormField>
                );
              }

              return (
                <FormField key={q.field} label={q.label} error={errorMessage} required={q.required} helper={q.helper}>
                  <Input
                    type={q.type === 'number' ? 'number' : 'text'}
                    {...register(q.field, { required: q.required ? `${q.label} is required` : false })}
                    error={!!err}
                  />
                </FormField>
              );
            })}

            <FormNavButtons onBack={handleBack} loading={isPending} />
          </form>
        </QuoteFormLayout>
      </div>
      <div className="hidden lg:flex w-[340px] flex-col border-l border-border">
        <TrudyPanel step={slug} setValue={setValue} isNewQuote={false} quoteNumber={quoteNumber} />
      </div>
    </div>
  );
}
