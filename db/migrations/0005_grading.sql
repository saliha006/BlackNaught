SET search_path = bn;

-- the censoring bound needs each prediction's probability next to its grade
CREATE OR REPLACE VIEW v_grades AS
  SELECT g.pred_id, g.graded_at, g.outcome, g.censored, g.reason, g.brier,
         p.outage_id, p.model_id, p.horizon_h, p.made_at, o.source, p.p_still_off
  FROM grade g JOIN prediction p USING (pred_id) JOIN outage o USING (outage_id);
