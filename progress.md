# Blacknaught: progress log and conflict board

**Every builder, every prompt:** run `git fetch` and read only the entries that are new since you last checked, with `git diff HEAD..origin/main -- progress.md`. Look for any open `⚠️ Conflicts` line that names you. If you find one, tell your user, then agree a fix with the person who flagged it before you touch that area.

**When you merge to `main`:** append one entry in this format, newest at the bottom:

```
### <YYYY-MM-DD HH:MM> — <feature> — @<builder>
- Shipped: <what changed, why>
- Touched: <files / modules / endpoints / shared contracts>
- ⚠️ Conflicts: @<Name> — <what of theirs this changes or could break> | none
- Conflict status: open | resolved by @<Name> <date>
```

## Latest
- **The volatile facts live here only:** current commit, test counts, what's merged vs local-only, and the VM status.
- **As of 2026-10-17 22:40:**
  - `main`: ingest → register → triage → grading → audit → operator approvals, all live on the VM. 162 tests green on s390x, 98% coverage.
  - **VM:** reachable (s390x, z17 9175, NNPA flag present, Ubuntu 24.04.5, 3 vCPU / 7.8 GiB, 45 GB free). Docker 29.8 + Compose v5 installed; Jupyter (`notebook`) on :38888 with a custom token; IBM lab image pulled; backend stack `bn-backend` (postgres:17 + app) running.
  - All other docs stay local and are never pushed: the PRD, briefs, decisions and research.

---

### 2026-10-17 21:40 — repo scaffold — @sali
- Shipped: `.gitignore` keeps every doc local except `progress.md` and `README.md`. It also excludes data, models and secrets. Added this conflict board.
- Touched: `.gitignore`, `progress.md`
- ⚠️ Conflicts: @rama: the `Rama-Frontend` branch predates this `.gitignore`. Rebase on `main` before adding files, so docs and data don't get committed by accident.
- Conflict status: open

### 2026-10-17 21:50 — VM access for Sali — @sali
- Shipped: used the team key once to add Sali's own ed25519 public key to `linux1`'s `authorized_keys`; Sali now logs in with their own key (`ssh datathon`). Probe saved above. No other VM change.
- Touched: VM `~/.ssh/authorized_keys` (append only). Nothing removed.
- ⚠️ Conflicts: @ahmed: you own VM keys. Nothing of yours was changed, and the team key + your key are still there. Still yours: remove the leaked team key once everyone has their own, delete the Drive link, and change the portal password (it was in the form). Docker isn't installed yet; tell Sali if you want him to run HANDOFF §3.1.
- Conflict status: open

### 2026-10-17 22:15 — VM platform setup (Docker + Jupyter) — @sali
- Shipped: Docker CE 29.8 + Compose v5 on the VM (HANDOFF §3.1); `linux1` in the docker group. Jupyter container `notebook` on :38888 with a custom token (stored in `~/.secrets/jupyter_token`, mode 600; never in git or chat); iptables ACCEPT 38888, persisted via iptables-persistent. Pulled the IBM lab image (9.85 GB).
- Touched: VM packages, iptables, `~/shared`, `~/.secrets`
- ⚠️ Conflicts: @ahmed: this was your task 3, done so the team isn't blocked. Ask Sali for the token, or rotate it (`~/.secrets/jupyter_token`, then recreate `notebook`). Also: the lab image is **RHEL 10.2 with OpenSSL 3.5.5**, so ML-DSA and AES-GCM work inside `app` directly; a separate signer container may be unnecessary.
- Conflict status: open

### 2026-10-17 22:40 — backend foundation — @sali
- Shipped: pg8000 DB layer (one thread per connection, reconnect on dropped backends), migration runner with a drift guard, schema `bn` + roles (`bn_migrator`/`bn_ingest`/`bn_api`/`bn_agent`, API reads views only), append-only audit table, backend compose stack (`backend/compose.backend.yml`: postgres:17 + IBM lab image), `.gitattributes` forcing LF. 17 tests on s390x.
- Touched: `backend/`, `db/`, `.gitattributes`, `.gitignore`
- ⚠️ Conflicts: @ahmed: Postgres for the backend stack publishes only on 127.0.0.1:5432; your `/infra` compose should reuse `db/init` + `db/migrations` and the same secret names (`secrets/*`). @nate: the `prediction`/`triage_snapshot` tables assume the `predict()` shape in system-design-choices §7.
- Conflict status: open

