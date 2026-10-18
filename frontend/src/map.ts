import {
  AttributionControl,
  type GeoJSONSource,
  type LayerSpecification,
  Map as MapLibreMap,
  type MapOptions,
  NavigationControl,
  setWorkerUrl,
} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import { beamsToGeoJSON, cellsToGeoJSON, isLocated, type Located, outagesToGeoJSON } from './geo';
import { sweepFeatures } from './sweep';
import type { Cell, Outage } from './types';

// MapLibre v6 looks for its worker next to its own module, which Vite's dep bundling moves; hand it Vite's built worker instead.
setWorkerUrl(workerUrl);

const BASEMAP = 'https://tiles.openfreemap.org/styles/dark';
const GB_BOUNDS: [number, number, number, number] = [-8.6, 49.8, 2.0, 59.2];
// Keep the map's focus clear of the outage panel: a right column on desktop, a bottom sheet on phones (styles.css).
const panelPad = () =>
  innerWidth > 720
    ? { top: 60, bottom: 40, left: 40, right: 420 }
    : { top: 60, bottom: Math.round(innerHeight * 0.45), left: 20, right: 20 };

// If OpenFreeMap is unreachable mid-recording, overlays still draw on a plain background.
const FALLBACK_STYLE: Exclude<MapOptions['style'], string | undefined> = {
  version: 8,
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#07090c' } }],
};

// Night-city palette (Arkham Knight / Spider-Man world maps): near-black ground, cool slate blocks, dim roads.
const CITY = {
  ground: '#07090c',
  water: '#0b0f14',
  land: '#0b0e12',
  roadMinor: '#191e25',
  roadMajor: '#242a32',
  motorway: '#2e353f',
  label: '#7d8693',
  labelHalo: '#07090c',
};

// Sensor sweeps only read once streets are visible; below this they are a few pixels wide.
const SWEEP_MINZOOM = 11;
const BEAM_GLOW_OPACITY = 0.14;

export interface OutageMap {
  setData(outages: Outage[], cells: Cell[]): void;
  /** Fly down to street level over an outage. `duration` in ms; longer for the opening dive. */
  focus(outage: Located, duration?: number): void;
  onSelect(handler: (id: number) => void): void;
  /** Ease to the tilted whole-GB view, for when there is no outage to dive into. */
  overview(): void;
  /** Jump back to the flat GB view behind the landing page, ready for the next dive. */
  reset(): void;
  /** Run the sensor animation only while the map is on screen. */
  setLive(on: boolean): void;
}

// Checked once up front: map 'error' events also fire for single missing sprites/tiles, which must not drop the basemap.
async function pickStyle(): Promise<MapOptions['style']> {
  try {
    const res = await fetch(BASEMAP, { signal: AbortSignal.timeout(4000) });
    if (res.ok) return BASEMAP;
  } catch {
    // unreachable or too slow: fall through
  }
  console.warn('Basemap unreachable, using plain background');
  return FALLBACK_STYLE;
}

function roadColour(id: string) {
  if (id.includes('motorway')) return CITY.motorway;
  if (id.includes('major')) return CITY.roadMajor;
  return CITY.roadMinor;
}

/** Recolour the OpenFreeMap layers in place and swap flat footprints for extruded buildings. */
function applyNightCity(map: MapLibreMap) {
  const layers = map.getStyle().layers;
  for (const layer of layers) {
    const { id, type } = layer;
    if (type === 'background') map.setPaintProperty(id, 'background-color', CITY.ground);
    else if (type === 'fill' && id === 'water') map.setPaintProperty(id, 'fill-color', CITY.water);
    else if (type === 'fill' && (id.startsWith('landuse') || id.startsWith('landcover')))
      map.setPaintProperty(id, 'fill-color', CITY.land);
    else if (type === 'line' && id.startsWith('highway')) map.setPaintProperty(id, 'line-color', roadColour(id));
    else if (type === 'line' && id.startsWith('waterway')) map.setPaintProperty(id, 'line-color', CITY.water);
    else if (type === 'symbol' && map.getLayoutProperty(id, 'text-field') !== undefined) {
      map.setPaintProperty(id, 'text-color', CITY.label);
      map.setPaintProperty(id, 'text-halo-color', CITY.labelHalo);
    }
  }

  if (!map.getLayer('building')) return;
  map.setLayoutProperty('building', 'visibility', 'none');
  const firstLabel = layers.find((l) => l.type === 'symbol')?.id;
  const buildings: LayerSpecification = {
    id: 'building-3d',
    type: 'fill-extrusion',
    source: 'openmaptiles',
    'source-layer': 'building',
    minzoom: 13,
    paint: {
      'fill-extrusion-color': [
        'interpolate', ['linear'], ['coalesce', ['get', 'render_height'], 8],
        0, '#141920',
        40, '#222933',
        150, '#36404d',
      ],
      'fill-extrusion-height': ['interpolate', ['linear'], ['zoom'], 13, 0, 14.5, ['coalesce', ['get', 'render_height'], 8]],
      'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0],
      'fill-extrusion-opacity': 0.94,
      'fill-extrusion-vertical-gradient': true,
    },
  };
  map.addLayer(buildings, firstLabel);
}

