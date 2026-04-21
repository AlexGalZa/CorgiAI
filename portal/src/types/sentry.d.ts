// Type stub for @sentry/nextjs — install the real package to enable monitoring.
// npm install @sentry/nextjs
declare module "@sentry/nextjs" {
  export function init(options: Record<string, unknown>): void;
  export function captureException(error: unknown, context?: Record<string, unknown>): void;
  export function captureMessage(message: string, level?: string): void;
}
