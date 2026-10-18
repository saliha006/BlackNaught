SET search_path = bn;

GRANT USAGE ON SCHEMA bn TO bn_ingest, bn_api, bn_agent;

-- ingest: writes feed data, never reads the register
GRANT SELECT, INSERT, UPDATE ON outage, outage_version, freq_reading, sensor_transition,
  event_counts, source_poll, postcode_geo TO bn_ingest;
GRANT INSERT ON ingest_reject TO bn_ingest;
GRANT USAGE ON SEQUENCE outage_outage_id_seq, ingest_reject_id_seq TO bn_ingest;
GRANT EXECUTE ON FUNCTION audit_append(text) TO bn_ingest, bn_agent, bn_api;

-- agent (+ scorer, grader): reads the register as ciphertext, writes decisions and scores
GRANT SELECT ON patient, outage, postcode_geo, freq_reading, source_poll TO bn_agent;
GRANT SELECT, INSERT ON prediction, grade, triage_snapshot, decision, cap_alert, audit_checkpoint TO bn_agent;
GRANT SELECT, INSERT, UPDATE ON agent_memory TO bn_agent;
GRANT UPDATE (state, decided_at) ON decision TO bn_agent;
GRANT USAGE ON SEQUENCE prediction_pred_id_seq TO bn_agent;
GRANT SELECT ON audit_log TO bn_agent;

-- api: views only, never raw tables
CREATE VIEW v_outage_public AS
  SELECT outage_id, source, source_ref, status, started_at, restored_at, restored_explicit,
         customers, priority_customers, postcodes, lat, lon, cell_l1, label, version, last_seen
  FROM outage;

CREATE VIEW v_freq_latest AS
  SELECT DISTINCT ON (grid) grid, measured_at, hz FROM freq_reading ORDER BY grid, measured_at DESC;

CREATE VIEW v_source_poll AS
  SELECT source, polled_at, ok, http_status, n_records, latency_ms, error FROM source_poll;

CREATE VIEW v_triage_latest AS
  SELECT t.tick_at, t.rank, 'P-' || upper(substr(md5(t.patient_id::text), 1, 6)) AS patient_ref,
         t.outage_id, p.device, p.reserve_h, p.other_backup, p.severity, p.cell_l1,
         t.harm, t.q_used, t.q_hours, t.escalate, t.why, t.model_id
  FROM triage_snapshot t JOIN patient p USING (patient_id)
  WHERE t.tick_at = (SELECT max(tick_at) FROM triage_snapshot);

CREATE VIEW v_grades AS
  SELECT g.pred_id, g.graded_at, g.outcome, g.censored, g.reason, g.brier,
         p.outage_id, p.model_id, p.horizon_h, p.made_at, o.source
  FROM grade g JOIN prediction p USING (pred_id) JOIN outage o USING (outage_id);

CREATE VIEW v_decisions AS
  SELECT decision_id, created_at, tool, args, state, approver, decided_at, rationale, audit_seq FROM decision;

CREATE VIEW v_audit AS
  SELECT seq, body, kind, prev_hash, hash FROM audit_log;

CREATE VIEW v_audit_checkpoint AS
  SELECT seq, head, at, alg, key_id, sig_b64, published_ref FROM audit_checkpoint;

GRANT SELECT ON v_outage_public, v_freq_latest, v_source_poll, v_triage_latest, v_grades,
  v_decisions, v_audit, v_audit_checkpoint TO bn_api;
