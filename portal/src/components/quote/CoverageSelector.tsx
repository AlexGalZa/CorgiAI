'use client';

import { Coverages, CustomCoverages, type AllCoverageType, type CoverageType, type CustomCoverageType } from '@/lib/quote-flow';
import { CheckIcon } from '@/components/icons';

interface Props {
  selectedCoverages: AllCoverageType[];
  onToggle: (id: AllCoverageType) => void;
}

export function CoverageSelector({ selectedCoverages, onToggle }: Props) {
  const instantCoverages = Object.values(Coverages);
  const brokeredCoverages = Object.values(CustomCoverages);

  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <div className="flex gap-3 items-baseline mb-3">
          <h2 className="font-heading text-lg font-medium text-heading">Instant Coverage</h2>
          <span className="text-sm text-body">Bind online in minutes</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {instantCoverages.map((c) => (
            <CoverageCard
              key={c.id}
              id={c.id}
              name={c.name}
              description={c.description}
              features={c.includedFeatures}
              selected={selectedCoverages.includes(c.id)}
              onToggle={() => onToggle(c.id)}
              instant
            />
          ))}
        </div>
      </div>

      <div className="space-y-1">
        <h2 className="font-heading text-lg font-medium text-heading mb-3">
          Need Something Else?
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {brokeredCoverages.map((c) => (
            <CoverageCard
              key={c.id}
              id={c.id}
              name={c.name}
              description={c.description}
              selected={selectedCoverages.includes(c.id)}
              onToggle={() => onToggle(c.id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function CoverageCard({
  id,
  name,
  description,
  features,
  selected,
  onToggle,
  instant,
}: {
  id: string;
  name: string;
  description: string;
  features?: string[];
  selected: boolean;
  onToggle: () => void;
  instant?: boolean;
}) {
  return (
    <div
      onClick={onToggle}
      className={`
        relative cursor-pointer rounded-2xl border p-4 transition-all
        ${selected ? 'border-primary bg-primary/5 shadow-[inset_0_0_0_1.5px_var(--color-primary)]' : 'border-border bg-surface hover:border-border-accent'}
      `}
    >
      <div className="flex items-start gap-3">
        <div className={`
          w-5 h-5 rounded-lg border flex items-center justify-center shrink-0 mt-0.5 transition-colors
          ${selected ? 'bg-primary border-primary' : 'border-border'}
        `}>
          {selected && <CheckIcon size={12} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-semibold text-heading">{name}</span>
            {instant && (
              <span className="text-[10px] font-medium text-primary bg-badge-orange-bg px-1.5 py-0.5 rounded-full">
                Instant
              </span>
            )}
          </div>
          <p className="text-[11px] text-muted leading-[1.5]">{description}</p>
          {features && features.length > 0 && selected && (
            <ul className="mt-2 space-y-1">
              {features.map((f) => (
                <li key={f} className="text-[11px] text-body flex items-start gap-1.5">
                  <span className="text-primary mt-0.5">✓</span>
                  {f}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
