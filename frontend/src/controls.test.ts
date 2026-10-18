// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest';
import { renderControls } from './controls';
import type { LayerGroup } from './map';
import { allOperators, type Filters } from './state';

function setup() {
  const root = document.createElement('div');
  const filters: Filters = { operators: allOperators(), escalationsOnly: false };
  const layers: Record<LayerGroup, boolean> = { beams: true, sweep: true, cells: true };
  const on = { filters: vi.fn(), layer: vi.fn(), live: vi.fn() };
  const controls = renderControls(root, filters, layers, on);
  const button = (name: string) =>
    [...root.querySelectorAll<HTMLButtonElement>('button')].find((b) => b.textContent!.startsWith(name))!;
  return { root, filters, layers, on, controls, button };
}

describe('renderControls', () => {
  it('starts with every operator and layer on and escalations off', () => {
    const { root } = setup();
    const pressed = [...root.querySelectorAll('[aria-pressed="true"]')].map((b) => b.textContent);
    expect(pressed).toEqual(['UKPN', 'SSEN', 'NPg', 'Beams', 'Sweep', 'Cells', 'Live']);
    expect(root.querySelectorAll('[role="group"]')).toHaveLength(4);
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

  it('pauses and resumes live updates', () => {
    const { on, button } = setup();
    button('Live').click();
    expect(on.live).toHaveBeenCalledWith(false);
    button('Live').click();
    expect(on.live).toHaveBeenLastCalledWith(true);
  });

  it('reports the stream state, with the event rate only while live', () => {
    const { controls, root } = setup();
    const live = () => root.querySelector<HTMLButtonElement>('.chip--live')!;
    controls.setLive('live', '1.2k events/s');
    expect(live().textContent).toBe('Live1.2k events/s');
    expect(live().getAttribute('aria-pressed')).toBe('true');
    controls.setLive('reconnecting', '1.2k events/s');
    expect(live().textContent).toBe('Reconnecting…');
    controls.setLive('paused');
    expect(live().getAttribute('aria-pressed')).toBe('false');
    controls.setLive('unavailable');
    expect(live().disabled).toBe(true);
    expect(live().title).toContain('Fixture');
  });
});
