import type { Label } from '../types';

export interface ChartCard {
  badge: HTMLSpanElement;
  note: HTMLParagraphElement;
  plot: HTMLDivElement;
  legend: HTMLDivElement;
  table: HTMLTableElement;
}

/** A chart with its title, provenance badge and a table-view twin, so no value is reachable only by hovering. */
export function chartCard(parent: HTMLElement, title: string, subtitle: string, label: Label | null): ChartCard {
  const card = document.createElement('section');
  card.className = 'card';
  const id = `card-${parent.children.length}`;
  card.setAttribute('aria-labelledby', id);

  const head = document.createElement('header');
  head.className = 'card__head';
  const titles = document.createElement('div');
  const h = document.createElement('h3');
  h.id = id;
  h.textContent = title;
  const sub = document.createElement('p');
  sub.className = 'card__sub';
  sub.textContent = subtitle;
  titles.append(h, sub);
  const badge = document.createElement('span');
  badge.className = 'badge';
  head.append(titles, badge);

  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'card__toggle';
  toggle.textContent = 'Table';
  toggle.setAttribute('aria-pressed', 'false');
  head.append(toggle);

  const note = document.createElement('p');
  note.className = 'card__note';
  const plot = document.createElement('div');
  plot.className = 'card__plot';
  const legend = document.createElement('div');
  legend.className = 'card__legend';
  const table = document.createElement('table');
  table.className = 'card__table';
  table.hidden = true;

  toggle.addEventListener('click', () => {
    const asTable = toggle.getAttribute('aria-pressed') !== 'true';
    toggle.setAttribute('aria-pressed', String(asTable));
    table.hidden = !asTable;
    plot.hidden = asTable;
    legend.hidden = asTable;
  });

  card.append(head, note, plot, legend, table);
  parent.append(card);
  const chart = { badge, note, plot, legend, table };
  setBadge(chart, label);
  return chart;
}

/** Provenance can change under a card (BASELINE becomes LIVE once a trained model replaces the climatology). */
export function setBadge(card: ChartCard, label: Label | null) {
  card.badge.hidden = label === null;
  card.badge.textContent = label ?? '';
  if (label) card.badge.dataset.label = label;
}

/** Says why a card is empty instead of leaving a blank box. */
export function showUnavailable(card: ChartCard, what: string) {
  card.note.textContent = `${what} is unavailable right now.`;
  card.plot.replaceChildren();
  card.legend.replaceChildren();
  card.table.replaceChildren();
}

export function fillTable(table: HTMLTableElement, head: string[], rows: string[][]) {
  const thead = document.createElement('thead');
  const hr = document.createElement('tr');
  for (const text of head) {
    const th = document.createElement('th');
    th.scope = 'col';
    th.textContent = text;
    hr.append(th);
  }
  thead.append(hr);
  const tbody = document.createElement('tbody');
  for (const row of rows) {
    const tr = document.createElement('tr');
    for (const text of row) {
      const td = document.createElement('td');
      td.textContent = text;
      tr.append(td);
    }
    tbody.append(tr);
  }
  table.replaceChildren(thead, tbody);
}

/** Legend entries keyed by the mark they describe: a line key for lines, a dot for dots. */
export function fillLegend(legend: HTMLElement, entries: { key: 'line' | 'dot'; tone: string; text: string }[]) {
  legend.replaceChildren(
    ...entries.map(({ key, tone, text }) => {
      const item = document.createElement('span');
      item.className = 'legend__item';
      const swatch = document.createElement('i');
      swatch.className = `legend__${key}`;
      swatch.dataset.tone = tone;
      item.append(swatch, text);
      return item;
    }),
  );
}
