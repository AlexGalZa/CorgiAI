import type { MetadataRoute } from 'next';

const BASE_URL = 'https://portal.corgiinsure.com';

/**
 * Sitemap for the corgi.insure marketing surface served via the portal.
 *
 * URLs are grouped by logical section and assigned priority + changeFrequency
 * per the M5 sitemap-organization card:
 *   - home:                  priority 1.0
 *   - product pages:         priority 0.9
 *   - blog / comparison:     priority 0.6
 *   - legal pages:           priority 0.3
 *
 * `lastModified` is stamped at build/request time. For pages with stable
 * content (legal, comparison) this is accurate enough; if we later move
 * marketing content into a CMS we should thread the CMS `updatedAt` through
 * instead of using the build timestamp.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();

  // Home — the primary landing surface.
  const home: MetadataRoute.Sitemap = [
    {
      url: BASE_URL,
      lastModified,
      changeFrequency: 'weekly',
      priority: 1.0,
    },
  ];

  // Product pages — core conversion surfaces (quote intake, product overviews).
  const productPages: MetadataRoute.Sitemap = [
    {
      url: `${BASE_URL}/quote/get-started`,
      lastModified,
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${BASE_URL}/book-demo`,
      lastModified,
      changeFrequency: 'weekly',
      priority: 0.4,
    },
  ];

  // Blog / comparison pages — competitor alternative pages used for SEO.
  const blogAndComparisonPages: MetadataRoute.Sitemap = [
    {
      url: `${BASE_URL}/embroker`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.6,
    },
    {
      url: `${BASE_URL}/vouch`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.6,
    },
  ];

  // Legal pages — required by regulators; rarely change.
  const legalPages: MetadataRoute.Sitemap = [
    {
      url: `${BASE_URL}/legal`,
      lastModified,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${BASE_URL}/disclaimers`,
      lastModified,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${BASE_URL}/broker-licenses`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.3,
    },
  ];

  return [...home, ...productPages, ...blogAndComparisonPages, ...legalPages];
}
