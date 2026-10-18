import { severityOf } from './geo';
import { distanceKm, sortNearby } from './nearby';
import type { LatLon, Outage } from './types';

// A cut this close could be the one that has your power off; further away, it isn't yours
export const NEAR_KM = 3;

export type Level = 'safe' | 'moderate' | 'severe' | 'unknown';
/** Where the browser's location request has got to: asked on page load, answered by the person. */
export type Location = 'pending' | 'denied' | 'found';

export interface StatusData {
  outages: Outage[];
  escalated: Set<number>;
}

export interface Status {
  level: Level;
  headline: string;
  detail: string;
  /** The cut to show on the map, when there's one near the person. */
  nearest: Outage | null;
}

const neutral = (headline: string, detail = ''): Status => ({ level: 'unknown', headline, detail, nearest: null });

/**
 * The answer to "is my power OK?", updating by itself as the location and the live data arrive. Green needs both:
 * without a location we can't honestly say someone is fine, and a failed load is never shown as safe.
 */
export function homeStatus(data: StatusData | null | 'failed', here: LatLon | null, location: Location): Status {
  if (data === 'failed') return neutral("Can't load power cuts right now", 'Try again in a minute.');
  if (location === 'denied') return neutral('Location is off', 'Allow location for this site to check your area.');
  if (!data || !here) return neutral('Checking your area…');
  const [nearest] = sortNearby(data.outages, data.escalated, here);
  const km = nearest ? distanceKm(here, nearest.centroid!) : Infinity;
  if (km > NEAR_KM) return { level: 'safe', headline: "You're safe", detail: `No power cut within ${NEAR_KM} km.`, nearest: null };
  const level = severityOf(nearest, data.escalated);
  return {
    level,
    headline: 'Not safe',
    detail: `${level === 'severe' ? 'Severe' : 'Moderate'} power cut ${km.toFixed(1)} km away`,
    nearest,
  };
}

export function renderStatus(root: HTMLElement, status: Status) {
  root.dataset.level = status.level;
  const headline = root.querySelector<HTMLElement>('#term-headline')!;
  const detail = root.querySelector<HTMLElement>('#term-detail')!;
  headline.textContent = status.headline;
  detail.textContent = status.detail;
  detail.hidden = !status.detail;
}
