import '@fontsource/ibm-plex-sans/300.css';
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-mono/400.css';
import './styles.css';
import './landing.css';
import { ApiError, getAreaRisk, getCells, getOutages, getStress, getTriage, isLive } from './api';
import { renderControls } from './controls';
import { isLocated } from './geo';
import { setupLanding } from './landing';
import { createMap, type LayerGroup, type OutageMap, type Padding } from './map';
import { markSelected, renderOutageList, sortOutages } from './outageList';
import { renderPredict } from './predict';
import { allOperators, escalatedOutages, type Filters, filterOutages } from './state';
import type { Cell, Outage } from './types';

// The opening dive is slower than a click-to-fly so the city has time to build up around the beam.
const DIVE_MS = 5200;
// The contract caps triage pages at 200; escalations need every ranked patient, not the top few.
const TRIAGE_LIMIT = 200;

const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;

const list = $<HTMLUListElement>('#outage-list');
const count = $('#outage-count');
const status = $('#data-mode');

status.textContent = isLive ? 'Live API' : 'Fixture data';
status.dataset.mode = isLive ? 'live' : 'fixture';

let map: OutageMap | null = null;
let active: Outage[] = [];
let cells: Cell[] = [];
let visible: Outage[] = [];
let escalated = new Set<number>();
let onMap = false;

const filters: Filters = { operators: allOperators(), escalationsOnly: false };
const layers: Record<LayerGroup, boolean> = { beams: true, sweep: true, cells: true };

const controls = renderControls($('#controls'), filters, layers, {
  filters: render,
  layer: (group, on) => map?.setLayerVisible(group, on),
});

/** The space the toggle row, Predict strip and outage panel cover, so the camera centres on the open part of the map. */
function chromePadding(): Padding {
  const top = $('#predict').getBoundingClientRect().bottom + 16;
  const panel = $('.panel').getBoundingClientRect();
  return innerWidth > 720
    ? { top, bottom: 40, left: 40, right: innerWidth - panel.left + 16 }
    : { top, bottom: innerHeight - panel.top + 16, left: 20, right: 20 };
}

function render() {
  visible = filterOutages(active, filters, escalated);
  map?.setData(visible, cells);
  count.textContent = String(visible.length);
  const filtered = visible.length < active.length;
  renderOutageList(list, visible, (o) => pick(o.id), filtered ? 'No power cuts match these filters.' : undefined);
}

function pick(id: number, duration?: number) {
  const o = visible.find((x) => x.id === id);
  if (!map || !o || !isLocated(o)) return;
  map.focus(o, duration);
  markSelected(list, id);
}

/** Zoom straight into the outage at the top of the list, the same one a person would check first. */
function dive() {
  if (!map) return;
  map.setLive(true);
  const top = sortOutages(visible.filter(isLocated))[0];
  if (top) pick(top.id, DIVE_MS);
  else map.overview();
}

const landing = setupLanding($('#landing'), [$('.topbar'), $('#controls'), $('#predict'), $('.stage')], () => {
  onMap = true;
  // One history entry per visit to the map, so the browser's own Back button also returns to the landing page.
  if (history.state?.view !== 'map') history.pushState({ view: 'map' }, '');
  dive();
});

function showLanding() {
  onMap = false;
  map?.setLive(false);
  landing.open();
  map?.reset();
  markSelected(list, -1);
}

const goHome = () => (history.state?.view === 'map' ? history.back() : showLanding());
$('#back-to-landing').addEventListener('click', goHome);
$('#topbar-logo').addEventListener('click', (e) => {
  e.preventDefault();
  goHome();
});

addEventListener('popstate', () => {
  if (history.state?.view === 'map') landing.close();
  else if (onMap) showLanding();
});

// A reload keeps the last history entry's state, but the page always starts on the landing page.
if (history.state?.view === 'map') history.replaceState(null, '');

async function start() {
  const [m, outages, cellData, triage] = await Promise.all([
    createMap($('#map'), chromePadding),
    getOutages(),
    getCells(),
    // Triage only powers the escalations toggle; the map must still load without it.
    getTriage(TRIAGE_LIMIT).catch(() => null),
  ]);
  map = m;
  active = outages.filter((o) => o.status === 'active');
  cells = cellData;
  escalated = escalatedOutages(triage);
  controls.setEscalations(triage ? escalated.size : null);

  render();
  map.onSelect((id) => pick(id));
  // The map can finish loading after the visitor has already left the landing page.
  if (onMap) dive();
}

// Each layer fails on its own: a missing forecast shows "No data" without holding up the map.
Promise.all([getAreaRisk().catch(() => null), getStress().catch(() => null)]).then(([risk, stress]) =>
  renderPredict($('#predict-tiles'), risk, stress),
);

start().catch((err: Error) => {
  list.replaceChildren();
  const msg = document.createElement('li');
  msg.className = 'panel__error';
  msg.textContent =
    err instanceof ApiError
      ? `Couldn't reach the API (${err.message}). Is the SSH tunnel to the VM open?`
      : `Couldn't show power cuts: ${err.message}`;
  list.append(msg);
});
