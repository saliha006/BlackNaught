SET search_path = bn;

-- Tamper-evident chain over decisions, approvals and tool calls (not telemetry).
-- body is canonical JSON stored as text so verification re-hashes the exact bytes.
CREATE TABLE audit_log (
  seq       bigint PRIMARY KEY,
  body      text NOT NULL,
  kind      text GENERATED ALWAYS AS ((body::jsonb)->>'kind') STORED,
  prev_hash bytea NOT NULL CHECK (length(prev_hash) = 32),
  hash      bytea NOT NULL UNIQUE CHECK (length(hash) = 32)
);

CREATE TABLE audit_checkpoint (
  seq           bigint PRIMARY KEY REFERENCES audit_log,
  head          bytea NOT NULL,
  at            timestamptz NOT NULL,
  alg           text,
  key_id        text,
  sig_b64       text,
  published_ref text
);

CREATE FUNCTION audit_append(p_body text) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = bn, pg_temp AS $$
DECLARE
  v_seq  bigint;
  v_prev bytea;
BEGIN
  PERFORM pg_advisory_xact_lock(727274);
  SELECT seq, hash INTO v_seq, v_prev FROM audit_log ORDER BY seq DESC LIMIT 1;
  v_seq  := coalesce(v_seq, 0) + 1;
  v_prev := coalesce(v_prev, decode(repeat('00', 32), 'hex'));
  INSERT INTO audit_log (seq, body, prev_hash, hash)
  VALUES (v_seq, p_body, v_prev, sha256(v_prev || convert_to(p_body, 'UTF8')));
  RETURN v_seq;
END $$;

CREATE FUNCTION audit_no_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only';
END $$;

CREATE TRIGGER audit_no_upd_del BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_no_change();
CREATE TRIGGER audit_no_trunc BEFORE TRUNCATE ON audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION audit_no_change();

REVOKE ALL ON audit_log, audit_checkpoint FROM PUBLIC;
REVOKE ALL ON FUNCTION audit_append(text) FROM PUBLIC;
