import type { FeatureCollection, Point, Polygon } from 'geojson';
import type { Cell, Outage, Scale } from './types';

// The API speaks [lat, lon]; GeoJSON and MapLibre want [lon, lat]. Every swap happens here.
const toLonLat = ([lat, lon]: [number, number]): [number, number] => [lon, lat];

// Marker radius grows with footprint so scale reads without colour (colour is reserved for severity).
export const SCALE_RADIUS: Record<Scale, number> = {
  home: 4,
  street: 7,
  area: 11,
  region: 16,
  system: 22,
  brownout: 7,
  unresolved: 5,
};

export function outagesToGeoJSON(outages: Outage[]): FeatureCollection<Point> {
  return {
    type: 'FeatureCollection',
    features: outages.map((o) => ({
      type: 'Feature',
      id: o.id,
      geometry: { type: 'Point', coordinates: toLonLat(o.centroid) },
      properties: { id: o.id, scale: o.scale, radius: SCALE_RADIUS[o.scale] },
    })),
  };
}

const M_PER_DEG_LAT = 111_320;

/** [lon, lat] of the point `metres` from a centre along `bearing` (radians clockwise from north). */
export function offsetLonLat(lat: number, lon: number, metres: number, bearing: number): [number, number] {
  const dLat = (metres * Math.cos(bearing)) / M_PER_DEG_LAT;
  const dLon = (metres * Math.sin(bearing)) / (M_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180));
  return [lon + dLon, lat + dLat];
}

/** Closed ring of `sides` points `metres` around a centre, as GeoJSON [lon, lat]. */
export function circleRing(lat: number, lon: number, metres: number, sides: number): [number, number][] {
  return Array.from({ length: sides + 1 }, (_, i) => offsetLonLat(lat, lon, metres, ((i % sides) / sides) * 2 * Math.PI));
}

// Height of the light beam over each outage, in metres. Taller = wider footprint.
export const SCALE_BEAM_M: Record<Scale, number> = {
  home: 300,
  street: 600,
  area: 900,
  region: 1400,
  system: 2000,
  brownout: 600,
  unresolved: 400,
};

// A thin bright core inside a wider faint glow reads as light rather than as a solid tube.
export const BEAM_CORE_M = 6;
export const BEAM_GLOW_M = 24;

/** Light beams over outage centroids: one core and one glow column per outage. */
export function beamsToGeoJSON(outages: Outage[]): FeatureCollection<Polygon> {
  return {
    type: 'FeatureCollection',
    features: outages.flatMap((o) => {
      const [lat, lon] = o.centroid;
      const height = SCALE_BEAM_M[o.scale];
      return (['core', 'glow'] as const).map((kind) => ({
        type: 'Feature' as const,
        geometry: { type: 'Polygon' as const, coordinates: [circleRing(lat, lon, kind === 'core' ? BEAM_CORE_M : BEAM_GLOW_M, 20)] },
        properties: { id: o.id, kind, height },
      }));
    }),
  };
}

export function cellsToGeoJSON(cells: Cell[]): FeatureCollection<Polygon> {
  return {
    type: 'FeatureCollection',
    features: cells.map((c) => ({
      type: 'Feature',
      geometry: { type: 'Polygon', coordinates: [c.bounds.map(toLonLat)] },
      properties: {
        cell_id: c.cell_id,
        suppressed: c.patients === 'suppressed',
        affected: c.outage_scale !== null,
      },
    })),
  };
}
