import { formatAgo } from '../format';
import { OPERATORS } from '../state';
import type { SourceHealth } from '../types';
import { type ChartCard, fillTable } from './card';
import { linear, plotRoot, svg } from './svg';
import { attachTip } from './tooltip';

const ROW_H = 26;
const LABEL_W = 70;
const STATUS_W = 74;
// The backend calls a feed stale after twice its polling interval; the scale runs to three so the line sits inside.
const STALE_AT = 2;
const SCALE_MAX = 3;

const STATUS_TONE: Record<SourceHealth['status'], string> = { ok: 'ink', stale: 'risk', degraded: 'risk', down: 'escalate' };

const OTHER_FEEDS: Record<string, string> = { elexon: 'Elexon', ioda: 'IODA' };

const feedName = (source: string) =>
  OPERATORS.find((op) => op.id === source)?.name ?? OTHER_FEEDS[source] ?? source.toUpperCase();

const ago = (seconds: number | null) => (seconds === null ? 'never' : formatAgo(seconds));

export function renderFeeds(card: ChartCard, feeds: SourceHealth[]) {
  const late = feeds.filter((f) => f.status !== 'ok').length;
  card.note.textContent = late ? `${late} of ${feeds.length} feeds need attention.` : `All ${feeds.length} feeds are on time.`;

  const { root, width } = plotRoot(card.plot, Math.max(1, feeds.length) * ROW_H, 'Time since each feed last delivered data');
  const x = linear([0, SCALE_MAX], [LABEL_W, width - STATUS_W]);
  feeds.forEach((f, i) => {
    const mid = i * ROW_H + ROW_H / 2;
    const ratio = f.staleness_s === null ? SCALE_MAX : Math.min(SCALE_MAX, f.staleness_s / f.interval_s);
    const tone = STATUS_TONE[f.status];
    svg('text', { class: 'tick', x: 0, y: mid + 4 }, root).textContent = feedName(f.source);
    svg('rect', { class: 'track', x: LABEL_W, y: mid - 3, width: x(SCALE_MAX) - LABEL_W, height: 6, rx: 3 }, root);
    svg('rect', { class: 'bar', 'data-tone': tone, x: LABEL_W, y: mid - 3, width: Math.max(2, x(ratio) - LABEL_W), height: 6, rx: 3 }, root);
    svg('line', { class: 'reference', x1: x(STALE_AT), x2: x(STALE_AT), y1: mid - 7, y2: mid + 7 }, root);
    svg('circle', { class: 'dot', 'data-tone': tone, cx: width - STATUS_W + 12, cy: mid, r: 4 }, root);
    svg('text', { class: 'value', x: width - STATUS_W + 22, y: mid + 4 }, root).textContent = f.status;
    const target = svg('rect', { class: 'hit', x: 0, y: i * ROW_H, width, height: ROW_H, tabindex: 0 }, root);
    const label = `${feedName(f.source)} · polled every ${f.interval_s} s · ${f.status}`;
    target.setAttribute('aria-label', `Last data ${ago(f.staleness_s)}: ${label}`);
    attachTip(target, () => [`Last data ${ago(f.staleness_s)}`, label]);
  });

  fillTable(
    card.table,
    ['Feed', 'Polled every', 'Last data', 'Status', 'Records last poll'],
    feeds.map((f) => [feedName(f.source), `${f.interval_s} s`, ago(f.staleness_s), f.status, f.records_last === null ? '–' : String(f.records_last)]),
  );
}
