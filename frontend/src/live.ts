import type { SourceHealth } from './types';

export type Refetch = 'outages' | 'triage' | 'grades' | 'all';

export interface LiveHandlers {
  refetch(what: Refetch): void;
  feed(row: SourceHealth): void;
  stats(eventsPerSecond: number): void;
  status(state: 'live' | 'reconnecting'): void;
}

// Events arrive in bursts (a poll can re-rank dozens of patients); at most one refetch per kind per second.
const COALESCE_MS = 1000;

const REFETCH_ON: Record<string, Refetch> = {
  outage: 'outages',
  triage: 'triage',
  grade: 'grades',
  // The server lost our place in its replay ring, so every view refetches from REST.
  resync: 'all',
};

/** Subscribes to the backend's SSE stream; returns a function that closes it. */
export function connectLive(on: LiveHandlers, url = '/stream', Source: typeof EventSource = EventSource): () => void {
  const source = new Source(url);
  const pending = new Map<Refetch, ReturnType<typeof setTimeout>>();

  for (const [event, what] of Object.entries(REFETCH_ON)) {
    source.addEventListener(event, () => {
      if (pending.has(what)) return;
      pending.set(
        what,
        setTimeout(() => {
          pending.delete(what);
          on.refetch(what);
        }, COALESCE_MS),
      );
    });
  }
  // A health event carries the whole row, so it patches in place without a refetch.
  source.addEventListener('source_health', (e) => on.feed(JSON.parse((e as MessageEvent).data)));
  source.addEventListener('stats', (e) => on.stats(JSON.parse((e as MessageEvent).data).events_per_s));
  source.onopen = () => on.status('live');
  // EventSource reconnects by itself with Last-Event-ID; this only reports that it's trying.
  source.onerror = () => on.status('reconnecting');

  return () => {
    source.close();
    for (const timer of pending.values()) clearTimeout(timer);
    pending.clear();
  };
}

export function formatRate(perSecond: number): string {
  if (perSecond >= 1000) return `${(perSecond / 1000).toFixed(1)}k events/s`;
  return `${perSecond < 10 ? perSecond.toFixed(1) : Math.round(perSecond)} events/s`;
}
