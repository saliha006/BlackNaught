import { deviceName } from './devices';
import { badge, button, el, facts, rerender } from './dom';
import { formatElapsed } from './format';
import type { TriageItem } from './types';

export interface TriageActions {
  show(outageId: number): void;
  sms(item: TriageItem): void;
  decide(decisionId: string, approve: boolean): void;
}

function row(item: TriageItem, awaiting: Set<string>, on: TriageActions) {
  const li = el('li', 'triage');
  li.dataset.key = item.patient_ref;
  li.dataset.escalate = String(item.escalate);

  const head = el('header', 'triage__head');
  head.append(
    el('span', 'triage__rank num', `#${item.rank}`),
    el('b', 'triage__device', deviceName(item.device)),
    badge('SIMULATED'),
    el('span', `sev ${item.escalate ? 'sev--escalate' : 'sev--calm'}`, item.escalate ? 'Escalate' : 'SMS check'),
  );

  // Staff see the expected case first, then the pessimistic case the rule actually used.
  const numbers = facts('triage__facts', [
    ['Backup left', formatElapsed(item.reserve_left_h)],
    ['Likely back in', formatElapsed(item.remaining_h.q50)],
    ['Range (q50 to q90)', `${formatElapsed(item.remaining_h.q50)} to ${formatElapsed(item.remaining_h.q90)}`],
    [`Rule used (${item.q_used})`, formatElapsed(item.remaining_h[item.q_used])],
    ['Harm-hours', item.harm.toFixed(1)],
  ]);

  const why = el('details', 'triage__why');
  why.append(el('summary', '', 'Why ranked here'));
  const reasons = el('ul');
  for (const line of item.why) reasons.append(el('li', '', line));
  why.append(reasons);

  const actions = el('div', 'triage__actions');
  actions.append(
    button('Show fault', 'chip', () => on.show(item.outage_id)),
    button('Preview SMS', 'chip', () => on.sms(item)),
  );
  if (item.decision_id && awaiting.has(item.decision_id)) {
    const id = item.decision_id;
    actions.append(
      button('Approve', 'chip chip--approve', () => on.decide(id, true)),
      button('Reject', 'chip', () => on.decide(id, false)),
    );
  }

  li.append(head, el('p', 'triage__ref', `${item.patient_ref} · fault ${item.outage_id}`), numbers, why, actions);
  return li;
}

/** The ranked list. `awaiting` holds decision ids still waiting for a person, the only rows that get approve buttons. */
export function renderTriage(list: HTMLElement, items: TriageItem[], awaiting: Set<string>, on: TriageActions) {
  if (items.length === 0) {
    list.replaceChildren(el('li', 'panel__loading', 'Nobody on the register is in a live power cut right now.'));
    return;
  }
  const sorted = [...items].sort((a, b) => a.rank - b.rank);
  rerender(list, JSON.stringify([sorted, [...awaiting]]), () => sorted.map((item) => row(item, awaiting, on)));
}
