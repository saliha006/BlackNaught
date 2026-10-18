import type { Outage, Triage } from './types';

// The operators whose live faults the backend ingests, in a fixed order so the chips never reshuffle.
export const OPERATORS = [
  { id: 'ukpn', name: 'UKPN' },
  { id: 'ssen', name: 'SSEN' },
  { id: 'npg', name: 'NPg' },
] as const;

export interface Filters {
  operators: Set<string>;
  escalationsOnly: boolean;
}

export const allOperators = () => new Set<string>(OPERATORS.map((op) => op.id));

const isFilterable = (source: string) => OPERATORS.some((op) => op.id === source);

/** Outages with at least one patient the triage says to escalate. */
export const escalatedOutages = (triage: Triage | null) =>
  new Set((triage?.items ?? []).filter((i) => i.escalate).map((i) => i.outage_id));

export function filterOutages(outages: Outage[], filters: Filters, escalated: Set<number>): Outage[] {
  return outages.filter(
    // A source with no chip can't be switched off, so it always shows rather than vanishing silently.
    (o) =>
      (!isFilterable(o.source) || filters.operators.has(o.source)) &&
      (!filters.escalationsOnly || escalated.has(o.id)),
  );
}

export const showsSource = (filters: Filters, source: string) =>
  !isFilterable(source) || filters.operators.has(source);
