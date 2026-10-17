SET search_path = bn;

-- a household sees only its own register rows: the login comes from the session, never from the request
CREATE FUNCTION me_home_patients(p_login text)
RETURNS TABLE (device text, reserve_h numeric, other_backup boolean, postcode_bidx bytea)
LANGUAGE sql SECURITY DEFINER SET search_path = bn, pg_temp AS $$
  SELECT pa.device, pa.reserve_h, pa.other_backup, pa.postcode_bidx
  FROM principal pr JOIN patient pa ON pa.household_id = pr.household_id
  WHERE pr.login = p_login AND pr.role = 'household'
$$;

REVOKE ALL ON FUNCTION me_home_patients(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION me_home_patients(text) TO bn_api;
