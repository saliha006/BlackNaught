import { formatCount, formatElapsed } from './format';
import { isLocated } from './geo';
import type { Outage } from './types';

const SOURCE_NAMES: Record<string, string> = {
  ukpn: 'UK Power Networks',
  ssen: 'SSEN',
  npg: 'Northern Powergrid',
  enwl: 'Electricity North West',
};

export function sortOutages(outages: Outage[]): Outage[] {
  // An unpublished count can't be ranked on, so it sorts as zero rather than guessing.
  const priority = (o: Outage) => o.priority_customers ?? 0;
  const customers = (o: Outage) => o.customers ?? 0;
  return [...outages].sort((a, b) => priority(b) - priority(a) || customers(b) - customers(a));
}

function row(o: Outage): HTMLLIElement {
  const li = document.createElement('li');
  // Still listed without a location: hiding a live outage would understate who is affected.
  const placed = isLocated(o);
  li.innerHTML = `
    <button class="outage" type="button" data-id="${o.id}"${placed ? '' : ' disabled'}>
      <span class="outage__top">
        <span class="outage__scale">${o.scale}</span>
        <span class="badge" data-label="${o.label}">${o.label}</span>
      </span>
      <span class="outage__source">${SOURCE_NAMES[o.source] ?? o.source}</span>
      <span class="outage__stats">
        <span><b class="num">${formatCount(o.customers)}</b> customers</span>
        <span><b class="num">${formatCount(o.priority_customers)}</b> priority</span>
        <span><b class="num">${formatElapsed(o.elapsed_h)}</b> off</span>
      </span>
      ${placed ? '' : '<span class="outage__note">No map location yet</span>'}
    </button>`;
  return li;
}

export function renderOutageList(list: HTMLElement, outages: Outage[], onPick: (o: Outage) => void) {
  const sorted = sortOutages(outages);
  list.replaceChildren(...sorted.map(row));
  list.onclick = (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>('button.outage');
    const picked = btn && sorted.find((o) => o.id === Number(btn.dataset.id));
    if (picked) onPick(picked);
  };
}

export function markSelected(list: HTMLElement, id: number) {
  for (const btn of list.querySelectorAll<HTMLButtonElement>('button.outage')) {
    const on = Number(btn.dataset.id) === id;
    btn.setAttribute('aria-pressed', String(on));
    if (on) btn.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
}
