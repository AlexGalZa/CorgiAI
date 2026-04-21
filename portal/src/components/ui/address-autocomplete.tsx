'use client';

import { useEffect, useRef, useState } from 'react';
import { Input } from '@/components/ui/input';

interface AddressResult {
  street_address: string;
  city: string;
  state: string;
  zip: string;
  country: string;
}

interface AddressAutocompleteProps {
  value: string;
  onChange: (raw: string, parsed?: AddressResult) => void;
  placeholder?: string;
  error?: boolean;
}

// ── Google Places Autocomplete ────────────────────────────────────────────────
// Loads the Google Maps JS API if NEXT_PUBLIC_GOOGLE_PLACES_KEY is set.
// Falls back to a plain text input if the key is absent.

const GMAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_PLACES_KEY ?? '';

function parseGooglePlace(place: google.maps.places.PlaceResult): AddressResult {
  const get = (type: string) =>
    place.address_components?.find((c) => c.types.includes(type))?.long_name ?? '';
  const getShort = (type: string) =>
    place.address_components?.find((c) => c.types.includes(type))?.short_name ?? '';

  const streetNumber = get('street_number');
  const route = get('route');
  return {
    street_address: [streetNumber, route].filter(Boolean).join(' '),
    city: get('locality') || get('sublocality') || get('administrative_area_level_2'),
    state: getShort('administrative_area_level_1'),
    zip: get('postal_code'),
    country: getShort('country'),
  };
}

let googleLoaded = false;
let loadPromise: Promise<void> | null = null;

function loadGoogleMaps(): Promise<void> {
  if (googleLoaded) return Promise.resolve();
  if (loadPromise) return loadPromise;

  loadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${GMAPS_KEY}&libraries=places`;
    script.async = true;
    script.defer = true;
    script.onload = () => { googleLoaded = true; resolve(); };
    script.onerror = reject;
    document.head.appendChild(script);
  });
  return loadPromise;
}

export function AddressAutocomplete({ value, onChange, placeholder, error }: AddressAutocompleteProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!GMAPS_KEY) return;

    loadGoogleMaps().then(() => {
      if (!inputRef.current) return;
      const ac = new window.google.maps.places.Autocomplete(inputRef.current, {
        types: ['address'],
        componentRestrictions: { country: ['us', 'pr', 'vi', 'gu', 'mp'] },
      });
      ac.addListener('place_changed', () => {
        const place = ac.getPlace();
        if (!place.address_components) return;
        const parsed = parseGooglePlace(place);
        onChange(place.formatted_address ?? parsed.street_address, parsed);
      });
      autocompleteRef.current = ac;
      setReady(true);
    }).catch(() => {
      // Google Maps failed to load — fallback to plain input
    });

    return () => {
      if (autocompleteRef.current) {
        window.google?.maps?.event?.clearInstanceListeners(autocompleteRef.current);
      }
    };
  }, [onChange]);

  return (
    <div className="relative">
      <Input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? (GMAPS_KEY ? 'Start typing your address…' : 'e.g. 123 Main St')}
        error={error}
        autoComplete={GMAPS_KEY ? 'off' : 'street-address'}
      />
      {GMAPS_KEY && !ready && (
        <p className="mt-1 text-[10px] text-muted">Loading address suggestions…</p>
      )}
      {!GMAPS_KEY && (
        <p className="mt-1 text-[10px] text-muted">
          Tip: add <code>NEXT_PUBLIC_GOOGLE_PLACES_KEY</code> to <code>.env.local</code> to enable address autocomplete.
        </p>
      )}
    </div>
  );
}
