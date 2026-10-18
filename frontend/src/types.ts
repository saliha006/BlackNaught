// Shapes mirror contracts/openapi.yaml (frozen by @sali).

export type Label = 'LIVE' | 'SIMULATED' | 'REPLAY' | 'TRANSFERRED' | 'BASELINE';

export type Scale = 'home' | 'street' | 'area' | 'region' | 'system' | 'brownout' | 'unresolved';

export type LatLon = [number, number];

export interface Outage {
  id: number;
  source: string;
  label: Label;
  status: 'active' | 'restored' | 'vanished' | 'planned';
  started_at: string;
  restored_at: string | null;
  elapsed_h: number;
  customers: number;
  priority_customers: number;
  scale: Scale;
  cell_l1: string;
  centroid: LatLon;
  postcode_count: number;
}

export interface TriageItem {
  rank: number;
  patient_ref: string;
  outage_id: number;
  scale: Scale;
  device: string;
  reserve_left_h: number;
  remaining_h: { q50: number; q75: number; q90: number };
  q_used: 'q50' | 'q75' | 'q90';
  harm: number;
  escalate: boolean;
  why: string[];
  decision_id: string | null;
}

export interface Triage {
  tick_at: string;
  items: TriageItem[];
}

export interface SourceHealth {
  source: string;
  status: 'ok' | 'stale' | 'down' | 'degraded';
  interval_s: number;
  staleness_s: number | null;
  records_last: number | null;
  consecutive_failures: number;
  label: Label;
}

export interface Cell {
  cell_id: string;
  level: number;
  bounds: LatLon[];
  patients: number | 'suppressed';
  outage_scale: Scale | null;
  risk_tomorrow: number | null;
}
