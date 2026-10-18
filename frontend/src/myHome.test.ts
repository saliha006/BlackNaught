// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest';
import sample from '../../fixtures/api/me_home.json';
import { renderMyHome } from './myHome';
import type { MyHome } from './types';

const home = sample as MyHome;

describe('renderMyHome', () => {
  it('shows one headline level over the three layer gauges', () => {
    const root = document.createElement('div');
    renderMyHome(root, home);
    expect(root.querySelector('.home__level')!.textContent).toBe('High');
    const gauges = [...root.querySelectorAll<HTMLElement>('.gauge')];
    expect(gauges).toHaveLength(3);
    expect(gauges[1].dataset.value).toBe('none');
    expect(gauges[1].textContent).toContain('No data');
    expect(root.querySelector('.badge')!.textContent).toBe('SIMULATED');
  });

  it('says "not enough data" rather than low, and never shows an ETA', () => {
    const root = document.createElement('div');
    renderMyHome(root, {
      ...home,
      power: 'on',
      since: null,
      reserve: { ...home.reserve, ends_at: null, hours_left: null },
      grid_context: { hz: null, note: 'grid health: the same for everyone' },
      risk: { ...home.risk, level: 'unknown' },
    });
    expect(root.querySelector('.home__level')!.textContent).toBe('Not enough data');
    expect(root.textContent).toContain('Power is on');
    expect(root.textContent).toContain('Grid frequency unavailable');
    expect(root.textContent!.toLowerCase()).not.toContain('eta');
    renderMyHome(root, { ...home, power: 'unknown', since: null });
    expect(root.textContent).toContain('Power state unknown');
  });
});
