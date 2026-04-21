'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { usePageTitle } from '@/hooks/use-page-title';
import { QUOTE_TYPES, AVAIL_COVERAGES, useQuotes, useQuoteDetail } from '@/hooks/use-quotes';
import { useAppStore } from '@/stores/use-app-store';
import { Btn3DWhite, BtnPrimary, BtnSecondary } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { PhoneIcon, CloseIcon } from '@/components/icons';
import type { APIQuoteListItem } from '@/types';
import { formatCurrency } from '@/lib/utils';
import { trackEvent } from '@/lib/analytics';

function QuoteStatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  if (s === 'draft') return <Badge variant="pending">Draft</Badge>;
  if (s === 'submitted' || s === 'quoted') return <Badge variant="active" />;
  if (s === 'needs_review') return <Badge variant="submitted" />;
  if (s === 'purchased') return <Badge variant="active" />;
  if (s === 'expired') return <Badge variant="expired" />;
  return <Badge variant="pending">{status}</Badge>;
}

function QuoteStatusLabel({ status }: { status: string }) {
  const s = status.toLowerCase();
  if (s === 'draft') return 'Draft';
  if (s === 'submitted') return 'Submitted';
  if (s === 'quoted') return 'Quoted';
  if (s === 'needs_review') return 'Needs Review';
  if (s === 'purchased') return 'Purchased';
  if (s === 'expired') return 'Expired';
  return status;
}

const COVERAGE_SLUG_LABELS: Record<string, string> = {
  'technology-errors-and-omissions': 'Tech E&O',
  'cyber-liability': 'Cyber',
  'directors-and-officers': 'D&O',
  'commercial-general-liability': 'GL',
  'employment-practices-liability': 'EPL',
  'fiduciary-liability': 'Fiduciary',
  'hired-and-non-owned-auto': 'HNOA',
  'media-liability': 'Media',
};

function formatCoverageList(coverages: string[]): string {
  return coverages
    .map((c) => COVERAGE_SLUG_LABELS[c] ?? c)
    .join(', ');
}

