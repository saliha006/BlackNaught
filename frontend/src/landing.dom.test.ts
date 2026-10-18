// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from 'vitest';
import html from '../index.html?raw';

// happy-dom has no 2D canvas; the bolt's drawing is checked in the browser instead.
const stopBolt = vi.fn();
vi.mock('./asciiBolt', () => ({ mountAsciiBolt: vi.fn(() => stopBolt) }));

const { setupLanding } = await import('./landing');

function mount(reducedMotion: boolean) {
  document.body.innerHTML = html.slice(html.indexOf('<body>') + 6, html.indexOf('<script'));
  window.matchMedia = vi.fn().mockReturnValue({ matches: reducedMotion }) as unknown as typeof window.matchMedia;
  const root = document.querySelector<HTMLElement>('#landing')!;
  const app = [document.querySelector<HTMLElement>('.stage')!];
  const onEnter = vi.fn();
  const landing = setupLanding(root, app, onEnter);
  return { root, app, onEnter, landing };
}

beforeEach(() => stopBolt.mockClear());

describe('setupLanding', () => {
  it('opens over an inert app and draws the ENWL curves', () => {
    const { root, app } = mount(true);
    expect(root.hidden).toBe(false);
    expect(app[0].inert).toBe(true);
    expect(root.querySelector('svg[data-curve="24"] .curve-line')!.getAttribute('d')).toMatch(/^M0\.0,0\.0 /);
    expect(root.querySelector('[data-still-off="4"]')!.textContent).toBe('45%');
  });

  it('fills triage and feed health from the API', async () => {
    const { root } = mount(true);
    await vi.waitFor(() => expect(root.querySelectorAll('#l-triage .l-triage__row')).toHaveLength(2));
    expect(root.querySelector('#l-sources')!.textContent).toContain('Northern Powergrid');
  });

  it('pages through the FAQ two questions at a time', () => {
    const { root } = mount(true);
    const prev = root.querySelector<HTMLButtonElement>('#l-faq-prev')!;
    const next = root.querySelector<HTMLButtonElement>('#l-faq-next')!;
    const titles = () => [...root.querySelectorAll('.l-faq__item h3')].map((h) => h.textContent);

    expect(titles()).toEqual(['What is Blacknaught?', 'Is any of this real?']);
    expect(prev.disabled).toBe(true);
    next.click();
    expect(titles()[0]).toBe('Can the map reveal where patients live?');
    expect(next.disabled).toBe(true);
    next.click();
    expect(titles()[0]).toBe('Can the map reveal where patients live?');
    prev.click();
    prev.click();
    expect(titles()[0]).toBe('What is Blacknaught?');
  });

  it('enters immediately under reduced motion and can reopen', () => {
    const { root, app, onEnter, landing } = mount(true);
    root.querySelector<HTMLButtonElement>('.l-hero [data-enter]')!.click();
    expect(onEnter).toHaveBeenCalledOnce();
    expect(stopBolt).toHaveBeenCalled();
    expect(root.hidden).toBe(true);
    expect(app[0].inert).toBe(false);

    landing.open();
    expect(root.hidden).toBe(false);
    expect(app[0].inert).toBe(true);
  });

  it('ignores open() while already open, so the bolt is never mounted twice', async () => {
    const { mountAsciiBolt } = await import('./asciiBolt');
    const { landing } = mount(true);
    const mounts = vi.mocked(mountAsciiBolt).mock.calls.length;
    landing.open();
    expect(vi.mocked(mountAsciiBolt).mock.calls.length).toBe(mounts);
  });

  it('can be closed from code, as the browser Forward button does', () => {
    const { root, onEnter, landing } = mount(true);
    landing.close();
    landing.close();
    expect(root.hidden).toBe(true);
    expect(onEnter).toHaveBeenCalledOnce();
  });

  it('cancels a fade-out when reopened mid-way (browser Back during the fade)', () => {
    const { root, onEnter, landing } = mount(false);
    landing.close();
    landing.open();
    expect(root.classList.contains('is-leaving')).toBe(false);
    expect(root.hidden).toBe(false);

    root.dispatchEvent(Object.assign(new Event('transitionend'), { propertyName: 'opacity' }));
    expect(onEnter).not.toHaveBeenCalled();
    expect(root.hidden).toBe(false);
  });

  it('waits for the overlay’s own opacity fade, not a child transition', () => {
    const { root, onEnter } = mount(false);
    root.querySelector<HTMLButtonElement>('.l-nav [data-enter]')!.click();
    expect(root.classList.contains('is-leaving')).toBe(true);

    const child = root.querySelector('.l-btn')!;
    child.dispatchEvent(Object.assign(new Event('transitionend', { bubbles: true }), { propertyName: 'opacity' }));
    root.dispatchEvent(Object.assign(new Event('transitionend'), { propertyName: 'transform' }));
    expect(onEnter).not.toHaveBeenCalled();

    root.dispatchEvent(Object.assign(new Event('transitionend'), { propertyName: 'opacity' }));
    expect(onEnter).toHaveBeenCalledOnce();
    expect(root.classList.contains('is-leaving')).toBe(false);
  });
});
