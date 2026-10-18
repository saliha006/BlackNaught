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
  customers: number | null;
  // Northern Powergrid publishes no priority-customer count, so this is null for its faults.
  priority_customers: number | null;
  scale: Scale;
  cell_l1: string | null;
  // Null until the operator's postcodes are geocoded (contract: anyOf [lat, lon] | null).
  centroid: LatLon | null;
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

export interface HorizonGrade {
  h: number;
  model_id: string;
  source: string;
  // Null while every prediction at this horizon is still censored: the outage hasn't resolved either way.
  brier: number | null;
  n: number;
  n_censored: number;
  bound: [number, number] | null;
}

export interface Grades {
  by_horizon: HorizonGrade[];
  trend: { at: string; brier: number; n?: number }[];
}

export interface AreaRisk {
  district: string;
  p_ge_k: number;
  expected: number;
  label: Label;
}

export interface GridStress {
  grid: string;
  hz: number | null;
  measured_at: string | null;
  state: 'NORMAL' | 'STRESSED' | 'EMERGENCY' | 'SPLIT_SUSPECTED' | 'UNKNOWN';
  seconds_to_next_rung: number | null;
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
