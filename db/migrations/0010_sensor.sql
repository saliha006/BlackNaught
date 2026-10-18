SET search_path = bn;

-- Ahmed's simulator (F2) registers each sensor once, so heartbeats carry only sensor_id and the home link is stored once.
-- Anchors and controls watch a street, not a household, hence the CHECK.
CREATE TABLE sensor (
  sensor_id    text PRIMARY KEY,
  type         text NOT NULL CHECK (type IN ('home', 'anchor', 'control')),
  household_id uuid,
  cell_l1      text NOT NULL,
  CHECK ((type = 'home') = (household_id IS NOT NULL))
);
CREATE INDEX sensor_cell_idx ON sensor (cell_l1);

GRANT SELECT, INSERT, UPDATE ON sensor TO bn_ingest;
GRANT SELECT ON sensor TO bn_agent;
