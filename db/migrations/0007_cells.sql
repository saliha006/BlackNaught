SET search_path = bn;

-- published every 15 minutes, never per event, so the map can't be differenced tick by tick
CREATE TABLE cell_snapshot (
  published_at timestamptz NOT NULL,
  cell_id      text NOT NULL,
  level        smallint NOT NULL CHECK (level BETWEEN 1 AND 3),
  patients     int CHECK (patients IS NULL OR patients = 0 OR patients >= 11),
  PRIMARY KEY (published_at, cell_id)
);

GRANT SELECT, INSERT, DELETE ON cell_snapshot TO bn_agent;

CREATE VIEW v_cells_published AS
  SELECT cell_id, level, patients, published_at FROM cell_snapshot
  WHERE published_at = (SELECT max(published_at) FROM cell_snapshot);

CREATE VIEW v_outage_cells AS
  SELECT cell_l1, customers FROM outage WHERE status = 'active' AND cell_l1 IS NOT NULL;

GRANT SELECT ON v_cells_published, v_outage_cells TO bn_api;
