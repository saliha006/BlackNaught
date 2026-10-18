import { describe, expect, it } from 'vitest';
import km from '../../backend/models/km_enwl.json';
import triage from '../../fixtures/api/triage.json';
import health from '../../fixtures/api/sources_health.json';
import { percentStillOff, sourceRow, survivalPath, triageRow } from './landing';
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
