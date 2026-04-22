'use client';

import { useParams, useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { QuoteFormLayout } from '@/components/quote/QuoteFormLayout';
import { FormNavButtons } from '@/components/quote/FormNavButtons';
import { TrudyPanel } from '@/components/trudy/TrudyPanel';
import { useQuoteStore } from '@/stores/use-quote-store';
import { buildStepPath, getPrevStep, AllCoveragesInfo } from '@/lib/quote-flow';

export default function SummaryPage() {
  const params = useParams<{ quoteNumber: string }>();
  const quoteNumber = params?.quoteNumber ?? '';
  const router = useRouter();
  const { formData } = useQuoteStore();
  const { setValue } = useForm();

  const handleBack = () => {
    const prev = getPrevStep('summary', formData.coverages ?? []);
    if (prev) router.push(buildStepPath(prev, quoteNumber));
  };

  const handleGetQuote = () => {
    router.push(`/quote/${quoteNumber}/checkout`);
  };

  const fullName = [formData.first_name, formData.last_name].filter(Boolean).join(' ');
  const addr = formData.company_info?.business_address;
  const fin = formData.company_info?.financial_details;
  const addressLine = [
    [addr?.street_address, addr?.suite].filter(Boolean).join(' '),
    [addr?.city, addr?.state].filter(Boolean).join(', '),
    addr?.zip,
  ].filter(Boolean).join(' · ');

  const formatCurrency = (v?: number) => {
    if (v === undefined || v === null || Number.isNaN(v)) return '—';
    try {
      return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v);
    } catch {
      return String(v);
    }
  };

  return (
    <div className="fixed inset-0 overflow-hidden bg-bg flex">
      <div className="flex-1 overflow-y-auto p-6 lg:p-10">
        <QuoteFormLayout
          title="Review your information"
          description="Take a moment to confirm everything looks right before we finalize your quote."
        >
          <div className="space-y-4">
            <SummaryCard title="Contact">
              <SummaryRow label="Name" value={fullName || '—'} />
              <SummaryRow label="Email" value={formData.email ?? '—'} />
              <SummaryRow label="Company" value={formData.company_name ?? '—'} />
            </SummaryCard>

            <SummaryCard title="Selected coverages">
              {(formData.coverages ?? []).length === 0 ? (
                <p className="text-sm text-muted">No coverages selected</p>
              ) : (
                <ul className="space-y-1.5">
                  {(formData.coverages ?? []).map((c) => (
                    <li key={c} className="flex items-center gap-2 text-sm text-body">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                      {AllCoveragesInfo[c]?.name ?? c}
                    </li>
                  ))}
                </ul>
              )}
            </SummaryCard>

            <SummaryCard title="Business address">
              <p className="text-sm text-body">{addressLine || '—'}</p>
            </SummaryCard>

            <SummaryCard title="Financials">
              <SummaryRow label="Annual revenue" value={formatCurrency(fin?.last_12_months_revenue)} />
              <SummaryRow label="Total employees" value={fin?.full_time_employees?.toString() ?? '—'} />
            </SummaryCard>
          </div>

          <FormNavButtons
            onBack={handleBack}
            onNext={handleGetQuote}
            nextType="button"
            nextLabel="Get my quote"
          />
        </QuoteFormLayout>
      </div>
      <div className="hidden lg:flex w-[340px] flex-col border-l border-border">
        <TrudyPanel step="summary" setValue={setValue} isNewQuote={false} quoteNumber={quoteNumber} />
      </div>
    </div>
  );
}

function SummaryCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <p className="text-[11px] font-semibold text-heading uppercase tracking-wide mb-2">{title}</p>
      {children}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <span className="text-[12px] text-muted">{label}</span>
      <span className="text-sm text-body text-right">{value}</span>
    </div>
  );
}
