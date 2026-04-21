'use client';

import { useEffect, useMemo, useRef } from 'react';
import { useForm, useWatch, Controller, type FieldValues, type UseFormReturn } from 'react-hook-form';
import { Input, Textarea, Label } from '@/components/ui/input';
import { CustomSelect } from '@/components/ui/custom-select';
import { DatePicker } from '@/components/ui/date-picker';
import { FormField } from './FormField';
import { FormNavButtons } from './FormNavButtons';
import { QuoteFormLayout } from './QuoteFormLayout';

// ─── Field definition types (from Form Builder API) ───

export interface FormFieldDef {
  id: string;
  field_type: FieldType;
  label: string;
  placeholder?: string;
  required?: boolean;
  options?: Array<{ value: string; label: string }>;
  default_value?: unknown;
  help_text?: string;
  section?: string;
  conditional?: {
    field: string;
    operator: 'eq' | 'neq' | 'in' | 'contains';
    value: unknown;
  };
  min?: number;
  max?: number;
  grid_cols?: number;
}

export type FieldType =
  | 'text' | 'textarea' | 'number' | 'currency' | 'percentage' | 'date'
  | 'select' | 'multi_select' | 'radio' | 'checkbox' | 'checkbox_group'
  | 'file_upload' | 'address' | 'phone' | 'email' | 'ein'
  | 'heading' | 'paragraph';

export interface FormDefinition {
  id: string;
  title: string;
  description?: string;
  fields: FormFieldDef[];
  /**
   * Current version of the schema as served by the backend. If the
   * saved answer payload was produced against an older version, the
   * DynamicForm flags newly-required-but-empty fields on mount.
   */
  version?: number;
  /** Coverage slug this form belongs to (used for schema-drift checks). */
  coverage_type?: string;
}

interface Props {
  definition: FormDefinition;
  defaultValues?: Record<string, unknown>;
  /**
   * Version of the schema that produced ``defaultValues``. When this
   * is less than ``definition.version``, the form re-checks required
   * fields on mount and flags any new required fields that are empty.
   * Omit for fresh quotes.
   */
  answerSchemaVersion?: number;
  onSubmit: (data: Record<string, unknown>) => void;
  onBack: () => void;
  loading?: boolean;
}

/**
 * Returns the list of field keys that are required by the current
 * schema but empty in the provided values. Skips conditional fields
 * when their dependency is not satisfied.
 */
function computeStaleRequiredKeys(
  fields: FormFieldDef[],
  values: Record<string, unknown>,
): string[] {
  const missing: string[] = [];
  for (const field of fields) {
    if (!field.required) continue;

    // Evaluate conditional visibility against the current values so we
    // don't flag fields the user can't even see yet.
    if (field.conditional) {
      const watched = values[field.conditional.field];
      let visible = false;
      switch (field.conditional.operator) {
        case 'eq': visible = watched === field.conditional.value; break;
        case 'neq': visible = watched !== field.conditional.value; break;
        case 'in':
          visible = Array.isArray(field.conditional.value) && field.conditional.value.includes(watched);
          break;
        case 'contains':
          visible = typeof watched === 'string' && watched.includes(String(field.conditional.value));
          break;
      }
      if (!visible) continue;
    }

    const v = values[field.id];
    const blank =
      v === undefined ||
      v === null ||
      (typeof v === 'string' && v.trim() === '') ||
      (Array.isArray(v) && v.length === 0);
    if (blank) missing.push(field.id);
  }
  return missing;
}

