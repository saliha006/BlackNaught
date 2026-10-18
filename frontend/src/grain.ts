/** A 64×64 RGBA tile of sparse single-pixel grain in one colour, for MapLibre's `fill-pattern`. */
export interface GrainTile {
  width: number;
  height: number;
  data: Uint8Array;
}

const SIZE = 64;
// About one pixel in twelve: dense enough to read as texture inside the fog, sparse enough that the streets show through
const DENSITY = 0.08;

/** Mulberry32: a tiny seeded PRNG, so the grain (and its tests) are the same on every load. */
function prng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function grainTile(hex: string, seed: number): GrainTile {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const random = prng(seed);
  const data = new Uint8Array(SIZE * SIZE * 4);
  for (let i = 0; i < SIZE * SIZE; i++) {
    if (random() >= DENSITY) continue;
    data.set([r, g, b, Math.round(140 + random() * 115)], i * 4);
  }
  return { width: SIZE, height: SIZE, data };
}
