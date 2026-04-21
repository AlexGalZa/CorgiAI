'use client';

import { useEffect } from 'react';

const BASE_TITLE = 'Corgi Insurance';

/**
 * Sets the document title for client-rendered pages.
 * Usage: usePageTitle('Quotes') → "Quotes | Corgi Insurance"
 */
export function usePageTitle(page: string) {
  useEffect(() => {
    document.title = page ? `${page} | ${BASE_TITLE}` : BASE_TITLE;
    return () => {
      document.title = BASE_TITLE;
    };
  }, [page]);
}