export function DynamicForm({
  definition,
  defaultValues = {},
  answerSchemaVersion,
  onSubmit,
  onBack,
  loading,
}: Props) {
  const form = useForm({
    defaultValues: defaultValues as FieldValues,
  });

  const { handleSubmit, register, control, setError, formState: { errors } } = form;

  // ── Schema-drift detection (H6) ───────────────────────────────────
  // If the saved answer payload was produced against an older schema
  // version, re-check required fields against the current schema and
  // mark newly-required-but-empty ones. This mirrors the backend's
  // pre-save validation so the user learns about the gap immediately.
  const hasStaleAnswers = useMemo(() => {
    if (!answerSchemaVersion || !definition.version) return false;
    return answerSchemaVersion < definition.version;
  }, [answerSchemaVersion, definition.version]);

  const flaggedRef = useRef(false);
  useEffect(() => {
    if (!hasStaleAnswers || flaggedRef.current) return;
    const missing = computeStaleRequiredKeys(definition.fields, defaultValues);
    for (const key of missing) {
      setError(key as never, {
        type: 'schema-drift',
        message: 'This field is now required. Please provide a value before submitting.',
      });
    }
    flaggedRef.current = true;
  }, [hasStaleAnswers, definition.fields, defaultValues, setError]);

  return (
    <QuoteFormLayout title={definition.title} description={definition.description}>
      <form
        className="space-y-6 pb-[calc(env(safe-area-inset-bottom)+6rem)] sm:pb-0"
        onSubmit={handleSubmit(onSubmit)}
      >
        {renderFields(definition.fields, form)}
        <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-background px-4 pt-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)] sm:static sm:border-0 sm:bg-transparent sm:p-0">
          <FormNavButtons
            onBack={onBack}
            nextType="submit"
            loading={loading}
          />
        </div>
      </form>
    </QuoteFormLayout>
  );
}

function renderFields(fields: FormFieldDef[], form: UseFormReturn<FieldValues>) {
  const { register, formState: { errors } } = form;

  // Group by section
  let currentSection: string | undefined;
  const elements: React.ReactNode[] = [];

  for (const field of fields) {
    // Conditional visibility
    if (field.conditional) {
      elements.push(
        <ConditionalField key={field.id} field={field} form={form} />
      );
      continue;
    }

    // Section headings
    if (field.section && field.section !== currentSection) {
      currentSection = field.section;
      elements.push(
        <div key={`section-${field.section}`} className="pt-4">
          <h3 className="font-semibold text-lg text-heading">{field.section}</h3>
        </div>
      );
    }

    elements.push(renderField(field, form));
  }

  return elements;
}

function ConditionalField({ field, form }: { field: FormFieldDef; form: UseFormReturn<FieldValues> }) {
  const conditional = field.conditional!;
  const watchedValue = useWatch({ control: form.control, name: conditional.field });

  let visible = false;
  switch (conditional.operator) {
    case 'eq': visible = watchedValue === conditional.value; break;
    case 'neq': visible = watchedValue !== conditional.value; break;
    case 'in': visible = Array.isArray(conditional.value) && conditional.value.includes(watchedValue); break;
    case 'contains': visible = typeof watchedValue === 'string' && watchedValue.includes(String(conditional.value)); break;
  }

  if (!visible) return null;

  return (
    <div className="ml-2 border-l border-primary pl-4">
      {renderField(field, form)}
    </div>
  );
}

