import type { LineString, Polygon } from 'geojson';
import { describe, expect, it } from 'vitest';
import outages from '../../fixtures/api/outages.json';
import type { Located } from './geo';
import { PULSE_PERIOD_S, SWEEP_PERIOD_S, SWEEP_RADIUS_M, sweepFeatures, TRAIL_WEDGES } from './sweep';

const street = (outages as Located[])[0];
const [lat, lon] = street.centroid;
const metres = ([x, y]: number[]) =>
  Math.hypot((x - lon) * 111_320 * Math.cos((lat * Math.PI) / 180), (y - lat) * 111_320);

const byKind = (t: number, kind: string) =>
  sweepFeatures([street], t).features.filter((f) => f.properties!.kind === kind);

describe('sweepFeatures', () => {
  it('draws a trail, a leading edge, a range ring and two pulses per outage', () => {
    expect(sweepFeatures([street], 0).features).toHaveLength(TRAIL_WEDGES + 4);
    expect(sweepFeatures([], 0).features).toEqual([]);
  });

  it('turns clockwise from north, a full turn per period', () => {
    const tip = (t: number) => (byKind(t, 'edge')[0].geometry as LineString).coordinates[1];
    expect(tip(0)[0]).toBeCloseTo(lon, 6);
    expect(tip(0)[1]).toBeGreaterThan(lat);
    expect(tip(SWEEP_PERIOD_S / 4)[0]).toBeGreaterThan(lon);
    expect(tip(SWEEP_PERIOD_S / 4)[1]).toBeCloseTo(lat, 6);
    expect(tip(SWEEP_PERIOD_S)).toEqual(tip(0));
  });

  it('reaches the radius for the outage scale', () => {
    const tip = (byKind(0, 'edge')[0].geometry as LineString).coordinates[1];
    expect(metres(tip)).toBeCloseTo(SWEEP_RADIUS_M.street, 0);
  });

  it('fades the trail behind the leading edge', () => {
    const alphas = byKind(0, 'wedge').map((f) => f.properties!.alpha as number);
    expect(alphas).toEqual([...alphas].sort((a, b) => b - a));
    expect(alphas[alphas.length - 1]).toBeGreaterThan(0);
    const wedge = (byKind(1, 'wedge')[0].geometry as Polygon).coordinates[0];
    expect(wedge[0]).toEqual(wedge[wedge.length - 1]);
  });

  it('expands pulses outward and fades them as they grow', () => {
    const pulses = (t: number) =>
      byKind(t, 'ring')
        .slice(1)
        .map((f) => ({ r: metres((f.geometry as LineString).coordinates[0]), alpha: f.properties!.alpha as number }));
    const [a, b] = pulses(PULSE_PERIOD_S * 0.25);
    expect(a.r).toBeCloseTo(SWEEP_RADIUS_M.street * 0.25, 0);
    expect(b.r).toBeCloseTo(SWEEP_RADIUS_M.street * 0.75, 0);
    expect(b.alpha).toBeLessThan(a.alpha);
    expect(pulses(PULSE_PERIOD_S * 0.5)[0].r).toBeGreaterThan(a.r);
  });
});
