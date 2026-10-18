// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest';
import outages from '../../fixtures/api/outages.json';
import { markSelected, renderOutageList, sortOutages } from './outageList';
import type { Outage } from './types';

const o = (id: number, priority_customers: number | null, customers: number | null) =>
  ({ id, priority_customers, customers }) as Outage;

it('ranks by priority customers, then customers, without mutating input', () => {
  const input = [o(1, 0, 900), o(2, 6, 10), o(3, 6, 200), o(4, 1, 5)];
  expect(sortOutages(input).map((x) => x.id)).toEqual([3, 2, 4, 1]);
  expect(input.map((x) => x.id)).toEqual([1, 2, 3, 4]);
});

it('ranks unpublished counts as zero, as Northern Powergrid sends them', () => {
  const input = [o(1, null, 23460), o(2, 1, 8), o(3, null, null)];
  expect(sortOutages(input).map((x) => x.id)).toEqual([2, 1, 3]);
});

describe('renderOutageList', () => {
  const fixture = outages as Outage[];

  function setup() {
    const list = document.createElement('ul');
    const onPick = vi.fn();
    renderOutageList(list, fixture, onPick);
    return { list, onPick };
  }

  it('renders one row per outage with its provenance label and readable source', () => {
    const { list } = setup();
    const rows = list.querySelectorAll('button.outage');
    expect(rows).toHaveLength(fixture.length);
    expect(rows[0].querySelector('.badge')!.textContent).toBe('LIVE');
    expect(list.textContent).toContain('UK Power Networks');
    expect(list.textContent).toContain('1 h 8 min');
  });

  it('passes the clicked outage to onPick, including clicks on inner text', () => {
    const { list, onPick } = setup();
    const btn = list.querySelector<HTMLButtonElement>('button[data-id="102"]')!;
    btn.querySelector<HTMLElement>('.outage__source')!.click();
    expect(onPick).toHaveBeenCalledWith(expect.objectContaining({ id: 102 }));
  });

  it('keeps an outage with no location in the list, disabled and saying why', () => {
    const list = document.createElement('ul');
    renderOutageList(list, [...fixture, { ...fixture[1], id: 999, centroid: null }], vi.fn());
    const row = list.querySelector<HTMLButtonElement>('button[data-id="999"]')!;
    expect(row.disabled).toBe(true);
    expect(row.textContent).toContain('No map location yet');
    expect(list.querySelector<HTMLButtonElement>('button[data-id="101"]')!.disabled).toBe(false);
    expect(list.querySelector('button[data-id="101"] .outage__note')).toBeNull();
  });

  it('says why the list is empty', () => {
    const list = document.createElement('ul');
    renderOutageList(list, [], vi.fn());
    expect(list.textContent).toBe('No active power cuts right now.');
    renderOutageList(list, [], vi.fn(), 'No power cuts match these filters.');
    expect(list.textContent).toBe('No power cuts match these filters.');
  });

  it('renders a hostile source name as text, not markup', () => {
    const list = document.createElement('ul');
    renderOutageList(list, [{ ...fixture[0], source: '<img src=x onerror=alert(1)>' }], vi.fn());
    expect(list.querySelector('img')).toBeNull();
    expect(list.querySelector('.outage__source')!.textContent).toBe('<img src=x onerror=alert(1)>');
  });

  it('ignores clicks outside a row', () => {
    const { list, onPick } = setup();
    list.click();
    expect(onPick).not.toHaveBeenCalled();
  });

  it('marks exactly one row as pressed', () => {
    const { list } = setup();
    markSelected(list, 103);
    markSelected(list, 101);
    const pressed = [...list.querySelectorAll('[aria-pressed="true"]')].map((b) => (b as HTMLElement).dataset.id);
    expect(pressed).toEqual(['101']);
  });
});
