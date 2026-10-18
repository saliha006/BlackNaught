SET search_path = bn;

-- Logins for the control-room operator and (later) households. The API role never reads these tables directly:
-- it goes through the narrow SECURITY DEFINER functions below.
CREATE TABLE principal (
  login        text PRIMARY KEY,
  role         text NOT NULL CHECK (role IN ('operator', 'household')),
  household_id uuid,
  pw_hash      text NOT NULL,
  failed       int NOT NULL DEFAULT 0,
  locked_until timestamptz
);

CREATE TABLE session (
  token_sha256 bytea PRIMARY KEY,
  login        text NOT NULL REFERENCES principal ON DELETE CASCADE,
  role         text NOT NULL,
  created_at   timestamptz NOT NULL,
  last_seen    timestamptz NOT NULL,
  expires_at   timestamptz NOT NULL
);

CREATE FUNCTION auth_principal(p_login text)
RETURNS TABLE (role text, pw_hash text, locked_until timestamptz)
LANGUAGE sql SECURITY DEFINER SET search_path = bn, pg_temp AS $$
  SELECT role, pw_hash, locked_until FROM principal WHERE login = p_login
$$;

-- 5 failures lock the login for 15 minutes; success resets the counter
CREATE FUNCTION auth_result(p_login text, p_ok boolean) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = bn, pg_temp AS $$
  UPDATE principal SET
    failed = CASE WHEN p_ok THEN 0 ELSE failed + 1 END,
    locked_until = CASE WHEN NOT p_ok AND failed + 1 >= 5 THEN now() + interval '15 minutes'
                        WHEN p_ok THEN NULL ELSE locked_until END
  WHERE login = p_login
$$;

CREATE FUNCTION session_create(p_token bytea, p_login text) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = bn, pg_temp AS $$
  INSERT INTO session (token_sha256, login, role, created_at, last_seen, expires_at)
  SELECT p_token, login, role, now(), now(), now() + interval '8 hours' FROM principal WHERE login = p_login
$$;

-- valid = not past the 8 h absolute limit and used within the last 30 min; touching extends the idle window
CREATE FUNCTION session_get(p_token bytea) RETURNS TABLE (login text, role text)
LANGUAGE sql SECURITY DEFINER SET search_path = bn, pg_temp AS $$
  UPDATE session SET last_seen = now()
  WHERE token_sha256 = p_token AND expires_at > now() AND last_seen > now() - interval '30 minutes'
  RETURNING login, role
$$;

CREATE FUNCTION session_delete(p_token bytea) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = bn, pg_temp AS $$
  DELETE FROM session WHERE token_sha256 = p_token
$$;

-- only a decision that is waiting for a human can be approved or rejected, and only once
CREATE FUNCTION approve_decision(p_id uuid, p_approve boolean, p_approver text) RETURNS text
LANGUAGE sql SECURITY DEFINER SET search_path = bn, pg_temp AS $$
  UPDATE decision SET state = CASE WHEN p_approve THEN 'approved' ELSE 'rejected' END,
                      approver = p_approver, decided_at = now()
  WHERE decision_id = p_id AND state = 'awaiting_approval'
  RETURNING state
$$;

REVOKE ALL ON principal, session FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_principal(text), auth_result(text, boolean), session_create(bytea, text),
  session_get(bytea), session_delete(bytea), approve_decision(uuid, boolean, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION auth_principal(text), auth_result(text, boolean), session_create(bytea, text),
  session_get(bytea), session_delete(bytea), approve_decision(uuid, boolean, text) TO bn_api;
GRANT UPDATE (audit_seq) ON decision TO bn_agent;
