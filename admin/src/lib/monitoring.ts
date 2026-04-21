/**
 * Sentry monitoring initialization for the admin dashboard.
 *
 * To activate: npm install @sentry/react
 * Then call `initSentry()` in main.tsx before React renders.
 */

const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN ?? '';
const ENVIRONMENT = import.meta.env.MODE ?? 'development';
const IS_PRODUCTION = ENVIRONMENT === 'production';

export function initSentry() {
  if (!SENTRY_DSN) {
    console.warn('[monitoring] VITE_SENTRY_DSN not set — skipping Sentry init');
    return;
  }

  import('@sentry/react')
    .then((Sentry) => {
      Sentry.init({
        dsn: SENTRY_DSN,
        environment: ENVIRONMENT,
        tracesSampleRate: IS_PRODUCTION ? 0.1 : 1.0,
        replaysSessionSampleRate: IS_PRODUCTION ? 0.1 : 0,
        replaysOnErrorSampleRate: 1.0,
        integrations: [
          Sentry.browserTracingIntegration(),
          Sentry.replayIntegration(),
        ],
      });
      console.info('[monitoring] Sentry initialized');
    })
    .catch(() => {
      console.info('[monitoring] @sentry/react not installed — run: npm install @sentry/react');
    });
}

export function captureException(error: unknown, context?: Record<string, unknown>) {
  console.error('[monitoring] Captured exception:', error, context);

  import('@sentry/react')
    .then((Sentry) => {
      Sentry.captureException(error, { extra: context });
    })
    .catch(() => {});
}

export function captureMessage(message: string, level: 'info' | 'warning' | 'error' = 'info') {
  console.log(`[monitoring] [${level}] ${message}`);

  import('@sentry/react')
    .then((Sentry) => {
      Sentry.captureMessage(message, level);
    })
    .catch(() => {});
}
