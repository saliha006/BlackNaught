// @vitest-environment happy-dom
import { beforeEach, describe, expect, it } from 'vitest';
import km from '../../../backend/models/km_enwl.json';
import grades from '../../../fixtures/api/agent_grades.json';
import risk from '../../../fixtures/api/areas_risk.json';
import outages from '../../../fixtures/api/outages.json';
import health from '../../../fixtures/api/sources_health.json';
import type { AreaRisk, Grades, Outage, SourceHealth } from '../types';
import { accuracyRows, gradedCount, renderAccuracy } from './accuracy';
import { chartCard, type ChartCard, setBadge, showUnavailable } from './card';
import { renderFeeds } from './feeds';
import { outlasting, renderOutageLength, stillOff } from './outageLength';
import { renderRisk, riskRows } from './risk';
import { hideTip, showTip } from './tooltip';

const g = grades as Grades;
const live = (outages as Outage[]).filter((o) => o.status === 'active');
let card: ChartCard;

beforeEach(() => {
  document.body.innerHTML = '';
  card = chartCard(document.body, 'Title', 'Subtitle', 'LIVE');
});

const text = (sel: string) => [...document.querySelectorAll(sel)].map((n) => n.textContent);

describe('chartCard', () => {
  it('flips between the chart and its table view', () => {
    const toggle = document.querySelector<HTMLButtonElement>('.card__toggle')!;
    toggle.click();
    expect(card.table.hidden).toBe(false);
    expect(card.plot.hidden).toBe(true);
    expect(toggle.getAttribute('aria-pressed')).toBe('true');
    toggle.click();
    expect(card.table.hidden).toBe(true);
  });

  it('updates or hides the provenance badge', () => {
    setBadge(card, 'BASELINE');
    expect(card.badge.textContent).toBe('BASELINE');
    expect(card.badge.dataset.label).toBe('BASELINE');
    setBadge(card, null);
    expect(card.badge.hidden).toBe(true);
  });

  it('explains an empty card', () => {
    renderRisk(card, risk as AreaRisk[]);
    showUnavailable(card, 'The district forecast');
    expect(card.note.textContent).toBe('The district forecast is unavailable right now.');
    expect(card.plot.children).toHaveLength(0);
    expect(card.table.children).toHaveLength(0);
  });
});

describe('outage length vs history', () => {
  it('reads the survival curve between hourly points and past its end', () => {
    expect(stillOff(km.curve, 0)).toBe(1);
    expect(stillOff(km.curve, 4)).toBeCloseTo(km.curve[4]);
    expect(stillOff(km.curve, 1.5)).toBeCloseTo((km.curve[1] + km.curve[2]) / 2);
    expect(stillOff(km.curve, 10_000)).toBe(km.curve[km.curve.length - 1]);
  });

  it('counts cuts that outlasted three quarters of history', () => {
    const long = { ...live[0], elapsed_h: 30 };
    expect(outlasting(km.curve, [live[0], long])).toBe(1);
  });

  it('draws one dot per cut, red where a patient is escalated, with a table twin', () => {
    renderOutageLength(card, km.curve, live, new Set([101]));
    expect(card.note.textContent).toBe('0 of 2 live cuts have already lasted longer than 75% of past outages.');
    const tones = [...card.plot.querySelectorAll('.dot')].map((d) => d.getAttribute('data-tone'));
    expect(tones).toEqual(['escalate', 'ink']);
    expect(card.plot.querySelector('.dot-hit')!.getAttribute('aria-label')).toContain('has an escalation');
    expect(card.table.querySelectorAll('tbody tr')).toHaveLength(2);
    expect(text('.legend__item')).toEqual(['UKPN history', 'Live cut', 'Has an escalation']);
  });

  it('tracks the pointer with a crosshair that snaps to the half hour', () => {
    renderOutageLength(card, km.curve, live, new Set());
    const hit = card.plot.querySelector('.hit')!;
    const cross = card.plot.querySelector('.crosshair')!;
    // happy-dom lays nothing out, so the plot box sits at 0,0 and clientX maps straight onto the axis.
    hit.dispatchEvent(new PointerEvent('pointermove', { clientX: 38 + (360 - 48) / 8, clientY: 50 }));
    expect(cross.getAttribute('visibility')).toBe('visible');
    expect(document.querySelector('.chart-tip strong')!.textContent).toBe(`${Math.round(km.curve[6] * 100)}% still off`);
    hit.dispatchEvent(new PointerEvent('pointermove', { clientX: 5000, clientY: 50 }));
    expect(document.querySelector('.chart-tip span')!.textContent).toBe('after 6 h, UKPN history');
    hit.dispatchEvent(new PointerEvent('pointerleave'));
    expect(cross.getAttribute('visibility')).toBe('hidden');
  });

  it('says so when the filters leave nothing', () => {
    renderOutageLength(card, km.curve, [], new Set());
    expect(card.note.textContent).toBe('No power cuts match these filters.');
  });
});

