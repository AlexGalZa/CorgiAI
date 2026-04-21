/**
 * Sentry monitoring initialization for the portal.
 *
 * To activate: npm install @sentry/nextjs
 * Then call initSentryServer() in instrumentation.ts
 * and initSentryClient() in root layout.
 */

// ---------- Config ----------

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN ?? "";
const ENVIRONMENT = process.env.NODE_ENV ?? "development";
const IS_PRODUCTION = ENVIRONMENT === "production";

// ---------- Server-side init ----------

export function initSentryServer() {
  if (!SENTRY_DSN) {
    console.warn("[monitoring] SENTRY_DSN not set — skipping server init");
    return;
  }

  import("@sentry/nextjs")
    .then((Sentry) => {
      Sentry.init({
        dsn: SENTRY_DSN,
        environment: ENVIRONMENT,
        tracesSampleRate: IS_PRODUCTION ? 0.1 : 1.0,
        debug: !IS_PRODUCTION,
      });
      console.info("[monitoring] Sentry server initialized");
    })
    .catch(() => {
      console.info("[monitoring] @sentry/nextjs not installed — run: npm install @sentry/nextjs");
    });
}

// ---------- Client-side init ----------

export function initSentryClient() {
  if (!SENTRY_DSN) {
    return;
  }

  import("@sentry/nextjs")
    .then((Sentry) => {
      Sentry.init({
        dsn: SENTRY_DSN,
        environment: ENVIRONMENT,
        tracesSampleRate: IS_PRODUCTION ? 0.1 : 1.0,
        replaysSessionSampleRate: IS_PRODUCTION ? 0.1 : 0,
        replaysOnErrorSampleRate: 1.0,
        integrations: [],
        debug: !IS_PRODUCTION,
      });
      console.info("[monitoring] Sentry client initialized");
    })
    .catch(() => {
      console.info("[monitoring] @sentry/nextjs not installed — run: npm install @sentry/nextjs");
    });
}

// ---------- Error capture ----------

export function captureException(error: unknown, context?: Record<string, unknown>) {
  console.error("[monitoring] Captured exception:", error, context);

  import("@sentry/nextjs")
    .then((Sentry) => {
      Sentry.captureException(error, { extra: context });
    })
    .catch(() => {});
}

export function captureMessage(message: string, level: "info" | "warning" | "error" = "info") {
  console.log(`[monitoring] [${level}] ${message}`);

  import("@sentry/nextjs")
    .then((Sentry) => {
      Sentry.captureMessage(message, level);
    })
    .catch(() => {});
}

// ---------- Web Vitals ----------

interface WebVital {
  id: string;
  name: string;
  value: number;
  delta: number;
  rating: "good" | "needs-improvement" | "poor";
}

export function reportWebVitals(metric: WebVital) {
  if (!IS_PRODUCTION) {
    console.debug(`[vitals] ${metric.name}: ${Math.round(metric.value)} (${metric.rating})`);
  }

  // Forward to analytics module
  import("./analytics")
    .then(({ trackEvent }) => {
      trackEvent("page_view", {
        metric_name: metric.name,
        metric_value: metric.value,
        metric_rating: metric.rating,
        page: typeof window !== "undefined" ? window.location.pathname : "",
      });
    })
    .catch(() => {});
}
