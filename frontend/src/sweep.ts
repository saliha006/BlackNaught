import type { Feature, FeatureCollection, LineString, Polygon } from 'geojson';
import { circleRing, type Located, offsetLonLat, SWEEP_RADIUS_M } from './geo';

export { SWEEP_RADIUS_M };

export const SWEEP_PERIOD_S = 3.6;
export const PULSE_PERIOD_S = 2.4;
export const TRAIL_WEDGES = 12;
const WEDGE_RAD = (5 * Math.PI) / 180;

type SweepFeature = Feature<Polygon | LineString, { kind: 'wedge' | 'edge' | 'ring'; alpha: number; width: number }>;

/**
 * The radar-style sweep around each outage at time `t` (seconds): a clockwise leading edge with a fading
 * trail of wedges, the range ring, and two pulses expanding outward half a period apart.
 * Centred on the outage centroid from the operator's public feed, never on a home.
 */
export function sweepFeatures(outages: Located[], t: number): FeatureCollection<Polygon | LineString> {
  const heading = ((t % SWEEP_PERIOD_S) / SWEEP_PERIOD_S) * 2 * Math.PI;
  const features: SweepFeature[] = [];

  for (const o of outages) {
    const [lat, lon] = o.centroid;
    const r = SWEEP_RADIUS_M[o.scale];
    const at = (bearing: number) => offsetLonLat(lat, lon, r, bearing);

    for (let i = 0; i < TRAIL_WEDGES; i++) {
      const lead = heading - i * WEDGE_RAD;
      const tail = lead - WEDGE_RAD;
      features.push({
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [[[lon, lat], at(tail), at((tail + lead) / 2), at(lead), [lon, lat]]] },
        properties: { kind: 'wedge', alpha: 0.3 * (1 - i / TRAIL_WEDGES) ** 1.6, width: 0 },
      });
    }
    features.push({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [[lon, lat], at(heading)] },
      properties: { kind: 'edge', alpha: 0.85, width: 1.5 },
    });
    features.push({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: circleRing(lat, lon, r, 64) },
      properties: { kind: 'ring', alpha: 0.22, width: 1 },
    });
    for (const offset of [0, 0.5]) {
      const p = (t / PULSE_PERIOD_S + offset) % 1;
      features.push({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: circleRing(lat, lon, r * p, 48) },
        properties: { kind: 'ring', alpha: 0.55 * (1 - p), width: 1.25 },
      });
    }
  }
  return { type: 'FeatureCollection', features };
}
