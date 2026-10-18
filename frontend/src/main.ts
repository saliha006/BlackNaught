import '@fontsource/ibm-plex-sans/300.css';
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-mono/400.css';
import './styles.css';
import './landing.css';
import km from '../../backend/models/km_ukpn.json';
import {
  ApiError,
  AuthError,
  decide,
  logout,
  getAreaRisk,
  getAudit,
  getCapXml,
  getCells,
  getDecisions,
  getGrades,
  getMyHome,
  getOutages,
  getSourcesHealth,
  getStress,
  getTriage,
  isLive,
} from './api';
import { confirmText, renderAudit, renderDecisions } from './agent';
import { renderAccuracy } from './charts/accuracy';
import { chartCard, setBadge, showUnavailable } from './charts/card';
import { renderFeeds } from './charts/feeds';
import { renderOutageLength } from './charts/outageLength';
import { renderRisk } from './charts/risk';
import { renderControls } from './controls';
import { formatElapsed } from './format';
import { isLocated } from './geo';
import { type Destination, setupLanding } from './landing';
import { connectLive, formatRate, type Refetch } from './live';
import type { LayerGroup, OutageMap, Padding } from './map';
import { askLogin, confirm, openModal } from './modal';
import { renderMyHome } from './myHome';
import { renderNearby } from './nearby';
import { markSelected, renderOutageList, sortOutages } from './outageList';
import { renderPredict } from './predict';
import { capPhone, parseCap, smsPhone } from './preview';
import { allOperators, escalatedOutages, type Filters, filterOutages, showsSource } from './state';
import { setupTabs } from './tabs';
import { renderTriage } from './triage';
import { findPair, renderTwoHouses } from './twoHouses';
import type { AgentDecision, AreaRisk, Cell, Grades, GridStress, LatLon, Outage, SourceHealth, Triage, TriageItem } from './types';

// The opening dive is slower than a click-to-fly so the city has time to build up around the beam.
const DIVE_MS = 5200;
// Long enough to notice on a recording, short enough that the list doesn't stay noisy.
const NEW_FLAG_MS = 8000;
// The contract caps triage pages at 200; escalations need every ranked patient, not the top few.
const TRIAGE_LIMIT = 200;

const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;

const list = $<HTMLUListElement>('#outage-list');
const count = $('#outage-count');
const status = $('#data-mode');
const dashboard = $('#dashboard');
$('#dash-grid').append($('#predict'), $('#two-houses'), $('.panel'));
let here: LatLon | null = null;

status.textContent = isLive ? 'Live API' : 'Fixture data';
status.dataset.mode = isLive ? 'live' : 'fixture';

let map: OutageMap | null = null;
let active: Outage[] = [];
let cells: Cell[] = [];
let visible: Outage[] = [];
let escalated = new Set<number>();
let onMap = false;
let outagesLoaded = false;
let panelsLoaded = false;
let grades: Grades | null = null;
let risk: AreaRisk[] | null = null;
let feeds: SourceHealth[] | null = null;
let stress: GridStress | null = null;
let selected: number | null = null;
let triageItems: TriageItem[] = [];
let stopLive: (() => void) | null = null;
let decisions: AgentDecision[] | null = null;
let openTab = 'tab-outages';
const fresh = new Set<number>();
const modalRoot = $('#modal-root');
let auditChecked = false;
let newSinceAnnounce = 0;
let announceTimer = 0;

/** One polite status line for what a screen reader should hear: decisions, audit verdicts, new faults. */
const announce = (text: string) => {
  $('#status').textContent = text;
};

function setSignedIn(name: string | null) {
  $('#signed-in').hidden = name === null;
  $('#signed-in-name').textContent = name ?? '';
}

// The session cookie is HttpOnly and there's no "who am I" endpoint, so the bar only knows sign-ins made on this page
$('#sign-out').addEventListener('click', async () => {
  modalRoot.querySelector('dialog')?.close();
  await logout().catch(() => undefined);
  setSignedIn(null);
  announce('Signed out');
});

const filters: Filters = { operators: allOperators(), escalationsOnly: false };
// Cells start off: the severity fog now shows where cuts are, and the fixed patient-count squares read as noise
const layers: Record<LayerGroup, boolean> = { beams: true, sweep: true, cells: false };

const controls = renderControls($('#controls'), filters, layers, {
  filters: render,
  layer: (group, on) => map?.setLayerVisible(group, on),
  live: setLiveUpdates,
});

