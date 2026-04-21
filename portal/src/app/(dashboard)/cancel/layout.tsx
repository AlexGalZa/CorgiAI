'use client';

import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

const STEPS: { id: string; path: string; label: string }[] = [
  { id: 'confirm', path: '/cancel/confirm', label: 'Confirm' },
  { id: 'alternatives', path: '/cancel/alternatives', label: 'Alternatives' },
  { id: 'effective-date', path: '/cancel/effective-date', label: 'Effective date' },
  { id: 'success', path: '/cancel/success', label: 'Done' },
];

export default function CancelLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const currentIndex = STEPS.findIndex((s) => pathname?.endsWith(s.path));

  return (
    <div className="max-w-[800px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-6 md:gap-8">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
          Cancel policy
        </span>
        <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">
          We&apos;re sorry to see you go
        </h1>
      </div>

      {/* Progress indicator */}
      <nav aria-label="Cancellation progress" className="flex items-center gap-2">
        {STEPS.map((step, i) => {
          const isCompleted = currentIndex > i;
          const isActive = currentIndex === i;
          return (
            <div key={step.id} className="flex items-center gap-2 flex-1">
              <div className="flex items-center gap-2 min-w-0">
                <div
                  className={`
                    shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-semibold
                    ${isActive ? 'bg-primary text-white' : ''}
                    ${isCompleted ? 'bg-heading text-white' : ''}
                    ${!isActive && !isCompleted ? 'bg-border text-muted' : ''}
                  `}
                >
                  {isCompleted ? (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                  ) : (
                    i + 1
                  )}
                </div>
                <span
                  className={`text-xs font-medium truncate hidden sm:inline ${
                    isActive ? 'text-heading' : 'text-muted'
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`flex-1 h-px ${isCompleted ? 'bg-heading' : 'bg-border'}`}
                />
              )}
            </div>
          );
        })}
      </nav>

      {/* Step content */}
      <div className="flex flex-col gap-4">{children}</div>
    </div>
  );
}
