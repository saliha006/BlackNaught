import type { Label } from './types';

export function el<K extends keyof HTMLElementTagNameMap>(tag: K, className = '', text?: string) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function button(text: string, className: string, onClick: () => void) {
  const b = el('button', className, text);
  b.type = 'button';
  b.dataset.action = text;
  b.addEventListener('click', onClick);
  return b;
}

export function badge(label: Label) {
  const b = el('span', 'badge', label);
  b.dataset.label = label;
  return b;
}

const shown = new WeakMap<HTMLElement, string>();

/**
 * Replaces a live list's rows only when its data changed. The stream can refresh several times a minute, so a
 * blind replace would collapse an open "why" and pull focus off a button mid-click. Rows carry `data-key`,
 * buttons `data-action`, and both are restored after a real change.
 */
export function rerender(list: HTMLElement, key: string, rows: () => HTMLElement[]) {
  if (shown.get(list) === key) return;
  shown.set(list, key);
  const open = new Set([...list.querySelectorAll<HTMLElement>('[data-key]:has(details[open])')].map((r) => r.dataset.key));
  const active = document.activeElement as HTMLElement | null;
  const focusRow = active && list.contains(active) ? active.closest<HTMLElement>('[data-key]')?.dataset.key : undefined;
  const focusAction = active?.dataset.action;

  list.replaceChildren(...rows());
  for (const row of list.querySelectorAll<HTMLElement>('[data-key]')) {
    if (open.has(row.dataset.key)) row.querySelector('details')?.setAttribute('open', '');
    if (row.dataset.key === focusRow) {
      (row.querySelector<HTMLElement>(`[data-action="${focusAction}"]`) ?? row.querySelector<HTMLElement>('button, summary'))?.focus();
    }
  }
}

/** Terms and values as a definition list, the same shape the two-houses card uses. */
export function facts(className: string, rows: [string, string][]) {
  const dl = el('dl', className);
  for (const [term, value] of rows) {
    const row = el('div');
    row.append(el('dt', '', term), el('dd', 'num', value));
    dl.append(row);
  }
  return dl;
}
