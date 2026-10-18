import { deviceName } from './devices';
import { badge, el, facts } from './dom';
import { formatElapsed } from './format';
import type { MyHome, RiskLayer } from './types';

const LEVEL_TEXT: Record<MyHome['risk']['level'], string> = {
  low: 'Low',
  elevated: 'Elevated',
  high: 'High',
  unknown: 'Not enough data',
};

const LAYER_NAMES: Record<RiskLayer['layer'], string> = { home: 'Your home', area: 'Your area', grid: 'The grid' };

function gauge(layer: RiskLayer) {
  const box = el('div', 'gauge');
  // No data is its own state, styled apart from "normal", so a silent feed never looks reassuring.
  box.dataset.value = layer.value === null ? 'none' : layer.value.toLowerCase();
  box.append(
    el('span', 'gauge__name', `${LAYER_NAMES[layer.layer]} · ${layer.horizon}`),
    el('b', 'gauge__value', layer.value === null ? 'No data' : layer.value.toLowerCase()),
    el('span', 'gauge__source', layer.updated ? `${layer.source} · ${new Date(layer.updated).toLocaleTimeString('en-GB')}` : layer.source),
  );
  return box;
}

/** A household's own view. Never an ETA: the reserve clock and the next action are what the person can act on. */
export function renderMyHome(root: HTMLElement, home: MyHome) {
  const head = el('header', 'home__head');
  head.append(el('b', '', home.household), badge(home.label));

  const risk = el('section', 'home__risk');
  risk.dataset.level = home.risk.level;
  risk.append(
    el('span', 'home__risk-label', 'Risk of losing power'),
    el('b', 'home__level', LEVEL_TEXT[home.risk.level]),
    el('p', 'home__reason', home.risk.reason),
  );
  const gauges = el('div', 'home__gauges');
  gauges.append(...home.risk.layers.map(gauge));

  const power = el('p', 'home__power');
  power.dataset.power = home.power;
  power.textContent =
    home.power === 'off'
      ? `Power is off${home.since ? ` since ${new Date(home.since).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}` : ''}`
      : home.power === 'on'
        ? 'Power is on'
        : 'Power state unknown';

  const left = home.reserve.hours_left;
  const reserve = facts('home__facts', [
    ['Device', deviceName(home.reserve.device)],
    ['Backup left', left === null ? '–' : formatElapsed(left)],
    [
      'Backup runs out',
      home.reserve.ends_at ? new Date(home.reserve.ends_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : 'not running',
    ],
  ]);

  const hz = home.grid_context.hz;
  root.replaceChildren(
    head,
    risk,
    gauges,
    power,
    reserve,
    el('p', 'home__action', home.next_action),
    el('p', 'home__grid', `${hz === null ? 'Grid frequency unavailable' : `Grid ${hz.toFixed(2)} Hz`} · ${home.grid_context.note}`),
  );
}