### 2026-10-17 23:10 — contract freeze + API skeleton — @sali
- Shipped: FastAPI app (`backend/app/main.py`) serving every PRD §11 endpoint under `/api` from fixtures. Response models in `backend/app/schemas.py`; event envelope in `backend/app/events.py`. Generated `contracts/openapi.yaml` + `contracts/events.schema.json`; demo fixtures in `fixtures/api/`.
- Touched: `backend/app/*`, `contracts/*`, `fixtures/api/*` (shared)
- ⚠️ Conflicts: @rama: please ✅ the contract here before building against it (mock from `fixtures/api/*.json`). @ahmed: please ✅ `events.schema.json` (co-author); add kinds you need. @nate: `contracts/model.md` is still yours; triage expects `predict()` to return `quantiles{q50,q75,q90}` + `surv[24]` per system-design-choices §7.
- Conflict status: open

### 2026-10-17 22:09 — event pipeline — @sali
- Shipped: batching writer (`backend/app/writer.py`), event bus with critical/bulk queues (`bus.py`), sensor state tracker (`sensors.py`), per-source time parsing (`timeparse.py`). 60 tests on s390x.
- Touched: `backend/app/{writer,bus,sensors,timeparse}.py`
- ⚠️ Conflicts: @ahmed: your simulator should publish events through `EventBus.publish` (dicts shaped like `contracts/events.schema.json`); `SensorTracker.cell_counts()` is the quorum input for your combiner. Silence = dropout, never down.
- Conflict status: open