const analysis = $('#analysis');
const cards = {
  length: chartCard(
    analysis,
    'Outage length vs history',
    `Live cuts on the survival curve of ${km.n.toLocaleString('en-GB')} UKPN outages`,
    'LIVE',
  ),
  accuracy: chartCard(analysis, 'Prediction accuracy', 'Brier score of predictions graded against real GB restorations', 'LIVE'),
  risk: chartCard(analysis, "Tomorrow's risk", 'Chance of 3 or more faults per ENWL district; not filtered by operator', null),
  feeds: chartCard(analysis, 'Feed health', 'Time since each feed last delivered; the tick marks stale (2× its polling interval)', 'LIVE'),
};
for (const card of Object.values(cards)) card.note.textContent = 'Loading…';

/** Charts follow the same filters as the map and list, so every number on screen agrees. */
function renderCharts() {
  if (outagesLoaded) renderOutageLength(cards.length, km.curve, visible, escalated);
  // Until the panel data arrives, "unavailable" would be a lie; the cards keep saying Loading.
  if (!panelsLoaded) return;
  if (grades) renderAccuracy(cards.accuracy, grades, filters.operators);
  else showUnavailable(cards.accuracy, 'Grading');
  if (risk) {
    setBadge(cards.risk, risk[0]?.label ?? null);
    renderRisk(cards.risk, risk);
  } else showUnavailable(cards.risk, 'The district forecast');
  if (feeds) renderFeeds(cards.feeds, feeds.filter((f) => showsSource(filters, f.source)));
  else showUnavailable(cards.feeds, 'Feed health');
}

/** The space the toggle row, Predict strip and outage panel cover, so the camera centres on the open part of the map. */
function chromePadding(): Padding {
  const nearby = $('#nearby').getBoundingClientRect();
  // The nearby list is the only thing over the map: a right column on wide screens, a bottom strip on a phone
  return innerWidth > 720
    ? { top: 120, bottom: 40, left: 40, right: innerWidth - nearby.left + 16 }
    : { top: 120, bottom: innerHeight - nearby.top + 16, left: 20, right: 20 };
}

function render() {
  visible = filterOutages(active, filters, escalated);
  map?.setData(visible, cells, escalated);
  count.textContent = String(visible.length);
  const filtered = visible.length < active.length;
  renderOutageList(list, visible, (o) => pick(o.id), filtered ? 'No power cuts match these filters.' : undefined);
  if (selected !== null) markSelected(list, selected, false);
  for (const id of fresh) list.querySelector(`button.outage[data-id="${id}"]`)?.classList.add('is-new');
  renderCharts();
  // The demo pair ignores the filters: it's the centrepiece, and hiding it behind a chip would lose it mid-recording.
  const pair = findPair(triageItems);
  renderTwoHouses($('#two-houses'), pair, active.find((o) => o.id === pair?.outageId), (id) => pick(id, undefined, active));
  renderNearby($('#nearby-list'), visible, escalated, here, (id) => pick(id, undefined, active));
  renderTriageTab();
}

const awaiting = () => new Set((decisions ?? []).filter((d) => d.state === 'awaiting_approval').map((d) => d.id));

function renderTriageTab() {
  const toEscalate = triageItems.filter((i) => i.escalate).length;
  $('#triage-count').textContent = toEscalate ? String(toEscalate) : '';
  if (openTab !== 'tab-triage') return;
  renderTriage($<HTMLUListElement>('#triage-list'), triageItems, awaiting(), {
    show: (id) => pick(id, undefined, active),
    sms: (item) => openModal(modalRoot, 'SMS preview').body.append(smsPhone(item)),
    decide: decideAndRefresh,
  });
}

function renderAgentTab() {
  if (openTab !== 'tab-agent') return;
  renderDecisions($<HTMLUListElement>('#decision-list'), decisions, { decide: decideAndRefresh, previewCap });
}

async function loadDecisions() {
  decisions = await getDecisions().catch(() => null);
  renderTriageTab();
  renderAgentTab();
}

async function verifyAudit() {
  const result = await getAudit().catch(() => 'failed' as const);
  renderAudit($('#audit'), result, verifyAudit);
  if (result === 'failed') announce("Couldn't verify the audit chain");
  else announce(result.ok ? 'Audit chain intact' : `Audit chain tampered at row ${result.first_bad_seq}`);
}

/** A 401/403 means the wrong person (or nobody) is signed in: ask for the role's login once, then retry. */
async function withLogin<T>(role: 'operator' | 'household', run: () => Promise<T>): Promise<T | null> {
  try {
    return await run();
  } catch (err) {
    if (!(err instanceof AuthError)) throw err;
    const who = await askLogin(modalRoot, role);
    if (who === null) return null;
    setSignedIn(who);
    return run();
  }
}

