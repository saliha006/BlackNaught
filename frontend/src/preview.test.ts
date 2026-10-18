// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest';
import xml from '../../fixtures/api/cap_alert_sample.xml?raw';
import triage from '../../fixtures/api/triage.json';
import { capPhone, parseCap, smsFor, smsPhone } from './preview';
import type { Triage } from './types';

const item = (triage as Triage).items[0];

describe('CAP preview', () => {
  it('reads the fields a phone shows and marks exercises', () => {
    const cap = parseCap(xml);
    expect(cap.status).toBe('Exercise');
    expect(cap.event).toContain('Power cut');
    expect(capPhone(cap).textContent).toContain('EXERCISE');
  });

  it('copes with a CAP document missing optional fields', () => {
    const cap = parseCap('<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2"><status>Actual</status></alert>');
    expect(cap.headline).toBe('');
    expect(capPhone(cap).textContent).toContain('Emergency alert');
  });
});

describe('SMS preview', () => {
  it('gives the action and the reserve clock, never an ETA', () => {
    const text = smsFor({ ...item, escalate: true, reserve_left_h: 2.5 });
    expect(text).toContain('2 h 30 min left');
    expect(text).toContain('call 999');
    expect(text.toLowerCase()).not.toMatch(/back (on|at)|restored by/);
    expect(smsFor({ ...item, escalate: false })).toContain('Reply 1');
    expect(smsPhone(item).textContent).toContain('Text message');
  });
});
