// A lightning bolt extruded into 3D and ray-cast into a character grid, after canvasui.dev's ASCII Object.
// Hand-rolled (no three.js): one prism and a few thousand rays per frame is cheap on a 2D canvas.

type V2 = [number, number];
type V3 = [number, number, number];

const BOLT: V2[] = [
  [0.18, 1.0],
  [-0.52, -0.08],
  [-0.04, -0.08],
  [-0.22, -1.0],
  [0.52, 0.14],
  [0.04, 0.14],
];
const HALF_DEPTH = 0.16;
const RAMP = ' .:-=+*#%@';
// View-space light: upper left, towards the viewer, like a studio key light.
const LIGHT = norm([-0.45, 0.6, 0.66]);

function norm([x, y, z]: V3): V3 {
  const l = Math.hypot(x, y, z) || 1;
  return [x / l, y / l, z / l];
}

const dot = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

export function pointInPolygon(x: number, y: number, poly: V2[]): boolean {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

const signedArea = (poly: V2[]) =>
  poly.reduce((s, [x1, y1], i) => {
    const [x2, y2] = poly[(i + 1) % poly.length];
    return s + x1 * y2 - x2 * y1;
  }, 0) / 2;

// Outward side normals depend on winding, so fix the sign once.
const WINDING = Math.sign(signedArea(BOLT));
const SIDES = BOLT.map((a, i) => {
  const b = BOLT[(i + 1) % BOLT.length];
  const n = norm([(b[1] - a[1]) * WINDING, -(b[0] - a[0]) * WINDING, 0]);
  return { a, b, n };
});

export interface Hit {
  t: number;
  normal: V3;
}

/** Nearest intersection of a ray (object space) with the extruded bolt, or null. */
export function castRay(o: V3, d: V3): Hit | null {
  let best: Hit | null = null;
  const consider = (t: number, normal: V3) => {
    if (t > 1e-6 && (!best || t < best.t)) best = { t, normal };
  };

  if (Math.abs(d[2]) > 1e-9) {
    for (const z of [HALF_DEPTH, -HALF_DEPTH]) {
      const t = (z - o[2]) / d[2];
      if (pointInPolygon(o[0] + t * d[0], o[1] + t * d[1], BOLT)) consider(t, [0, 0, Math.sign(z)]);
    }
  }

  for (const { a, b, n } of SIDES) {
    const denom = dot(d, n);
    if (Math.abs(denom) < 1e-9) continue;
    const t = ((a[0] - o[0]) * n[0] + (a[1] - o[1]) * n[1]) / denom;
    const p: V3 = [o[0] + t * d[0], o[1] + t * d[1], o[2] + t * d[2]];
    if (Math.abs(p[2]) > HALF_DEPTH) continue;
    const ex = b[0] - a[0];
    const ey = b[1] - a[1];
    const s = ((p[0] - a[0]) * ex + (p[1] - a[1]) * ey) / (ex * ex + ey * ey);
    if (s >= 0 && s <= 1) consider(t, n);
  }
  return best;
}

// Rotation = yaw about Y, then pitch about X. Columns of R map object axes to view.
function rotation(yaw: number, pitch: number) {
  const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
  const R: [V3, V3, V3] = [
    [cy, 0, sy],
    [sp * sy, cp, -sp * cy],
    [-cp * sy, sp, cp * cy],
  ];
  const toView = (v: V3): V3 => [dot(R[0], v), dot(R[1], v), dot(R[2], v)];
  const toObject = (v: V3): V3 => [
    R[0][0] * v[0] + R[1][0] * v[1] + R[2][0] * v[2],
    R[0][1] * v[0] + R[1][1] * v[1] + R[2][1] * v[2],
    R[0][2] * v[0] + R[1][2] * v[1] + R[2][2] * v[2],
  ];
  return { toView, toObject };
}

/** Glyph for a silhouette edge, matched to its direction so edges read as lines, not noise. */
export function edgeGlyph(gx: number, gy: number): string {
  // (gx, gy) points across the edge; the stroke runs perpendicular to it.
  const angle = ((Math.atan2(gy, gx) * 180) / Math.PI + 180) % 180;
  if (angle < 22.5 || angle >= 157.5) return '|';
  if (angle < 67.5) return '\\';
  if (angle < 112.5) return '-';
  return '/';
}

export const shadeGlyph = (b: number) => RAMP[Math.min(RAMP.length - 1, Math.max(1, Math.round(b * (RAMP.length - 1))))];

export interface Cell {
  ch: string;
  b: number;
}

/**
 * One frame as a grid of glyphs. `aspect` is cell width / height, so a monospace grid
 * still draws a correctly proportioned bolt.
 */
export function renderFrame(cols: number, rows: number, yaw: number, pitch: number, aspect: number): Cell[][] {
  const { toView, toObject } = rotation(yaw, pitch);
  const scale = 2.3 / Math.min(cols * aspect, rows);
  const dir = toObject([0, 0, -1]);
  const grid: (Cell & { hit: boolean })[][] = [];

  for (let r = 0; r < rows; r++) {
    const row: (Cell & { hit: boolean })[] = [];
    for (let c = 0; c < cols; c++) {
      const u = (c + 0.5 - cols / 2) * aspect * scale;
      const v = -(r + 0.5 - rows / 2) * scale;
      const hit = castRay(toObject([u, v, 5]), dir);
      if (!hit) {
        row.push({ ch: ' ', b: 0, hit: false });
        continue;
      }
      const n = toView(hit.normal);
      const lambert = Math.max(0, dot(n, LIGHT));
      const rim = Math.pow(1 - Math.abs(n[2]), 3) * 0.35;
      const b = Math.min(1, 0.12 + 0.78 * lambert + rim);
      row.push({ ch: shadeGlyph(b), b, hit: true });
    }
    grid.push(row);
  }

  const isHit = (r: number, c: number) => grid[r]?.[c]?.hit ?? false;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (!grid[r][c].hit) continue;
      const gx = +isHit(r, c + 1) - +isHit(r, c - 1);
      const gy = +isHit(r - 1, c) - +isHit(r + 1, c);
      if (gx !== 0 || gy !== 0) grid[r][c].ch = edgeGlyph(gx, gy);
    }
  }
  return grid.map((row) => row.map(({ ch, b }) => ({ ch, b })));
}

