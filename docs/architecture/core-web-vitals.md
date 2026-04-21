# Core Web Vitals (corgi.insure)

Tracks the marketing-site performance work landed in card **M5 — Sitemap
Organization + Image Compression + Core Web Vitals**. This is the reference
checklist for what ships in this card, what is deferred to a follow-up
operational step, and what the long-term targets are.

## Targets

| Metric                          | Target (mobile, p75) | Notes                                                      |
| ------------------------------- | -------------------- | ---------------------------------------------------------- |
| LCP (Largest Contentful Paint)  | < 2.5 s              | Hero image / headline on `/` and on product pages.         |
| CLS (Cumulative Layout Shift)   | < 0.1                | Reserve space for above-the-fold imagery.                  |
| INP (Interaction to Next Paint) | < 200 ms             | Replaces FID. Watch on the quote-start CTA.                |
| TTFB                            | < 800 ms             | Vercel edge + standalone output (`portal/next.config.ts`). |

Measurement: Chrome UX Report (CrUX) for field data, Lighthouse CI for lab.
PR-time budgets are enforced via Lighthouse CI (follow-up, see pending).

## Shipped in M5

- **Sitemap organization.** `portal/src/app/sitemap.ts` now groups marketing
  URLs into four tiers and sets `priority`, `lastModified`, and
  `changeFrequency` per tier:
  - home — `1.0`, weekly
  - product pages — `0.9`, weekly
  - blog / comparison pages — `0.6`, monthly
  - legal pages — `0.3`, yearly/monthly
- **Robots policy** (`portal/src/app/robots.ts`) continues to disallow
  `/quote/`, `/login`, `/register`, `/verify-code` so crawlers do not index
  auth or partial-quote flows.
- **Image host allowlist** in `portal/next.config.ts` already scopes
  `next/image` to `*.s3.amazonaws.com` and `*.s3.us-east-1.amazonaws.com`,
  which keeps optimized variants served through Next's image pipeline with
  automatic WebP/AVIF negotiation for remote sources.

## Pending / deferred

These items are explicitly **out of scope for M5** and should be picked up in
a follow-up card. The work is described here so the operator running that
card has a starting point.

### 1. Convert static PNGs in `portal/public/images/` to WebP

Current state: `portal/public/images/` contains four marketing PNGs:

- `policy-directors-officers-1.png`
- `policy-directors-officers-2.png`
- `rec-tech-professional-liability-1.png`
- `rec-tech-professional-liability-2.png`

These are served as-is because files under `/public` bypass the `next/image`
optimizer. The build step below is the recommended operational pipeline:

```bash
# One-off conversion (run from repo root, requires `cwebp` installed).
for f in portal/public/images/*.png; do
  cwebp -q 82 "$f" -o "${f%.png}.webp"
done
```

Follow-up work when adopting:

1. Commit the `.webp` siblings alongside the `.png` originals.
2. Update every `<Image src="/images/*.png">` call site to use the `.webp`
   variant (or switch to importing the file so Next picks format from the
   extension).
3. Delete the `.png` originals once all references are migrated.
4. Wire `cwebp` (or `sharp`) into the portal `build` script so future PNG
   additions fail CI unless a `.webp` sibling is present.

Do not convert the SVG icons in `portal/public/` (corgi-icon, corgi-logo,
husky-icon, file, globe, next, vercel, window). SVG is already optimal for
those assets.

### 2. Font preload

The portal loads fonts via `next/font` inside `portal/src/app/layout.tsx`.
Confirm preload hints are emitted for the above-the-fold font weights (400,
500 for body; 600 for heading). If any heading weight is used on the hero
but not preloaded, add it to the `next/font` `weight` array so Next emits a
`<link rel="preload" as="font" crossOrigin>` tag automatically.

### 3. Lazy-loading recommendations

- Marketing `<Image>` components below the fold should pass `loading="lazy"`
  (the default) and **never** `priority`.
- Exactly one image per marketing page should carry `priority` — the LCP
  candidate. On `/` that is the hero; on each comparison page that is the
  top hero illustration.
- Defer any embedded `<iframe>` (Stripe elements, demo videos) with
  `loading="lazy"` attribute so it does not block LCP.

### 4. Lighthouse CI budget

Add a GitHub Actions job that runs `lhci autorun` against the built portal
with a mobile config, and fails the PR if LCP > 2.5 s or CLS > 0.1 on `/`,
`/embroker`, and `/vouch`. Budget file: `portal/lighthouserc.json`.

### 5. Third-party script audit

`portal/next.config.ts` CSP currently permits `https://js.stripe.com` and
`'unsafe-inline' 'unsafe-eval'` for `script-src`. Audit whether Stripe is
actually used on marketing routes; if not, scope the CSP so marketing
routes can drop `'unsafe-eval'` and the Stripe origin, tightening the
budget for injected third-party JS and improving INP.

## Related cards / files

- `portal/src/app/sitemap.ts` — sitemap source of truth for corgi.insure.
- `portal/src/app/robots.ts` — crawler policy (pairs with the sitemap).
- `portal/next.config.ts` — image remote patterns + security headers.
- Card 6.3 — first introduced `portal/src/app/sitemap.ts`.
- Card M5 (this card) — grouping, priorities, and the checklist above.
