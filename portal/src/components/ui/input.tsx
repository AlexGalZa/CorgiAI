'use client';

import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes, type SelectHTMLAttributes } from 'react';

const baseInputClasses = 'w-full px-3 py-2 border border-[var(--color-border-raw)] rounded-xl text-[11px] font-sans text-[var(--color-heading-raw)] outline-none bg-[var(--color-card-bg)] transition-[border-color] duration-200 min-h-9 tracking-normal focus:border-primary placeholder:text-[var(--color-muted-raw)]';

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { error?: boolean; errorId?: string }>(
  ({ error, errorId, className = '', ...props }, ref) => (
    <input
      ref={ref}
      aria-invalid={error || undefined}
      aria-describedby={error && errorId ? errorId : undefined}
      className={`${baseInputClasses} ${error ? '!border-danger' : ''} ${className}`}
      {...props}
    />
  )
);
Input.displayName = 'Input';

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className = '', ...props }, ref) => (
    <textarea
      ref={ref}
      className={`${baseInputClasses} resize-y min-h-24 ${className}`}
      {...props}
    />
  )
);
Textarea.displayName = 'Textarea';

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className = '', children, ...props }, ref) => (
    <select
      ref={ref}
      className={`${baseInputClasses} coi-select ${className}`}
      {...props}
    >
      {children}
    </select>
  )
);
Select.displayName = 'Select';

export function Label({ children, className = '', htmlFor }: { children: React.ReactNode; className?: string; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className={`text-[11px] font-semibold text-[var(--color-heading-raw)] mb-1 block tracking-normal leading-[1.2] ${className}`}>
      {children}
    </label>
  );
}
