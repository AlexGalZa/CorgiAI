/**
 * Lazy-loaded page components for bundle splitting.
 *
 * Usage in App Router: import these in route `page.tsx` files when you want
 * to code-split heavy client components.
 *
 * Example:
 *   import { LazyQuoteSummary } from "@/lib/lazy";
 *   export default function Page() { return <LazyQuoteSummary />; }
 */

import { lazy } from "react";

// ---------- Quote flow (heaviest pages) ----------

export const LazyQuoteGetStarted = lazy(
  () => import("@/app/quote/get-started/page")
);

// ---------- Dashboard pages ----------

export const LazyCertificatesPage = lazy(
  () => import("@/app/(dashboard)/certificates/page")
);

export const LazyBillingPage = lazy(
  () => import("@/app/(dashboard)/billing/page")
);

export const LazyClaimsPage = lazy(
  () => import("@/app/(dashboard)/claims/page")
);

export const LazyDocumentsPage = lazy(
  () => import("@/app/(dashboard)/documents/page")
);
