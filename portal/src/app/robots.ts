import type { MetadataRoute } from 'next';

const BASE_URL = 'https://portal.corgiinsure.com';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/quote/', '/login', '/register', '/verify-code'],
    },
    sitemap: `${BASE_URL}/sitemap.xml`,
  };
}
