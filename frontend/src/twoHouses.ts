import { deviceName } from './devices';
import { el } from './dom';
import { formatElapsed } from './format';
import type { Outage, TriageItem } from './types';

export interface Pair {
  outageId: number;
  escalated: TriageItem;
  calm: TriageItem;
}

// The demo script's pair: an oxygen concentrator that escalates beside a ventilator that only needs an SMS check.
const prefer = (items: TriageItem[], device: string) => items.find((i) => i.device === device) ?? items[0];

/** The first fault (by triage rank) where one patient escalates and another doesn't: same fault, different answers. */
export function findPair(items: TriageItem[]): Pair | null {
  const byOutage = new Map<number, TriageItem[]>();
  for (const item of [...items].sort((a, b) => a.rank - b.rank)) {
    byOutage.set(item.outage_id, [...(byOutage.get(item.outage_id) ?? []), item]);
  }
  for (const [outageId, group] of byOutage) {
    const escalated = group.filter((i) => i.escalate);
    const calm = group.filter((i) => !i.escalate);
    if (escalated.length && calm.length) {
      return { outageId, escalated: prefer(escalated, 'o2_concentrator'), calm: prefer(calm, 'ventilator') };
    }
  }
  return null;
}


function house(name: string, item: TriageItem): HTMLElement {
  const box = el('article', 'house');
  box.dataset.escalate = String(item.escalate);

  const head = el('header', 'house__head');
  const badge = el('span', 'badge', 'SIMULATED');
  badge.dataset.label = 'SIMULATED';
  head.append(el('b', '', name), badge);

  // Staff view: the expected case first, then the range the decision actually used.
  const facts = el('dl', 'house__facts');
  for (const [term, value] of [
    ['Backup left', formatElapsed(item.reserve_left_h)],
    ['Power likely back in', formatElapsed(item.remaining_h.q50)],
    [`Could take (${item.q_used})`, formatElapsed(item.remaining_h[item.q_used])],
  ]) {
    const row = el('div', '');
    row.append(el('dt', '', term), el('dd', 'num', value));
    facts.append(row);
  }

  const verdict = el('p', `sev ${item.escalate ? 'sev--escalate' : 'sev--calm'}`, item.escalate ? 'Escalate' : 'SMS check');
  const why = el('ul', 'house__why');
  for (const line of item.why) why.append(el('li', '', line));

  box.append(head, el('p', 'house__device', deviceName(item.device)), facts, verdict, why);
  return box;
}

// Kept across live re-renders, so a refresh never snaps the card shut while someone is reading it
let expanded = false;

/** The demo centrepiece: one real fault, two synthetic households, different answers. */
export function renderTwoHouses(root: HTMLElement, pair: Pair | null, outage: Outage | undefined, onShow: (id: number) => void) {
  const title = el('h2', 'two-houses__title', 'Two houses, one fault');
  title.id = 'two-houses-title';
  if (!pair) {
    root.replaceChildren(
      title,
      el('p', 'two-houses__note', "No fault has the demo pair yet: it appears once a patient who escalates and one who doesn't share a fault."),
    );
    return;
  }

  const where = outage ? `${outage.source.toUpperCase()} ${outage.scale} fault · off ${formatElapsed(outage.elapsed_h)}` : `Fault ${pair.outageId}`;
  const show = el('button', 'l-btn l-btn--ghost two-houses__show', 'Show on map');
  show.type = 'button';
  show.addEventListener('click', () => onShow(pair.outageId));

  const head = el('header', 'two-houses__head');
  const titles = el('div', '');
  titles.append(title, el('p', 'two-houses__note', where));
  head.append(titles, show);

  const houses = el('div', 'two-houses__grid');
  houses.id = 'two-houses-grid';
  houses.append(house('House A', pair.escalated), house('House B', pair.calm));
  houses.hidden = !expanded;

  // Folded, the card is one line over the map: the verdicts, and a way to open the detail
  const summary = el('p', 'two-houses__summary', 'House A: Escalate · House B: SMS check');
  const toggle = el('button', 'l-btn l-btn--ghost two-houses__toggle', expanded ? 'Hide details' : 'Show both houses');
  toggle.type = 'button';
  toggle.setAttribute('aria-expanded', String(expanded));
  toggle.setAttribute('aria-controls', houses.id);
  toggle.addEventListener('click', () => {
    expanded = !expanded;
    houses.hidden = !expanded;
    toggle.textContent = expanded ? 'Hide details' : 'Show both houses';
    toggle.setAttribute('aria-expanded', String(expanded));
    root.dataset.expanded = String(expanded);
  });
  root.dataset.expanded = String(expanded);
  const bar = el('div', 'two-houses__bar');
  bar.append(summary, toggle);
  root.replaceChildren(head, bar, houses);
}
