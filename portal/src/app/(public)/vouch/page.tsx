import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Corgi vs Vouch — Compare Business Insurance | Corgi Insurance',
  description:
    'Compare Corgi Insurance and Vouch on pricing, speed to quote, self-serve capabilities, and tech-forward coverage for startups and growing teams.',
};

// TODO(marketing): Filler comparison copy below — replace with vetted,
// legally-reviewed competitor claims before this page is indexed/launched.
const features = [
  {
    label: 'Pricing approach',
    corgi: 'Transparent, usage-aware pricing available to businesses of any stage.',
    competitor:
      'Startup-oriented pricing, historically focused on venture-backed companies.',
  },
  {
    label: 'Speed to quote',
    corgi: 'Bindable quote in under 3 minutes for supported lines.',
    competitor: 'Fast online quote flow with underwriter review on some products.',
  },
  {
    label: 'Self-serve',
    corgi: 'Full self-serve: quote, bind, manage endorsements, file claims online.',
    competitor: 'Self-serve quoting with guided onboarding for complex coverages.',
  },
  {
    label: 'Technology-forward',
    corgi: 'API-first platform with real-time certificates and integrations.',
    competitor: 'Modern dashboard with integrations tailored to startup stacks.',
  },
  {
    label: 'Who it\u2019s for',
    corgi: 'Small and mid-sized businesses across industries.',
    competitor: 'Primarily high-growth startups and venture-backed companies.',
  },
  {
    label: 'Coverage highlights',
    corgi: 'GL, Cyber, E&O, Workers Comp, BOP, and certificate management.',
    competitor: 'D&O, E&O, Cyber, EPLI, and other startup-focused lines.',
  },
];

export default function VouchComparisonPage() {
  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-10 md:py-16 flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
          Comparison
        </span>
        <h1 className="font-heading text-[32px] sm:text-[44px] font-medium text-heading tracking-[-1.5px] leading-[1.05]">
          Corgi vs Vouch
        </h1>
        <p className="text-base text-body max-w-[720px] leading-[1.5]">
          Vouch built a strong product for venture-backed startups. Corgi takes a
          broader approach: the same tech-forward experience, available to any small
          or mid-sized business that wants coverage fast.
        </p>
      </header>

      <section className="bg-surface border border-border rounded-2xl overflow-x-auto">
        <table className="w-full min-w-[640px] text-left border-collapse">
          <thead>
            <tr className="bg-bg">
              <th className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase px-6 py-4 border-b border-border">
                Feature
              </th>
              <th className="text-[11px] font-semibold text-primary tracking-normal leading-[1.2] uppercase px-6 py-4 border-b border-border">
                Corgi
              </th>
              <th className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase px-6 py-4 border-b border-border">
                Vouch
              </th>
            </tr>
          </thead>
          <tbody>
            {features.map((row, i) => (
              <tr
                key={row.label}
                className={i !== features.length - 1 ? 'border-b border-border' : ''}
              >
                <th
                  scope="row"
                  className="align-top text-sm font-medium text-heading px-6 py-5 w-[28%]"
                >
                  {row.label}
                </th>
                <td className="align-top text-sm text-body px-6 py-5 leading-[1.5]">
                  {row.corgi}
                </td>
                <td className="align-top text-sm text-muted px-6 py-5 leading-[1.5]">
                  {row.competitor}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="bg-surface border border-border rounded-2xl px-6 md:px-10 py-8 md:py-10 flex flex-col gap-4">
        <h2 className="font-heading text-2xl font-medium text-heading tracking-[-0.768px] leading-[1.1]">
          See what Corgi quotes for your business.
        </h2>
        <p className="text-sm text-body leading-[1.5] max-w-[640px]">
          Tell us about your business and get a bindable quote in minutes. Keep the
          speed and developer-friendly tooling — without being locked into a single
          stage of company.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/quote"
            className="inline-flex items-center text-sm font-semibold bg-primary text-white rounded-xl px-5 py-2.5 no-underline hover:opacity-90 transition-opacity"
          >
            Get a quote
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center text-sm font-medium text-primary bg-transparent border border-primary rounded-xl px-5 py-2.5 no-underline hover:bg-primary hover:text-white transition-colors"
          >
            Create an account
          </Link>
        </div>
      </section>

      <p className="text-xs text-muted leading-[1.5]">
        Comparison based on publicly available information about Vouch as of the
        page&rsquo;s last update. Product offerings and pricing change; verify
        details on each provider&rsquo;s site before making a purchase decision.
      </p>
    </div>
  );
}