/** Mounts an auto-rotating, drag-to-orbit ASCII bolt on a canvas. Returns a cleanup function. */
export function mountAsciiBolt(canvas: HTMLCanvasElement): () => void {
  const ctx = canvas.getContext('2d')!;
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const FONT_PX = 10;
  const CELL_W = FONT_PX * 0.6;
  const CELL_H = FONT_PX * 1.15;

  // Idle motion sways ±SWAY around `base` instead of spinning, so the bolt never sits edge-on (a flat bar) on video.
  const SWAY = 0.75;
  let base = 0;
  let phase = 0;
  let fling = 0;
  let yaw = base;
  let pitch = -0.25;
  let dragging = false;
  let last = { x: 0, y: 0 };
  let raf = 0;
  let prev = performance.now();
  let visible = true;

  const draw = () => {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (canvas.width !== Math.round(w * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.font = `400 ${FONT_PX}px 'IBM Plex Mono', ui-monospace, monospace`;
    ctx.textBaseline = 'top';

    const cols = Math.floor(w / CELL_W);
    const rows = Math.floor(h / CELL_H);
    const frame = renderFrame(cols, rows, yaw, pitch, CELL_W / CELL_H);
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const { ch, b } = frame[r][c];
        if (ch === ' ') continue;
        ctx.fillStyle = `rgb(237 237 239 / ${0.18 + 0.82 * b})`;
        ctx.fillText(ch, c * CELL_W, r * CELL_H);
      }
    }
  };

  const tick = (now: number) => {
    const dt = Math.min(0.05, (now - prev) / 1000);
    prev = now;
    if (!dragging) {
      phase += dt;
      base += fling * dt;
      fling *= Math.exp(-dt * 2);
      yaw = base + SWAY * Math.sin(phase * 0.7);
    }
    draw();
    raf = visible ? requestAnimationFrame(tick) : 0;
  };

  const onDown = (e: PointerEvent) => {
    dragging = true;
    last = { x: e.clientX, y: e.clientY };
    canvas.setPointerCapture(e.pointerId);
  };
  const onMove = (e: PointerEvent) => {
    if (!dragging) return;
    const dx = e.clientX - last.x;
    const dy = e.clientY - last.y;
    last = { x: e.clientX, y: e.clientY };
    yaw += dx * 0.01;
    base = yaw - SWAY * Math.sin(phase * 0.7);
    pitch = Math.max(-1.2, Math.min(1.2, pitch + dy * 0.01));
    fling = dx * 0.6;
    if (reduceMotion) draw();
  };
  const onUp = () => (dragging = false);

  canvas.addEventListener('pointerdown', onDown);
  canvas.addEventListener('pointermove', onMove);
  canvas.addEventListener('pointerup', onUp);
  canvas.addEventListener('pointercancel', onUp);

  // Stop the loop when the bolt is scrolled away or the tab is hidden.
  const io = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting && !document.hidden;
    if (visible && !raf && !reduceMotion) {
      prev = performance.now();
      raf = requestAnimationFrame(tick);
    }
  });
  io.observe(canvas);

  const ro = new ResizeObserver(draw);
  ro.observe(canvas);

  document.fonts.ready.then(draw);
  if (!reduceMotion) raf = requestAnimationFrame(tick);

  return () => {
    cancelAnimationFrame(raf);
    io.disconnect();
    ro.disconnect();
  };
}
