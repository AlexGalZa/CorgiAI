import Link from 'next/link';

const SUPPORT_EMAIL = 'support@corgiinsure.com';
const SUPPORT_PHONE = process.env.NEXT_PUBLIC_SUPPORT_PHONE ?? null;

const FAQ_ITEMS = [
  {
    q: 'How do I download my certificate of insurance?',
    a: 'Go to Certificates in the sidebar, find your policy, and click the Download button. Certificates are available as PDFs.',
  },
  {
    q: 'When do I get renewal reminders?',
    a: 'We send email reminders 60 days and 30 days before your policy renewal date. Make sure your notification preferences are enabled in Settings.',
  },
  {
    q: 'How do I update my payment method?',
    a: 'Go to Billing in the sidebar and click "Change payment method". You will be redirected to our secure payment portal.',
  },
  {
    q: 'How do I add or remove team members?',
    a: 'Go to Organization in the sidebar. Owners can invite new members by email and set their role (viewer or editor).',
  },
  {
    q: 'How do I file a claim?',
    a: 'Go to Claims in the sidebar and click "File a claim". Fill in the details and our team will review it within 2 business days.',
  },
  {
    q: 'Can I have multiple organizations under one account?',
    a: 'Yes. Click your organization name at the top of the sidebar, then choose "Create organization". You can switch between organizations at any time.',
  },
  {
    q: 'What coverage types does Corgi offer?',
    a: 'Corgi offers general liability, professional liability (E&O), cyber liability, and workers compensation, among others. Start a quote to see what is available for your business.',
  },
  {
    q: 'How do I contact support?',
    a: `Email us at ${SUPPORT_EMAIL}${SUPPORT_PHONE ? ` or call ${SUPPORT_PHONE}` : ''}. We typically respond within one business day.`,
  },
];

export default function HelpPage() {
  return (
    <div className="min-h-screen bg-bg">
      <div className="max-w-[720px] mx-auto px-4 sm:px-6 py-12 md:py-16 flex flex-col gap-10">
        {/* Header */}
        <div className="flex flex-col gap-3">
          <span className="text-[11px] font-semibold text-muted tracking-normal uppercase">
            Support
          </span>
          <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">
            How can we help?
          </h1>
          <p className="text-sm text-body mt-1">
            Browse the questions below or reach out directly and we will get back to you.
          </p>
        </div>

        {/* Contact CTA */}
        <div className="bg-surface border border-border rounded-2xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex flex-col gap-1">
            <span className="text-sm font-semibold text-heading">Contact support</span>
            <span className="text-[13px] text-muted">
              Our team is available Monday to Friday, 9 am to 5 pm PT.
            </span>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 shrink-0">
            <a
              href={`mailto:${SUPPORT_EMAIL}?subject=Corgi support request`}
              className={[
                'inline-flex items-center justify-center gap-1.5 rounded-xl px-4 py-2 text-sm font-medium',
                'bg-primary text-white hover:bg-primary-dark transition-colors no-underline',
                'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none',
              ].join(' ')}
            >
              Email support
            </a>
            {SUPPORT_PHONE && (
              <a
                href={`tel:${SUPPORT_PHONE}`}
                className={[
                  'inline-flex items-center justify-center gap-1.5 rounded-xl px-4 py-2 text-sm font-medium',
                  'bg-surface border border-border text-body hover:bg-bg transition-colors no-underline',
                  'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none',
                ].join(' ')}
              >
                {SUPPORT_PHONE}
              </a>
            )}
          </div>
        </div>

        {/* FAQ */}
        <div className="flex flex-col gap-3">
          <h2 className="text-base font-semibold text-heading">Frequently asked questions</h2>
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            {FAQ_ITEMS.map(({ q, a }, i) => (
              <details
                key={i}
                className={[
                  'group',
                  i < FAQ_ITEMS.length - 1 ? 'border-b border-border' : '',
                ].join(' ')}
              >
                <summary
                  className={[
                    'flex items-center justify-between px-5 py-4 cursor-pointer list-none',
                    'text-sm font-medium text-heading select-none',
                    'hover:bg-bg transition-colors',
                    'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none',
                  ].join(' ')}
                >
                  <span>{q}</span>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="shrink-0 text-muted transition-transform duration-200 group-open:rotate-180"
                    aria-hidden="true"
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </summary>
                <div className="px-5 pb-4 text-[13px] text-body leading-[1.6]">{a}</div>
              </details>
            ))}
          </div>
        </div>

        {/* Back to dashboard */}
        <div>
          <Link
            href="/"
            className={[
              'inline-flex items-center gap-1.5 text-sm font-medium text-primary no-underline hover:underline',
              'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none rounded',
            ].join(' ')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Back to dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
