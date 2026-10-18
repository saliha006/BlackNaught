import type { LayerGroup } from './map';
import { type Filters, OPERATORS } from './state';

export const LAYERS: { id: LayerGroup; name: string }[] = [
  { id: 'beams', name: 'Beams' },
  { id: 'sweep', name: 'Sweep' },
  { id: 'cells', name: 'Cells' },
];

export interface ControlHandlers {
  filters(): void;
  layer(group: LayerGroup, visible: boolean): void;
  live(on: boolean): void;
}

export type LiveState = 'live' | 'reconnecting' | 'paused' | 'unavailable';

export interface Controls {
  /** Outages with an escalated patient; null when triage couldn't be loaded, which disables the toggle. */
  setEscalations(count: number | null): void;
  /** `rate` is the backend's events per second, shown while the stream is live. */
  setLive(state: LiveState, rate?: string): void;
}

const LIVE_WORDS: Record<LiveState, string> = {
  live: 'Live',
  reconnecting: 'Reconnecting…',
  paused: 'Paused',
  unavailable: 'No live stream',
};

function chip(label: string, pressed: boolean, onToggle: (pressed: boolean) => void): HTMLButtonElement {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'chip';
  b.textContent = label;
  b.setAttribute('aria-pressed', String(pressed));
  b.addEventListener('click', () => {
    const next = b.getAttribute('aria-pressed') !== 'true';
    b.setAttribute('aria-pressed', String(next));
    onToggle(next);
  });
  return b;
}

function group(label: string, items: HTMLElement[]): HTMLDivElement {
  const g = document.createElement('div');
  g.className = 'controls__group';
  g.setAttribute('role', 'group');
  g.setAttribute('aria-label', label);
  const name = document.createElement('span');
  name.className = 'controls__label';
  name.textContent = label;
  g.append(name, ...items);
  return g;
}

/** One toggle row that scopes the map, the list and every chart, so their numbers always agree. */
export function renderControls(
  root: HTMLElement,
  filters: Filters,
  layers: Record<LayerGroup, boolean>,
  on: ControlHandlers,
): Controls {
  const operators = OPERATORS.map((op) =>
    chip(op.name, filters.operators.has(op.id), (pressed) => {
      if (pressed) filters.operators.add(op.id);
      else filters.operators.delete(op.id);
      on.filters();
    }),
  );

  const escalations = chip('Escalations only', filters.escalationsOnly, (pressed) => {
    filters.escalationsOnly = pressed;
    on.filters();
  });
  escalations.classList.add('chip--severity');
  const escalationCount = document.createElement('span');
  escalationCount.className = 'chip__count num';
  escalations.append(escalationCount);

  const mapLayers = LAYERS.map((l) =>
    chip(l.name, layers[l.id], (pressed) => {
      layers[l.id] = pressed;
      on.layer(l.id, pressed);
    }),
  );

  const live = chip(LIVE_WORDS.live, true, on.live);
  live.classList.add('chip--live');
  const liveRate = document.createElement('span');
  liveRate.className = 'chip__count num';

  root.replaceChildren(
    group('Operators', operators),
    group('Show', [escalations]),
    group('Map', mapLayers),
    group('Updates', [live]),
  );

  return {
    setEscalations(count) {
      escalations.disabled = count === null;
      escalations.title = count === null ? 'Triage is unavailable right now' : '';
      escalationCount.textContent = count === null ? '–' : String(count);
    },
    setLive(state, rate) {
      live.dataset.state = state;
      live.disabled = state === 'unavailable';
      live.title = state === 'unavailable' ? 'Fixture data has no live stream' : '';
      live.setAttribute('aria-pressed', String(state === 'live' || state === 'reconnecting'));
      liveRate.textContent = state === 'live' && rate ? rate : '';
      live.replaceChildren(LIVE_WORDS[state], liveRate);
    },
  };
}
