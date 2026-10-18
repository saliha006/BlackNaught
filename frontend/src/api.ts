import type { Cell, Outage, SourceHealth, Triage } from './types';

export const isLive = import.meta.env.MODE === 'live';

// Lazy so the live build never ships the fixtures.
const fixtures = import.meta.glob<{ default: unknown }>('../../fixtures/api/*.json');

async function fixture<T>(name: string): Promise<T> {
  const load = fixtures[`../../fixtures/api/${name}.json`];
  if (!load) throw new Error(`No fixture named ${name}.json`);
  return (await load()).default as T;
}

/** A failure talking to the backend, kept apart from bugs in this app so only these get the "check the tunnel" hint. */
export class ApiError extends Error {}

async function live<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { Accept: 'application/json' } }).catch((e: Error) => {
    throw new ApiError(`${path}: ${e.message}`);
  });
  if (!res.ok) throw new ApiError(`${path} returned ${res.status}`);
  return res.json() as Promise<T>;
}

export const getOutages = () =>
  isLive ? live<Outage[]>('/api/outages?status=active') : fixture<Outage[]>('outages');

export const getCells = () =>
  isLive ? live<Cell[]>('/api/cells?level=1') : fixture<Cell[]>('cells');

export const getTriage = (limit = 3) =>
  isLive ? live<Triage>(`/api/triage?limit=${limit}`) : fixture<Triage>('triage');

export const getSourcesHealth = () =>
  isLive
    ? live<{ sources: SourceHealth[] }>('/api/sources/health')
    : fixture<{ sources: SourceHealth[] }>('sources_health');
