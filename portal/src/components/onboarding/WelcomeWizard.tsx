'use client';

import { useState, useEffect } from 'react';

const STORAGE_KEY = 'corgi_onboarding_complete';

const STEPS = [
  {
    title: 'Welcome to Corgi',
    subtitle: 'Your business insurance, simplified.',
    description:
      'Corgi helps you find, manage, and maintain the right coverage for your company — all in one place.',
    icon: (
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="text-primary" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
  },
  {
    title: 'Your Coverage',
    subtitle: 'Everything at a glance.',
    description:
      'Your dashboard shows active policies, upcoming renewals, and recommended coverages — so you always know where you stand.',
    icon: (
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="text-primary" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="9" rx="1" />
        <rect x="14" y="3" width="7" height="5" rx="1" />
        <rect x="14" y="12" width="7" height="9" rx="1" />
        <rect x="3" y="16" width="7" height="5" rx="1" />
      </svg>
    ),
  },
  {
    title: 'Get a Quote',
    subtitle: 'Coverage in minutes, not weeks.',
    description:
      'Tell us about your business, pick a coverage type, and we\'ll generate a quote instantly. You can bind coverage right from the portal.',
    icon: (
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="text-primary" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    ),
  },
  {
    title: "You're Ready!",
    subtitle: 'Go explore your portal.',
    description:
      'That\'s it — you\'re all set. If you ever need help, look for the orange "Talk to us" buttons throughout the app.',
    icon: (
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" className="text-primary" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <path d="M22 4 12 14.01l-3-3" />
      </svg>
    ),
  },
];

export default function WelcomeWizard() {
  const [visible, setVisible] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    // Only run on the client
    if (typeof window === 'undefined') return;
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) setVisible(true);
  }, []);

  const dismiss = () => {
    setExiting(true);
    setTimeout(() => {
      localStorage.setItem(STORAGE_KEY, 'true');
      setVisible(false);
    }, 250);
  };

  const next = () => {
    if (currentStep === STEPS.length - 1) {
      dismiss();
    } else {
      setCurrentStep((s) => s + 1);
    }
  };

  const back = () => {
    if (currentStep > 0) setCurrentStep((s) => s - 1);
  };

  if (!visible) return null;

  const step = STEPS[currentStep];
  const isLast = currentStep === STEPS.length - 1;

  return (
    <div
      className={`fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm transition-opacity duration-300 ${
        exiting ? 'opacity-0' : 'opacity-100'
      }`}
    >
      <div className="w-full max-w-[440px] bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden mx-4">
        {/* Content */}
        <div className="px-8 pt-8 pb-6 flex flex-col items-center text-center gap-4">
          {step.icon}
          <div className="flex flex-col gap-1">
            <h2 className="font-heading text-2xl font-medium text-heading tracking-[-0.768px] leading-none m-0">
              {step.title}
            </h2>
            <p className="text-sm font-medium text-primary m-0">{step.subtitle}</p>
          </div>
          <p className="text-sm text-muted leading-relaxed m-0 max-w-[340px]">
            {step.description}
          </p>
        </div>

        {/* Footer */}
        <div className="px-8 pb-8 flex flex-col gap-4">
          {/* Step dots */}
          <div className="flex items-center justify-center gap-2">
            {STEPS.map((_, i) => (
              <span
                key={i}
                className={`w-2 h-2 rounded-full transition-all ${
                  i === currentStep
                    ? 'bg-primary w-6'
                    : i < currentStep
                    ? 'bg-primary/40'
                    : 'bg-border'
                }`}
              />
            ))}
          </div>

          {/* Buttons */}
          <div className="flex items-center gap-3">
            {currentStep > 0 && (
              <button
                onClick={back}
                className="flex-1 py-2.5 px-4 rounded-xl border border-border bg-surface text-sm font-medium text-heading cursor-pointer font-sans transition-colors hover:bg-bg"
              >
                Back
              </button>
            )}
            <button
              onClick={next}
              className="flex-1 py-2.5 px-4 rounded-xl border-none bg-primary text-white text-sm font-medium cursor-pointer font-sans transition-colors hover:bg-primary-dark"
            >
              {isLast ? "Let's go!" : 'Next'}
            </button>
          </div>

          {/* Skip */}
          {!isLast && (
            <button
              onClick={dismiss}
              className="bg-transparent border-none text-xs text-muted cursor-pointer font-sans p-0 hover:text-body transition-colors"
            >
              Skip intro
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