### 2026-10-17 22:17 — live grid ingest (F1) — @sali
- Shipped: pollers for UKPN, Northern Powergrid, SSEN (every 120 s) and Elexon (every 30 s) with retries, Retry-After and backoff; per-record validation (more than 50% bad = degraded); outage versioning with `vanished` after 2 missed polls (never `restored`); NPg rows merged by incident reference; postcodes.io cache; `/api/outages`, `/api/grids/gb/stress`, `/api/sources/health` and `/api/health` now live (workers start when `BN_WORKERS=1`). 103 tests on s390x, 98% coverage.
- Touched: `backend/app/{ingest/*,geocode,health,cells,stress,runtime,main}.py`, `fixtures/feeds/*` (recorded on the VM), `events.schema.json` (`dno_fault` gains `outage_id`)
- ⚠️ Conflicts: @rama: `/api/outages` is now live data; `scale` is an interim rule by customers affected until the combiner lands. @ahmed: `dno_fault` events now carry `outage_id`; `stress.state()` is a band rule; the interim scale rule lives in `main.footprint_scale` (both yours/Nate's to replace). @nate: ENWL + UKPN historic CSVs are downloading to `~/data/raw/` on the VM.
- Conflict status: open

### 2026-10-17 22:21 — field encryption + synthetic register — @sali
- Shipped: AES-256-GCM via libcrypto ctypes (`backend/app/crypto.py`, CPACF; NIST KATs pass on s390x), HMAC postcode blind index, `python -m app.seed` places synthetic patients on live fault postcodes (Ofcom 07700 900xxx numbers, `--two-houses <outage_id>` for the demo pair). Test suite now forced onto `blacknaught_test` (it had been using the main DB). 113 tests on s390x.
- Touched: `backend/app/{crypto,seed}.py`, `backend/tests/conftest.py`
- ⚠️ Conflicts: @ahmed: the DEK is read from `secrets/dek` for now; wrapping it with your signer's KEK is still open (PRD §14). @nate: device/reserve mix in `seed.DEVICES` uses PRD §2 ranges until your household distributions land; swap them in there.
- Conflict status: open

### 2026-10-17 22:23 — NPg time + customer fix — @sali
- Shipped: NPg `loggedtime` parsed as UK wall-clock (the feed mislabels BST as +00:00); customers fall back to `totalpredictedpowercut`; tests force `BN_WORKERS=0`. Live ingest now runs continuously on the VM (`compose.backend.yml`, `BN_WORKERS=1`). 115 tests on s390x.
- Touched: `backend/app/{timeparse,ingest/feeds}.py`, `backend/compose.backend.yml`, `backend/tests/*`
- ⚠️ Conflicts: none
- Conflict status: none

### 2026-10-17 22:32 — triage scorer (F5) — @sali
- Shipped: harm-hours triage (`backend/app/{survival,harm,triage}.py`), KM fallback fitted on the VM from 312,936 ENWL outages (`backend/models/km_enwl.json`, also in `evidence/`), live `/api/triage` with cursor paging, predictions logged for grading every 15 min, UKPN umbrella records with placeholder dates rejected, seeder only uses faults under 6 h old. 133 tests on s390x.
- Touched: `backend/app/*`, `db/migrations/0004_triage.sql`, `backend/models/km_enwl.json`
- ⚠️ Conflicts: @nate: triage calls `model.predict(elapsed_h)` and expects `{quantiles:{q50,q75,q90}, surv:[24]}`; swap `KmModel` for M2 behind the same shape (`app/triage.py`). @rama: `/api/triage` is live; `why` reasons are display-ready. @ahmed: the agent should read `v_triage_latest`; `decision_id` is null until your agent writes decisions.
- Conflict status: open

### 2026-10-17 22:34 — horizon grading (F7) — @sali
- Shipped: grader task (`backend/app/grading.py`) running every 60 s on the VM; evidence-based outcome rules (explicit restore → 0/1, still listed after the horizon → 1, otherwise censored with a reason); live `/api/agent/grades` with censoring bounds and an hourly trend. 146 tests on s390x.
- Touched: `backend/app/{grading,runtime,main}.py`, `db/migrations/0005_grading.sql`
- ⚠️ Conflicts: @ahmed: recalibration should read `v_grades` (UKPN rows are the trustworthy ones; `censored` rows carry a reason). @rama: `/api/agent/grades` is live.
- Conflict status: open

### 2026-10-17 22:37 — audit chain (task 13) — @sali
- Shipped: `backend/app/audit.py`: append (canonical JSON via `audit_append`), checkpoints every 500 rows / 5 min (signed when `BN_SIGNER_URL` is set, otherwise stored unsigned and reported as `sig_ok: null`), live `/api/audit/verify` that locates the first tampered row; model load is audited at boot. 153 tests on s390x.
- Touched: `backend/app/{audit,runtime,main,config}.py`
- ⚠️ Conflicts: @ahmed: the signer contract the backend calls is `POST /sign {purpose, payload_b64}` → `{alg, key_id, sig_b64}` and `POST /verify {payload_b64, sig_b64}` → `{ok}`. Set `BN_SIGNER_URL` for the app once it's up. Off-box publication of checkpoints is still yours.
- Conflict status: open

### 2026-10-17 22:40 — operator login + approvals (task 14) — @sali
- Shipped: argon2id operator login with server-side sessions (hash-only tokens, HttpOnly/SameSite=Strict cookie on /api, 30 min idle / 8 h absolute, lockout after 5 failures, per-IP rate limit), approval endpoint gated on the operator role with 409 for anything not awaiting approval, `decisions.create()` for the agent (escalate / draft_cap_alert / bulk_sms wait for approval), live `/api/agent/decisions`; decisions, approvals and logins are all audited. 162 tests on s390x.
- Touched: `backend/app/{auth,decisions,main}.py`, `db/migrations/0006_auth_decisions.sql`
- ⚠️ Conflicts: @ahmed: create agent decisions with `app.decisions.create(db_agent, tool, args, rationale)`; check `state` before acting on anything in `NEEDS_APPROVAL`. @rama: approvals need `POST /api/auth/login {login:'operator', passphrase}` first (cookie-based); the password is in the VM's `secrets/operator_pw`, ask Sali.
- Conflict status: open
