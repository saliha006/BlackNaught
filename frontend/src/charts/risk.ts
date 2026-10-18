import type { AreaRisk } from '../types';
import { type ChartCard, fillTable } from './card';
import { linear, plotRoot, svg } from './svg';
import { attachTip } from './tooltip';

const ROW_H = 22;
const LABEL_W = 96;
const VALUE_W = 40;

export const riskRows = (risk: AreaRisk[]) => [...risk].sort((a, b) => b.p_ge_k - a.p_ge_k);

const pct = (p: number) => `${Math.round(p * 100)}%`;

export function renderRisk(card: ChartCard, risk: AreaRisk[]) {
  const rows = riskRows(risk);
  card.note.textContent = rows.length
    ? `${rows[0].district} is the district most likely to see 3 or more faults tomorrow.`
    : 'No district forecast right now.';

  const { root, width } = plotRoot(card.plot, Math.max(1, rows.length) * ROW_H, 'Chance of 3 or more faults tomorrow per district');
  const x = linear([0, 1], [LABEL_W, width - VALUE_W]);
  rows.forEach((r, i) => {
    const mid = i * ROW_H + ROW_H / 2;
    svg('text', { class: 'tick', x: 0, y: mid + 4 }, root).textContent = r.district;
    // Emphasis, not a ramp: the top district in full ink, the rest in the context grey.
    svg('rect', { class: 'bar', 'data-tone': i === 0 ? 'ink' : 'context', x: LABEL_W, y: mid - 4, width: Math.max(2, x(r.p_ge_k) - LABEL_W), height: 8, rx: 2 }, root);
    svg('text', { class: 'value', x: x(r.p_ge_k) + 6, y: mid + 4 }, root).textContent = pct(r.p_ge_k);
    const target = svg('rect', { class: 'hit', x: 0, y: i * ROW_H, width, height: ROW_H, tabindex: 0 }, root);
    const label = `${r.district} · ${r.expected.toFixed(1)} faults expected`;
    target.setAttribute('aria-label', `${pct(r.p_ge_k)} chance of 3 or more faults: ${label}`);
    attachTip(target, () => [`${pct(r.p_ge_k)} chance of 3+ faults`, label]);
  });

  fillTable(
    card.table,
    ['District', 'Chance of 3+ faults', 'Faults expected'],
    rows.map((r) => [r.district, pct(r.p_ge_k), r.expected.toFixed(1)]),
  );
}
