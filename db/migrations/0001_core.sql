CREATE SCHEMA bn AUTHORIZATION bn_owner;
SET search_path = bn;

CREATE TABLE schema_migrations (
  version int PRIMARY KEY,
  sha256 text NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE outage (
  outage_id         bigserial PRIMARY KEY,
  source            text NOT NULL CHECK (source IN ('ukpn','npg','ssen','sensor','replay')),
  source_ref        text NOT NULL,
  status            text NOT NULL CHECK (status IN ('active','restored','vanished','planned')),
  started_at        timestamptz NOT NULL,
  restored_at       timestamptz,
  restored_explicit boolean NOT NULL DEFAULT false,
  first_seen        timestamptz NOT NULL,
  last_seen         timestamptz NOT NULL,
  missed_polls      smallint NOT NULL DEFAULT 0,
  customers         int,
  priority_customers int,
  postcodes         text[] NOT NULL DEFAULT '{}',
  lat               double precision,
  lon               double precision,
  cell_l1           text,
  feeder            jsonb,
  label             text NOT NULL DEFAULT 'LIVE',
  content_hash      bytea NOT NULL,
  version           int NOT NULL DEFAULT 1,
  linked_outage_id  bigint REFERENCES outage,
  UNIQUE (source, source_ref)
);
CREATE INDEX outage_active_idx ON outage (status) WHERE status = 'active';
CREATE INDEX outage_postcodes_idx ON outage USING gin (postcodes);

CREATE TABLE outage_version (
  outage_id   bigint NOT NULL REFERENCES outage,
  version     int NOT NULL,
  observed_at timestamptz NOT NULL,
  raw         jsonb NOT NULL,
  PRIMARY KEY (outage_id, version)
);

CREATE TABLE freq_reading (
  grid        text NOT NULL DEFAULT 'gb',
  measured_at timestamptz NOT NULL,
  hz          numeric(6,3) NOT NULL,
  PRIMARY KEY (grid, measured_at)
);

CREATE TABLE sensor_transition (
  sensor_id text NOT NULL,
  at        timestamptz NOT NULL,
  state     text NOT NULL CHECK (state IN ('up','down','last_gasp','dropout')),
  cell_l1   text NOT NULL,
  label     text NOT NULL,
  PRIMARY KEY (sensor_id, at)
);

CREATE TABLE event_counts (
  minute  timestamptz NOT NULL,
  kind    text NOT NULL,
  n       int NOT NULL,
  dropped int NOT NULL DEFAULT 0,
  PRIMARY KEY (minute, kind)
);

CREATE TABLE source_poll (
  source      text NOT NULL,
  polled_at   timestamptz NOT NULL,
  ok          boolean NOT NULL,
  http_status int,
  n_records   int,
  latency_ms  int,
  error       text,
  PRIMARY KEY (source, polled_at)
);

CREATE TABLE postcode_geo (
  postcode       text PRIMARY KEY,
  lat            double precision,
  lon            double precision,
  lsoa           text,
  admin_district text,
  valid          boolean NOT NULL,
  fetched_at     timestamptz NOT NULL
);

CREATE TABLE ingest_reject (
  id         bigserial PRIMARY KEY,
  at         timestamptz NOT NULL DEFAULT now(),
  source     text,
  source_ref text,
  error      text,
  raw        jsonb
);

-- Synthetic register only (Marist ToU §9): the CHECK makes real rows impossible to insert.
CREATE TABLE patient (
  patient_id    uuid PRIMARY KEY,
  household_id  uuid NOT NULL,
  cell_l1       text NOT NULL,
  postcode_bidx bytea NOT NULL,
  contact_ct    bytea NOT NULL,
  device        text NOT NULL,
  flow_lpm      numeric,
  reserve_h     numeric NOT NULL CHECK (reserve_h >= 0),
  other_backup  boolean NOT NULL,
  severity      smallint NOT NULL CHECK (severity BETWEEN 1 AND 5),
  synthetic     boolean NOT NULL DEFAULT true CHECK (synthetic)
);
CREATE INDEX patient_bidx_idx ON patient (postcode_bidx);

CREATE TABLE prediction (
  pred_id      bigserial PRIMARY KEY,
  outage_id    bigint NOT NULL REFERENCES outage,
  made_at      timestamptz NOT NULL,
  elapsed_h    real NOT NULL,
  model_id     text NOT NULL,
  model_sha256 text NOT NULL,
  horizon_h    smallint NOT NULL CHECK (horizon_h IN (2,4)),
  p_still_off  real NOT NULL CHECK (p_still_off BETWEEN 0 AND 1),
  quantiles    jsonb NOT NULL,
  UNIQUE (outage_id, made_at, horizon_h, model_id)
);

CREATE TABLE grade (
  pred_id   bigint PRIMARY KEY REFERENCES prediction,
  graded_at timestamptz NOT NULL,
  outcome   smallint CHECK (outcome IN (0,1)),
  censored  boolean NOT NULL,
  reason    text NOT NULL,
  brier     real
);

CREATE TABLE triage_snapshot (
  tick_at    timestamptz NOT NULL,
  patient_id uuid NOT NULL REFERENCES patient,
  outage_id  bigint NOT NULL REFERENCES outage,
  rank       int NOT NULL,
  harm       real NOT NULL,
  q_used     text NOT NULL,
  q_hours    real NOT NULL,
  escalate   boolean NOT NULL,
  why        jsonb NOT NULL,
  model_id   text NOT NULL,
  PRIMARY KEY (tick_at, patient_id, outage_id)
);

CREATE TABLE decision (
  decision_id uuid PRIMARY KEY,
  created_at  timestamptz NOT NULL,
  tool        text NOT NULL,
  args        jsonb NOT NULL,
  state       text NOT NULL CHECK (state IN ('auto_done','awaiting_approval','approved','rejected','exported','expired')),
  approver    text,
  decided_at  timestamptz,
  rationale   jsonb,
  audit_seq   bigint
);

CREATE TABLE agent_memory (
  key        text PRIMARY KEY,
  value      jsonb NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE cap_alert (
  decision_id uuid PRIMARY KEY REFERENCES decision,
  identifier  text UNIQUE NOT NULL,
  xml         text NOT NULL,
  sig_b64     text,
  created_at  timestamptz NOT NULL
);
