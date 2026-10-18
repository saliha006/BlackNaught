import '@fontsource/ibm-plex-sans/300.css';
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-mono/400.css';
import './styles.css';
import './landing.css';
import { getCells, getOutages, isLive } from './api';
import { setupLanding } from './landing';
import { createMap, type OutageMap } from './map';
import { markSelected, renderOutageList, sortOutages } from './outageList';
import type { Outage } from './types';

// The opening dive is slower than a click-to-fly so the city has time to build up around the beam.
const DIVE_MS = 5200;

const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;

const list = $<HTMLUListElement>('#outage-list');
const count = $('#outage-count');
const status = $('#data-mode');

status.textContent = isLive ? 'Live API' : 'Fixture data';
status.dataset.mode = isLive ? 'live' : 'fixture';

let map: OutageMap | null = null;
let active: Outage[] = [];
let onMap = false;

function pick(id: number, duration?: number) {
  const o = active.find((x) => x.id === id);
  if (!map || !o) return;
  map.focus(o, duration);
  markSelected(list, id);
}

/** Zoom straight into the outage at the top of the list, the same one a person would check first. */
function dive() {
  if (!map) return;
  map.setLive(true);
  const top = sortOutages(active)[0];
  if (top) pick(top.id, DIVE_MS);
  else map.overview();
}

const landing = setupLanding($('#landing'), [$('.topbar'), $('.stage')], () => {
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
  const [m, outages, cells] = await Promise.all([createMap($('#map')), getOutages(), getCells()]);
  map = m;
  active = outages.filter((o) => o.status === 'active');

  map.setData(active, cells);
  count.textContent = String(active.length);
  renderOutageList(list, active, (o) => pick(o.id));
  map.onSelect((id) => pick(id));
  // The map can finish loading after the visitor has already left the landing page.
  if (onMap) dive();
}

start().catch((err: Error) => {
  list.replaceChildren();
  const msg = document.createElement('li');
  msg.className = 'panel__error';
  msg.textContent = isLive
    ? `Couldn't reach the API (${err.message}). Is the SSH tunnel to the VM open?`
    : `Couldn't load fixtures: ${err.message}`;
  list.append(msg);
});
