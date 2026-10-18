// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest';
import triage from '../../fixtures/api/triage.json';
import { renderTriage } from './triage';
import type { Triage } from './types';

const items = (triage as Triage).items;
const actions = () => ({ show: vi.fn(), sms: vi.fn(), decide: vi.fn() });

describe('renderTriage', () => {
  it('ranks rows, shows the expected case before the range, and labels patients as simulated', () => {
    const list = document.createElement('ul');
    renderTriage(list, [...items].reverse(), new Set(), actions());
    const rows = [...list.querySelectorAll('li.triage')];
    expect(rows[0].querySelector('.triage__rank')!.textContent).toBe('#1');
    const terms = [...rows[0].querySelectorAll('dt')].map((d) => d.textContent);
    expect(terms.slice(0, 3)).toEqual(['Backup left', 'Likely back in', 'Range (q50 to q90)']);
    expect(rows[0].querySelector('.badge')!.textContent).toBe('SIMULATED');
    expect(rows[0].querySelector('summary')!.textContent).toBe('Why ranked here');
  });

  it('offers approve and reject only for decisions still waiting', () => {
    const list = document.createElement('ul');
    const on = actions();
    const withDecision = [
      { ...items[0], decision_id: 'd-1' },
      { ...items[0], rank: 2, decision_id: 'd-2' },
    ];
    renderTriage(list, withDecision, new Set(['d-1']), on);
    const [first, second] = list.querySelectorAll('li.triage');
    expect(second.textContent).not.toContain('Approve');
    (first.querySelector('.chip--approve') as HTMLButtonElement).click();
    expect(on.decide).toHaveBeenCalledWith('d-1', true);
    const buttons = [...first.querySelectorAll('button')];
    buttons.find((b) => b.textContent === 'Reject')!.click();
    buttons.find((b) => b.textContent === 'Preview SMS')!.click();
    buttons.find((b) => b.textContent === 'Show fault')!.click();
    expect(on.decide).toHaveBeenCalledWith('d-1', false);
    expect(on.sms).toHaveBeenCalledWith(withDecision[0]);
    expect(on.show).toHaveBeenCalledWith(items[0].outage_id);
  });

  it('keeps an open "why" and the focused button when a refresh changes the data', () => {
    document.body.innerHTML = '<ul id="l"></ul>';
    const list = document.querySelector<HTMLElement>('#l')!;
    const on = actions();
    renderTriage(list, items, new Set(), on);
    const first = list.querySelector<HTMLElement>('li.triage')!;
    first.querySelector('details')!.setAttribute('open', '');
    first.querySelector<HTMLButtonElement>('[data-action="Preview SMS"]')!.focus();
    const before = list.firstElementChild;
    renderTriage(list, items, new Set(), on);
    expect(list.firstElementChild).toBe(before);
    renderTriage(list, [{ ...items[0], harm: items[0].harm + 1 }, ...items.slice(1)], new Set(), on);
    const again = list.querySelector<HTMLElement>(`[data-key="${items[0].patient_ref}"]`)!;
    expect(again).not.toBe(before);
    expect(again.querySelector('details')!.hasAttribute('open')).toBe(true);
    expect((document.activeElement as HTMLElement).dataset.action).toBe('Preview SMS');
  });

  it('says so when nobody is in a live cut', () => {
    const list = document.createElement('ul');
    renderTriage(list, [], new Set(), actions());
    expect(list.textContent).toContain('Nobody on the register');
  });
});
