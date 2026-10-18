import { describe, expect, it } from 'vitest';
import { castRay, edgeGlyph, pointInPolygon, renderFrame, shadeGlyph } from './asciiBolt';

describe('pointInPolygon', () => {
  const square: [number, number][] = [[0, 0], [1, 0], [1, 1], [0, 1]];
  it('separates inside from outside', () => {
    expect(pointInPolygon(0.5, 0.5, square)).toBe(true);
    expect(pointInPolygon(1.5, 0.5, square)).toBe(false);
  });
});

describe('castRay', () => {
  it('hits the front cap facing the viewer', () => {
    const hit = castRay([0, 0.5, 5], [0, 0, -1]);
    expect(hit?.normal).toEqual([0, 0, 1]);
    expect(hit?.t).toBeCloseTo(5 - 0.16);
  });

  it('misses through the notch of the bolt', () => {
    expect(castRay([0.45, 0.8, 5], [0, 0, -1])).toBeNull();
  });

  it('hits a side face when looking edge-on', () => {
    const hit = castRay([-5, -0.5, 0], [1, 0, 0]);
    expect(hit).not.toBeNull();
    expect(hit!.normal[2]).toBe(0);
    expect(hit!.normal[0]).toBeLessThan(0);
  });
});

describe('glyphs', () => {
  it('matches edge direction', () => {
    expect(edgeGlyph(1, 0)).toBe('|');
    expect(edgeGlyph(0, 1)).toBe('-');
    expect(edgeGlyph(1, 1)).toBe('\\');
    expect(edgeGlyph(-1, 1)).toBe('/');
  });

  it('shades lit faces denser and never returns blank for a hit', () => {
    expect(shadeGlyph(1)).toBe('@');
    expect(shadeGlyph(0)).not.toBe(' ');
  });
});

describe('renderFrame', () => {
  const frame = renderFrame(60, 30, 0, 0, 0.5);
  const text = frame.map((r) => r.map((c) => c.ch).join('')).join('\n');

  it('returns the requested grid size', () => {
    expect(frame).toHaveLength(30);
    expect(frame.every((r) => r.length === 60)).toBe(true);
  });

  it('draws a bolt in the middle with blank corners and outlined edges', () => {
    expect(frame[15].some((c) => c.ch !== ' ')).toBe(true);
    expect(frame[0][0].ch).toBe(' ');
    expect(text).toMatch(/[/\\|-]/);
  });

  it('changes as the bolt rotates', () => {
    const turned = renderFrame(60, 30, 1.2, 0, 0.5)
      .map((r) => r.map((c) => c.ch).join(''))
      .join('\n');
    expect(turned).not.toBe(text);
  });
});
