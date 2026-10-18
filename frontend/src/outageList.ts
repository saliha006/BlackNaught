import { formatCount, formatElapsed } from './format';
import type { Outage } from './types';

const SOURCE_NAMES: Record<string, string> = {
  ukpn: 'UK Power Networks',
  ssen: 'SSEN',
  npg: 'Northern Powergrid',
  enwl: 'Electricity North West',
};

export function sortOutages(outages: Outage[]): Outage[] {
  return [...outages].sort((a, b) => b.priority_customers - a.priority_customers || b.customers - a.customers);
}

function row(o: Outage): HTMLLIElement {
  const li = document.createElement('li');
  li.innerHTML = `
    <button class="outage" type="button" data-id="${o.id}">
      <span class="outage__top">
        <span class="outage__scale">${o.scale}</span>
        <span class="badge" data-label="${o.label}">${o.label}</span>
      </span>
      <span class="outage__source">${SOURCE_NAMES[o.source] ?? o.source}</span>
      <span class="outage__stats">
        <span><b class="num">${formatCount(o.customers)}</b> customers</span>
        <span><b class="num">${o.priority_customers}</b> priority</span>
        <span><b class="num">${formatElapsed(o.elapsed_h)}</b> off</span>
      </span>
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