/** Approvals and rejections both go through a named confirm step: these send (or stop) a 999 packet or a public alert. */
async function confirmDecision(id: string, approve: boolean): Promise<boolean> {
  const row = triageItems.find((i) => i.decision_id === id);
  const decision = decisions?.find((d) => d.id === id) ?? {
    id,
    tool: row ? 'escalate' : 'unknown',
    state: 'awaiting_approval' as const,
    created_at: '',
    args_summary: row ? JSON.stringify({ patient: row.patient_ref }) : '',
    rationale: [],
  };
  return confirm(modalRoot, confirmText(decision, approve, row ? formatElapsed(row.reserve_left_h) : undefined));
}

async function decideAndRefresh(id: string, approve: boolean) {
  if (!(await confirmDecision(id, approve))) return;
  try {
    const result = await withLogin('operator', () => decide(id, approve));
    if (!result) return;
    announce(`${approve ? 'Approved' : 'Rejected'}${result.audit_seq ? `, audit row ${result.audit_seq}` : ''}`);
    // reload('triage') refreshes the decisions too, so the decided row loses its buttons
    await reload('triage');
  } catch (err) {
    // 409 means another operator decided first: a normal outcome with two people on shift, not a fault
    const message = (err as Error).message;
    const text = message.endsWith('409') ? 'Already decided by another operator.' : `The decision wasn't recorded: ${message}`;
    openModal(modalRoot, 'Not sent').body.append(text);
  }
}

async function previewCap(id: string) {
  const modal = openModal(modalRoot, 'Public alert preview');
  try {
    modal.body.append(capPhone(parseCap(await getCapXml(id))));
  } catch (err) {
    modal.body.append(`The alert isn't available: ${(err as Error).message}`);
  }
}

async function openMyHome() {
  try {
    const home = await withLogin('household', getMyHome);
    if (!home) return;
    const modal = openModal(modalRoot, 'My home');
    renderMyHome(modal.body, home);
  } catch (err) {
    openModal(modalRoot, 'My home').body.append(`Couldn't load your home: ${(err as Error).message}`);
  }
}

$('#open-my-home').addEventListener('click', openMyHome);

setupTabs($('.tabs'), (panel) => {
  openTab = panel;
  if (panel === 'tab-triage') renderTriageTab();
  if (panel === 'tab-agent') {
    renderAgentTab();
    // Verify walks the whole chain on the server, so arrowing past the tab mustn't re-run it; the button does
    if (!auditChecked) {
      auditChecked = true;
      void verifyAudit();
    }
  }
});

function pick(id: number, duration?: number, from: Outage[] = visible) {
  const o = from.find((x) => x.id === id);
  if (!map || !o || !isLocated(o)) return;
  selected = id;
  map.focus(o, duration);
  markSelected(list, id);
}

function applyTriage(triage: Triage | null) {
  triageItems = triage?.items ?? [];
  escalated = escalatedOutages(triage);
  controls.setEscalations(triage ? escalated.size : null);
}

/** Refetch what a stream event says changed. The panel keeps its last good frame, dimmed, until new data lands. */
async function reload(what: Refetch) {
  const all = what === 'all';
  analysis.classList.add('is-refreshing');
  try {
    if (all || what === 'outages') active = (await getOutages()).filter((o) => o.status === 'active');
    if (all || what === 'triage') {
      applyTriage(await getTriage(TRIAGE_LIMIT));
      // The agent acts on each triage tick, so its decisions are refreshed alongside.
      void loadDecisions();
    }
    if (all || what === 'grades') grades = await getGrades();
    if (all) {
      [risk, stress, feeds] = await Promise.all([getAreaRisk(), getStress(), getSourcesHealth().then((h) => h.sources)]);
      renderPredict($('#predict-tiles'), risk, stress);
      renderPredict($('#forecast-tiles'), risk, stress);
    }
    render();
  } catch {
    // A failed refresh leaves the last good data up; the toggle says the link is struggling.
    controls.setLive('reconnecting');
  } finally {
    analysis.classList.remove('is-refreshing');
  }
}

function setLiveUpdates(on: boolean) {
  stopLive?.();
  stopLive = null;
  if (!on) {
    controls.setLive('paused');
    return;
  }
  controls.setLive('reconnecting');
  stopLive = connectLive({
    refetch: reload,
    feed(row) {
      feeds = feeds ? feeds.map((f) => (f.source === row.source ? row : f)) : [row];
      renderCharts();
    },
    stats: (rate) => controls.setLive('live', formatRate(rate)),
    ping(id) {
      fresh.add(id);
      // Batched, so a burst of new faults is one sentence rather than a run of interruptions
      newSinceAnnounce += 1;
      clearTimeout(announceTimer);
      announceTimer = window.setTimeout(() => {
        announce(`${newSinceAnnounce} new power cut${newSinceAnnounce === 1 ? '' : 's'}`);
        newSinceAnnounce = 0;
      }, 5000);
      setTimeout(() => {
        fresh.delete(id);
        list.querySelector(`button.outage[data-id="${id}"]`)?.classList.remove('is-new');
      }, NEW_FLAG_MS);
    },
    status: (state) => controls.setLive(state),
  });
}

