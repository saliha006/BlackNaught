import { OPERATORS } from '../state';
import type { Grades, HorizonGrade } from '../types';
import { type ChartCard, fillTable } from './card';
import { clamp, linear, plotRoot, svg } from './svg';
import { attachTip } from './tooltip';

// A forecast of 50% every time scores 0.25, so anything above this line is worse than a coin flip.
const COIN_FLIP = 0.25;
const TREND_H = 132;
const ROW_H = 26;
const M = { top: 10, right: 52, bottom: 22, left: 38 };

export const gradedCount = (grades: Grades) => grades.by_horizon.reduce((sum, g) => sum + g.n, 0);

const operatorName = (source: string) => OPERATORS.find((op) => op.id === source)?.name ?? source.toUpperCase();

/** Rows for the chosen operators, in chip order then horizon, so they never reshuffle when data refreshes. */
export function accuracyRows(grades: Grades, operators: Set<string>): HorizonGrade[] {
  const order = (s: string) => {
    const i = OPERATORS.findIndex((op) => op.id === s);
    return i < 0 ? OPERATORS.length : i;
  };
  return grades.by_horizon
    .filter((g) => !OPERATORS.some((op) => op.id === g.source) || operators.has(g.source))
    .sort((a, b) => order(a.source) - order(b.source) || a.h - b.h);
}

const clock = (iso: string) => new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

function renderTrend(card: ChartCard, grades: Grades) {
  const { root, width } = plotRoot(card.plot, TREND_H, 'Brier score of graded predictions per hour');
  const trend = grades.trend;
  const top = Math.max(0.3, ...trend.map((t) => t.brier * 1.1));
  const x = linear([0, Math.max(1, trend.length - 1)], [M.left, width - M.right]);
  const y = linear([0, top], [TREND_H - M.bottom, M.top]);

  for (const t of [0, 0.1, 0.2, 0.3].filter((t) => t <= top)) {
    svg('line', { class: 'grid', x1: M.left, x2: width - M.right, y1: y(t), y2: y(t) }, root);
    svg('text', { class: 'tick', x: M.left - 6, y: y(t) + 4, 'text-anchor': 'end' }, root).textContent = t.toFixed(1);
  }
  svg('line', { class: 'reference', x1: M.left, x2: width - M.right, y1: y(COIN_FLIP), y2: y(COIN_FLIP) }, root);
  svg('text', { class: 'tick', x: width - M.right + 4, y: y(COIN_FLIP) + 4 }, root).textContent = 'coin flip';

  if (trend.length) {
    svg('path', { class: 'line', d: trend.map((t, i) => `${i ? 'L' : 'M'}${x(i)},${y(t.brier)}`).join('') }, root);
    svg('text', { class: 'tick', x: x(0), y: TREND_H - 6, 'text-anchor': 'start' }, root).textContent = clock(trend[0].at);
    svg('text', { class: 'tick', x: x(trend.length - 1), y: TREND_H - 6, 'text-anchor': 'end' }, root).textContent =
      clock(trend[trend.length - 1].at);
  }
  trend.forEach((t, i) => {
    svg('circle', { class: 'dot', 'data-tone': 'ink', cx: x(i), cy: y(t.brier), r: 4 }, root);
    const target = svg('circle', { class: 'dot-hit', cx: x(i), cy: y(t.brier), r: 12, tabindex: 0 }, root);
    const label = `${clock(t.at)}${t.n === undefined ? '' : ` · ${t.n} graded`}`;
    target.setAttribute('aria-label', `${label}: Brier ${t.brier.toFixed(3)}`);
    attachTip(target, () => [`Brier ${t.brier.toFixed(3)}`, label]);
  });
}

function renderRows(container: HTMLElement, rows: HorizonGrade[]) {
  const height = Math.max(1, rows.length) * ROW_H;
  const { root, width } = plotRoot(container, height, 'Brier score by operator and horizon');
  const labelW = 86;
  const x = linear([0, 0.3], [labelW, width - M.right]);
  rows.forEach((g, i) => {
    const mid = i * ROW_H + ROW_H / 2;
    svg('text', { class: 'tick', x: 0, y: mid + 4 }, root).textContent = `${operatorName(g.source)} · ${g.h} h`;
    if (g.brier === null) {
      svg('text', { class: 'tick', x: labelW, y: mid + 4 }, root).textContent = `Not graded yet · ${g.n_censored} censored`;
      return;
    }
    const end = x(clamp(g.brier, 0, 0.3));
    svg('rect', { class: 'bar', 'data-tone': 'ink', x: labelW, y: mid - 4, width: Math.max(2, end - labelW), height: 8, rx: 2 }, root);
    const value = svg('text', { class: 'value', x: end + 6, y: mid + 4 }, root);
    value.textContent = g.brier.toFixed(3);
    const target = svg('rect', { class: 'hit', x: labelW, y: i * ROW_H, width: width - labelW, height: ROW_H, tabindex: 0 }, root);
    const bound = g.bound ? ` · could be ${g.bound[0].toFixed(2)}–${g.bound[1].toFixed(2)} once censored cases resolve` : '';
    const label = `${operatorName(g.source)} at ${g.h} h · ${g.n} graded, ${g.n_censored} censored${bound}`;
    target.setAttribute('aria-label', `Brier ${g.brier.toFixed(3)}: ${label}`);
    attachTip(target, () => [`Brier ${g.brier!.toFixed(3)}`, label]);
  });
}

export function renderAccuracy(card: ChartCard, grades: Grades, operators: Set<string>) {
  const rows = accuracyRows(grades, operators);
  card.note.textContent = `${gradedCount(grades)} predictions graded against real restorations. Lower is better; trend covers all operators.`;
  renderTrend(card, grades);
  const rowsBox = document.createElement('div');
  rowsBox.className = 'card__rows';
  card.plot.append(rowsBox);
  renderRows(rowsBox, rows);
  fillTable(card.table, ['Operator', 'Horizon or hour', 'Brier', 'Graded', 'Censored', 'Possible range'], [
    ...rows.map((g) => [
      operatorName(g.source),
      `${g.h} h`,
      g.brier === null ? '–' : g.brier.toFixed(3),
      String(g.n),
      String(g.n_censored),
      g.bound ? `${g.bound[0].toFixed(2)}–${g.bound[1].toFixed(2)}` : '–',
    ]),
    ...grades.trend.map((t) => ['All operators', clock(t.at), t.brier.toFixed(3), t.n === undefined ? '–' : String(t.n), '–', '–']),
  ]);
}
