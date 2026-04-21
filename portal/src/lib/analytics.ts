// Simple analytics — logs events. Replace with real analytics service (Mixpanel, Amplitude, etc.)
type EventName =
  | 'page_view'
  | 'quote_started'
  | 'quote_completed'
  | 'policy_purchased'
  | 'claim_filed'
  | 'certificate_downloaded'
  | 'theme_changed';

interface AnalyticsEvent {
  name: EventName;
  properties?: Record<string, string | number | boolean>;
  timestamp: string;
}

const queue: AnalyticsEvent[] = [];

export function trackEvent(name: EventName, properties?: Record<string, string | number | boolean>) {
  const event: AnalyticsEvent = {
    name,
    properties,
    timestamp: new Date().toISOString(),
  };
  queue.push(event);

  console.debug('[analytics]', name, properties);
}

let flushTimer: ReturnType<typeof setInterval> | null = null;

async function flushQueue() {
  if (queue.length === 0) return;
  const events = queue.splice(0, queue.length);
  try {
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/users/analytics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ events }),
    });
  } catch {
    // Re-queue on failure so they aren't lost
    queue.unshift(...events);
  }
}

if (typeof window !== 'undefined' && !flushTimer) {
  flushTimer = setInterval(flushQueue, 30_000);
}

export function getEventQueue() {
  return [...queue];
}
