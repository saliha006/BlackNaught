import { formatElapsed } from '../format';
import type { Outage } from '../types';
import { type ChartCard, fillLegend, fillTable } from './card';
import { linear, plotRoot, svg } from './svg';
import { attachTip, hideTip, showTip } from './tooltip';

const X_MAX_H = 48;
const HEIGHT = 196;
const M = { top: 8, right: 10, bottom: 24, left: 38 };

/** Share of past outages still off after `h` hours: hourly KM points, linear between, flat past the curve's end. */
export function stillOff(curve: number[], h: number): number {
  if (h <= 0) return 1;
  const last = curve.length - 1;
  if (h >= last) return curve[last];
  const i = Math.floor(h);
  return curve[i] + (curve[i + 1] - curve[i]) * (h - i);
}

const pct = (share: number) => `${Math.round(share * 100)}%`;

/** How many live cuts have already outlasted three quarters of history. */
export const outlasting = (curve: number[], outages: Outage[]) =>
  outages.filter((o) => stillOff(curve, o.elapsed_h) <= 0.25).length;

export function renderOutageLength(card: ChartCard, curve: number[], outages: Outage[], escalated: Set<number>) {
  card.note.textContent = outages.length
    ? `${outlasting(curve, outages)} of ${outages.length} live cuts have already lasted longer than 75% of past outages.`
    : 'No power cuts match these filters.';

  const { root, width } = plotRoot(card.plot, HEIGHT, 'Survival curve of past outages with live cuts placed on it');
  const x = linear([0, X_MAX_H], [M.left, width - M.right]);
  const y = linear([0, 1], [HEIGHT - M.bottom, M.top]);

  for (const t of [0, 0.25, 0.5, 0.75, 1]) {
    svg('line', { class: 'grid', x1: M.left, x2: width - M.right, y1: y(t), y2: y(t) }, root);
    svg('text', { class: 'tick', x: M.left - 6, y: y(t) + 4, 'text-anchor': 'end' }, root).textContent = pct(t);
  }
  for (const h of [0, 12, 24, 36, 48]) {
    svg('text', { class: 'tick', x: x(h), y: HEIGHT - 6, 'text-anchor': 'middle' }, root).textContent = `${h} h`;
  }

  const hours = Array.from({ length: X_MAX_H * 2 + 1 }, (_, i) => i / 2);
  const line = hours.map((h, i) => `${i ? 'L' : 'M'}${x(h).toFixed(1)},${y(stillOff(curve, h)).toFixed(1)}`).join('');
  svg('path', { class: 'area', d: `${line}L${x(X_MAX_H)},${y(0)}L${x(0)},${y(0)}Z` }, root);
  svg('path', { class: 'line', d: line }, root);

  const cross = svg('line', { class: 'crosshair', y1: M.top, y2: HEIGHT - M.bottom, visibility: 'hidden' }, root);
  const hit = svg('rect', { class: 'hit', x: M.left, y: M.top, width: width - M.left - M.right, height: HEIGHT - M.top - M.bottom }, root);
  hit.addEventListener('pointermove', (e) => {
    const box = root.getBoundingClientRect();
    const h = Math.round(((e.clientX - box.left - M.left) / (width - M.left - M.right)) * X_MAX_H * 2) / 2;
    if (h < 0 || h > X_MAX_H) return;
    cross.setAttribute('x1', String(x(h)));
    cross.setAttribute('x2', String(x(h)));
    cross.setAttribute('visibility', 'visible');
    showTip(e.clientX, box.top + y(stillOff(curve, h)), `${pct(stillOff(curve, h))} still off`, `after ${formatElapsed(h)}, UKPN history`);
  });
  hit.addEventListener('pointerleave', () => {
    cross.setAttribute('visibility', 'hidden');
    hideTip();
  });

  for (const o of outages) {
    const share = stillOff(curve, o.elapsed_h);
    const cx = x(Math.min(o.elapsed_h, X_MAX_H));
    const cy = y(share);
    const tone = escalated.has(o.id) ? 'escalate' : 'ink';
    svg('circle', { class: 'dot', 'data-tone': tone, cx, cy, r: 4 }, root);
    const target = svg('circle', { class: 'dot-hit', cx, cy, r: 12, tabindex: 0 }, root);
    const label = `${o.source.toUpperCase()} ${o.scale} · off ${formatElapsed(o.elapsed_h)}${tone === 'escalate' ? ' · has an escalation' : ''}`;
    target.setAttribute('aria-label', `${label}: longer than ${pct(1 - share)} of past outages`);
    attachTip(target, () => [`Longer than ${pct(1 - share)} of past outages`, label]);
  }

  fillLegend(card.legend, [
    { key: 'line', tone: 'ink', text: 'UKPN history' },
    { key: 'dot', tone: 'ink', text: 'Live cut' },
    { key: 'dot', tone: 'escalate', text: 'Has an escalation' },
  ]);
  fillTable(
    card.table,
    ['Operator', 'Scale', 'Off for', 'Past outages still off then'],
    outages.map((o) => [o.source.toUpperCase(), o.scale, formatElapsed(o.elapsed_h), pct(stillOff(curve, o.elapsed_h))]),
  );
}
