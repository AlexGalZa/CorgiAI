'use client';

import { useParams, useRouter, notFound } from 'next/navigation';
import { useForm, type UseFormSetValue, type FieldValues } from 'react-hook-form';
import { QuoteFormLayout } from '@/components/quote/QuoteFormLayout';
import { FormField } from '@/components/quote/FormField';
import { FormNavButtons } from '@/components/quote/FormNavButtons';
import { TrudyPanel } from '@/components/trudy/TrudyPanel';
import { Input, Textarea } from '@/components/ui/input';
import { useQuoteStore } from '@/stores/use-quote-store';
import { useSaveQuoteStep } from '@/hooks/use-quote';
import { buildStepPath, getNextStep, getPrevStep, type StepId } from '@/lib/quote-flow';

type CompanySection =
  | 'business-address'
  | 'organization-info'
  | 'financial-details'
  | 'structure-operations';

const SECTIONS: readonly CompanySection[] = [
  'business-address',
  'organization-info',
  'financial-details',
  'structure-operations',
];

export default function CompanySectionPage() {
  const params = useParams<{ quoteNumber: string; section: string }>();
  const section = params?.section as CompanySection | undefined;
  if (!section || !SECTIONS.includes(section as CompanySection)) {
    notFound();
  }

  switch (section) {
    case 'business-address':
      return <BusinessAddressForm />;
    case 'organization-info':
      return <OrganizationInfoForm />;
    case 'financial-details':
      return <FinancialDetailsForm />;
    case 'structure-operations':
      return <StructureOperationsForm />;
    default:
      notFound();
  }
}

// ────────────────────────────────────────────────────────────────
// Shared layout wrapper
// ────────────────────────────────────────────────────────────────

interface ShellProps {
  title: string;
  description: string;
  trudyStep: string;
  setValue: UseFormSetValue<FieldValues>;
  children: React.ReactNode;
}

