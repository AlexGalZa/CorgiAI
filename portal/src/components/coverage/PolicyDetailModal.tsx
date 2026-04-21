import { useState } from 'react';
import Image from 'next/image';
import { Modal } from '@/components/ui/modal';
import { Badge } from '@/components/ui/badge';
import { Btn3DWhite, Btn3DOrange } from '@/components/ui/button';
import { CloseIcon, DownloadIcon } from '@/components/icons';
import { formatCurrency } from '@/lib/utils';
import type { APIPolicy } from '@/types';
import { getCoverageLabel, getCoverageImage, formatPolicyDate, COVERAGE_TOOLTIPS } from './constants';
import { CoverageLabel } from './CoverageTooltip';
import { FileIcon, EditIcon } from './Icons';

export interface PolicyDetailModalProps {
  policy: APIPolicy | null;
  open: boolean;
  onClose: () => void;
  onModifyLimits: () => void;
}

/* ─── "What's Covered" data per coverage type ─── */

interface CoverageInfo {
  perils: string[];
  exclusions: string[];
}

const COVERAGE_PERILS: Record<string, CoverageInfo> = {
  'technology-errors-and-omissions': {
    perils: [
      'Software defects & bugs causing client losses',
      'Data loss or corruption from your services',
      'Service delivery failures & missed deadlines',
      'Breach of contract claims from clients',
      'Intellectual property infringement (in your work product)',
      'Failure of technology to perform as promised',
    ],
    exclusions: [
      'Intentional or criminal acts',
      'Bodily injury or property damage (covered by GL)',
      'Prior known claims or circumstances',
      'Employment-related disputes',
      'Patent infringement claims',
      'Contractual liability beyond professional services',
    ],
  },
  'cyber-liability': {
    perils: [
      'Data breaches & unauthorized access',
      'Ransomware attacks & cyber extortion',
      'Business interruption from cyber events',
      'Notification costs for affected individuals',
      'Credit monitoring & identity restoration',
      'Regulatory fines & penalties',
      'Forensic investigation costs',
    ],
    exclusions: [
      'Acts of war or terrorism',
      'Unencrypted devices (some policies)',
      'Known vulnerabilities left unpatched',
      'Intentional employee misconduct',
      'Infrastructure failures unrelated to cyber events',
      'Prior breaches or incidents',
    ],
  },
  'directors-and-officers': {
    perils: [
      'Shareholder lawsuits & derivative actions',
      'Regulatory investigations & proceedings',
      'Management decisions resulting in financial loss',
      'Securities claims & violations',
      'Wrongful acts in capacity as director/officer',
      'Defense costs & legal fees',
    ],
    exclusions: [
      'Fraud, dishonesty, or criminal conduct',
      'Personal profit or illegal remuneration',
      'Bodily injury & property damage',
      'Prior or pending litigation',
      'Pollution-related claims',
      'Professional services errors (covered by E&O)',
    ],
  },
  'commercial-general-liability': {
    perils: [
      'Bodily injury to third parties',
      'Property damage to third-party property',
      'Advertising injury & defamation',
      'Products & completed operations liability',
      'Medical expenses for injured parties',
      'Legal defense costs',
    ],
    exclusions: [
      'Professional errors & omissions',
      'Employee injuries (covered by Workers\' Comp)',
      'Automobile-related liability',
      'Pollution & environmental damage',
      'Intentional acts & expected damages',
      'Contractual liability (beyond insured contracts)',
    ],
  },
  'employment-practices-liability': {
    perils: [
      'Wrongful termination claims',
      'Discrimination (age, race, gender, disability)',
      'Sexual harassment allegations',
      'Retaliation & whistleblower claims',
      'Wage & hour disputes',
      'Failure to promote or hire',
    ],
    exclusions: [
      'Criminal or fraudulent acts',
      'ERISA & benefits plan disputes',
      'Workers\' compensation claims',
      'COBRA & WARN Act violations',
      'Intentional violation of law by management',
      'Prior known employment disputes',
    ],
  },
  'fiduciary-liability': {
    perils: [
      'Mismanagement of employee benefit plans',
      'Breach of fiduciary duty under ERISA',
      'Errors in plan administration',
      'Imprudent investment decisions',
      'Failure to monitor plan expenses',
      'Prohibited transaction claims',
    ],
    exclusions: [
      'Fraud & dishonesty by fiduciaries',
      'Bodily injury & property damage',
      'Tax penalties & fines',
      'Prior known breaches',
      'Claims by plan sponsors against themselves',
      'Defined benefit plan underfunding',
    ],
  },
  'hired-and-non-owned-auto': {
    perils: [
      'Liability for accidents in rented/hired vehicles',
      'Liability for employee-owned vehicles on business',
      'Bodily injury to third parties in auto accidents',
      'Property damage from covered auto accidents',
      'Legal defense costs for covered claims',
    ],
    exclusions: [
      'Damage to the hired/rented vehicle itself',
      'Company-owned vehicles (need commercial auto)',
      'DUI or illegal activity',
      'Vehicles used for racing or livery',
      'Loading & unloading of goods (some policies)',
    ],
  },
  'media-liability': {
    perils: [
      'Copyright & trademark infringement',
      'Defamation, libel & slander claims',
      'Invasion of privacy from published content',
      'Plagiarism & unauthorized use of ideas',
      'Misappropriation of trade secrets',
      'Emotional distress from media content',
    ],
    exclusions: [
      'Intentional or knowing violations',
      'Contractual liability',
      'Bodily injury & property damage',
      'Criminal acts',
      'Patent infringement',
      'Prior published content (retroactive date applies)',
    ],
  },
};

