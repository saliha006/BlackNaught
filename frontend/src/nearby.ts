import { button, el } from './dom';
import { formatCount, formatElapsed } from './format';
import { isLocated, severityOf } from './geo';
import type { LatLon, Outage } from './types';

const OPERATOR_NAMES: Record<string, string> = { ukpn: 'UK Power Networks', ssen: 'SSEN', npg: 'Northern Powergrid' };
const R_KM = 6371;

/** Great-circle distance; plenty precise for "how far away is this cut". */
export function distanceKm([lat1, lon1]: LatLon, [lat2, lon2]: LatLon): number {
  const rad = Math.PI / 180;
  const a = Math.sin(((lat2 - lat1) * rad) / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(((lon2 - lon1) * rad) / 2) ** 2;
  return 2 * R_KM * Math.asin(Math.sqrt(a));
}

/** Nearest first once we know where the person is; until then, severe before moderate, then by people affected. */
export function sortNearby(outages: Outage[], escalated: Set<number>, here: LatLon | null): Outage[] {
  const located = outages.filter(isLocated);
  if (here) return [...located].sort((a, b) => distanceKm(here, a.centroid) - distanceKm(here, b.centroid));
  const rank = (o: Outage) => (severityOf(o, escalated) === 'severe' ? 0 : 1);
  return [...located].sort((a, b) => rank(a) - rank(b) || (b.customers ?? 0) - (a.customers ?? 0));
}

function card(o: Outage, escalated: Set<number>, here: LatLon | null, onShow: (id: number) => void) {
  const severity = severityOf(o, escalated);
  const li = el('li', 'near');
  li.dataset.severity = severity;
  const head = el('p', 'near__head');
  head.append(el('b', 'near__sev', severity === 'severe' ? 'Severe' : 'Moderate'), ` · ${o.scale} cut`);
  const lines = [
    el('p', 'near__who', OPERATOR_NAMES[o.source] ?? o.source.toUpperCase()),
    el('p', 'near__facts', `Off for ${formatElapsed(o.elapsed_h)} · ${formatCount(o.customers)} customers`),
  ];
  if (here) lines.push(el('p', 'near__dist', `${distanceKm(here, o.centroid!).toFixed(1)} km away`));
  li.append(head, ...lines, button('Show on map', 'chip', () => onShow(o.id)));
  return li;
}

/** The public view's one panel: live cuts as large, plain cards, scrollable. */
export function renderNearby(
  list: HTMLElement,
  outages: Outage[],
  escalated: Set<number>,
  here: LatLon | null,
  onShow: (id: number) => void,
) {
  const sorted = sortNearby(outages, escalated, here);
  if (sorted.length === 0) {
    list.replaceChildren(el('li', 'near__empty', 'No power cuts on the map right now.'));
    return;
  }
  list.replaceChildren(...sorted.map((o) => card(o, escalated, here, onShow)));
}