function Shell({ title, description, trudyStep, setValue, children }: ShellProps) {
  return (
    <div className="fixed inset-0 overflow-hidden bg-bg flex">
      <div className="flex-1 overflow-y-auto p-6 lg:p-10">
        <QuoteFormLayout title={title} description={description}>
          {children}
        </QuoteFormLayout>
      </div>
      <div className="hidden lg:flex w-[340px] flex-col border-l border-border">
        <TrudyPanel step={trudyStep} setValue={setValue} isNewQuote={false} />
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// Business Address
// ────────────────────────────────────────────────────────────────

interface BusinessAddressValues {
  street_address: string;
  suite?: string;
  city: string;
  state: string;
  zip_code: string;
}

function BusinessAddressForm() {
  const params = useParams<{ quoteNumber: string }>();
  const quoteNumber = params?.quoteNumber ?? '';
  const router = useRouter();
  const { formData, updateFormData, markStepCompleted, setCompletedSteps } = useQuoteStore();
  const { mutateAsync: saveStep, isPending } = useSaveQuoteStep(quoteNumber);
  const stepId: StepId = 'business-address';

  const existing = formData.company_info?.business_address;
  const { register, handleSubmit, setValue, formState: { errors } } = useForm<BusinessAddressValues>({
    defaultValues: {
      street_address: existing?.street_address ?? '',
      suite: existing?.suite ?? '',
      city: existing?.city ?? '',
      state: existing?.state ?? '',
      zip_code: existing?.zip ?? '',
    },
  });

  const onSubmit = async (values: BusinessAddressValues) => {
    const result = await saveStep({ step_id: stepId, data: values as unknown as Record<string, unknown> });
    updateFormData({
      company_info: {
        ...formData.company_info,
        business_address: {
          street_address: values.street_address,
          suite: values.suite,
          city: values.city,
          state: values.state,
          zip: values.zip_code,
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
      title="Business address"
      description="Where is your business located? This helps us determine eligibility and pricing."
      trudyStep="coverage-intro"
      setValue={setValue as unknown as UseFormSetValue<FieldValues>}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <FormField label="Street address" error={errors.street_address?.message} required>
          <Input
            placeholder="123 Main St"
            autoComplete="address-line1"
            {...register('street_address', { required: 'Street address is required' })}
            error={!!errors.street_address}
          />
        </FormField>

        <FormField label="Suite / Unit" error={errors.suite?.message}>
          <Input
            placeholder="Suite 200"
            autoComplete="address-line2"
            {...register('suite')}
          />
        </FormField>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <FormField label="City" error={errors.city?.message} required>
            <Input
              placeholder="San Francisco"
              autoComplete="address-level2"
              {...register('city', { required: 'City is required' })}
              error={!!errors.city}
            />
          </FormField>
          <FormField label="State" error={errors.state?.message} required>
            <Input
              placeholder="CA"
              maxLength={2}
              autoComplete="address-level1"
              {...register('state', {
                required: 'State is required',
                minLength: { value: 2, message: 'Use 2-letter state code' },
                maxLength: { value: 2, message: 'Use 2-letter state code' },
              })}
              error={!!errors.state}
            />
          </FormField>
          <FormField label="ZIP code" error={errors.zip_code?.message} required>
            <Input
              placeholder="94103"
              autoComplete="postal-code"
              {...register('zip_code', { required: 'ZIP is required' })}
              error={!!errors.zip_code}
            />
          </FormField>
        </div>

        <FormNavButtons onBack={handleBack} loading={isPending} />
      </form>
    </Shell>
  );
}

// ────────────────────────────────────────────────────────────────
// Organization Info
// ────────────────────────────────────────────────────────────────

interface OrganizationInfoValues {
  company_name: string;
  dba_name?: string;
  ein?: string;
  business_start_date?: string;
}

function OrganizationInfoForm() {
  const params = useParams<{ quoteNumber: string }>();
  const quoteNumber = params?.quoteNumber ?? '';
  const router = useRouter();
  const { formData, updateFormData, markStepCompleted, setCompletedSteps } = useQuoteStore();
  const { mutateAsync: saveStep, isPending } = useSaveQuoteStep(quoteNumber);
  const stepId: StepId = 'organization-info';

  const existing = formData.company_info?.organization_info;
  const { register, handleSubmit, setValue, formState: { errors } } = useForm<OrganizationInfoValues>({
    defaultValues: {
      company_name: existing?.entity_legal_name ?? formData.company_name ?? '',
      dba_name: existing?.dba_name ?? '',
      ein: existing?.federal_ein ?? '',
      business_start_date: existing?.business_start_date ?? '',
    },
  });

  const onSubmit = async (values: OrganizationInfoValues) => {
    const result = await saveStep({ step_id: stepId, data: values as unknown as Record<string, unknown> });
    updateFormData({
      company_info: {
        ...formData.company_info,
        organization_info: {
          ...formData.company_info?.organization_info,
          entity_legal_name: values.company_name,
          dba_name: values.dba_name,
          federal_ein: values.ein,
          business_start_date: values.business_start_date,
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
      title="Organization details"
      description="Tell us a little more about your company."
      trudyStep="company"
      setValue={setValue as unknown as UseFormSetValue<FieldValues>}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <FormField label="Legal company name" error={errors.company_name?.message} required>
          <Input
            placeholder="Acme, Inc."
            autoComplete="organization"
            {...register('company_name', { required: 'Company name is required' })}
            error={!!errors.company_name}
          />
        </FormField>

        <FormField label="DBA / trade name" error={errors.dba_name?.message} helper="Optional — leave blank if none">
          <Input
            placeholder="Acme"
            {...register('dba_name')}
          />
        </FormField>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <FormField label="Federal EIN" error={errors.ein?.message} helper="9-digit tax ID (optional)">
            <Input
              placeholder="12-3456789"
              {...register('ein')}
            />
          </FormField>
          <FormField label="Business start date" error={errors.business_start_date?.message}>
            <Input
              type="date"
              {...register('business_start_date')}
            />
          </FormField>
        </div>

        <FormNavButtons onBack={handleBack} loading={isPending} />
      </form>
    </Shell>
  );
}

// ────────────────────────────────────────────────────────────────
// Financial Details
// ────────────────────────────────────────────────────────────────

interface FinancialDetailsValues {
  annual_revenue: number | string;
  total_employees: number | string;
  annual_payroll?: number | string;
}

function FinancialDetailsForm() {
  const params = useParams<{ quoteNumber: string }>();
  const quoteNumber = params?.quoteNumber ?? '';
  const router = useRouter();
  const { formData, updateFormData, markStepCompleted, setCompletedSteps } = useQuoteStore();
  const { mutateAsync: saveStep, isPending } = useSaveQuoteStep(quoteNumber);
  const stepId: StepId = 'financial-details';

  const existingFin = formData.company_info?.financial_details;
  const existingOrg = formData.company_info?.organization_info;
  const { register, handleSubmit, setValue, formState: { errors } } = useForm<FinancialDetailsValues>({
    defaultValues: {
      annual_revenue: existingFin?.last_12_months_revenue ?? '',
      total_employees: existingFin?.full_time_employees ?? '',
      annual_payroll: existingOrg?.estimated_payroll ?? '',
    },
  });

  const onSubmit = async (values: FinancialDetailsValues) => {
    const result = await saveStep({ step_id: stepId, data: values as unknown as Record<string, unknown> });
    const revenueNum = values.annual_revenue === '' ? undefined : Number(values.annual_revenue);
    const employeesNum = values.total_employees === '' ? undefined : Number(values.total_employees);
    const payrollNum = values.annual_payroll === '' || values.annual_payroll === undefined
      ? undefined
      : Number(values.annual_payroll);
    updateFormData({
      company_info: {
        ...formData.company_info,
        financial_details: {
          ...formData.company_info?.financial_details,
          last_12_months_revenue: revenueNum,
          full_time_employees: employeesNum,
        },
        organization_info: {
          ...formData.company_info?.organization_info,
          estimated_payroll: payrollNum,
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
      title="Financial details"
      description="We use these figures to size your coverage and calculate pricing."
      trudyStep="company"
      setValue={setValue as unknown as UseFormSetValue<FieldValues>}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <FormField label="Annual revenue (USD)" error={errors.annual_revenue?.message} required>
          <Input
            type="number"
            min="0"
            step="1000"
            placeholder="1000000"
            {...register('annual_revenue', {
              required: 'Annual revenue is required',
              valueAsNumber: false,
            })}
            error={!!errors.annual_revenue}
          />
        </FormField>

        <FormField label="Total employees" error={errors.total_employees?.message} required>
          <Input
            type="number"
            min="0"
            step="1"
            placeholder="15"
            {...register('total_employees', {
              required: 'Employee count is required',
              valueAsNumber: false,
            })}
            error={!!errors.total_employees}
          />
        </FormField>

        <FormField label="Annual payroll (USD)" error={errors.annual_payroll?.message} helper="Optional">
          <Input
            type="number"
            min="0"
            step="1000"
            placeholder="750000"
            {...register('annual_payroll', { valueAsNumber: false })}
          />
        </FormField>

        <FormNavButtons onBack={handleBack} loading={isPending} />
      </form>
    </Shell>
  );
}

// ────────────────────────────────────────────────────────────────
// Structure & Operations
// ────────────────────────────────────────────────────────────────

interface StructureOperationsValues {
  is_technology_company: boolean;
  has_subsidiaries: boolean;
  business_description?: string;
}

function StructureOperationsForm() {
  const params = useParams<{ quoteNumber: string }>();
  const quoteNumber = params?.quoteNumber ?? '';
  const router = useRouter();
  const { formData, updateFormData, markStepCompleted, setCompletedSteps } = useQuoteStore();
  const { mutateAsync: saveStep, isPending } = useSaveQuoteStep(quoteNumber);
  const stepId: StepId = 'structure-operations';

  const existing = formData.company_info?.structure_operations;
  const { register, handleSubmit, setValue, formState: { errors } } = useForm<StructureOperationsValues>({
    defaultValues: {
      is_technology_company: existing?.is_technology_company ?? false,
      has_subsidiaries: existing?.has_subsidiaries ?? false,
      business_description: existing?.business_description ?? '',
    },
  });

  const onSubmit = async (values: StructureOperationsValues) => {
    const result = await saveStep({ step_id: stepId, data: values as unknown as Record<string, unknown> });
    updateFormData({
      company_info: {
        ...formData.company_info,
        structure_operations: {
          ...formData.company_info?.structure_operations,
          is_technology_company: values.is_technology_company,
          has_subsidiaries: values.has_subsidiaries,
          business_description: values.business_description,
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
      title="Structure & operations"
      description="A few final questions about how your business is organized."
      trudyStep="company"
      setValue={setValue as unknown as UseFormSetValue<FieldValues>}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <label className="flex items-start gap-3 p-3 border border-border rounded-xl cursor-pointer hover:bg-surface/50 transition-colors">
          <input
            type="checkbox"
            className="mt-0.5 h-4 w-4 rounded border-border accent-primary"
            {...register('is_technology_company')}
          />
          <div>
            <span className="text-sm font-semibold text-heading block">We are a technology company</span>
            <span className="text-[11px] text-muted">Software, SaaS, IT services, or tech-enabled products</span>
          </div>
        </label>

        <label className="flex items-start gap-3 p-3 border border-border rounded-xl cursor-pointer hover:bg-surface/50 transition-colors">
          <input
            type="checkbox"
            className="mt-0.5 h-4 w-4 rounded border-border accent-primary"
            {...register('has_subsidiaries')}
          />
          <div>
            <span className="text-sm font-semibold text-heading block">We have subsidiaries</span>
            <span className="text-[11px] text-muted">Any other legal entities owned by this company</span>
          </div>
        </label>

        <FormField label="Business description" error={errors.business_description?.message} helper="Briefly describe what your business does">
          <Textarea
            placeholder="We build cloud-based project management software for construction teams..."
            rows={4}
            {...register('business_description')}
          />
        </FormField>

        <FormNavButtons onBack={handleBack} loading={isPending} />
      </form>
    </Shell>
  );
}
