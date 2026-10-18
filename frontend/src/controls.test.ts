// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest';
import { renderControls } from './controls';
import type { LayerGroup } from './map';
import { allOperators, type Filters } from './state';

function setup() {
  const root = document.createElement('div');
  const filters: Filters = { operators: allOperators(), escalationsOnly: false };
  const layers: Record<LayerGroup, boolean> = { beams: true, sweep: true, cells: true };
  const on = { filters: vi.fn(), layer: vi.fn() };
  const controls = renderControls(root, filters, layers, on);
  const button = (name: string) =>
    [...root.querySelectorAll<HTMLButtonElement>('button')].find((b) => b.textContent!.startsWith(name))!;
  return { root, filters, layers, on, controls, button };
}

describe('renderControls', () => {
  it('starts with every operator and layer on and escalations off', () => {
    const { root } = setup();
    const pressed = [...root.querySelectorAll('[aria-pressed="true"]')].map((b) => b.textContent);
    expect(pressed).toEqual(['UKPN', 'SSEN', 'NPg', 'Beams', 'Sweep', 'Cells']);
    expect(root.querySelectorAll('[role="group"]')).toHaveLength(3);
  });

  it('switches an operator off and back on, telling the page each time', () => {
    const { filters, on, button } = setup();
    button('SSEN').click();
    expect(filters.operators.has('ssen')).toBe(false);
    expect(button('SSEN').getAttribute('aria-pressed')).toBe('false');
    button('SSEN').click();
    expect(filters.operators.has('ssen')).toBe(true);
    expect(on.filters).toHaveBeenCalledTimes(2);
  });

  it('toggles escalations only', () => {
    const { filters, on, button } = setup();
    button('Escalations only').click();
    expect(filters.escalationsOnly).toBe(true);
    expect(on.filters).toHaveBeenCalledOnce();
  });

  it('hides a map layer group', () => {
    const { layers, on, button } = setup();
    button('Sweep').click();
    expect(layers.sweep).toBe(false);
    expect(on.layer).toHaveBeenCalledWith('sweep', false);
  });

  it('shows the escalation count, and disables the toggle when triage is unavailable', () => {
    const { controls, button } = setup();
    controls.setEscalations(3);
    expect(button('Escalations only').textContent).toBe('Escalations only3');
    expect(button('Escalations only').disabled).toBe(false);
    controls.setEscalations(null);
    expect(button('Escalations only').disabled).toBe(true);
    expect(button('Escalations only').title).toContain('unavailable');
  });
});
