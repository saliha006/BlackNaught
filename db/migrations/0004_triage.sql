SET search_path = bn;

-- snapshots every 30 s would grow ~1M rows/day; the scorer prunes anything older than its retention window
GRANT DELETE ON triage_snapshot TO bn_agent;

-- the API needs the outage footprint next to each ranked patient, without touching the register
CREATE OR REPLACE VIEW v_triage_latest AS
  SELECT t.tick_at, t.rank, 'P-' || upper(substr(md5(t.patient_id::text), 1, 6)) AS patient_ref,
         t.outage_id, p.device, p.reserve_h, p.other_backup, p.severity, p.cell_l1,
         t.harm, t.q_used, t.q_hours, t.escalate, t.why, t.model_id, o.customers
  FROM triage_snapshot t
  JOIN patient p USING (patient_id)
  JOIN outage o USING (outage_id)
  WHERE t.tick_at = (SELECT max(tick_at) FROM triage_snapshot);