function renderField(field: FormFieldDef, form: UseFormReturn<FieldValues>) {
  const { register, formState: { errors } } = form;
  const error = errors[field.id]?.message as string | undefined;

  switch (field.field_type) {
    case 'heading':
      return (
        <div key={field.id} className="pt-4 pb-2">
          <h3 className="font-semibold text-lg text-heading">{field.label}</h3>
        </div>
      );

    case 'paragraph':
      return (
        <p key={field.id} className="text-sm text-body leading-[1.6]">{field.label}</p>
      );

    case 'text':
    case 'phone':
    case 'email':
    case 'ein':
      return (
        <FormField key={field.id} label={field.label} error={error} required={field.required}>
          <Input
            type={field.field_type === 'email' ? 'email' : field.field_type === 'phone' ? 'tel' : 'text'}
            placeholder={field.placeholder}
            {...register(field.id, { required: field.required ? `${field.label} is required` : false })}
          />
        </FormField>
      );

    case 'textarea':
      return (
        <FormField key={field.id} label={field.label} error={error} required={field.required}>
          <Textarea
            placeholder={field.placeholder}
            {...register(field.id, { required: field.required ? `${field.label} is required` : false })}
          />
        </FormField>
      );

    case 'number':
    case 'currency':
    case 'percentage':
      return (
        <FormField key={field.id} label={field.label} error={error} required={field.required}>
          <Input
            type="number"
            placeholder={field.placeholder}
            min={field.min}
            max={field.max}
            {...register(field.id, {
              required: field.required ? `${field.label} is required` : false,
              valueAsNumber: true,
            })}
          />
        </FormField>
      );

    case 'date':
      return (
        <FormField key={field.id} label={field.label} error={error} required={field.required}>
          <Controller
            name={field.id}
            control={form.control}
            rules={{ required: field.required ? `${field.label} is required` : false }}
            render={({ field: f }) => (
              <DatePicker
                value={f.value ?? ''}
                onChange={f.onChange}
                placeholder={field.placeholder || 'Select date'}
                error={!!error}
              />
            )}
          />
        </FormField>
      );

    case 'select':
      return (
        <FormField key={field.id} label={field.label} error={error} required={field.required}>
          <Controller
            name={field.id}
            control={form.control}
            rules={{ required: field.required ? `${field.label} is required` : false }}
            render={({ field: f }) => (
              <CustomSelect
                value={f.value ?? ''}
                onChange={f.onChange}
                placeholder="Select..."
                options={field.options ?? []}
                error={!!error}
              />
            )}
          />
        </FormField>
      );

    case 'radio':
      return (
        <FormField key={field.id} label={field.label} error={error} required={field.required}>
          <div className="flex gap-4 mt-1">
            {field.options?.map((o) => (
              <label key={o.value} className="flex items-center gap-2 cursor-pointer text-sm text-body">
                <input
                  type="radio"
                  value={o.value}
                  {...register(field.id, { required: field.required ? `${field.label} is required` : false })}
                  className="accent-primary"
                />
                {o.label}
              </label>
            ))}
          </div>
        </FormField>
      );

    case 'checkbox':
      return (
        <label key={field.id} className="flex items-center gap-2 cursor-pointer text-sm text-body">
          <input
            type="checkbox"
            {...register(field.id)}
            className="accent-primary w-4 h-4"
          />
          {field.label}
        </label>
      );

    case 'checkbox_group':
    case 'multi_select':
      return (
        <FormField key={field.id} label={field.label} error={error} required={field.required}>
          <div className="space-y-2 mt-1">
            {field.options?.map((o) => (
              <label key={o.value} className="flex items-center gap-2 cursor-pointer text-sm text-body">
                <input
                  type="checkbox"
                  value={o.value}
                  {...register(field.id)}
                  className="accent-primary w-4 h-4"
                />
                {o.label}
              </label>
            ))}
          </div>
        </FormField>
      );

    case 'file_upload':
      return (
        <FormField key={field.id} label={field.label} error={error} required={field.required}>
          <div className="border-2 border-dashed border-border rounded-xl p-6 text-center hover:border-primary transition-colors cursor-pointer">
            <input
              type="file"
              multiple
              {...register(field.id)}
              className="hidden"
              id={`file-${field.id}`}
            />
            <label htmlFor={`file-${field.id}`} className="cursor-pointer">
              <p className="text-sm text-muted">
                Drag & drop files here, or <span className="text-primary font-medium">browse</span>
              </p>
            </label>
          </div>
        </FormField>
      );

    case 'address':
      return (
        <div key={field.id} className="space-y-3">
          <Label>{field.label}</Label>
          <Input placeholder="Street address" {...register(`${field.id}.street_address`)} />
          <Input placeholder="Apt/Suite (optional)" {...register(`${field.id}.suite`)} />
          <div className="grid grid-cols-3 gap-3">
            <Input placeholder="City" {...register(`${field.id}.city`)} />
            <Input placeholder="State" {...register(`${field.id}.state`)} />
            <Input placeholder="Zip" {...register(`${field.id}.zip`)} />
          </div>
        </div>
      );

    default:
      return null;
  }
}
