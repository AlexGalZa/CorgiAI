'use client';

import { type ReactNode } from 'react';

interface Props {
  title: string;
  description?: string;
  children: ReactNode;
}

export function QuoteFormLayout({ title, description, children }: Props) {
  return (
    <div className="mx-auto max-w-[640px]">
      <div className="mb-6">
        <h1 className="font-heading text-2xl font-medium text-heading tracking-[-0.768px] leading-none mb-2">
          {title}
        </h1>
        {description && (
          <p className="text-sm text-body leading-[1.6]">{description}</p>
        )}
      </div>
      {children}
    </div>
  );
}
