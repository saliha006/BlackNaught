let tip: HTMLDivElement | null = null;

function element() {
  // Re-create it if the page threw the old node away, or tips would update an element nobody can see.
  if (!tip?.isConnected) {
    tip = document.createElement('div');
    tip.className = 'chart-tip';
    tip.setAttribute('role', 'tooltip');
    tip.hidden = true;
    document.body.append(tip);
  }
  return tip;
}

/** Value leads, label follows; both go in as text because labels come from the API. */
export function showTip(x: number, y: number, value: string, label: string) {
  const el = element();
  const strong = document.createElement('strong');
  strong.textContent = value;
  const span = document.createElement('span');
  span.textContent = label;
  el.replaceChildren(strong, span);
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
  el.hidden = false;
}

export function hideTip() {
  if (tip) tip.hidden = true;
}

/** Same readout on hover and keyboard focus, anchored above the mark. */
export function attachTip(mark: SVGElement, read: () => [value: string, label: string]) {
  const show = () => {
    const r = mark.getBoundingClientRect();
    showTip(r.left + r.width / 2, r.top, ...read());
  };
  mark.addEventListener('pointerenter', show);
  mark.addEventListener('focus', show);
  mark.addEventListener('pointerleave', hideTip);
  mark.addEventListener('blur', hideTip);
}
