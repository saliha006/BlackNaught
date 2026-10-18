const NS = 'http://www.w3.org/2000/svg';

export function svg<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attrs: Record<string, string | number> = {},
  parent?: Element,
): SVGElementTagNameMap[K] {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  parent?.append(node);
  return node;
}

export const linear =
  ([d0, d1]: [number, number], [r0, r1]: [number, number]) =>
  (v: number) =>
    r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);

export const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** A plot root sized to its container; happy-dom and hidden cards report 0 width, so fall back to the rail's width. */
export function plotRoot(container: HTMLElement, height: number, label: string) {
  const width = container.clientWidth || 360;
  const root = svg('svg', { viewBox: `0 0 ${width} ${height}`, width, height, role: 'img', 'aria-label': label });
  container.replaceChildren(root);
  return { root, width };
}
