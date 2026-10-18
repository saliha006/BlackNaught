import km from '../../backend/models/km_enwl.json';
import { getSourcesHealth, getTriage } from './api';
import { mountAsciiBolt } from './asciiBolt';
import { deviceName } from './devices';
import { formatAgo, formatElapsed } from './format';
import type { SourceHealth, TriageItem } from './types';

const SOURCE_NAMES: Record<string, string> = {
  ukpn: 'UK Power Networks',
  ssen: 'SSEN',
  npg: 'Northern Powergrid',
  elexon: 'Elexon frequency',
  ioda: 'IODA',
  enwl: 'Electricity North West',
};

/** SVG path for S(h), the share of outages still off after h hours, over the first `hours` hours. */
export function survivalPath(curve: number[], hours: number, w: number, h: number): string {
  return curve
    .slice(0, hours + 1)
    .map((s, i) => `${i === 0 ? 'M' : 'L'}${((i / hours) * w).toFixed(1)},${((1 - s) * h).toFixed(1)}`)
    .join(' ');
}

export const percentStillOff = (curve: number[], hour: number) => `${Math.round(curve[hour] * 100)}%`;

export function triageRow(item: TriageItem): string {
  const action = item.escalate
    ? '<span class="sev sev--escalate">Escalate</span>'
    : '<span class="sev sev--calm">SMS check</span>';
  return `
    <li class="l-triage__row">
      <span class="l-triage__rank num">${item.rank}</span>
      <span class="l-triage__who">
        <b>${deviceName(item.device)}</b>
        <span><b class="num">${formatElapsed(item.reserve_left_h)}</b> reserve · may stay off <b class="num">${formatElapsed(item.remaining_h[item.q_used])}</b> (${item.q_used})</span>
      </span>
      ${action}
    </li>`;
}

export function sourceRow(s: SourceHealth): string {
  const age = s.staleness_s === null ? '–' : formatAgo(s.staleness_s);
  return `
    <tr>
      <th scope="row">${SOURCE_NAMES[s.source] ?? s.source}</th>
      <td><span class="l-chip num">every ${s.interval_s} s</span></td>
      <td class="num">${age}</td>
      <td><span class="l-status" data-status="${s.status}">${s.status}</span></td>
    </tr>`;
}

const FAQ = [
  {
    q: 'What is Blacknaught?',
    a: 'A decision service for health workers. It reads live power-cut feeds, predicts how much longer each cut will last, and ranks people on oxygen or ventilators by who will run out of backup first.',
  },
  {
    q: 'Is any of this real?',
    a: 'The faults, their timings and customer counts are live from GB network operators, and every prediction is graded against the real restoration. The patients are synthetic and labelled SIMULATED everywhere.',
  },
  {
    q: 'Can the map reveal where patients live?',
    a: 'No. Homes are never drawn. The map only shows fixed cells with at least 11 people in them, and smaller cells are suppressed.',
  },
  {
    q: 'Why does it run on LinuxONE?',
    a: 'The register stays encrypted on the box. Models are trained and signed there, every event is scored as it arrives, and the audit log is tamper-evident.',
  },
];

function setupFaq(root: HTMLElement) {
  const list = root.querySelector<HTMLElement>('#l-faq-list')!;
  const prev = root.querySelector<HTMLButtonElement>('#l-faq-prev')!;
  const next = root.querySelector<HTMLButtonElement>('#l-faq-next')!;
  const perPage = 2;
  let page = 0;
  const pages = Math.ceil(FAQ.length / perPage);
  const render = () => {
    list.innerHTML = FAQ.slice(page * perPage, page * perPage + perPage)
      .map(({ q, a }) => `<div class="l-faq__item"><h3>${q}</h3><p>${a}</p></div>`)
      .join('');
    prev.disabled = page === 0;
    next.disabled = page === pages - 1;
  };
  prev.onclick = () => {
    page = Math.max(0, page - 1);
    render();
  };
  next.onclick = () => {
    page = Math.min(pages - 1, page + 1);
    render();
  };
  render();
}

function fillCurves(root: HTMLElement) {
  for (const svg of root.querySelectorAll<SVGSVGElement>('svg[data-curve]')) {
    const hours = Number(svg.dataset.curve);
    const [, , w, h] = svg.getAttribute('viewBox')!.split(' ').map(Number);
    const line = survivalPath(km.curve, hours, w, h);
    svg.querySelector('.curve-line')!.setAttribute('d', line);
    svg.querySelector('.curve-area')!.setAttribute('d', `${line} L${w},${h} L0,${h} Z`);
  }
  for (const el of root.querySelectorAll<HTMLElement>('[data-still-off]')) {
    el.textContent = percentStillOff(km.curve, Number(el.dataset.stillOff));
  }
}

async function fillLiveBits(root: HTMLElement) {
  const triageList = root.querySelector<HTMLElement>('#l-triage')!;
  const sourceBody = root.querySelector<HTMLElement>('#l-sources')!;
  const [triage, health] = await Promise.allSettled([getTriage(), getSourcesHealth()]);
  triageList.innerHTML =
    triage.status === 'fulfilled'
      ? triage.value.items.slice(0, 3).map(triageRow).join('')
      : '<li class="l-muted">Triage is unavailable right now.</li>';
  sourceBody.innerHTML =
    health.status === 'fulfilled'
      ? health.value.sources.map(sourceRow).join('')
      : '<tr><td colspan="4" class="l-muted">Feed health is unavailable right now.</td></tr>';
}

/** Wires the landing overlay. `onEnter` runs once the overlay has faded out over the map. */
export function setupLanding(root: HTMLElement, app: HTMLElement[], onEnter: () => void) {
  let stopBolt = mountAsciiBolt(root.querySelector('#l-bolt')!);
  fillCurves(root);
  setupFaq(root);
  fillLiveBits(root);

  const setOpen = (open: boolean) => {
    root.hidden = !open;
    for (const el of app) el.inert = open;
  };

  // Set while the fade-out runs, so a quick browser Back can cancel it.
  let leaving: ((e: TransitionEvent) => void) | null = null;

  const close = () => {
    if (root.hidden || leaving) return;
    root.classList.add('is-leaving');
    stopBolt();
    const done = () => {
      leaving = null;
      root.classList.remove('is-leaving');
      setOpen(false);
      onEnter();
    };
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return done();
    // transitionend bubbles from children (button hovers), so wait for the overlay's own fade.
    leaving = (e) => {
      if (e.target !== root || e.propertyName !== 'opacity') return;
      root.removeEventListener('transitionend', leaving!);
      done();
    };
    root.addEventListener('transitionend', leaving);
  };

  const open = () => {
    if (leaving) {
      root.removeEventListener('transitionend', leaving);
      leaving = null;
      root.classList.remove('is-leaving');
    } else if (!root.hidden) {
      return;
    }
    setOpen(true);
    root.scrollTop = 0;
    stopBolt = mountAsciiBolt(root.querySelector('#l-bolt')!);
  };

  for (const btn of root.querySelectorAll<HTMLElement>('[data-enter]')) btn.addEventListener('click', close);

  setOpen(true);
  return { open, close };
}
