'use client';

import type { ReactNode, ButtonHTMLAttributes } from 'react';

/* ─── 3D "raised" button variants ─── */

interface Btn3DProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  fullWidth?: boolean;
}

export function BtnDark({ children, fullWidth, className = '', ...props }: Btn3DProps) {
  return (
    <button
      className={`bg-btn-dark-bg rounded-xl pb-1 inline-flex flex-col items-center border-none cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${fullWidth ? 'w-full' : ''} ${className}`}
      {...props}
    >
      <div className={`bg-btn-dark rounded-xl px-4 py-2 flex items-center justify-center gap-1 text-sm font-medium text-white tracking-normal leading-[1.2] whitespace-nowrap hover:bg-heading transition-colors ${fullWidth ? 'w-full' : ''}`}>
        {children}
      </div>
    </button>
  );
}

export function BtnPrimary({ children, fullWidth, className = '', ...props }: Btn3DProps) {
  return (
    <button
      className={`bg-primary-dark rounded-xl pb-1 inline-flex flex-col items-center border-none cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${fullWidth ? 'w-full' : ''} ${className}`}
      {...props}
    >
      <div className={`bg-primary rounded-xl px-4 py-2 flex items-center justify-center gap-1 text-sm font-medium text-white tracking-normal leading-[1.2] whitespace-nowrap hover:bg-primary-dark transition-colors ${fullWidth ? 'w-full' : ''}`}>
        {children}
      </div>
    </button>
  );
}

export function BtnSecondary({ children, className = '', ...props }: Btn3DProps) {
  return (
    <button
      className={`bg-surface shadow-[inset_0_0_0_1px_var(--color-border)] rounded-xl pb-1 inline-flex flex-col items-center border-none cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${className}`}
      {...props}
    >
      <div className="bg-surface border border-border rounded-xl px-4 py-2 flex items-center justify-center gap-1 text-sm font-medium text-body tracking-normal leading-[1.2] whitespace-nowrap hover:bg-bg transition-colors">
        {children}
      </div>
    </button>
  );
}

export function Btn3DWhite({ children, fullWidth, className = '', ...props }: Btn3DProps) {
  return (
    <button
      className={`bg-white shadow-[inset_0_0_0_1px_var(--color-border)] rounded-xl pb-1 cursor-pointer border-none flex flex-col items-center focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${fullWidth ? 'w-full' : ''} ${className}`}
      {...props}
    >
      <div className={`flex items-center justify-center gap-1 bg-white border border-border rounded-xl px-4 py-2 text-sm font-medium text-heading tracking-normal font-sans transition-colors hover:bg-bg ${fullWidth ? 'w-full' : ''}`}>
        {children}
      </div>
    </button>
  );
}

export function Btn3DOrange({ children, fullWidth, className = '', ...props }: Btn3DProps) {
  return (
    <button
      className={`bg-primary-dark rounded-xl pb-1 cursor-pointer border-none flex flex-col items-center focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${fullWidth ? 'w-full' : ''} ${className}`}
      {...props}
    >
      <div className={`flex items-center justify-center gap-1 bg-primary rounded-xl px-4 py-2 text-sm font-medium text-white tracking-normal font-sans transition-opacity hover:opacity-92 ${fullWidth ? 'w-full' : ''}`}>
        {children}
      </div>
    </button>
  );
}

export function Btn3DDark({ children, fullWidth, className = '', ...props }: Btn3DProps) {
  return (
    <button
      className={`bg-btn-dark-bg rounded-xl pb-1 cursor-pointer border-none flex flex-col items-center focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${fullWidth ? 'w-full' : ''} ${className}`}
      {...props}
    >
      <div className={`flex items-center justify-center gap-1 bg-heading rounded-xl px-4 py-2 text-sm font-medium text-white tracking-normal font-sans transition-opacity hover:opacity-88 ${fullWidth ? 'w-full' : ''}`}>
        {children}
      </div>
    </button>
  );
}

export function BtnLink({ children, className = '', ...props }: Btn3DProps) {
  return (
    <button
      className={`text-sm font-medium text-primary tracking-normal leading-[1.2] cursor-pointer bg-transparent border-none font-sans p-0 self-start hover:underline focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function BtnDanger({ children, className = '', ...props }: Btn3DProps) {
  return (
    <button
      className={`bg-white shadow-[inset_0_0_0_1px_var(--color-danger)] border-none rounded-xl pb-1 cursor-pointer flex flex-col items-center focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${className}`}
      {...props}
    >
      <div className="flex items-center justify-center gap-1 bg-white border border-danger rounded-xl px-4 py-2 text-xs font-normal text-danger font-sans tracking-normal leading-[1.2] w-full">
        {children}
      </div>
    </button>
  );
}

export function BtnDangerConfirm({ children, className = '', ...props }: Btn3DProps) {
  return (
    <button
      className={`bg-white shadow-[inset_0_0_0_1px_var(--color-danger)] border-none rounded-xl pb-1 cursor-pointer flex-1 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none ${className}`}
      {...props}
    >
      <div className="flex items-center justify-center gap-1 bg-white border border-danger rounded-xl px-4 py-2 text-sm font-medium text-danger font-sans tracking-normal leading-[1.2]">
        {children}
      </div>
    </button>
  );
}
