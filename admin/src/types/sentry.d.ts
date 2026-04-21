// Type stub for @sentry/react — install the real package to enable monitoring.
declare module "@sentry/react" {
  export function init(options: Record<string, unknown>): void;
  export function captureException(error: unknown, context?: Record<string, unknown>): void;
  export function captureMessage(message: string, level?: string): void;
  export function browserTracingIntegration(): unknown;
  export function replayIntegration(options?: Record<string, unknown>): unknown;
}