describe('prediction accuracy', () => {
  it('totals the grades and keeps rows in chip then horizon order', () => {
    expect(gradedCount(g)).toBe(66);
    const mixed: Grades = {
      trend: [],
      by_horizon: [
        { ...g.by_horizon[0], source: 'npg', h: 2 },
        { ...g.by_horizon[0], source: 'ukpn', h: 4 },
        { ...g.by_horizon[0], source: 'ukpn', h: 2 },
      ],
    };
    expect(accuracyRows(mixed, new Set(['ukpn', 'ssen', 'npg'])).map((r) => `${r.source}${r.h}`)).toEqual(['ukpn2', 'ukpn4', 'npg2']);
    expect(accuracyRows(mixed, new Set(['npg'])).map((r) => r.source)).toEqual(['npg']);
  });

  it('draws the trend with a coin-flip line and says when a horizon has no grades yet', () => {
    const withCensored: Grades = { ...g, by_horizon: [...g.by_horizon, { ...g.by_horizon[0], source: 'ssen', brier: null, n: 0, n_censored: 9 }] };
    renderAccuracy(card, withCensored, new Set(['ukpn', 'ssen']));
    expect(card.plot.querySelectorAll('svg')).toHaveLength(2);
    expect(card.plot.querySelector('.reference')).not.toBeNull();
    expect(card.plot.textContent).toContain('coin flip');
    expect(card.plot.textContent).toContain('Not graded yet · 9 censored');
    expect(card.plot.querySelectorAll('.bar[data-tone="ink"]')).toHaveLength(2);
    expect(card.table.querySelectorAll('tbody tr')).toHaveLength(3 + g.trend.length);
  });
});

describe("tomorrow's risk", () => {
  it('sorts districts by chance and emphasises only the top one', () => {
    expect(riskRows(risk as AreaRisk[]).map((r) => r.district)).toEqual(['Manchester', 'Lancaster']);
    renderRisk(card, risk as AreaRisk[]);
    expect(card.note.textContent).toContain('Manchester');
    const tones = [...card.plot.querySelectorAll('.bar')].map((b) => b.getAttribute('data-tone'));
    expect(tones).toEqual(['ink', 'context']);
  });

  it('handles an empty forecast', () => {
    renderRisk(card, []);
    expect(card.note.textContent).toBe('No district forecast right now.');
  });
});

describe('feed health', () => {
  const feeds = health.sources as SourceHealth[];

  it('flags late feeds with severity colour and their status word', () => {
    renderFeeds(card, feeds);
    expect(card.note.textContent).toBe('1 of 4 feeds need attention.');
    const npg = [...card.plot.querySelectorAll('.dot')][2];
    expect(npg.getAttribute('data-tone')).toBe('risk');
    expect(card.plot.textContent).toContain('stale');
    expect(card.table.textContent).toContain('7 min ago');
  });

  it('names feeds the way the team does and handles a feed with no data yet', () => {
    renderFeeds(card, [{ ...feeds[0], source: 'ioda', staleness_s: null, records_last: null, status: 'down' }]);
    expect(card.plot.textContent).toContain('IODA');
    expect(card.table.textContent).toContain('never');
    expect(card.plot.querySelector('.dot')!.getAttribute('data-tone')).toBe('escalate');
    expect(card.note.textContent).toBe('1 of 1 feeds need attention.');
  });

  it('says all clear when every feed is on time', () => {
    renderFeeds(card, feeds.filter((f) => f.status === 'ok'));
    expect(card.note.textContent).toBe('All 3 feeds are on time.');
  });
});

describe('tooltip', () => {
  it('shows value first, label second, as text', () => {
    showTip(10, 20, '<b>80%</b>', 'Bolton');
    const tip = document.querySelector<HTMLElement>('.chart-tip')!;
    expect(tip.hidden).toBe(false);
    expect(tip.querySelector('strong')!.textContent).toBe('<b>80%</b>');
    expect(tip.querySelector('b')).toBeNull();
    hideTip();
    expect(tip.hidden).toBe(true);
  });

  it('opens on keyboard focus of a mark', () => {
    renderRisk(card, risk as AreaRisk[]);
    card.plot.querySelector('.hit')!.dispatchEvent(new Event('focus'));
    expect(document.querySelector('.chart-tip strong')!.textContent).toBe('31% chance of 3+ faults');
    card.plot.querySelector('.hit')!.dispatchEvent(new Event('blur'));
    expect(document.querySelector<HTMLElement>('.chart-tip')!.hidden).toBe(true);
  });
});
