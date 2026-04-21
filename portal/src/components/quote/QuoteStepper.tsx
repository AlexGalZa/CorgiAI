'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { CheckIcon } from '@/components/icons';
import { useQuoteStore } from '@/stores/use-quote-store';
import {
  getVisibleSteps,
  buildStepPath,
  type FormSection,
  FormSectionLabels,
  type StepId,
  type AllCoverageType,
} from '@/lib/quote-flow';

export function QuoteStepper() {
  const pathname = usePathname();
  const quoteNumber = useQuoteStore((s) => s.quoteNumber);
  const completedSteps = useQuoteStore((s) => s.completedSteps);
  const coverages = (useQuoteStore((s) => s.formData.coverages) || []) as AllCoverageType[];
  const expandedSections = useQuoteStore((s) => s.expandedSections);

  if (!quoteNumber) return null;

  const steps = getVisibleSteps(coverages);
  // Group steps by section
  const sections = new Map<FormSection, typeof steps>();
  for (const step of steps) {
    if (!sections.has(step.section)) sections.set(step.section, []);
    sections.get(step.section)!.push(step);
  }

  const isStepActive = (stepId: StepId) => {
    const stepPath = steps.find((s) => s.id === stepId);
    if (!stepPath) return false;
    return pathname === buildStepPath(stepPath, quoteNumber);
  };

  const isStepCompleted = (stepId: StepId) => completedSteps.includes(stepId);

  const orderedSections: FormSection[] = ['individual', 'company-info', 'coverage-forms', 'claims-history'];

  return (
    <nav className="w-[260px] shrink-0 border-r border-border bg-surface p-5 hidden lg:block">
      <div className="sticky top-20">
        <div className="flex flex-col gap-5">
          {orderedSections.map((sectionId) => {
            const sectionSteps = sections.get(sectionId);
            if (!sectionSteps || sectionSteps.length === 0) return null;

            // Individual steps render without section header
            if (sectionId === 'individual') {
              return sectionSteps.map((step) => (
                <StepItem
                  key={step.id}
                  name={step.name}
                  href={buildStepPath(step, quoteNumber)}
                  active={isStepActive(step.id)}
                  completed={isStepCompleted(step.id)}
                />
              ));
            }

            const isExpanded = expandedSections.includes(sectionId) || sectionSteps.some((s) => isStepActive(s.id));
            const allCompleted = sectionSteps.every((s) => isStepCompleted(s.id));

            return (
              <div key={sectionId}>
                <div className="flex items-center gap-2 mb-2">
                  {allCompleted && (
                    <span className="w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                      <CheckIcon size={10} />
                    </span>
                  )}
                  <span className="text-[11px] font-semibold text-muted uppercase tracking-wide">
                    {FormSectionLabels[sectionId]}
                  </span>
                </div>
                {isExpanded && (
                  <div className="flex flex-col gap-1 ml-1 border-l border-border pl-3">
                    {sectionSteps.map((step) => (
                      <StepItem
                        key={step.id}
                        name={step.name}
                        href={buildStepPath(step, quoteNumber)}
                        active={isStepActive(step.id)}
                        completed={isStepCompleted(step.id)}
                        compact
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

function StepItem({
  name,
  href,
  active,
  completed,
  compact = false,
}: {
  name: string;
  href: string;
  active: boolean;
  completed: boolean;
  compact?: boolean;
}) {
  return (
    <Link
      href={href}
      className={`
        flex items-center gap-2 rounded-lg transition-colors no-underline
        ${compact ? 'px-2 py-1.5 text-[11px]' : 'px-3 py-2 text-sm'}
        ${active ? 'bg-primary/10 text-primary font-medium' : completed ? 'text-heading hover:bg-bg' : 'text-muted hover:text-body'}
      `}
    >
      {completed && !active && (
        <span className="w-4 h-4 rounded-full bg-primary flex items-center justify-center shrink-0">
          <CheckIcon size={8} />
        </span>
      )}
      {active && (
        <span className="w-2 h-2 rounded-full bg-primary shrink-0" />
      )}
      <span>{name}</span>
    </Link>
  );
}
