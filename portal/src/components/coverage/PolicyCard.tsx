import Image from 'next/image';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Btn3DWhite } from '@/components/ui/button';
import { ShieldIcon, DownloadIcon } from '@/components/icons';
import { formatCurrency } from '@/lib/utils';
import type { APIPolicy } from '@/types';
import { getCoverageLabel, getCoverageImage, formatPolicyDate } from './constants';
import { CoverageLabel } from './CoverageTooltip';
import { FileIcon } from './Icons';

export interface PolicyCardProps {
  policy: APIPolicy;
  onClick: () => void;
}

export function PolicyCard({ policy, onClick }: PolicyCardProps) {
  const coverageLabel = getCoverageLabel(policy.coverage_slug || policy.coverage_type);
  const coverageImage = getCoverageImage(policy.coverage_slug || policy.coverage_type);

  return (
    <div
      onClick={onClick}
      className="bg-surface border border-border rounded-2xl flex flex-col md:flex-row overflow-hidden transition-all duration-200 hover:border-border-accent hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)] cursor-pointer"
    >
      {/* Left panel */}
      <div className="w-full md:w-[209px] shrink-0 border-b md:border-b-0 md:border-r border-border flex flex-col justify-between bg-bg">
        <div className="p-6 flex flex-col gap-3">
          {/* Carrier row */}
          <div className="flex items-center gap-2 h-[30px]">
            <div className="w-[30px] h-[30px] bg-white border border-border rounded-lg flex items-center justify-center shrink-0">
              <ShieldIcon className="w-4 h-4 stroke-body shrink-0" />
            </div>
            <span className="text-xs font-semibold text-heading leading-[1.2]">
              {policy.carrier}
            </span>
          </div>

          {/* Policy type + number + badge */}
          <div className="flex flex-col gap-1">
            <span className="text-base font-semibold text-heading leading-[1.2]">
              <CoverageLabel slug={policy.coverage_slug || policy.coverage_type} />
            </span>
            <span className="text-xs font-normal text-muted leading-[1.2]">
              {policy.policy_number}
            </span>
            <div className="mt-1">
              <Badge variant="active" />
            </div>
          </div>
        </div>

        {/* Corgi illustration with gradient fade — hidden on mobile */}
        {coverageImage && (
          <div className="hidden md:block w-full relative overflow-hidden">
            <div className="relative">
              <Image
                src={coverageImage}
                alt={coverageLabel}
                width={209}
                height={140}
                className="w-full block object-cover"
              />
              <div
                className="absolute inset-0"
                style={{
                  background:
                    'linear-gradient(to bottom, var(--color-bg) 14.6%, rgba(250,250,249,0) 58.9%)',
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Right panel */}
      <div className="flex-1 p-5 px-6 flex items-center">
        <div className="flex-1 flex flex-col gap-6">
          {/* Coverage details row */}
          <div className="flex flex-col sm:flex-row gap-4 sm:gap-12">
            <div className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold text-muted uppercase leading-[1.2]">
                Effective
              </span>
              <span className="text-sm font-semibold text-heading leading-[1.2]">
                {formatPolicyDate(policy.effective_date)} – {formatPolicyDate(policy.expiration_date)}
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold text-muted uppercase leading-[1.2]">
                Annual premium
              </span>
              <span className="text-sm font-semibold text-heading leading-[1.2]">
                {formatCurrency(policy.premium)}
              </span>
            </div>
          </div>

          {/* Key limits table */}
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold text-muted uppercase leading-[1.2]">
              Key limits
            </span>
            <div className="bg-surface border border-border rounded-lg overflow-hidden">
              <div className="flex items-center group transition-colors hover:bg-bg">
                <div className="w-[120px] sm:w-[240px] p-3 text-sm font-normal text-body leading-[1.2]">
                  Per occurrence
                </div>
                <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] ml-auto">
                  {formatCurrency(policy.per_occurrence_limit ?? 0)}
                </div>
              </div>
              <div className="flex items-center border-t border-border group transition-colors hover:bg-bg">
                <div className="w-[120px] sm:w-[240px] p-3 text-sm font-normal text-body leading-[1.2]">
                  Aggregate
                </div>
                <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] ml-auto">
                  {formatCurrency(policy.aggregate_limit ?? 0)}
                </div>
              </div>
              <div className="flex items-center border-t border-border group transition-colors hover:bg-bg">
                <div className="w-[120px] sm:w-[240px] p-3 text-sm font-normal text-body leading-[1.2]">
                  Retention
                </div>
                <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] ml-auto">
                  {formatCurrency(policy.retention ?? 0)}
                </div>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-3" onClick={(e) => e.stopPropagation()}>
            <Btn3DWhite>
              <DownloadIcon size={16} /> Download PDF
            </Btn3DWhite>
            <Btn3DWhite>
              <FileIcon /> Get certificate
            </Btn3DWhite>
            <Link
              href={`/policies/${policy.id}`}
              className="inline-flex items-center gap-1 text-sm font-medium text-primary bg-transparent border-none cursor-pointer p-0 self-center hover:underline focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none rounded"
            >
              View details
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
