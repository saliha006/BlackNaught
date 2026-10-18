// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest';
import { setupTabs } from './tabs';

function mount() {
  document.body.innerHTML = `
    <div role="tablist">
      <button role="tab" aria-controls="a" aria-selected="true">A</button>
      <button role="tab" aria-controls="b" aria-selected="false">B</button>
    </div>
    <div id="a"></div><div id="b" hidden></div>`;
  return document.querySelector<HTMLElement>('[role="tablist"]')!;
}

describe('setupTabs', () => {
  it('switches panels on click and keeps one tab in the Tab order', () => {
    const changed = vi.fn();
    setupTabs(mount(), changed);
    const [a, b] = document.querySelectorAll<HTMLButtonElement>('[role="tab"]');
    b.click();
    expect(changed).toHaveBeenCalledWith('b');
    expect(document.getElementById('a')!.hidden).toBe(true);
    expect(b.getAttribute('aria-selected')).toBe('true');
    expect([a.tabIndex, b.tabIndex]).toEqual([-1, 0]);
  });

  it('moves with the arrow keys, wraps, and ignores other keys', () => {
    const changed = vi.fn();
    const list = mount();
    const tabs = setupTabs(list, changed);
    document.querySelector<HTMLButtonElement>('[role="tab"]')!.focus();
    list.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
    expect(changed).toHaveBeenLastCalledWith('b');
    list.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    expect(changed).toHaveBeenCalledTimes(1);
    list.dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true }));
    expect(changed).toHaveBeenLastCalledWith('a');
    list.dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true }));
    expect(changed).toHaveBeenLastCalledWith('b');
    tabs.select('a');
    expect(document.getElementById('a')!.hidden).toBe(false);
  });
});