function getDefaultCoverageInfo(): CoverageInfo {
  return {
    perils: [
      'Third-party claims related to covered activities',
      'Legal defense costs & settlements',
      'Regulatory investigation expenses',
    ],
    exclusions: [
      'Intentional or criminal acts',
      'Prior known claims',
      'Bodily injury & property damage (unless specifically covered)',
    ],
  };
}

type Tab = 'overview' | 'whats-covered';

export function PolicyDetailModal({
  policy,
  open,
  onClose,
  onModifyLimits,
}: PolicyDetailModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  if (!policy) return null;

  const slug = policy.coverage_slug || policy.coverage_type;
  const coverageLabel = getCoverageLabel(slug);
  const coverageImage = getCoverageImage(slug);
  const coverageInfo = COVERAGE_PERILS[slug] || getDefaultCoverageInfo();
  const description = COVERAGE_TOOLTIPS[slug] || `Coverage provided under your ${coverageLabel} policy.`;

  return (
    <Modal open={open} onClose={() => { onClose(); setActiveTab('overview'); }} width={600} titleId="policy-detail-title">
      {/* Header with corgi illustration */}
      <div className="bg-bg border-b border-border h-[240px] flex flex-col items-center justify-end overflow-hidden relative px-6">
        <button
          onClick={() => { onClose(); setActiveTab('overview'); }}
          aria-label="Close"
          className="absolute top-5 right-5 cursor-pointer w-6 h-6 flex items-center justify-center bg-transparent border-none p-0"
        >
          <CloseIcon size={20} color="var(--color-muted)" />
        </button>
        {coverageImage && (
          <Image
            src={coverageImage}
            alt={coverageLabel}
            width={552}
            height={200}
            className="w-full object-contain"
            priority
          />
        )}
      </div>

      {/* Title + Badge */}
      <div className="px-6 pt-5 pb-0 flex items-center justify-between">
        <div id="policy-detail-title" className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
          <CoverageLabel slug={slug} />
        </div>
        <Badge variant="active" />
      </div>

      {/* Tab navigation */}
      <div className="px-6 pt-4 flex gap-0 border-b border-border">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 bg-transparent border-x-0 border-t-0 cursor-pointer font-sans transition-colors ${
            activeTab === 'overview'
              ? 'text-primary border-primary'
              : 'text-muted border-transparent hover:text-heading'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('whats-covered')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 bg-transparent border-x-0 border-t-0 cursor-pointer font-sans transition-colors ${
            activeTab === 'whats-covered'
              ? 'text-primary border-primary'
              : 'text-muted border-transparent hover:text-heading'
          }`}
        >
          What&apos;s Covered
        </button>
      </div>

      {/* ─── Overview Tab ─── */}
      {activeTab === 'overview' && (
        <>
          <div className="p-5 px-6 border-b border-border flex flex-col gap-4">
            {/* Details table */}
            <div className="bg-bg border border-border rounded-lg overflow-hidden">
              <div className="flex items-center justify-between border-b border-border">
                <div className="p-3 text-sm font-normal text-body w-[240px]">Policy number</div>
                <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                  {policy.policy_number}
                </div>
              </div>
              <div className="flex items-center justify-between border-b border-border">
                <div className="p-3 text-sm font-normal text-body w-[240px]">Carrier</div>
                <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                  {policy.carrier}
                </div>
              </div>
              <div className="flex items-center justify-between border-b border-border">
                <div className="p-3 text-sm font-normal text-body w-[240px]">Effective</div>
                <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                  {formatPolicyDate(policy.effective_date)} – {formatPolicyDate(policy.expiration_date)}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="p-3 text-sm font-normal text-body w-[240px]">Annual premium</div>
                <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                  {formatCurrency(policy.premium)}
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-3">
              <Btn3DWhite fullWidth>
                <DownloadIcon size={16} /> Download PDF
              </Btn3DWhite>
              <Btn3DWhite fullWidth>
                <FileIcon /> Get certificate
              </Btn3DWhite>
            </div>
          </div>

          {/* Current limits section */}
          <div className="p-5 px-6 flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <div className="px-1 text-[11px] font-semibold text-muted uppercase leading-[1.2]">
                Current limits
              </div>
              <div className="bg-white border border-border rounded-lg overflow-hidden">
                <div className="flex items-center justify-between">
                  <div className="p-3 text-sm font-normal text-body w-[240px]">Per occurrence</div>
                  <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                    {formatCurrency(policy.per_occurrence_limit ?? 0)}
                  </div>
                </div>
                <div className="flex items-center justify-between border-t border-border">
                  <div className="p-3 text-sm font-normal text-body w-[240px]">Aggregate</div>
                  <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                    {formatCurrency(policy.aggregate_limit ?? 0)}
                  </div>
                </div>
                <div className="flex items-center justify-between border-t border-border">
                  <div className="p-3 text-sm font-normal text-body w-[240px]">Retention</div>
                  <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                    {formatCurrency(policy.retention ?? 0)}
                  </div>
                </div>
              </div>
            </div>

            <Btn3DOrange
              fullWidth
              onClick={() => {
                onClose();
                setActiveTab('overview');
                onModifyLimits();
              }}
            >
              <EditIcon color="currentColor" /> Modify limits
            </Btn3DOrange>
          </div>
        </>
      )}

      {/* ─── What's Covered Tab ─── */}
      {activeTab === 'whats-covered' && (
        <div className="p-5 px-6 flex flex-col gap-5">
          {/* Description */}
          <div className="flex flex-col gap-2">
            <div className="text-sm text-body leading-[1.6]">
              {description}
            </div>
          </div>

          {/* Key Covered Perils */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <div className="w-1 h-4 bg-primary rounded-full" />
              <div className="text-[11px] font-semibold text-primary uppercase tracking-[0.3px]">
                What&apos;s covered
              </div>
            </div>
            <div className="bg-bg border border-border rounded-xl p-4">
              <ul className="flex flex-col gap-2 m-0 pl-0 list-none">
                {coverageInfo.perils.map((peril) => (
                  <li key={peril} className="flex items-start gap-2.5 text-sm text-heading leading-[1.4]">
                    <svg className="w-4 h-4 shrink-0 mt-0.5 text-success" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    {peril}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Key Exclusions */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <div className="w-1 h-4 bg-danger rounded-full" />
              <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">
                Common exclusions
              </div>
            </div>
            <div className="bg-white border border-border rounded-xl p-4">
              <ul className="flex flex-col gap-2 m-0 pl-0 list-none">
                {coverageInfo.exclusions.map((exclusion) => (
                  <li key={exclusion} className="flex items-start gap-2.5 text-sm text-body leading-[1.4]">
                    <svg className="w-4 h-4 shrink-0 mt-0.5 text-danger" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                    {exclusion}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Limits Summary */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <div className="w-1 h-4 bg-primary rounded-full" />
              <div className="text-[11px] font-semibold text-primary uppercase tracking-[0.3px]">
                Your limits
              </div>
            </div>
            <div className="border border-border rounded-xl overflow-hidden">
              <div className="flex items-center justify-between bg-bg">
                <div className="p-3 text-sm font-normal text-body w-[200px]">Per occurrence</div>
                <div className="p-3 text-sm font-semibold text-heading tracking-[-0.21px]">
                  {formatCurrency(policy.per_occurrence_limit ?? 0)}
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-border bg-bg">
                <div className="p-3 text-sm font-normal text-body w-[200px]">Aggregate</div>
                <div className="p-3 text-sm font-semibold text-heading tracking-[-0.21px]">
                  {formatCurrency(policy.aggregate_limit ?? 0)}
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-border bg-bg">
                <div className="p-3 text-sm font-normal text-body w-[200px]">Retention</div>
                <div className="p-3 text-sm font-semibold text-heading tracking-[-0.21px]">
                  {formatCurrency(policy.retention ?? 0)}
                </div>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-muted leading-[1.5]">
            This is a summary for informational purposes. Please review your full policy document for complete terms, conditions, and exclusions.
          </div>
        </div>
      )}
    </Modal>
  );
}
