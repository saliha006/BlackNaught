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
  b.addEventListener('click', onClick);
  return b;
}

export function badge(label: Label) {
  const b = el('span', 'badge', label);
  b.dataset.label = label;
  return b;
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
