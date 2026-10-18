import { describe, expect, it } from 'vitest';
import { escapeHtml, formatCount, formatElapsed } from './format';

describe('formatElapsed', () => {
  it.each([
    [0, '0 min'],
    [0.5, '30 min'],
    [1, '1 h'],
    [1.13, '1 h 8 min'],
    [0.999, '1 h'],
    [-0.2, '0 min'],
  ])('%s h → %s', (h, out) => {
    expect(formatElapsed(h)).toBe(out);
  });
});

it('formatCount groups thousands and shows a dash for a count the operator does not publish', () => {
  expect(formatCount(12345)).toBe('12,345');
  expect(formatCount(0)).toBe('0');
  expect(formatCount(null)).toBe('–');
});

it('escapeHtml keeps API strings from becoming markup', () => {
  expect(escapeHtml(`<img src=x onerror="alert(1)">'&`)).toBe('&lt;img src=x onerror=&quot;alert(1)&quot;&gt;&#39;&amp;');
  expect(escapeHtml('UK Power Networks')).toBe('UK Power Networks');
});
