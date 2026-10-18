// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest';
import risk from '../../fixtures/api/areas_risk.json';
import stress from '../../fixtures/api/grid_stress_gb.json';
import { areaTile, gridTile, homesTile, renderPredict } from './predict';
import type { AreaRisk, GridStress } from './types';

describe('areaTile', () => {
  it('leads with the district most likely to see 3+ faults', () => {
    expect(areaTile(risk as AreaRisk[])).toMatchObject({
      value: '31%',
      detail: 'Manchester: chance of 3 or more faults',
      label: 'LIVE',
    });
  });

  it('says "No data" rather than looking calm when the forecast is missing', () => {
    expect(areaTile(null)).toMatchObject({ value: 'No data', label: null });
    expect(areaTile([]).value).toBe('No data');
  });
});

describe('gridTile', () => {
  const base = stress as GridStress;

  it('shows the state in words with the frequency', () => {
    expect(gridTile(base)).toMatchObject({ value: 'Normal', detail: 'GB frequency 50.02 Hz', severity: null });
  });

  it('colours only the stressed and emergency states', () => {
    expect(gridTile({ ...base, state: 'STRESSED' }).severity).toBe('risk');
    expect(gridTile({ ...base, state: 'EMERGENCY' }).severity).toBe('escalate');
    expect(gridTile({ ...base, state: 'SPLIT_SUSPECTED' })).toMatchObject({ value: 'Split suspected', severity: 'escalate' });
  });

  it('handles a missing reading and a missing endpoint', () => {
    expect(gridTile({ ...base, hz: null }).detail).toBe('No frequency reading yet');
    expect(gridTile(null).value).toBe('No data');
  });
});

it('keeps the home-sensor claim to the real probe result', () => {
  expect(homesTile()).toMatchObject({ value: 'Not served yet', label: 'REPLAY' });
  expect(homesTile().detail).not.toMatch(/every|predicts/i);
});

it('renders three tiles with badges and severity hooks', () => {
  const root = document.createElement('div');
  renderPredict(root, risk as AreaRisk[], { ...(stress as GridStress), state: 'EMERGENCY' });
  const tiles = root.querySelectorAll('.tile');
  expect(tiles).toHaveLength(3);
  expect(tiles[0].querySelector('.tile__value')!.textContent).toBe('31%');
  expect(tiles[1].querySelector('.badge')!.textContent).toBe('REPLAY');
  expect((tiles[2] as HTMLElement).dataset.severity).toBe('escalate');

  renderPredict(root, null, null);
  expect(root.querySelectorAll('.tile .badge')).toHaveLength(1);
});
