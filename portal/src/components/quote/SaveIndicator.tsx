'use client';

import { useQuoteStore } from '@/stores/use-quote-store';

export function SaveIndicator() {
  const saveStatus = useQuoteStore((s) => s.saveStatus);

  if (saveStatus === 'idle') return null;

  return (
    <div className="text-[11px] font-medium tracking-normal">
      {saveStatus === 'saving' && <span className="text-muted">Saving...</span>}
      {saveStatus === 'saved' && <span className="text-success">Saved</span>}
      {saveStatus === 'error' && <span className="text-danger">Save failed</span>}
    </div>
  );
}
