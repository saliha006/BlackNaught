// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest';
import decisions from '../../fixtures/api/agent_decisions.json';
import audit from '../../fixtures/api/audit_verify.json';
import { renderAudit, renderDecisions } from './agent';
import type { AgentDecision, AuditVerify } from './types';

const sample = decisions as AgentDecision[];
const handlers = () => ({ decide: vi.fn(), previewCap: vi.fn() });

describe('renderDecisions', () => {
  it('names each tool, and only waiting decisions get approve buttons', () => {
    const list = document.createElement('ul');
    const on = handlers();
    renderDecisions(list, sample, on);
    const [waiting, done] = list.querySelectorAll('li.decision');
    expect(waiting.querySelector('b')!.textContent).toBe('Escalate to 999');
    expect(done.querySelector('button')).toBeNull();
    (waiting.querySelector('.chip--approve') as HTMLButtonElement).click();
    expect(on.decide).toHaveBeenCalledWith(sample[0].id, true);
  });

  it('previews a CAP alert only once a person has approved it', () => {
    const list = document.createElement('ul');
    const on = handlers();
    const cap: AgentDecision = { ...sample[0], id: 'c', tool: 'draft_cap_alert', state: 'approved' };
    renderDecisions(list, [cap, { ...cap, id: 'w', state: 'awaiting_approval' }], on);
    const [approved, waiting] = list.querySelectorAll('li.decision');
    expect(waiting.textContent).not.toContain('Preview alert');
    [...approved.querySelectorAll('button')].find((b) => b.textContent === 'Preview alert')!.click();
    expect(on.previewCap).toHaveBeenCalledWith('c');
  });

  it('explains an empty or missing log', () => {
    const list = document.createElement('ul');
    renderDecisions(list, [], handlers());
    expect(list.textContent).toContain('No agent decisions yet');
    renderDecisions(list, null, handlers());
    expect(list.textContent).toContain('unavailable');
  });
});

describe('renderAudit', () => {
  it('shows an intact chain with its signed checkpoint', () => {
    const root = document.createElement('section');
    const verify = vi.fn();
    renderAudit(root, audit as AuditVerify, verify);
    expect(root.dataset.ok).toBe('true');
    expect(root.textContent).toContain('valid (ML-DSA-65)');
    root.querySelector('button')!.click();
    expect(verify).toHaveBeenCalled();
  });

  it('turns red and names the first bad row when tampered', () => {
    const root = document.createElement('section');
    const broken: AuditVerify = { ...(audit as AuditVerify), ok: false, first_bad_seq: 42, reason: 'hash_mismatch' };
    renderAudit(root, broken, vi.fn());
    expect(root.dataset.ok).toBe('false');
    expect(root.textContent).toContain('Tampered at row 42: a row was changed after it was written');
  });

  it('separates unsigned and missing checkpoints from bad ones', () => {
    const root = document.createElement('section');
    const base = audit as AuditVerify;
    renderAudit(root, { ...base, last_checkpoint: { seq: 3, sig_ok: null, head_matches: true } }, vi.fn());
    expect(root.textContent).toContain('unsigned');
    renderAudit(root, { ...base, last_checkpoint: null }, vi.fn());
    expect(root.textContent).toContain('none yet');
    renderAudit(root, null, vi.fn());
    expect(root.textContent).toContain('Not checked yet');
    expect(root.querySelector('h2')!.textContent).toBe('Audit chain');
  });

  it('drops an old verdict when a fresh check fails', () => {
    const root = document.createElement('section');
    renderAudit(root, { ...(audit as AuditVerify), ok: false, first_bad_seq: 1, reason: 'missing_seq' }, vi.fn());
    renderAudit(root, 'failed', vi.fn());
    expect(root.dataset.ok).toBeUndefined();
    expect(root.textContent).toContain("Couldn't verify right now");
  });
});
