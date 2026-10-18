import { badge, button, el, facts, rerender } from './dom';
import type { AgentDecision, AuditVerify } from './types';

const TOOL_NAMES: Record<string, string> = {
  escalate: 'Escalate to 999',
  assign_visit: 'Assign visits',
  notify_carer: 'SMS the carer',
  request_supplier: 'Request a cylinder',
  draft_cap_alert: 'Public alert (CAP)',
  write_sitrep: 'Situation report',
  mark_source_stale: 'Mark feed stale',
  recalibrate: 'Recalibrate',
};

const STATE_TEXT: Record<string, string> = {
  auto_done: 'Done',
  awaiting_approval: 'Waiting for approval',
  approved: 'Approved',
  rejected: 'Rejected',
  exported: 'Exported',
  expired: 'Expired',
};

export interface DecisionActions {
  decide(id: string, approve: boolean): void;
  previewCap(id: string): void;
}

function decisionRow(d: AgentDecision, on: DecisionActions) {
  const li = el('li', 'decision');
  li.dataset.key = d.id;
  li.dataset.state = d.state;
  const head = el('header', 'decision__head');
  head.append(
    el('b', '', TOOL_NAMES[d.tool] ?? d.tool),
    el('span', 'decision__state', STATE_TEXT[d.state] ?? d.state),
    el('time', 'decision__time num', new Date(d.created_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })),
  );
  const why = el('ul', 'decision__why');
  for (const line of d.rationale) why.append(el('li', '', line));
  li.append(head, el('p', 'decision__args', d.args_summary), why);

  const actions = el('div', 'triage__actions');
  if (d.state === 'awaiting_approval') {
    actions.append(
      button('Approve', 'chip chip--approve', () => on.decide(d.id, true)),
      button('Reject', 'chip', () => on.decide(d.id, false)),
    );
  }
  // The backend serves the CAP XML only after a person approves it, so earlier there's nothing to preview.
  if (d.tool === 'draft_cap_alert' && (d.state === 'approved' || d.state === 'exported')) {
    actions.append(button('Preview alert', 'chip', () => on.previewCap(d.id)));
  }
  if (actions.childElementCount) li.append(actions);
  return li;
}

export function renderDecisions(list: HTMLElement, decisions: AgentDecision[] | null, on: DecisionActions) {
  if (decisions === null) {
    list.replaceChildren(el('li', 'panel__loading', 'The decision log is unavailable right now.'));
    return;
  }
  if (decisions.length === 0) {
    list.replaceChildren(el('li', 'panel__loading', 'No agent decisions yet. They appear here as the agent acts.'));
    return;
  }
  rerender(list, JSON.stringify(decisions), () => decisions.map((d) => decisionRow(d, on)));
}

const REASON_TEXT: Record<string, string> = {
  missing_seq: 'a row is missing',
  broken_link: 'a row no longer points at the one before it',
  hash_mismatch: 'a row was changed after it was written',
  checkpoint_head_mismatch: 'the chain no longer matches its signed checkpoint',
};

/** Verify walks the whole hash chain on the server; red names the first row that no longer fits. */
export function renderAudit(root: HTMLElement, result: AuditVerify | 'failed' | null, onVerify: () => void) {
  const head = el('header', 'audit__head');
  head.append(el('h2', '', 'Audit chain'), badge('LIVE'), button('Verify now', 'chip', onVerify));
  if (result === null || result === 'failed') {
    // An old verdict must not stay on screen (or stay red) once a fresh check can't run
    delete root.dataset.ok;
    root.replaceChildren(head, el('p', 'card__note', result === null ? 'Not checked yet.' : "Couldn't verify right now."));
    return;
  }
  root.dataset.ok = String(result.ok);
  const verdict = result.ok
    ? el('p', 'audit__verdict', `Intact: ${result.rows.toLocaleString('en-GB')} rows check out`)
    : el('p', 'audit__verdict', `Tampered at row ${result.first_bad_seq}: ${REASON_TEXT[result.reason ?? ''] ?? result.reason}`);
  const cp = result.last_checkpoint;
  const signature = cp === null ? 'none yet' : cp.sig_ok === null ? 'unsigned' : cp.sig_ok ? 'valid (ML-DSA-65)' : 'INVALID';
  root.replaceChildren(
    head,
    verdict,
    facts('audit__facts', [
      ['Last checkpoint', cp ? `row ${cp.seq}` : '–'],
      ['Signature', signature],
      ['Checked in', `${result.took_ms} ms`],
    ]),
  );
}
