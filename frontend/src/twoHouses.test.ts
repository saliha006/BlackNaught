// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest';
import outages from '../../fixtures/api/outages.json';
import triage from '../../fixtures/api/triage.json';
import { findPair, renderTwoHouses } from './twoHouses';
import type { Outage, TriageItem } from './types';

const items = (triage as { items: TriageItem[] }).items;
const item = (over: Partial<TriageItem>): TriageItem => ({ ...items[0], ...over });

describe('findPair', () => {
  it('finds the fixture pair: an escalation and an SMS check on the same fault', () => {
    const pair = findPair(items)!;
    expect(pair.outageId).toBe(101);
    expect(pair.escalated.device).toBe('o2_concentrator');
    expect(pair.calm.device).toBe('ventilator');
  });

  it('returns null when every patient on every fault escalates, as live triage does today', () => {
    expect(findPair(items.map((i) => ({ ...i, escalate: true })))).toBeNull();
    expect(findPair([])).toBeNull();
  });

  it('takes the highest-ranked mixed fault and prefers the demo devices', () => {
    const list = [
      item({ rank: 5, outage_id: 2, escalate: true, device: 'suction' }),
      item({ rank: 6, outage_id: 2, escalate: false, device: 'powered_bed' }),
      item({ rank: 1, outage_id: 1, escalate: true, device: 'suction' }),
      item({ rank: 2, outage_id: 1, escalate: true, device: 'o2_concentrator' }),
      item({ rank: 3, outage_id: 1, escalate: false, device: 'powered_bed' }),
      item({ rank: 4, outage_id: 1, escalate: false, device: 'ventilator' }),
    ];
    const pair = findPair(list)!;
    expect(pair.outageId).toBe(1);
    expect([pair.escalated.device, pair.calm.device]).toEqual(['o2_concentrator', 'ventilator']);
  });
});

describe('renderTwoHouses', () => {
  const root = document.createElement('section');

  it('shows both houses with the expected case first and a clear verdict', () => {
    const onShow = vi.fn();
    renderTwoHouses(root, findPair(items), (outages as Outage[])[0], onShow);
    const houses = root.querySelectorAll('.house');
    expect(houses).toHaveLength(2);
    expect(houses[0].querySelector('.house__device')!.textContent).toBe('Oxygen concentrator');
    expect(houses[0].querySelector('.sev')!.textContent).toBe('Escalate');
    expect(houses[1].querySelector('.sev')!.textContent).toBe('SMS check');
    expect([...houses[0].querySelectorAll('dt')].map((d) => d.textContent)).toEqual([
      'Backup left',
      'Power likely back in',
      'Could take (q90)',
    ]);
    expect(houses[0].querySelector('.badge')!.textContent).toBe('SIMULATED');
    expect(root.textContent).toContain('UKPN street fault · off 1 h 8 min');
    root.querySelector<HTMLButtonElement>('.two-houses__show')!.click();
    expect(onShow).toHaveBeenCalledWith(101);
  });

  it('never shows a patient an ETA-style promise, only staff-facing ranges', () => {
    renderTwoHouses(root, findPair(items), undefined, vi.fn());
    expect(root.textContent).toContain('Fault 101');
    expect(root.textContent).not.toMatch(/\bETA\b/);
  });

  it('says plainly when no fault has the pair yet', () => {
    renderTwoHouses(root, null, undefined, vi.fn());
    expect(root.querySelectorAll('.house')).toHaveLength(0);
    expect(root.textContent).toContain('No fault has the demo pair yet');
  });
});
