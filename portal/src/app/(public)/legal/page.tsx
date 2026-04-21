import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Legal & Terms of Service | Corgi Insurance',
  description:
    'Terms of Service and legal information for Corgi Insurance Services, Inc.',
};

export default function LegalPage() {
  return (
    <main className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-10 md:py-14 flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
          Legal
        </span>
        <h1 className="font-heading text-[28px] sm:text-[36px] font-medium text-heading tracking-[-1.152px] leading-none">
          Terms of Service.
        </h1>
        <p className="text-sm text-muted">Last updated: placeholder date</p>
      </div>

      <div className="rounded-2xl border border-dashed border-border bg-surface px-5 py-4 text-sm text-muted">
        This page contains placeholder content pending legal review. Do not rely
        on it for any binding interpretation of the relationship between you and
        Corgi Insurance Services, Inc.
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          1. Acceptance of terms
        </h2>
        <p className="text-sm leading-relaxed text-body">
          By accessing or using the Corgi Insurance platform (the &ldquo;Service&rdquo;),
          you agree to be bound by these Terms of Service and our accompanying
          disclaimers. If you do not agree, please do not use the Service.
          Placeholder copy; final language will be provided by counsel.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          2. The Service
        </h2>
        <p className="text-sm leading-relaxed text-body">
          Corgi operates a digital insurance brokerage that connects commercial
          policyholders with admitted and non-admitted carriers. Insurance
          policies are issued by the applicable carrier, not by Corgi. Placeholder
          copy pending review.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          3. Eligibility and accounts
        </h2>
        <p className="text-sm leading-relaxed text-body">
          You must be at least 18 years of age and authorized to bind the business
          on whose behalf you are acting. You are responsible for maintaining the
          confidentiality of your account credentials. Placeholder copy.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          4. Disclaimers and limitation of liability
        </h2>
        <p className="text-sm leading-relaxed text-body">
          The Service is provided on an &ldquo;as is&rdquo; and &ldquo;as available&rdquo;
          basis. See our{' '}
          <Link href="/disclaimers" className="text-primary hover:underline">
            full disclaimers
          </Link>{' '}
          for the complete list of limitations and carrier-specific notices.
          Placeholder copy.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          5. Licensing
        </h2>
        <p className="text-sm leading-relaxed text-body">
          Corgi is a licensed insurance producer. For a state-by-state list of
          license numbers and registered entities, see our{' '}
          <Link href="/broker-licenses" className="text-primary hover:underline">
            broker licenses
          </Link>{' '}
          page.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-medium text-heading tracking-[-0.5px]">
          6. Contact
        </h2>
        <p className="text-sm leading-relaxed text-body">
          Questions about these terms can be directed to{' '}
          <a
            href="mailto:hello@corgi.insure"
            className="text-primary hover:underline"
          >
            hello@corgi.insure
          </a>
          .
        </p>
      </section>
    </main>
  );
}
