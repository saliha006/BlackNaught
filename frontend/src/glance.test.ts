// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest';
import outages from '../../fixtures/api/outages.json';
import { GLANCE_BOUNDS, nearestText, projectGB, renderGlance } from './glance';
import type { Outage } from './types';

const all = outages as Outage[];

function mount() {
  document.body.innerHTML = `<section id="g">
    <b id="glance-count"></b><b id="glance-severe"></b><b id="glance-moderate"></b>
    <span id="glance-glows"></span><span id="glance-updated"></span></section>`;
  return document.querySelector<HTMLElement>('#g')!;
}

describe('projectGB', () => {
  it('maps the picture corners to 0% and 100%', () => {
    const [w, s, e, n] = GLANCE_BOUNDS;
    expect(projectGB([n, w])).toEqual([0, 0]);
    const [x, y] = projectGB([s, e]);
    expect([x, y].map(Math.round)).toEqual([100, 100]);
  });

  it('puts London east of and below Manchester', () => {
    const [lx, ly] = projectGB([51.507, -0.128]);
    const [mx, my] = projectGB([53.48, -2.242]);
    expect(lx).toBeGreaterThan(mx);
    expect(ly).toBeGreaterThan(my);
  });
});

describe('renderGlance', () => {
  it('counts cuts by severity and places one glow per located cut', () => {
    const root = mount();
    const located = all.filter((o) => o.centroid);
    renderGlance(root, { outages: all, escalated: new Set([located[0].id]) });
    expect(root.querySelector('#glance-count')!.textContent).toBe(String(all.length));
    expect(root.querySelector('#glance-severe')!.textContent).toBe(String(all.filter((o) => o.id === located[0].id || o.scale === 'region' || o.scale === 'system').length));
    const glows = root.querySelectorAll<HTMLElement>('.glance__glow');
    expect(glows).toHaveLength(located.length);
    expect(glows[0].dataset.severity).toBe('severe');
    expect(root.dataset.state).toBe('ready');
  });

  it('never shows a false all-clear when the data fails', () => {
    const root = mount();
    renderGlance(root, null);
    expect(root.querySelector('#glance-count')!.textContent).toBe('–');
    expect(root.querySelector('#glance-updated')!.textContent).toContain("Can't load");
    expect(root.dataset.state).toBe('error');
  });
});

describe('nearestText', () => {
  it('names the distance and severity of the closest cut, or says there are none', () => {
    const located = all.filter((o) => o.centroid);
    expect(nearestText({ outages: located, escalated: new Set() }, located[0].centroid!)).toMatch(/^Nearest power cut: 0\.0 km away · (Severe|Moderate)$/);
    expect(nearestText({ outages: [], escalated: new Set() }, [51.5, -0.1])).toBe('No power cuts on the map right now.');
  });
});
