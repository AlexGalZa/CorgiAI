'use client';

import type { ReactNode } from 'react';

interface Props {
  label: string;
  error?: string;
  helper?: string;
  required?: boolean;
  children: ReactNode;
  className?: string;
}

export function FormField({ label, error, helper, required, children, className = '' }: Props) {
  return (
    <div className={className}>
      <label className="text-[11px] font-semibold text-heading mb-1 block tracking-normal leading-[1.2]">
        {label}
        {required && <span className="text-primary ml-0.5">*</span>}
      </label>
      {children}
      {error ? (
        <p className="text-[11px] text-danger mt-1">{error}</p>
      ) : helper ? (
        <p className="text-[11px] text-muted mt-1 leading-[1.4]">{helper}</p>
      ) : null}
    </div>
  );
}
