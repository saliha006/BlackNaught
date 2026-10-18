import { describe, expect, it } from 'vitest';
import cells from '../../fixtures/api/cells.json';
import outages from '../../fixtures/api/outages.json';
import {
  BEAM_CORE_M,
  BEAM_GLOW_M,
  beamsToGeoJSON,
  cellsToGeoJSON,
  circleRing,
  isLocated,
  offsetLonLat,
  outagesToGeoJSON,
  SCALE_BEAM_M,
  SCALE_RADIUS,
} from './geo';
import type { Cell, Outage } from './types';

describe('outagesToGeoJSON', () => {
  it('swaps the API [lat, lon] centroid into GeoJSON [lon, lat]', () => {
    const fc = outagesToGeoJSON(outages as Outage[]);
    const first = fc.features[0];
    expect(first.geometry.coordinates).toEqual([-0.098, 51.536]);
    expect(first.id).toBe(101);
  });

  it('sizes markers by scale', () => {
    const fc = outagesToGeoJSON(outages as Outage[]);
    expect(fc.features.map((f) => f.properties!.radius)).toEqual(
      (outages as Outage[]).map((o) => SCALE_RADIUS[o.scale]),
    );
  });

  it('returns an empty collection for no outages', () => {
    expect(outagesToGeoJSON([]).features).toEqual([]);
  });

  it('leaves out outages the backend has not located yet, as the live feed sends them', () => {
    const unplaced = { ...(outages as Outage[])[1], id: 999, centroid: null };
    expect(isLocated(unplaced)).toBe(false);
    expect(isLocated((outages as Outage[])[0])).toBe(true);
    const mixed = [(outages as Outage[])[0], unplaced];
    expect(outagesToGeoJSON(mixed).features.map((f) => f.id)).toEqual([101]);
    expect(beamsToGeoJSON(mixed).features.map((f) => f.properties!.id)).toEqual([101, 101]);
  });
});

describe('offsetLonLat / circleRing', () => {
  it('moves north at bearing 0 and east at a quarter turn, by the given metres', () => {
    const [, north] = offsetLonLat(51.5, -0.1, 111.32, 0);
    expect(north).toBeCloseTo(51.501, 6);
    const [east, lat] = offsetLonLat(51.5, -0.1, 100, Math.PI / 2);
    expect(lat).toBeCloseTo(51.5, 9);
    expect((east + 0.1) * 111_320 * Math.cos((51.5 * Math.PI) / 180)).toBeCloseTo(100, 6);
  });

  it('closes the ring', () => {
    const ring = circleRing(51.5, -0.1, 50, 8);
    expect(ring).toHaveLength(9);
    expect(ring[0]).toEqual(ring[8]);
  });
});

describe('beamsToGeoJSON', () => {
  const fc = beamsToGeoJSON(outages as Outage[]);
  const radius = (ring: number[][], lat: number) => (ring[0][1] - lat) * 111_320;

  it('puts a thin core inside a wider glow on each centroid, in [lon, lat]', () => {
    expect(fc.features).toHaveLength(outages.length * 2);
    const [core, glow] = fc.features;
    expect(core.properties).toMatchObject({ id: 101, kind: 'core' });
    expect(glow.properties).toMatchObject({ id: 101, kind: 'glow' });
    expect(radius(core.geometry.coordinates[0], 51.536)).toBeCloseTo(BEAM_CORE_M, 6);
    expect(radius(glow.geometry.coordinates[0], 51.536)).toBeCloseTo(BEAM_GLOW_M, 6);
  });

  it('makes wider outages taller', () => {
    expect(SCALE_BEAM_M.area).toBeGreaterThan(SCALE_BEAM_M.street);
    expect(fc.features[0].properties!.height).toBe(SCALE_BEAM_M.street);
  });
});

describe('cellsToGeoJSON', () => {
  const fc = cellsToGeoJSON(cells as Cell[]);

  it('keeps the closed ring and swaps every vertex', () => {
    const ring = fc.features[0].geometry.coordinates[0];
    expect(ring[0]).toEqual([-0.096, 51.53]);
    expect(ring[0]).toEqual(ring[ring.length - 1]);
  });

  it('flags suppressed and affected cells', () => {
    expect(fc.features[0].properties).toMatchObject({ suppressed: false, affected: true });
    expect(fc.features[1].properties).toMatchObject({ suppressed: true, affected: false });
  });
});