/** Zoom straight into the outage at the top of the list, the same one a person would check first. */
function dive() {
  if (!map) return;
  map.setLive(true);
  const top = sortOutages(visible.filter(isLocated))[0];
  if (top) pick(top.id, DIVE_MS);
  else map.overview();
}

/** The operator dashboard sits over the map, so going back to the map is instant and keeps the camera where it was. */
function showDashboard(on: boolean) {
  dashboard.hidden = !on;
  if (on) {
    renderTriageTab();
    renderAgentTab();
    // Its cards measured zero while hidden, so the charts redraw at their real width
    renderCharts();
  }
}

const landing = setupLanding($('#landing'), [$('.topbar'), $('#controls'), $('#forecast'), $('.stage')], (to: Destination) => {
  onMap = true;
  // One history entry per visit, so the browser's own Back button also returns to the landing page.
  if (history.state?.view !== to) history.pushState({ view: to }, '');
  showDashboard(to === 'dashboard');
  dive();
});

$('#open-dashboard').addEventListener('click', () => {
  history.pushState({ view: 'dashboard' }, '');
  showDashboard(true);
});
$('#dash-to-map').addEventListener('click', () => {
  history.pushState({ view: 'map' }, '');
  showDashboard(false);
});
$('#use-location').addEventListener('click', () => {
  // Only on request: the page never asks for a location by itself
  navigator.geolocation?.getCurrentPosition(
    (pos) => {
      here = [pos.coords.latitude, pos.coords.longitude];
      $('#use-location').textContent = 'Nearest first';
      render();
    },
    () => announce("Couldn't get your location; showing the most serious cuts first"),
    { timeout: 8000 },
  );
});

function showLanding() {
  onMap = false;
  map?.setLive(false);
  landing.open();
  map?.reset();
  markSelected(list, -1);
}

const goHome = () => (history.state?.view ? history.back() : showLanding());
$('#back-to-landing').addEventListener('click', goHome);
$('#topbar-logo').addEventListener('click', (e) => {
  e.preventDefault();
  goHome();
});

addEventListener('popstate', () => {
  const view = history.state?.view;
  if (view === 'map' || view === 'dashboard') {
    showDashboard(view === 'dashboard');
    landing.close(view);
  } else if (onMap) {
    showDashboard(false);
    showLanding();
  }
});

// A reload keeps the last history entry's state, but the page always starts on the landing page.
if (history.state?.view) history.replaceState(null, '');

async function start() {
  const [m, outages, cellData, triage] = await Promise.all([
    // MapLibre is most of the JS; loading it as its own chunk lets the landing page paint before it arrives
    import('./map').then(({ createMap }) => createMap($('#map'), chromePadding)),
    getOutages(),
    getCells(),
    // Triage only powers the escalations toggle; the map must still load without it.
    getTriage(TRIAGE_LIMIT).catch(() => null),
  ]);
  map = m;
  for (const [group, on] of Object.entries(layers) as [LayerGroup, boolean][]) if (!on) map.setLayerVisible(group, false);
  active = outages.filter((o) => o.status === 'active');
  cells = cellData;
  outagesLoaded = true;
  applyTriage(triage);
  void loadDecisions();

  render();
  map.onSelect((id) => pick(id));
  // The map can finish loading after the visitor has already left the landing page.
  if (onMap) dive();
  if (isLive) setLiveUpdates(true);
  else controls.setLive('unavailable');
}

// Each panel fails on its own: a missing forecast shows "No data" without holding up the map.
Promise.all([
  getAreaRisk().catch(() => null),
  getStress().catch(() => null),
  getGrades().catch(() => null),
  getSourcesHealth().catch(() => null),
]).then(([riskData, stressData, gradeData, health]) => {
  risk = riskData;
  stress = stressData;
  grades = gradeData;
  feeds = health?.sources ?? null;
  panelsLoaded = true;
  renderPredict($('#predict-tiles'), risk, stress);
  renderPredict($('#forecast-tiles'), risk, stress);
  renderCharts();
});

let resizeTimer = 0;
addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = window.setTimeout(renderCharts, 150);
});

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
