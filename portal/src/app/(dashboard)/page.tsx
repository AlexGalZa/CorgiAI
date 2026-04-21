'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePageTitle } from '@/hooks/use-page-title';
import { usePolicies, usePolicyKPIs } from '@/hooks/use-policies';
import { useClaims } from '@/hooks/use-claims';
import { BtnSecondary } from '@/components/ui/button';
import { ShieldIcon } from '@/components/icons';
import type { APIPolicy } from '@/types';
import {
  PolicyCard,
  PolicyDetailModal,
  ModifyLimitsModal,
  LimitDisclaimerModal,
  RecommendedSection,
  LoadingSkeleton,
} from '@/components/coverage';

export default function CoveragePage() {
  usePageTitle('Coverage');
  const { data: policies, isLoading, isError, refetch } = usePolicies();
  const { data: claims } = useClaims();
  const { activeCount, totalCoverage, nextRenewal } = usePolicyKPIs();

  const [selectedPolicy, setSelectedPolicy] = useState<APIPolicy | null>(null);
  const [disclaimerOpen, setDisclaimerOpen] = useState(false);
  const [modifyLimitsOpen, setModifyLimitsOpen] = useState(false);
  const [modifyPolicy, setModifyPolicy] = useState<APIPolicy | null>(null);

  const openClaimsCount =
    claims?.filter((c) => c.status.toLowerCase() !== 'closed').length ?? 0;

  if (isLoading) return <LoadingSkeleton />;

  if (isError) {
    return (
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col items-center gap-4 pt-32">
        <div className="text-sm text-muted">Failed to load policies.</div>
        <button
          onClick={() => refetch()}
          className="text-sm font-medium text-primary bg-transparent border border-primary rounded-xl px-4 py-2 cursor-pointer hover:bg-primary hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
        >
          Retry
        </button>
      </div>
    );
  }

  const activePolicies = policies?.filter((p) => p.status === 'active') ?? [];
  const hasActivePolicies = activePolicies.length > 0;

  const nextRenewalFormatted = nextRenewal
    ? new Date(nextRenewal).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : null;

  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-6 md:gap-8">
      {/* Page header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
            Insurance
          </span>
          <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">
            Your Coverage.
          </h1>
        </div>
        <Link href="/quotes">
          <BtnSecondary>
            <svg
              className="w-4 h-4 stroke-body"
              viewBox="0 0 24 24"
              fill="none"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 12h14" />
              <path d="M12 5v14" />
            </svg>
            Add coverage
          </BtnSecondary>
        </Link>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-surface border border-border rounded-2xl px-6 py-5 flex flex-col gap-1">
          <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
            Active policies
          </span>
          <span className="font-heading text-2xl font-medium text-heading tracking-[-0.768px] leading-none">
            {activeCount}
          </span>
          <span className="text-xs font-normal text-muted tracking-normal leading-[1.2]">
            {activeCount === 0
              ? 'No active policies'
              : `${activeCount} active polic${activeCount === 1 ? 'y' : 'ies'}`}
          </span>
        </div>
        <div className="bg-surface border border-border rounded-2xl px-6 py-5 flex flex-col gap-1">
          <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
            Total coverage
          </span>
          <span className="font-heading text-2xl font-medium text-heading tracking-[-0.768px] leading-none">
            {totalCoverage != null ? `$${totalCoverage.toLocaleString()}` : '\u2014'}
          </span>
          <span className="text-xs font-normal text-muted tracking-normal leading-[1.2]">
            Across all coverages
          </span>
        </div>
        <div className="bg-surface border border-border rounded-2xl px-6 py-5 flex flex-col gap-1">
          <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
            Next renewal
          </span>
          <span className="font-heading text-2xl font-medium text-heading tracking-[-0.768px] leading-none">
            {nextRenewalFormatted ?? '\u2014'}
          </span>
          <span className="text-xs font-normal text-muted tracking-normal leading-[1.2]">
            {nextRenewalFormatted ? 'Earliest expiration' : '\u2014'}
          </span>
        </div>
        <div className="bg-surface border border-border rounded-2xl px-6 py-5 flex flex-col gap-1">
          <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
            Open claims
          </span>
          <span className="font-heading text-2xl font-medium text-heading tracking-[-0.768px] leading-none">
            {openClaimsCount}
          </span>
          <Link
            href="/claims"
            className="text-xs font-medium text-primary tracking-normal leading-[1.2] hover:underline no-underline"
          >
            View claims →
          </Link>
        </div>
      </div>

      {/* Recommended Coverages */}
      <RecommendedSection />

      {/* Active Policies */}
      <div className="flex flex-col gap-3">
        <div className="pl-4 text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
          Active policies
        </div>
        {!hasActivePolicies ? (
          <div className="border border-dashed border-border rounded-2xl text-center py-12 px-10">
            <div className="mb-3">
              <ShieldIcon className="w-6 h-6 stroke-muted inline-block" />
            </div>
            <div className="text-sm text-muted mb-1">No active policies yet.</div>
            <div className="text-[13px] text-muted leading-[1.5]">
              Get started by exploring coverage options tailored to your business.
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {activePolicies.map((policy) => (
              <PolicyCard
                key={policy.id}
                policy={policy}
                onClick={() => setSelectedPolicy(policy)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Policy Detail Modal */}
      <PolicyDetailModal
        policy={selectedPolicy}
        open={!!selectedPolicy}
        onClose={() => setSelectedPolicy(null)}
        onModifyLimits={() => {
          setModifyPolicy(selectedPolicy);
          setDisclaimerOpen(true);
        }}
      />

      {/* Limit Disclaimer Modal */}
      <LimitDisclaimerModal
        open={disclaimerOpen}
        onClose={() => setDisclaimerOpen(false)}
        onConfirm={() => setModifyLimitsOpen(true)}
      />

      {/* Modify Limits Modal */}
      <ModifyLimitsModal
        policy={modifyPolicy}
        open={modifyLimitsOpen}
        onClose={() => {
          setModifyLimitsOpen(false);
          setModifyPolicy(null);
        }}
      />
    </div>
  );
}