/** Light beams with a sweep at their foot: a radar-style scan, the ground glow and two stacked core segments. */
function addSensorLayers(map: MapLibreMap) {
  map.addLayer({
    id: 'sweep-fill',
    type: 'fill',
    source: 'sweep',
    minzoom: SWEEP_MINZOOM,
    filter: ['==', ['get', 'kind'], 'wedge'],
    paint: { 'fill-color': '#ffffff', 'fill-opacity': ['get', 'alpha'], 'fill-antialias': false },
  });
  map.addLayer({
    id: 'sweep-line',
    type: 'line',
    source: 'sweep',
    minzoom: SWEEP_MINZOOM,
    filter: ['!=', ['get', 'kind'], 'wedge'],
    paint: { 'line-color': '#ffffff', 'line-opacity': ['get', 'alpha'], 'line-width': ['get', 'width'] },
  });
  // Light pooling on the street where each beam lands; doubles per zoom level so it keeps one size on the ground.
  map.addLayer({
    id: 'outage-glow',
    type: 'circle',
    source: 'outages',
    minzoom: 12,
    paint: {
      'circle-radius': ['interpolate', ['exponential', 2], ['zoom'], 12, 3, 16, 48],
      'circle-color': '#ffffff',
      'circle-opacity': 0.4,
      'circle-blur': 1,
      'circle-pitch-alignment': 'map',
    },
  });
}

function addBeamLayers(map: MapLibreMap) {
  // Extrusion opacity cannot vary along a column, so the core is two stacked segments: bright below, faint above.
  map.addLayer({
    id: 'beam-core',
    type: 'fill-extrusion',
    source: 'beams',
    minzoom: 12,
    filter: ['==', ['get', 'kind'], 'core'],
    paint: {
      'fill-extrusion-color': '#ffffff',
      'fill-extrusion-height': ['*', ['get', 'height'], 0.6],
      'fill-extrusion-opacity': 0.9,
      'fill-extrusion-vertical-gradient': false,
    },
  });
  map.addLayer({
    id: 'beam-core-top',
    type: 'fill-extrusion',
    source: 'beams',
    minzoom: 12,
    filter: ['==', ['get', 'kind'], 'core'],
    paint: {
      'fill-extrusion-color': '#ffffff',
      'fill-extrusion-base': ['*', ['get', 'height'], 0.6],
      'fill-extrusion-height': ['get', 'height'],
      'fill-extrusion-opacity': 0.35,
      'fill-extrusion-vertical-gradient': false,
    },
  });
  // 3D layers share one depth buffer: drawn first, the wider glow would hide the core inside it.
  map.addLayer({
    id: 'beam-glow',
    type: 'fill-extrusion',
    source: 'beams',
    minzoom: 12,
    filter: ['==', ['get', 'kind'], 'glow'],
    paint: {
      'fill-extrusion-color': '#e8eef5',
      'fill-extrusion-height': ['*', ['get', 'height'], 0.85],
      'fill-extrusion-opacity': BEAM_GLOW_OPACITY,
      'fill-extrusion-vertical-gradient': false,
    },
  });
}

