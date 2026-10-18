#!/bin/bash
# Runs once on first DB start. Passwords come from compose secrets, never from env or git.
set -euo pipefail
pw() { tr -d '\n' < "/run/secrets/$1"; }

psql -v ON_ERROR_STOP=1 --username postgres <<SQL
CREATE ROLE bn_owner NOLOGIN;
CREATE ROLE bn_migrator LOGIN PASSWORD '$(pw db_migrator_pw)' IN ROLE bn_owner;
CREATE ROLE bn_ingest LOGIN PASSWORD '$(pw db_ingest_pw)';
CREATE ROLE bn_api    LOGIN PASSWORD '$(pw db_api_pw)';
CREATE ROLE bn_agent  LOGIN PASSWORD '$(pw db_agent_pw)';
CREATE DATABASE blacknaught OWNER bn_owner;
CREATE DATABASE blacknaught_test OWNER bn_owner;
SQL

for db in blacknaught blacknaught_test; do
  psql -v ON_ERROR_STOP=1 --username postgres --dbname "$db" <<SQL
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE $db FROM PUBLIC;
GRANT CONNECT ON DATABASE $db TO bn_ingest, bn_api, bn_agent, bn_migrator;
SQL
done
