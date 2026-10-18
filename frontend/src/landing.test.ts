import { describe, expect, it } from 'vitest';
import km from '../../backend/models/km_enwl.json';
import triage from '../../fixtures/api/triage.json';
import health from '../../fixtures/api/sources_health.json';
import { percentStillOff, sourceRow, survivalPath, triageRow, ukpnBrier } from './landing';
import type { SourceHealth, TriageItem } from './types';

describe('survivalPath', () => {
  it('starts top-left at S(0)=1 and spans the full width', () => {
    const d = survivalPath([1, 0.5, 0.25], 2, 100, 50);
    expect(d).toBe('M0.0,0.0 L50.0,25.0 L100.0,37.5');
  });

  it('only uses the requested hours of the real ENWL curve', () => {
    expect(survivalPath(km.curve, 24, 240, 100).split(' ')).toHaveLength(25);
  });
});

it('reads the share still off from the hourly curve', () => {
  expect(percentStillOff(km.curve, 0)).toBe('100%');
  expect(percentStillOff(km.curve, 4)).toBe('45%');
});

describe('ukpnBrier', () => {
  it('weights UKPN +2 h by graded count across models and ignores other rows', () => {
    const row = (model_id: string, brier: number | null, n: number, source = 'ukpn', h = 2) => ({
      h, model_id, source, brier, n, n_censored: 0, bound: null,
    });
    const grades = {
      by_horizon: [row('a', 0.2, 100), row('b', 0.1, 300), row('a', 0.9, 50, 'ssen'), row('a', 0.9, 50, 'ukpn', 4), row('c', null, 0)],
      trend: [],
    };
    expect(ukpnBrier(grades)).toEqual({ brier: 0.125, n: 400 });
    expect(ukpnBrier({ by_horizon: [], trend: [] })).toBeNull();
  });
});

describe('triageRow', () => {
  const [a, b] = triage.items as TriageItem[];

  it('shows escalation with a text label and the quantile used', () => {
    const html = triageRow(a);
    expect(html).toContain('Oxygen concentrator');
    expect(html).toContain('sev--escalate');
    expect(html).toContain('Escalate');
    expect(html).toContain('(q90)');
  });

  it('shows an SMS check for a patient with plenty of reserve', () => {
    const html = triageRow(b);
    expect(html).toContain('Ventilator');
    expect(html).toContain('SMS check');
    expect(html).not.toContain('Escalate');
  });
});

it('keeps unknown device and source names as text', () => {
  const [a] = triage.items as TriageItem[];
  expect(triageRow({ ...a, device: '<b>x</b>' })).toContain('&lt;b&gt;x&lt;/b&gt;');
  const [ukpn] = health.sources as SourceHealth[];
  expect(sourceRow({ ...ukpn, source: '<i>y</i>' })).toContain('&lt;i&gt;y&lt;/i&gt;');
});

describe('sourceRow', () => {
  const [ukpn, , npg] = health.sources as SourceHealth[];

  it('names the operator and shows recent staleness in seconds', () => {
    const html = sourceRow(ukpn);
    expect(html).toContain('UK Power Networks');
    expect(html).toContain('41 s ago');
    expect(html).toContain('data-status="ok"');
  });

  it('switches to minutes and flags stale feeds', () => {
    const html = sourceRow(npg);
    expect(html).toContain('7 min ago');
    expect(html).toContain('data-status="stale"');
  });

  it('falls back to the raw id for unknown sources and a dash for no data yet', () => {
    expect(sourceRow({ ...ukpn, source: 'npg2', staleness_s: null })).toMatch(/npg2[\s\S]*–/);
  });
});
