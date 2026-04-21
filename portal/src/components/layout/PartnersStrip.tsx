/**
 * Shared investor logo strip shown on public / unauthenticated pages.
 * Drop the partner images at `public/images/partners/<slug>.webp`
 * (or `.png`). Any missing logo hides itself gracefully; we never
 * show a broken image on a page whose whole job is building trust.
 */

interface Partner {
  name: string;
  src: string;
  width: number;
  height: number;
}

const PARTNERS: Partner[] = [
  { name: 'Y Combinator', src: '/images/partners/y-combinator-logo.webp', width: 100, height: 18 },
  { name: 'Kindred Ventures', src: '/images/partners/kindred-ventures-logo.webp', width: 70, height: 18 },
  { name: 'Seven Stars', src: '/images/partners/seven-stars-logo.png', width: 75, height: 28 },
  { name: 'Contrary', src: '/images/partners/contrary-logo.webp', width: 105, height: 18 },
  { name: 'SV Angel', src: '/images/partners/sv-angel-logo.webp', width: 46, height: 28 },
  { name: 'Rebel Fund', src: '/images/partners/rebel-fund-logo.webp', width: 56, height: 26 },
];

export default function PartnersStrip() {
  return (
    <div className="flex flex-col items-center gap-2 md:gap-3">
      <p className="text-xs md:text-sm font-medium text-muted">Made possible with</p>
      <div className="flex max-w-3xl flex-wrap items-center justify-center gap-4 md:gap-5 grayscale opacity-70">
        {PARTNERS.map((p) => (
          <img
            key={p.src}
            src={p.src}
            alt={p.name}
            width={p.width}
            height={p.height}
            loading="lazy"
            decoding="async"
            className="h-4 md:h-5 w-auto select-none"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        ))}
      </div>
    </div>
  );
}
