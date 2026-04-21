import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Corgi vs Embroker — Compare Business Insurance | Corgi Insurance',
  description:
    'See how Corgi Insurance compares to Embroker on pricing, speed to quote, self-serve experience, and modern technology for growing businesses.',
};

// TODO(marketing): Filler comparison copy below — replace with vetted,
// legally-reviewed competitor claims before this page is indexed/launched.
const features = [
  {
    label: 'Pricing approach',
    corgi: 'Transparent, usage-aware pricing with no broker markup.',
    competitor: 'Traditional broker-quoted pricing with tier-based plans.',
  },
  {
    label: 'Speed to quote',
    corgi: 'Bindable quote in under 3 minutes, fully online.',
    competitor: 'Typically minutes to hours depending on product and inputs.',
  },
  {
    label: 'Self-serve experience',
    corgi: 'End-to-end self-serve: quote, bind, issue, and manage policies.',
    competitor: 'Self-serve for some products; others routed through agents.',
  },
  {
    label: 'Technology-forward',
    corgi: 'Modern API-first platform with real-time certificate issuance.',
    competitor: 'Digital platform with broker-assisted workflows for complex lines.',
  },
  {
    label: 'Coverage breadth',
    corgi: 'Core SMB lines: GL, Cyber, E&O, Workers Comp, BOP.',
    competitor: 'Broad portfolio including management liability and specialty.',
  },
  {
    label: 'Support model',
    corgi: 'In-app support with licensed advisors available on demand.',
    competitor: 'Dedicated broker model with human guidance.',
  },
];

export default function EmbrokerComparisonPage() {
  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-10 md:py-16 flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
          Comparison
        </span>
        <h1 className="font-heading text-[32px] sm:text-[44px] font-medium text-heading tracking-[-1.5px] leading-[1.05]">
          Corgi vs Embroker
        </h1>
        <p className="text-base text-body max-w-[720px] leading-[1.5]">
          Both Corgi and Embroker help modern businesses get insured online. Here&rsquo;s
          how we stack up on the things that actually matter when you need coverage
          quickly and without surprises.
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
                Embroker
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
          Ready to see your Corgi quote?
        </h2>
        <p className="text-sm text-body leading-[1.5] max-w-[640px]">
          Answer a handful of questions about your business and get a bindable quote
          in minutes — no broker calls required.
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
        Comparison based on publicly available information about Embroker as of the
        page&rsquo;s last update. Product offerings and pricing change; verify details
        on each provider&rsquo;s site before making a purchase decision.
      </p>
    </div>
  );
}
