SET search_path = bn;

-- public geocodes of DNO postcodes (no patient data) for CAP polygons
CREATE VIEW v_postcode_geo AS SELECT postcode, lat, lon FROM postcode_geo WHERE valid;

-- whether any patient on the outage escalated without backup, without exposing who
CREATE VIEW v_outage_severity AS
  SELECT outage_id, bool_or(escalate AND NOT other_backup) AS severe FROM v_triage_latest GROUP BY outage_id;

CREATE VIEW v_cap_alert AS SELECT decision_id, identifier, xml, sig_b64, created_at FROM cap_alert;

-- stored once per approved alert; a second call can't overwrite it
CREATE FUNCTION cap_store(p_decision uuid, p_identifier text, p_xml text, p_sig text) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path = bn, pg_temp AS $$
  INSERT INTO cap_alert (decision_id, identifier, xml, sig_b64, created_at)
  SELECT d.decision_id, p_identifier, p_xml, p_sig, now() FROM decision d
  WHERE d.decision_id = p_decision AND d.tool = 'draft_cap_alert' AND d.state = 'approved'
  ON CONFLICT (decision_id) DO NOTHING
  RETURNING true
$$;

REVOKE ALL ON FUNCTION cap_store(uuid, text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION cap_store(uuid, text, text, text) TO bn_api;
GRANT SELECT ON v_postcode_geo, v_outage_severity, v_cap_alert TO bn_api;
