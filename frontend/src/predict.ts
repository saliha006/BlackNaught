import type { AreaRisk, GridStress, Label } from './types';

type Severity = 'risk' | 'escalate' | null;

export interface TileView {
  name: string;
  label: Label | null;
  value: string;
  detail: string;
  lead: string;
  severity: Severity;
}

export function areaTile(risk: AreaRisk[] | null): TileView {
  const base = { name: 'Area · tomorrow', lead: 'Lead time: hours to days', severity: null };
  const top = risk?.length ? risk.reduce((a, b) => (b.p_ge_k > a.p_ge_k ? b : a)) : null;
  // A layer with no data says so; it never falls back to looking calm (BLACKNAUGHT.md NOW, option C).
  if (!top) return { ...base, label: null, value: 'No data', detail: 'District risk is unavailable right now' };
  return {
    ...base,
    label: top.label,
    value: `${Math.round(top.p_ge_k * 100)}%`,
    detail: `${top.district}: chance of 3 or more faults`,
  };
}

// Nate's home-sensor model isn't served yet; until it is, the tile reports the real Accra probe result and nothing more.
export const homesTile = (): TileView => ({
  name: 'Homes · next 30 min',
  label: 'REPLAY',
  value: 'Not served yet',
  detail: 'Accra probe: 1 in 5 top alerts came true (9× chance)',
  lead: 'Lead time: minutes',
  severity: null,
});

const STRESS_SEVERITY: Record<GridStress['state'], Severity> = {
  NORMAL: null,
  UNKNOWN: null,
  STRESSED: 'risk',
  EMERGENCY: 'escalate',
  SPLIT_SUSPECTED: 'escalate',
};

const STRESS_WORDS: Record<GridStress['state'], string> = {
  NORMAL: 'Normal',
  UNKNOWN: 'Unknown',
  STRESSED: 'Stressed',
  EMERGENCY: 'Emergency',
  SPLIT_SUSPECTED: 'Split suspected',
};

export function gridTile(stress: GridStress | null): TileView {
  const base = { name: 'Grid · now', lead: 'Lead time: seconds' };
  if (!stress) return { ...base, label: null, value: 'No data', detail: 'Grid frequency is unavailable right now', severity: null };
  return {
    ...base,
    label: stress.label,
    value: STRESS_WORDS[stress.state],
    detail: stress.hz === null ? 'No frequency reading yet' : `GB frequency ${stress.hz.toFixed(2)} Hz`,
    severity: STRESS_SEVERITY[stress.state],
  };
}

function tile(view: TileView): HTMLElement {
  const el = document.createElement('article');
  el.className = 'tile';
  if (view.severity) el.dataset.severity = view.severity;

  const head = document.createElement('header');
  head.className = 'tile__head';
  const name = document.createElement('span');
  name.textContent = view.name;
  head.append(name);
  if (view.label) {
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.dataset.label = view.label;
    badge.textContent = view.label;
    head.append(badge);
  }

  const lines = (['value', 'detail', 'lead'] as const).map((key) => {
    const p = document.createElement('p');
    p.className = `tile__${key}`;
    p.textContent = view[key];
    return p;
  });
  el.append(head, ...lines);
  return el;
}

/** The three prediction layers from the brief, each with its honest lead time. */
export function renderPredict(root: HTMLElement, risk: AreaRisk[] | null, stress: GridStress | null) {
  root.replaceChildren(tile(areaTile(risk)), tile(homesTile()), tile(gridTile(stress)));
}
