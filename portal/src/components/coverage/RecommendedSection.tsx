import Image from 'next/image';
import Link from 'next/link';
import { BtnSecondary } from '@/components/ui/button';
import { ArrowRightIcon } from '@/components/icons';
import { RECOMMENDED_COVERAGES } from './constants';
import { CoverageLabel } from './CoverageTooltip';

export function RecommendedSection() {
  return (
    <div className="bg-bg border border-border rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-4 sm:px-6 pt-6 pb-4 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="flex flex-col gap-2">
          <span className="text-[11px] font-semibold text-primary uppercase tracking-[0.5px] leading-[1.2]">
            Recommended for your stage
          </span>
          <div className="font-heading text-[20px] sm:text-[22px] font-normal text-heading tracking-[-0.5px] leading-[1.3]">
            Companies like yours typically
            <br className="hidden sm:block" />
            add these next.
          </div>
        </div>
        <Link href="/quotes" className="shrink-0">
          <BtnSecondary>
            See all coverage
            <ArrowRightIcon size={14} />
          </BtnSecondary>
        </Link>
      </div>

      {/* Two-column grid — stacks on mobile */}
      <div className="px-4 sm:px-6 pb-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {RECOMMENDED_COVERAGES.map((rec, idx) => (
          <div key={idx} className="bg-white border border-border rounded-2xl overflow-hidden flex flex-col">
            {/* Image area */}
            <div className="h-[160px] bg-bg flex items-center justify-center overflow-hidden">
              <Image
                src={rec.image}
                alt={rec.name}
                width={400}
                height={160}
                className="w-full h-full object-cover"
              />
            </div>

            {/* Content */}
            <div className="p-5 flex flex-col gap-3 flex-1">
              <div className="flex flex-col gap-2">
                <span className="text-[15px] font-semibold text-heading leading-[1.2]">
                  <CoverageLabel slug={rec.slug} />
                </span>
                <span className="text-[13px] font-normal text-muted leading-[1.5]">
                  {rec.desc}
                </span>
              </div>

              <Link href="/quotes" className="text-sm font-medium text-primary no-underline hover:underline">
                Get a quote &nbsp;&gt;
              </Link>

              {/* Social proof */}
              <div className="mt-auto pt-3 border-t border-border flex items-center gap-2">
                <div className="flex -space-x-1.5">
                  {rec.avatars.map((av, i) => (
                    <div
                      key={i}
                      className="w-6 h-6 rounded-full border-2 border-white flex items-center justify-center text-[10px] font-bold text-white"
                      style={{ backgroundColor: av.color }}
                    >
                      {av.letter}
                    </div>
                  ))}
                </div>
                <span className="text-xs font-normal text-muted">{rec.socialText}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
