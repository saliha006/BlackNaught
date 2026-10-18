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

export type DecisionStateName = 'auto_done' | 'awaiting_approval' | 'approved' | 'rejected' | 'exported' | 'expired';

export interface AgentDecision {
  id: string;
  tool: string;
  state: DecisionStateName;
  created_at: string;
  args_summary: string;
  rationale: string[];
}

export interface DecisionState {
  decision_id: string;
  state: DecisionStateName;
  audit_seq: number | null;
}

export interface AuditVerify {
  ok: boolean;
  rows: number;
  first_bad_seq: number | null;
  reason: string | null;
  // sig_ok is null when the checkpoint was written before the signer existed: unknown, not failed.
  last_checkpoint: { seq: number; sig_ok: boolean | null; head_matches: boolean } | null;
  took_ms: number;
}

export interface RiskLayer {
  layer: 'home' | 'area' | 'grid';
  // Null means the layer has no data; it must never be read as "low".
  value: string | null;
  horizon: string;
  source: string;
  updated: string | null;
}

export interface HomeRisk {
  level: 'low' | 'elevated' | 'high' | 'unknown';
  reason: string;
  layers: RiskLayer[];
}

export interface MyHome {
  household: string;
  label: Label;
  power: 'on' | 'off' | 'unknown';
  since: string | null;
  reserve: { device: string; ends_at: string | null; hours_left: number | null };
  voltage: { t: string; pu: number }[];
  bands: Record<string, number>;
  next_action: string;
  grid_context: { hz: number | null; note: string };
  risk: HomeRisk;
}
