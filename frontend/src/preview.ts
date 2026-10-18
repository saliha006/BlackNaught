import { deviceName } from './devices';
import { badge, el } from './dom';
import { formatElapsed } from './format';
import type { TriageItem } from './types';

export interface CapFields {
  status: string;
  sent: string;
  event: string;
  urgency: string;
  severity: string;
  headline: string;
  description: string;
  instruction: string;
  area: string;
}

/** Reads the fields a phone would show; anything missing is empty rather than a crash, since CAP allows it. */
export function parseCap(xml: string): CapFields {
  // The encoding declaration means nothing once the XML is already a JS string, and some parsers (happy-dom) reject it
  const doc = new DOMParser().parseFromString(xml.replace(/^\s*<\?xml[^>]*>\s*/, ''), 'application/xml');
  // CAP elements are unprefixed, so the plain tag name finds them without namespace lookups
  const text = (tag: string) => doc.getElementsByTagName(tag)[0]?.textContent?.trim() ?? '';
  return {
    status: text('status'),
    sent: text('sent'),
    event: text('event'),
    urgency: text('urgency'),
    severity: text('severity'),
    headline: text('headline'),
    description: text('description'),
    instruction: text('instruction'),
    area: text('areaDesc'),
  };
}

/**
 * The carer SMS for a ranked patient. Fixed wording (no free text from the model) and never an ETA: it gives the
 * action and the reserve clock, which is what the person can act on.
 */
export function smsFor(item: TriageItem): string {
  const device = deviceName(item.device).toLowerCase();
  const left = formatElapsed(item.reserve_left_h);
  const ask = item.escalate
    ? "We're arranging a check. If breathing gets worse, call 999 now."
    : 'Reply 1 if you are OK, or 2 if you need help.';
  return `Blacknaught: the power is off at your home. The ${device} backup has about ${left} left. ${ask}`;
}

function phone(kind: string, lines: HTMLElement[]) {
  const frame = el('div', 'phone');
  const screen = el('div', 'phone__screen');
  const bubble = el('div', 'phone__msg');
  bubble.append(el('p', 'phone__kind', kind), ...lines);
  screen.append(bubble);
  frame.append(screen);
  return frame;
}

export function smsPhone(item: TriageItem) {
  // The template is real; the person receiving it is not
  return phone('Text message · template', [badge('SIMULATED'), el('p', 'phone__text', smsFor(item))]);
}

export function capPhone(cap: CapFields) {
  const kind = cap.status === 'Exercise' ? 'Emergency alert · EXERCISE' : 'Emergency alert';
  const lines = [el('p', 'phone__headline', cap.headline || cap.event)];
  if (cap.description) lines.push(el('p', 'phone__text', cap.description));
  if (cap.instruction) lines.push(el('p', 'phone__text', cap.instruction));
  if (cap.area) lines.push(el('p', 'phone__meta', `Area: ${cap.area}`));
  lines.push(el('p', 'phone__meta', `${cap.severity} · ${cap.urgency}`));
  return phone(kind, lines);
}
