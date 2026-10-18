import { describe, expect, it } from 'vitest';
import outages from '../../fixtures/api/outages.json';
import triage from '../../fixtures/api/triage.json';
import { allOperators, escalatedOutages, type Filters, filterOutages, showsSource } from './state';
import type { Outage, Triage } from './types';

const all = outages as Outage[];
const filters = (over: Partial<Filters> = {}): Filters => ({
  operators: allOperators(),
  escalationsOnly: false,
  ...over,
});

describe('escalatedOutages', () => {
  it('collects outages with at least one escalated patient', () => {
    expect([...escalatedOutages(triage as Triage)]).toEqual([101]);
  });

  it('is empty when triage is missing', () => {
    expect(escalatedOutages(null).size).toBe(0);
  });
});

describe('filterOutages', () => {
  it('keeps everything with every operator on', () => {
    expect(filterOutages(all, filters(), new Set())).toHaveLength(all.length);
  });

  it('drops operators that are switched off', () => {
    const shown = filterOutages(all, filters({ operators: new Set(['ukpn']) }), new Set());
    expect(shown.map((o) => o.source)).toEqual(['ukpn']);
  });

  it('keeps sources that have no chip, so they cannot vanish silently', () => {
    const enwl = { ...all[0], id: 7, source: 'enwl' };
    expect(filterOutages([enwl], filters({ operators: new Set() }), new Set())).toEqual([enwl]);
    expect(showsSource(filters({ operators: new Set() }), 'elexon')).toBe(true);
    expect(showsSource(filters({ operators: new Set() }), 'ssen')).toBe(false);
  });

  it('narrows to outages with an escalation when asked', () => {
    const shown = filterOutages(all, filters({ escalationsOnly: true }), new Set([102]));
    expect(shown.map((o) => o.id)).toEqual([102]);
  });
});
