import { el } from './dom';
import { isLocated, severityOf } from './geo';
import { distanceKm, sortNearby } from './nearby';
import type { LatLon, Outage, Scale } from './types';

// The exact bounds public/gb-night.webp was captured at (MapLibre fitBounds on GB_BOUNDS, no padding, no tilt),
// so a glow placed by these numbers sits on the right town in the picture.
export const GLANCE_BOUNDS: [number, number, number, number] = [-8.7259, 49.8, 2.1259, 59.2];

const mercY = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));

/** Position in the picture as percentages from its top-left corner, by Web Mercator like the map it came from. */
export function projectGB([lat, lon]: LatLon): [number, number] {
  const [w, s, e, n] = GLANCE_BOUNDS;
  return [((lon - w) / (e - w)) * 100, ((mercY(n) - mercY(lat)) / (mercY(n) - mercY(s))) * 100];
}

// Glow size in the picture, by how much ground the cut covers
const GLOW_PX: Record<Scale, number> = { home: 10, street: 14, area: 20, region: 30, system: 44, brownout: 14, unresolved: 12 };

export interface GlanceData {
  outages: Outage[];
  escalated: Set<number>;
}

/** The landing page's glance window: how many cuts, how bad, and where, readable in a second without any controls. */
export function renderGlance(root: HTMLElement, data: GlanceData | null) {
  const count = root.querySelector('#glance-count')!;
  const severe = root.querySelector('#glance-severe')!;
  const moderate = root.querySelector('#glance-moderate')!;
  const glows = root.querySelector('#glance-glows')!;
  const updated = root.querySelector('#glance-updated')!;
  // A failed load must never read as "0 power cuts": that would be a false all-clear
  if (!data) {
    for (const n of [count, severe, moderate]) n.textContent = '–';
    glows.replaceChildren();
    updated.textContent = "Can't load power cuts right now";
    root.dataset.state = 'error';
    return;
  }
  const located = data.outages.filter(isLocated);
  const severeCount = data.outages.filter((o) => severityOf(o, data.escalated) === 'severe').length;
  count.textContent = String(data.outages.length);
  severe.textContent = String(severeCount);
  moderate.textContent = String(data.outages.length - severeCount);
  updated.textContent = `updated ${new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}`;
  root.dataset.state = 'ready';
  glows.replaceChildren(
    ...located.map((o) => {
      const [x, y] = projectGB(o.centroid);
      const glow = el('i', 'glance__glow');
      glow.dataset.severity = severityOf(o, data.escalated);
      glow.style.left = `${x}%`;
      glow.style.top = `${y}%`;
      glow.style.setProperty('--size', `${GLOW_PX[o.scale]}px`);
      return glow;
    }),
  );
}

/** "Is there one near me?": the closest cut in plain words. Never an ETA. */
export function nearestText(data: GlanceData, here: LatLon): string {
  const [nearest] = sortNearby(data.outages, data.escalated, here);
  if (!nearest) return 'No power cuts on the map right now.';
  const severity = severityOf(nearest, data.escalated) === 'severe' ? 'Severe' : 'Moderate';
  return `Nearest power cut: ${distanceKm(here, nearest.centroid!).toFixed(1)} km away · ${severity}`;
}
