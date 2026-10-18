import { describe, expect, it } from 'vitest';
import outages from '../../fixtures/api/outages.json';
import { fogAreasToGeoJSON, SWEEP_RADIUS_M } from './geo';
import { grainTile } from './grain';
import type { Outage } from './types';

describe('grainTile', () => {
  it('is a sparse, repeatable 64×64 tile in the given colour', () => {
    const tile = grainTile('#e5484d', 7);
    expect([tile.width, tile.height, tile.data.length]).toEqual([64, 64, 64 * 64 * 4]);
    const lit = [];
    for (let i = 0; i < 64 * 64; i++) if (tile.data[i * 4 + 3] > 0) lit.push(i);
    expect(lit.length / (64 * 64)).toBeGreaterThan(0.05);
    expect(lit.length / (64 * 64)).toBeLessThan(0.12);
    expect([...tile.data.slice(lit[0] * 4, lit[0] * 4 + 3)]).toEqual([0xe5, 0x48, 0x4d]);
    expect(grainTile('#e5484d', 7).data).toEqual(tile.data);
    expect(grainTile('#e5484d', 8).data).not.toEqual(tile.data);
  });
});

describe('fogAreasToGeoJSON', () => {
  it('stacks three discs per located cut, the largest at the footprint radius, with its severity', () => {
    const located = (outages as Outage[]).filter((o) => o.centroid);
    const fc = fogAreasToGeoJSON(located, new Set([located[0].id]));
    expect(fc.features).toHaveLength(located.length * 3);
    expect(fc.features[0].properties).toEqual({ id: located[0].id, severity: 'severe' });
    const [lat] = located[0].centroid!;
    const ring = fc.features[2].geometry.coordinates[0];
    const northMost = Math.max(...ring.map(([, y]) => y));
    expect((northMost - lat) * 111_320).toBeCloseTo(SWEEP_RADIUS_M[located[0].scale], -1);
  });
});