export async function createMap(container: HTMLElement): Promise<OutageMap> {
  const map = new MapLibreMap({
    container,
    style: await pickStyle(),
    bounds: GB_BOUNDS,
    fitBoundsOptions: { padding: panelPad() },
    maxPitch: 75,
    attributionControl: false,
  });
  // Bottom-right sits under the floating panel; OSM attribution must stay visible.
  map.addControl(new AttributionControl({ compact: true }), 'bottom-left');
  map.addControl(new NavigationControl({ visualizePitch: true }), 'bottom-left');

  let selected: number | null = null;
  let selectHandler: (id: number) => void = () => {};

  await new Promise((resolve) => map.once('style.load', resolve));

  applyNightCity(map);
  map.setSky({
    'sky-color': '#07090c',
    'horizon-color': '#151a21',
    'fog-color': '#07090c',
    'fog-ground-blend': 0.55,
    'horizon-fog-blend': 0.7,
    'sky-horizon-blend': 0.6,
  });
  map.setLight({ anchor: 'map', position: [1.4, 215, 35], color: '#c9d3df', intensity: 0.45 });

  map.addSource('cells', { type: 'geojson', data: cellsToGeoJSON([]) });
  map.addSource('outages', { type: 'geojson', data: outagesToGeoJSON([]) });
  map.addSource('beams', { type: 'geojson', data: beamsToGeoJSON([]) });
  map.addSource('sweep', { type: 'geojson', data: sweepFeatures([], 0) });

  map.addLayer({
    id: 'cells-fill',
    type: 'fill',
    source: 'cells',
    paint: {
      'fill-color': '#ffffff',
      'fill-opacity': ['case', ['get', 'affected'], 0.12, ['get', 'suppressed'], 0.02, 0.05],
    },
  });
  map.addLayer({
    id: 'cells-line',
    type: 'line',
    source: 'cells',
    paint: { 'line-color': '#ffffff', 'line-opacity': 0.35, 'line-width': 1 },
  });
  addSensorLayers(map);
  map.addLayer({
    id: 'outage-halo',
    type: 'circle',
    source: 'outages',
    paint: {
      'circle-radius': ['*', ['get', 'radius'], 2.2],
      'circle-color': '#ffffff',
      'circle-opacity': ['case', ['boolean', ['feature-state', 'selected'], false], 0.18, 0.07],
      'circle-pitch-alignment': 'map',
    },
  });
  map.addLayer({
    id: 'outage-dot',
    type: 'circle',
    source: 'outages',
    paint: {
      'circle-radius': ['get', 'radius'],
      'circle-color': '#07090c',
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': ['case', ['boolean', ['feature-state', 'selected'], false], 2.5, 1.5],
      'circle-pitch-alignment': 'map',
    },
  });
  addBeamLayers(map);

  map.on('click', 'outage-dot', (e) => {
    const id = e.features?.[0]?.properties?.id;
    if (typeof id === 'number') selectHandler(id);
  });
  map.on('mouseenter', 'outage-dot', () => (map.getCanvas().style.cursor = 'pointer'));
  map.on('mouseleave', 'outage-dot', () => (map.getCanvas().style.cursor = ''));

  const select = (id: number | null) => {
    if (selected !== null) map.setFeatureState({ source: 'outages', id: selected }, { selected: false });
    selected = id;
    if (id !== null) map.setFeatureState({ source: 'outages', id }, { selected: true });
  };

  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let located: Located[] = [];
  let live = false;
  let sweeping = false;
  let raf = 0;

  const drawSensors = (t: number) => {
    const bounds = map.getBounds();
    const visible = map.getZoom() >= SWEEP_MINZOOM ? located.filter((o) => bounds.contains([o.centroid[1], o.centroid[0]])) : [];
    // Nothing to sweep and nothing left on screen: leave the map idle instead of re-rendering every frame.
    if (visible.length === 0 && !sweeping) return;
    sweeping = visible.length > 0;
    (map.getSource('sweep') as GeoJSONSource).setData(sweepFeatures(visible, t));
    map.setPaintProperty('beam-glow', 'fill-extrusion-opacity', BEAM_GLOW_OPACITY + 0.06 * Math.sin(t * 2.4));
  };
  const loop = (now: number) => {
    drawSensors(now / 1000);
    raf = requestAnimationFrame(loop);
  };
  // Reduced motion: one still frame per camera move instead of a running animation.
  map.on('moveend', () => {
    if (live && reduceMotion) drawSensors(0);
  });

  return {
    setData(outages, cells) {
      located = outages.filter(isLocated);
      (map.getSource('outages') as GeoJSONSource).setData(outagesToGeoJSON(outages));
      (map.getSource('beams') as GeoJSONSource).setData(beamsToGeoJSON(outages));
      (map.getSource('cells') as GeoJSONSource).setData(cellsToGeoJSON(cells));
    },
    focus(outage, duration = 3200) {
      select(outage.id);
      const [lat, lon] = outage.centroid;
      map.flyTo({
        center: [lon, lat],
        zoom: 15.4,
        pitch: 64,
        bearing: -28,
        duration,
        padding: panelPad(),
        essential: false,
      });
    },
    onSelect(handler) {
      selectHandler = handler;
    },
    overview() {
      const camera = map.cameraForBounds(GB_BOUNDS, { padding: panelPad() });
      map.easeTo({ ...camera, pitch: 42, bearing: -12, duration: 2400 });
    },
    reset() {
      select(null);
      map.jumpTo({ ...map.cameraForBounds(GB_BOUNDS, { padding: panelPad() }), pitch: 0, bearing: 0 });
    },
    setLive(on) {
      live = on;
      cancelAnimationFrame(raf);
      raf = 0;
      if (!on) return;
      if (reduceMotion) drawSensors(0);
      else raf = requestAnimationFrame(loop);
    },
  };
}
