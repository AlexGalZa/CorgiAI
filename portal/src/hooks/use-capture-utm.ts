/**
 * Capture UTM attribution from window.location + document.referrer.
 *
 * Reads utm_source / utm_medium / utm_campaign from the current URL on mount,
 * stashes them in sessionStorage so they survive internal navigation across
 * the quote flow, and exposes the merged payload to callers that need to
 * attach it to a quote creation request.
 */
import { useEffect, useState } from 'react';

export interface UtmAttribution {
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  referrer_url: string;
  landing_page_url: string;
}

const STORAGE_KEY = 'corgi.utm_attribution';

const EMPTY: UtmAttribution = {
  utm_source: '',
  utm_medium: '',
  utm_campaign: '',
  referrer_url: '',
  landing_page_url: '',
};

function truncate(value: string, max: number): string {
  if (!value) return '';
  return value.length > max ? value.slice(0, max) : value;
}

function readFromStorage(): UtmAttribution | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<UtmAttribution>;
    return { ...EMPTY, ...parsed };
  } catch {
    return null;
  }
}

function writeToStorage(attribution: UtmAttribution): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(attribution));
  } catch {
    // sessionStorage may be unavailable (Safari private mode, quota, etc.) — non-fatal.
  }
}

export function captureUtmFromWindow(): UtmAttribution {
  if (typeof window === 'undefined') return EMPTY;

  const params = new URLSearchParams(window.location.search);
  const fromUrl: UtmAttribution = {
    utm_source: truncate(params.get('utm_source') ?? '', 64),
    utm_medium: truncate(params.get('utm_medium') ?? '', 64),
    utm_campaign: truncate(params.get('utm_campaign') ?? '', 128),
    referrer_url: document.referrer ?? '',
    landing_page_url: window.location.href,
  };

  const hasAnyUtm = fromUrl.utm_source || fromUrl.utm_medium || fromUrl.utm_campaign;
  if (hasAnyUtm) {
    writeToStorage(fromUrl);
    return fromUrl;
  }

  const stored = readFromStorage();
  if (stored) return stored;

  // No UTM params and nothing stored — still preserve referrer/landing page
  // so backend can see un-attributed direct traffic.
  writeToStorage(fromUrl);
  return fromUrl;
}

export function useCaptureUtm(): UtmAttribution {
  const [attribution, setAttribution] = useState<UtmAttribution>(EMPTY);

  useEffect(() => {
    setAttribution(captureUtmFromWindow());
  }, []);

  return attribution;
}