export default function QuotesPage() {
  usePageTitle('Quotes');
  const router = useRouter();
  const { showToast } = useAppStore();
  const { data: apiQuotes, isLoading: quotesLoading } = useQuotes();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedQuoteNumber, setSelectedQuoteNumber] = useState<string | null>(null);

  const [showCompare, setShowCompare] = useState(false);

  const { data: quoteDetail } = useQuoteDetail(selectedQuoteNumber);

  const startQuote = useCallback((coverageName: string) => {
    trackEvent('quote_started', { coverage: coverageName });
    router.push('/quote/get-started');
  }, [router]);

  const filteredTypes = QUOTE_TYPES.filter((t) => {
    const q = searchQuery.toLowerCase();
    return !q || t.name.toLowerCase().includes(q) || t.desc.toLowerCase().includes(q);
  });

  // Separate quotes into in-progress and completed
  const inProgressQuotes = (apiQuotes ?? []).filter((q) =>
    ['draft', 'submitted', 'needs_review'].includes(q.status.toLowerCase())
  );
  const completedQuotes = (apiQuotes ?? []).filter((q) =>
    ['quoted', 'purchased', 'expired'].includes(q.status.toLowerCase())
  );

  return (
    <div className="max-w-[1100px] mx-auto px-12 py-10 flex flex-col gap-8">

      <div className="flex flex-col gap-8">
          <div className="flex items-end justify-between">
            <div className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">Quotes</span>
              <h1 className="font-heading text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">Explore Coverages.</h1>
            </div>
          </div>


          {/* In-progress quote banner */}
          {!quotesLoading && inProgressQuotes.length > 0 && (
            <div className="flex items-center justify-between gap-4 p-4 bg-primary/5 border border-primary/20 rounded-2xl">
              <div className="flex items-center gap-3">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-primary">
                  <circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" />
                </svg>
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-semibold text-heading">You have an existing quote in progress</span>
                  <span className="text-[11px] text-muted">
                    {inProgressQuotes[0].quote_number} · {formatCoverageList(inProgressQuotes[0].coverages)}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedQuoteNumber(inProgressQuotes[0].quote_number)}
                className="shrink-0 inline-flex items-center justify-center bg-primary text-white text-sm font-semibold rounded-xl px-5 py-2.5 cursor-pointer border-none hover:bg-primary-dark transition-colors"
              >
                Continue Quote
              </button>
            </div>
          )}

          {/* In Progress Quotes */}
          {!quotesLoading && inProgressQuotes.length > 0 && (
            <div className="flex flex-col gap-3">
              <div className="pl-4 text-[11px] font-semibold text-muted leading-[1.2] uppercase">In Progress</div>
              <div className="bg-surface border border-border rounded-2xl overflow-hidden">
                <div className="border-b border-border">
                  {/* Table header */}
                  <div className="flex items-center px-6 py-3 bg-bg">
                    <div className="text-[11px] font-semibold text-muted uppercase flex-1">Quote</div>
                    <div className="text-[11px] font-semibold text-muted uppercase w-48">Coverages</div>
                    <div className="text-[11px] font-semibold text-muted uppercase w-24 text-right">Status</div>
                    <div className="text-[11px] font-semibold text-muted uppercase w-28 text-right">Amount</div>
                    <div className="w-24" />
                  </div>
                </div>
                {inProgressQuotes.map((quote) => (
                  <QuoteRow
                    key={quote.id}
                    quote={quote}
                    onView={() => setSelectedQuoteNumber(quote.quote_number)}
                    onResume={() => {
                      router.push(`/quote/${quote.quote_number}/products`);
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Completed Quotes */}
          {!quotesLoading && completedQuotes.length > 0 && (
            <div className="flex flex-col gap-3">
              <div className="pl-4 text-[11px] font-semibold text-muted leading-[1.2] uppercase">Completed</div>
              <div className="bg-surface border border-border rounded-2xl overflow-hidden">
                <div className="border-b border-border">
                  <div className="flex items-center px-6 py-3 bg-bg">
                    <div className="text-[11px] font-semibold text-muted uppercase flex-1">Quote</div>
                    <div className="text-[11px] font-semibold text-muted uppercase w-48">Coverages</div>
                    <div className="text-[11px] font-semibold text-muted uppercase w-24 text-right">Status</div>
                    <div className="text-[11px] font-semibold text-muted uppercase w-28 text-right">Amount</div>
                    <div className="w-24" />
                  </div>
                </div>
                {completedQuotes.map((quote) => (
                  <QuoteRow
                    key={quote.id}
                    quote={quote}
                    onView={() => setSelectedQuoteNumber(quote.quote_number)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Available Coverage Grid */}
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            <div className="px-6 py-5 border-b border-border flex items-center justify-between">
              <span className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">Available Coverage</span>
              <button
                onClick={() => setShowCompare(true)}
                className="inline-flex items-center gap-1.5 text-sm font-medium text-primary bg-transparent border border-primary/30 rounded-xl px-4 py-2 cursor-pointer hover:bg-primary/5 transition-colors font-sans"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M16 3h5v5" /><path d="M8 3H3v5" /><path d="M12 22v-8.3a4 4 0 0 0-1.172-2.872L3 3" /><path d="m15 9 6-6" />
                </svg>
                Compare Plans
              </button>
            </div>
            <div className="grid grid-cols-3">
              {AVAIL_COVERAGES.map((c, i) => (
                <div
                  key={c.name}
                  className={`flex flex-col cursor-pointer transition-shadow relative ${i % 3 !== 2 ? 'border-r border-border' : ''} ${i < 3 ? 'border-b border-border' : ''} group`}
                  onClick={() => startQuote(c.name)}
                >
                  <div className="absolute inset-0 shadow-[inset_0_0_0_3px_var(--color-primary)]/25 opacity-0 transition-opacity pointer-events-none group-hover:opacity-100" />
                  <div className="h-[90px] bg-bg flex items-center justify-center overflow-hidden border-b border-border">
                    <svg width="80" height="50" viewBox="0 0 80 50" fill="none"><text x="10" y="35" fontFamily="Inter,sans-serif" fontSize="32" fontWeight="800" fill="currentColor" opacity="0.08" className="text-heading">0101</text></svg>
                  </div>
                  <div className="p-4 flex flex-col justify-between gap-4 flex-1">
                    <div className="flex flex-col gap-2 leading-[1.2]">
                      <span className="text-sm font-semibold text-heading">{c.name}</span>
                      <span className="text-xs font-normal text-muted">{c.desc}</span>
                    </div>
                    <span className="text-sm font-medium text-primary no-underline font-sans group-hover:underline">Get coverage →</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* CTA banner */}
          <div className="bg-primary rounded-xl px-6 py-5 flex items-center justify-between gap-6">
            <div className="flex-1 flex flex-col gap-2 leading-[1.2] text-white">
              <span className="text-sm font-semibold">Not sure what you need?</span>
              <span className="text-xs font-normal">Talk to your account manager — they&apos;ll recommend the right coverage for your stage.</span>
            </div>
            <Btn3DWhite className="shrink-0" onClick={() => showToast('Connecting to agent...')}>
              Talk to us <PhoneIcon />
            </Btn3DWhite>
          </div>
        </div>

      {/* Compare Plans Modal */}
      <ComparePlansModal
        open={showCompare}
        onClose={() => setShowCompare(false)}
        onSelect={(coverageName) => {
          setShowCompare(false);
          startQuote(coverageName);
        }}
      />

      {/* Quote Detail Modal */}
      <Modal open={!!selectedQuoteNumber} onClose={() => setSelectedQuoteNumber(null)} width={540}>
        {quoteDetail && (
          <div className="p-6 flex flex-col gap-5">
            <div className="flex items-start justify-between">
              <div className="flex flex-col gap-1">
                <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
                  Quote {quoteDetail.quote_number}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <QuoteStatusBadge status={quoteDetail.status} />
                </div>
              </div>
              <button onClick={() => setSelectedQuoteNumber(null)} className="bg-transparent border-none cursor-pointer p-0 leading-none shrink-0">
                <CloseIcon />
              </button>
            </div>

            {/* Coverages */}
            <div className="flex flex-col gap-1">
              <div className="px-1 text-[11px] font-semibold text-muted uppercase">Coverages</div>
              <div className="flex flex-wrap gap-2">
                {quoteDetail.coverages.map((c) => (
                  <span key={c} className="text-xs bg-bg border border-border rounded-full py-1 px-3 text-heading">
                    {COVERAGE_SLUG_LABELS[c] ?? c}
                  </span>
                ))}
              </div>
            </div>

            {/* Pricing */}
            {quoteDetail.total_amount > 0 && (
              <div className="flex flex-col gap-1">
                <div className="px-1 text-[11px] font-semibold text-muted uppercase">Pricing</div>
                <div className="border border-border rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between">
                    <div className="p-3 text-sm font-normal text-body w-48 shrink-0">Annual premium</div>
                    <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">
                      {formatCurrency(quoteDetail.total_amount)}
                    </div>
                  </div>
                  <div className="flex items-center justify-between border-t border-border">
                    <div className="p-3 text-sm font-normal text-body w-48 shrink-0">Monthly</div>
                    <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">
                      {formatCurrency(quoteDetail.total_monthly)}/mo
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Rating breakdown */}
            {quoteDetail.rating_result?.breakdown && (
              <div className="flex flex-col gap-1">
                <div className="px-1 text-[11px] font-semibold text-muted uppercase">Breakdown</div>
                <div className="border border-border rounded-lg overflow-hidden">
                  {Object.entries(quoteDetail.rating_result.breakdown).map(([slug, data], i) => (
                    <div key={slug} className={`flex items-center justify-between ${i > 0 ? 'border-t border-border' : ''}`}>
                      <div className="p-3 text-sm font-normal text-body flex-1">{COVERAGE_SLUG_LABELS[slug] ?? slug}</div>
                      <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">
                        {formatCurrency(data.premium)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {quoteDetail.needs_review && quoteDetail.rating_result?.review_reasons && (
              <div className="bg-[rgba(255,222,204,0.2)] border border-primary rounded-xl p-3 flex flex-col gap-1">
                <div className="text-sm font-semibold text-heading">Needs Review</div>
                {quoteDetail.rating_result.review_reasons.map((r, i) => (
                  <div key={i} className="text-[11px] text-body">
                    <strong>{COVERAGE_SLUG_LABELS[r.coverage] ?? r.coverage}:</strong> {r.reason}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

function QuoteRow({
  quote,
  onView,
  onResume,
}: {
  quote: APIQuoteListItem;
  onView: () => void;
  onResume?: () => void;
}) {
  return (
    <div className="flex items-center px-6 py-3 border-b border-border last:border-b-0 hover:bg-bg transition-colors">
      <div className="flex-1 min-w-0">
        <button onClick={onView} className="text-sm font-medium text-heading bg-transparent border-none cursor-pointer p-0 hover:underline font-sans">
          {quote.quote_number}
        </button>
        <div className="text-[11px] text-muted mt-0.5">
          {new Date(quote.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
        </div>
      </div>
      <div className="w-48 text-xs text-body truncate">
        {formatCoverageList(quote.coverages)}
      </div>
      <div className="w-24 text-right">
        <QuoteStatusBadge status={quote.status} />
      </div>
      <div className="w-28 text-right text-sm font-medium text-heading">
        {quote.quote_amount ? formatCurrency(quote.quote_amount) : '—'}
      </div>
      <div className="w-24 text-right">
        {onResume && (
          <button
            onClick={onResume}
            className="text-xs font-medium text-primary bg-transparent border-none cursor-pointer p-0 hover:underline font-sans"
          >
            Resume →
          </button>
        )}
      </div>
    </div>
  );
}

/* ─── Compare Plans Modal ─── */

interface ComparisonPlan {
  id: string;
  name: string;
  shortName: string;
  description: string;
  startingPremium: string;
  perOccurrence: string;
  aggregate: string;
  deductible: string;
  coveredPerils: string[];
  recommended?: boolean;
}

const COMPARISON_PLANS: ComparisonPlan[] = [
  {
    id: 'tech_pro',
    name: 'Tech E&O',
    shortName: 'Tech E&O',
    description: 'For software & tech service failures',
    startingPremium: 'From $4,250/yr',
    perOccurrence: '$1M – $5M',
    aggregate: '$2M – $5M',
    deductible: '$5K – $50K',
    coveredPerils: ['Software defects', 'Data loss', 'Service failures', 'Breach of contract', 'IP infringement'],
    recommended: true,
  },
  {
    id: 'cyber',
    name: 'Cyber Liability',
    shortName: 'Cyber',
    description: 'For data breaches & cyber attacks',
    startingPremium: 'From $3,800/yr',
    perOccurrence: '$1M – $5M',
    aggregate: '$2M – $5M',
    deductible: '$20K – $60K',
    coveredPerils: ['Data breaches', 'Ransomware', 'Business interruption', 'Notification costs', 'Forensics'],
    recommended: true,
  },
  {
    id: 'gl',
    name: 'General Liability',
    shortName: 'GL',
    description: 'For bodily injury & property damage',
    startingPremium: 'From $2,200/yr',
    perOccurrence: '$1M – $5M',
    aggregate: '$2M – $5M',
    deductible: '$500 – $2K',
    coveredPerils: ['Bodily injury', 'Property damage', 'Advertising injury', 'Products liability'],
  },
  {
    id: 'eo',
    name: 'Errors & Omissions',
    shortName: 'E&O',
    description: 'For professional service failures',
    startingPremium: 'From $3,600/yr',
    perOccurrence: '$1M – $5M',
    aggregate: '$2M – $5M',
    deductible: '$5K – $50K',
    coveredPerils: ['Negligent acts', 'Professional duty failures', 'Missed deadlines', 'Bad advice'],
  },
  {
    id: 'fiduciary',
    name: 'Fiduciary Liability',
    shortName: 'Fiduciary',
    description: 'For benefit plan mismanagement',
    startingPremium: 'From $2,900/yr',
    perOccurrence: '$1M – $5M',
    aggregate: '$2M – $5M',
    deductible: '$10K – $60K',
    coveredPerils: ['Plan mismanagement', 'ERISA breaches', 'Investment errors', 'Admin failures'],
  },
];

const COMPARE_FEATURES = [
  { key: 'startingPremium', label: 'Starting premium' },
  { key: 'perOccurrence', label: 'Per occurrence limit' },
  { key: 'aggregate', label: 'Aggregate limit' },
  { key: 'deductible', label: 'Deductible range' },
] as const;

function ComparePlansModal({
  open,
  onClose,
  onSelect,
}: {
  open: boolean;
  onClose: () => void;
  onSelect: (coverageName: string) => void;
}) {
  return (
    <Modal open={open} onClose={onClose} width={1024} titleId="compare-plans-title">
      <div className="p-6 sm:p-8 flex flex-col gap-6">

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h2
              id="compare-plans-title"
              className="font-heading text-[22px] sm:text-[26px] font-medium text-heading leading-none tracking-[-0.5px]"
            >
              Compare plans
            </h2>
            <p className="text-sm text-muted leading-[1.4]">
              Find the plan that matches your coverage needs.
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 p-1.5 -mr-1 rounded-lg bg-transparent border-none cursor-pointer text-muted hover:text-heading hover:bg-black/[.04] transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
          >
            <CloseIcon />
          </button>
        </div>

        {/* Plan cards */}
        <div className="flex flex-col sm:grid sm:grid-cols-5 gap-3">
          {COMPARISON_PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`flex flex-col rounded-2xl border overflow-hidden ${
                plan.recommended
                  ? 'border-primary/40 bg-primary/[0.03] sm:order-first'
                  : 'border-border bg-surface'
              }`}
              style={plan.recommended ? { order: -1 } : undefined}
            >
              {/* Card header. The Recommended pill reserves vertical space on
                  every card (via the h-5 placeholder) so pricing rows line up
                  across cards regardless of whether the pill is shown. */}
              <div
                className={`px-4 pt-4 pb-3 border-b ${
                  plan.recommended ? 'border-primary/20' : 'border-border'
                }`}
              >
                <div className="h-5 mb-2 flex items-center">
                  {plan.recommended && (
                    <span className="bg-primary text-white text-[10px] font-semibold rounded-full px-2 py-0.5 leading-none uppercase tracking-wide">
                      Recommended
                    </span>
                  )}
                </div>
                <div className="text-sm font-semibold text-heading leading-[1.2]">
                  {plan.shortName}
                </div>
                <div className="text-[11px] text-muted leading-[1.3] mt-0.5 min-h-[2.6em]">
                  {plan.description}
                </div>
              </div>

              {/* Feature spec sheet. Label + value stack vertically inside each
                  row so wide values like "From $4,250" have room to render on
                  their own line without colliding with the label. */}
              <div className="flex flex-col px-4 py-3 gap-0">
                {COMPARE_FEATURES.map((feature, fi) => (
                  <div
                    key={feature.key}
                    className={`flex flex-col gap-0.5 py-2 ${
                      fi < COMPARE_FEATURES.length - 1 ? 'border-b border-border' : ''
                    }`}
                  >
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-muted leading-[1.2]">
                      {feature.label}
                    </span>
                    <span
                      className={`text-[12px] leading-[1.3] ${
                        feature.key === 'startingPremium'
                          ? 'font-semibold text-heading'
                          : 'text-body'
                      }`}
                    >
                      {plan[feature.key]}
                    </span>
                  </div>
                ))}
              </div>

              {/* What is covered */}
              <div
                className={`px-4 py-3 border-t flex-1 ${
                  plan.recommended ? 'border-primary/20' : 'border-border'
                }`}
              >
                <div className="text-[10px] font-semibold text-muted uppercase tracking-wide mb-2">
                  What&apos;s covered
                </div>
                <ul className="flex flex-col gap-1.5 m-0 pl-0 list-none">
                  {plan.coveredPerils.map((peril) => (
                    <li key={peril} className="flex items-start gap-1.5 text-[11px] text-body leading-[1.3]">
                      <svg
                        className="w-3 h-3 shrink-0 mt-0.5 text-success"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      {peril}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Select button */}
              <div
                className={`px-4 pb-4 pt-3 border-t ${
                  plan.recommended ? 'border-primary/20' : 'border-border'
                }`}
              >
                {plan.recommended ? (
                  <BtnPrimary
                    fullWidth
                    onClick={() => onSelect(plan.name)}
                  >
                    Select
                  </BtnPrimary>
                ) : (
                  <BtnSecondary
                    className="w-full"
                    onClick={() => onSelect(plan.name)}
                  >
                    Select
                  </BtnSecondary>
                )}
              </div>
            </div>
          ))}
        </div>

      </div>
    </Modal>
  );
}
