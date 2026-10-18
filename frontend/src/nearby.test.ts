// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest';
import outages from '../../fixtures/api/outages.json';
import { distanceKm, renderNearby, sortNearby } from './nearby';
import type { Outage } from './types';

const all = (outages as Outage[]).filter((o) => o.centroid);

describe('sortNearby', () => {
  it('puts severe cuts first, then the most customers, until we know where the person is', () => {
    const [a, b] = all;
    const sorted = sortNearby([{ ...a, customers: 5 }, { ...b, customers: 500 }], new Set([a.id]), null);
    expect(sorted[0].id).toBe(a.id);
    expect(sortNearby([{ ...a, customers: 5 }, { ...b, customers: 500 }], new Set(), null)[0].id).toBe(b.id);
  });

  it('sorts nearest first once there is a location, and skips cuts without one', () => {
    const near = { ...all[0], id: 1, centroid: [51.5, -0.1] as [number, number] };
    const far = { ...all[0], id: 2, centroid: [55.9, -3.2] as [number, number] };
    const nowhere = { ...all[0], id: 3, centroid: null };
    expect(sortNearby([far, nowhere, near], new Set(), [51.51, -0.12]).map((o) => o.id)).toEqual([1, 2]);
  });
});

describe('distanceKm', () => {
  it('measures London to Edinburgh at about 530 km', () => {
    expect(distanceKm([51.5074, -0.1278], [55.9533, -3.1883])).toBeCloseTo(534, -1);
  });
});

describe('renderNearby', () => {
  it('shows the severity in words, the distance when known, and flies to the cut', () => {
    const list = document.createElement('ul');
    const onShow = vi.fn();
    renderNearby(list, [all[0]], new Set([all[0].id]), [51.5, -0.1], onShow);
    const li = list.querySelector<HTMLElement>('li.near')!;
    expect(li.dataset.severity).toBe('severe');
    expect(li.textContent).toContain('Severe');
    expect(li.textContent).toContain('km away');
    li.querySelector('button')!.click();
    expect(onShow).toHaveBeenCalledWith(all[0].id);
    renderNearby(list, [], new Set(), null, onShow);
    expect(list.textContent).toContain('No power cuts');
  });
});
