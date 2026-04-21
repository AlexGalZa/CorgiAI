'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Input } from '@/components/ui/input';
import { Btn3DOrange } from '@/components/ui/button';
import { ArrowRightIcon, CorgiLogo } from '@/components/icons';
import { FormField } from '@/components/quote/FormField';
import { useCreateQuote } from '@/hooks/use-quote';
import { useCaptureUtm } from '@/hooks/use-capture-utm';
import { useQuoteStore } from '@/stores/use-quote-store';
import PartnersStrip from '@/components/layout/PartnersStrip';

const GetStartedSchema = z.object({
  name: z.string().trim().min(2, 'Please enter your full name'),
  company_name: z.string().min(1, 'Company name is required'),
  email: z.string().email('Please enter a valid email'),
});

type GetStartedData = z.infer<typeof GetStartedSchema>;

export default function QuoteGetStartedPage() {
  const router = useRouter();
  const { mutateAsync: createQuote, isPending } = useCreateQuote();
  const utm = useCaptureUtm();
  const { setQuoteNumber, updateFormData, markStepCompleted } = useQuoteStore();
  const [apiError, setApiError] = useState('');

  const { register, handleSubmit, formState: { errors } } = useForm<GetStartedData>({
    resolver: zodResolver(GetStartedSchema) as any,
  });

  const onSubmit = async (data: GetStartedData) => {
    setApiError('');
    const trimmed = data.name.trim().replace(/\s+/g, ' ');
    const [first_name, ...rest] = trimmed.split(' ');
    const last_name = rest.join(' ');

    try {
      const result = await createQuote({ coverages: [] });
      setQuoteNumber(result.quote_number);
      updateFormData({
        first_name,
        last_name,
        email: data.email,
        company_name: data.company_name,
        utm_source: utm.utm_source,
        utm_medium: utm.utm_medium,
        utm_campaign: utm.utm_campaign,
        referrer_url: utm.referrer_url,
        landing_page_url: utm.landing_page_url,
      });
      markStepCompleted('welcome');
      router.push(`/quote/${result.quote_number}/products`);
    } catch (err) {
      setApiError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    }
  };

  return (
    <div className="fixed inset-0 overflow-y-auto bg-bg flex flex-col font-sans">
      {/* Split hero: orange pitch on the left, white action zone on the right. */}
      <div className="flex-1 relative">
        {/* Background split (absolute so the form card can overlap the seam). */}
        <div className="absolute inset-0 grid grid-cols-1 lg:grid-cols-2">
          {/* Orange pitch panel. */}
          <div className="bg-primary text-white flex flex-col justify-between px-6 sm:px-10 lg:px-16 py-8 lg:py-12 min-h-[320px]">
            <Link href="/" className="inline-flex items-center no-underline w-fit">
              <CorgiLogo className="h-7 w-auto brightness-0 invert" />
            </Link>

            <div>
              <h1 className="font-heading text-[40px] sm:text-[52px] lg:text-[64px] font-medium tracking-[-2px] leading-[0.98] mb-6 lg:mb-8">
                Real coverage.<br />Real fast.
              </h1>
              <ul className="space-y-2 text-base lg:text-lg">
                <li className="flex items-center gap-3">
                  <WhiteCheck />
                  Instant online quotes
                </li>
                <li className="flex items-center gap-3">
                  <WhiteCheck />
                  No credit card required
                </li>
                <li className="flex items-center gap-3">
                  <WhiteCheck />
                  Expert support
                </li>
              </ul>
            </div>

            <div />
          </div>

          {/* White action panel + corgi peeking in. */}
          <div className="relative bg-surface min-h-[260px] overflow-hidden">
            <Link
              href="https://corgi.insure/help"
              className="absolute top-6 right-6 lg:top-8 lg:right-10 inline-flex items-center px-4 py-2 rounded-full border border-border text-sm font-medium text-heading bg-surface hover:bg-bg no-underline transition-colors z-10"
            >
              Help
            </Link>

            <img
              src="/corgi-hero.webp"
              alt=""
              className="hidden lg:block absolute right-[-40px] top-1/2 -translate-y-1/2 w-[55%] max-w-[520px] h-auto pointer-events-none select-none animate-enter"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        </div>

        {/* Form card floats over the orange/white seam on desktop. */}
        <div className="relative z-10 min-h-full flex items-center justify-center lg:justify-start px-5 sm:px-8 py-8 lg:py-12 lg:pl-[calc(50%-230px)]">
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="w-full max-w-[440px] bg-surface border border-border rounded-2xl shadow-[0_12px_32px_rgba(15,23,42,0.12)] p-6 sm:p-8 space-y-4"
          >
            <FormField label="Name" error={errors.name?.message} required>
              <Input
                placeholder="Jane Doe"
                autoComplete="name"
                {...register('name')}
                error={!!errors.name}
              />
            </FormField>

            <FormField label="Company Name" error={errors.company_name?.message} required>
              <Input
                placeholder="Acme Corp"
                autoComplete="organization"
                {...register('company_name')}
                error={!!errors.company_name}
              />
            </FormField>

            <FormField label="Work Email" error={errors.email?.message} required>
              <Input
                type="email"
                placeholder="you@company.com"
                autoComplete="email"
                {...register('email')}
                error={!!errors.email}
              />
            </FormField>

            {apiError && (
              <p className="text-[11px] text-danger">{apiError}</p>
            )}

            <div className="pt-1">
              <Btn3DOrange fullWidth disabled={isPending} type="submit">
                {isPending ? 'Building your quote...' : 'See my quote'} <ArrowRightIcon />
              </Btn3DOrange>
              <p className="text-[11px] text-muted text-center mt-2.5 leading-[1.5]">
                No credit card. Two-minute questionnaire.
              </p>
            </div>

            <p className="text-[11px] text-muted text-center pt-3 border-t border-border/60">
              Already a customer?{' '}
              <a href="/login" className="text-primary font-medium no-underline hover:underline">
                Sign in
              </a>
            </p>
          </form>
        </div>
      </div>

      <footer className="shrink-0 py-3 px-5 border-t border-border/60 bg-surface">
        <PartnersStrip />
      </footer>
    </div>
  );
}

function WhiteCheck() {
  return (
    <svg
      className="w-4 h-4 text-white shrink-0"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}
