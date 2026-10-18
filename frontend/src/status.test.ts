// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest';
import outages from '../../fixtures/api/outages.json';
import { homeStatus, renderStatus } from './status';
import type { Outage } from './types';

const located = (outages as Outage[]).filter((o) => o.centroid);
const cut = located[0];
const data = { outages: located, escalated: new Set<number>() };

describe('homeStatus', () => {
  it('says it is checking until both the location and the data are in', () => {
    expect(homeStatus(data, null, 'pending')).toMatchObject({ level: 'unknown', headline: 'Checking your area…' });
    expect(homeStatus(null, [51.5, -0.1], 'found').headline).toBe('Checking your area…');
  });

  it('never calls a failed load or a refused location safe', () => {
    expect(homeStatus('failed', [51.5, -0.1], 'found')).toMatchObject({ level: 'unknown', headline: "Can't load power cuts right now" });
    expect(homeStatus(data, null, 'denied')).toMatchObject({ level: 'unknown', headline: 'Location is off' });
  });

  it('says safe when the nearest cut is more than 3 km away', () => {
    const [lat, lon] = cut.centroid!;
    expect(homeStatus({ outages: [cut], escalated: new Set() }, [lat + 0.1, lon], 'found')).toMatchObject({ level: 'safe', nearest: null });
    expect(homeStatus({ outages: [], escalated: new Set() }, [lat, lon], 'found').headline).toBe("You're safe");
  });

  it('says not safe, coloured by severity, and points at the cut', () => {
    const near = homeStatus({ outages: [{ ...cut, scale: 'street' }], escalated: new Set() }, cut.centroid!, 'found');
    expect(near).toMatchObject({ level: 'moderate', headline: 'Not safe', detail: 'Moderate power cut 0.0 km away' });
    expect(near.nearest?.id).toBe(cut.id);
    expect(homeStatus({ outages: [cut], escalated: new Set([cut.id]) }, cut.centroid!, 'found').level).toBe('severe');
  });
});

describe('renderStatus', () => {
  it('writes the answer and hides an empty detail line', () => {
    document.body.innerHTML = '<div id="s"><p id="term-headline"></p><p id="term-detail"></p></div>';
    const root = document.querySelector<HTMLElement>('#s')!;
    renderStatus(root, { level: 'safe', headline: "You're safe", detail: '', nearest: null });
    expect(root.dataset.level).toBe('safe');
    expect(root.querySelector('#term-headline')!.textContent).toBe("You're safe");
    expect(root.querySelector<HTMLElement>('#term-detail')!.hidden).toBe(true);
  });
});
