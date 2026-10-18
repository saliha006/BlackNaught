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

## Headline (changed 2026-10-18)
**Blacknaught predicts blackouts before they happen and protects the people they'd hurt most.**
- **Predict**, with honest lead times:
  1. district fault risk for tomorrow (hours to days);
  2. homes most likely to lose power in the next 30 min, from fuse-box/meter sensors (minutes; real Accra data: 1 in 5 top alerts come true, 9× chance);
  3. grid-wide stress (seconds).
- **Protect:** triage + alerts for electricity-dependent people.
- **Never pitch:** "predicts every blackout", "minutes ahead from frequency" or "voltage dips warn of blackouts".

## Start here (teammates, first 15 minutes)
1. **GitHub:** accept the collaborator invite for `saliha006/BlackNaught` (check your email or github.com/notifications). Then:
   ```bash
   git clone https://github.com/saliha006/BlackNaught.git && cd BlackNaught
   git config user.email "<the email on YOUR GitHub account>"   # judges read who committed
   git config core.hooksPath scripts/git-hooks                   # blocks AI co-author trailers on commits
   git config blacknaught.builder <sali|ahmed|nate|rama>         # who you are; publish-context.sh refuses without it
   ```
2. **Shared docs, kept in sync automatically:** from your clone's root run `bash scripts/sync-context.sh`.
   - It unpacks the team docs from the `context` branch (never committed to `main`):
     - `CLAUDE.md`;
     - `BLACKNAUGHT.md` (NOW, spec, backend design, Parked);
     - `DATATHON-CONTEXT.md`;
     - your `builder-file-<name>.md`;
     - `.claude/skills/`;
     - the research ledger + IBM handoff.
   - From then on, **your Claude re-syncs at the start of every prompt** (a CLAUDE.md rule) and tells you what changed.
   - Only Sali publishes doc changes, except your own finished-task move: `bash scripts/publish-context.sh "what changed"`.
   - ⚠ The repo is public; `context` is deleted before submission.
3. **VM access:** run `ssh-keygen -t ed25519` if you have no key, and send **only** `~/.ssh/id_ed25519.pub` to Sali. Then connect with `ssh linux1@148.100.78.95`.
4. **Things that live only on the VM** (read them there; never paste them in chat or commit them):

   | What | Where on the VM |
   |---|---|
   | Jupyter token | `~/.secrets/jupyter_token` |
   | Operator login password | `~/BlackNaught/secrets/operator_pw` |
   | Demo household logins | `~/BlackNaught/backend/secrets/households.txt` |
   | Training data | `~/data/raw/` |

5. **Rama, live API on your laptop:** the API listens only inside the VM until Ahmed's nginx edge is up, so tunnel to it:
   ```bash
   ssh -N -L 8000:localhost:8000 linux1@148.100.78.95
   ```
   Then use `http://localhost:8000/api/docs` and `http://localhost:8000/stream`.
   - Without VM access, mock from `fixtures/api/*.json`. These are validated against the live response models; they include `cap_alert_sample.xml` and `stream_sample.txt`.
6. **One stack:** `infra/docker-compose.yml` runs Sali's `backend/compose.backend.yml` (project `bn-backend`: `postgres:17` + `app`) plus Ahmed's signer; edge and Granite join it next.
   - Deploy and restart with that file only. An `up` from `backend/` takes the signer settings back off `app`.
   - In a `~/work/<name>` clone, use only `run --rm` (below): the project name is the live stack's, so an `up` there would swap your clone's code into the live app.
7. **Nate:** the model interface the backend calls is `contracts/model.md`. ⚠ The feature list for M2 is an open item to agree with Sali.

## Who owns what
Ask the owner before changing their area, and flag them in `⚠️ Conflicts` if you touch it. Full task lists are in each person's brief (`builder-file-<name>.md`, shared on Discord), not on GitHub.

| Who | Role | Branch | Owns (paths / pieces) | How the rest plugs into it |
|---|---|---|---|---|
| **Sali** `saliha006` | Backend; repo + docs owner | `sali-backend` | `/backend`, `/db`, `contracts/openapi.yaml`. Ingest, triage, grading, audit chain, operator login + approvals, SSE `/stream`, k≥11 map, area-risk baseline, CAP export, `/me/home`, IODA. **Status: brief tasks 1–20 done and live on the VM** | Everything is served under `/api/*` (docs at `/api/docs`) |
| **Ahmed** `meep-boop` | Platform + agent; **VM owner** | `ahmed-platform` | `/infra` (team compose, nginx edge with PQ TLS, LUKS), `/agent` (agent loop, evidence combiner), signer (ML-DSA), sensor simulator, Granite, NNPA serving, VM keys + portal restarts | Agent creates decisions with `app.decisions.create()`; signer contract `POST /sign`, `POST /verify` (set `BN_SIGNER_URL`); simulator publishes events per `contracts/events.schema.json` |
| **Nate** `aldrichbanas07` | Data + ML | `nate-ml` | `/ml`, `grids/*.yaml`, `contracts/model.md`. M2 duration model, **M8 weather fault risk (prediction layer 1)**, **home-sensor early-warning model (layer 2; start from `backend/app/probe_precursor.py`)**, M4 grid stress (layer 3), LR table, evaluation numbers | M2 replaces `KmModel` behind `predict(elapsed_h) → {quantiles, surv[24]}`; M8 replaces `arearisk.area_risk()`; data in `~/data/raw/` on the VM |
| **Rama** `rama0623` | Frontend; video edit lead | `Rama-Frontend` | `/frontend` (Vite + TS + MapLibre): map, triage list, two-houses card, agent panel, audit view, CAP/SMS previews, "my home"; screen recordings + video edit | Builds against the live `/api/*` + `/stream` (mocks in `fixtures/api/`); `dist/` is served by Ahmed's nginx |

**Shared** (anyone may edit; flag it): `contracts/*`, `fixtures/*`, `docker-compose.yml`.

## How we work (read once)
**GitHub:**
- Code and push from your **own laptop**, as yourself: `git config user.email` must be your GitHub email, because judges read the history.
- Each person has their own branch: `sali-backend`, `nate-ml`, `Rama-Frontend`, `ahmed-platform`.
- **Per feature:**
  1. Check this board.
  2. Code and test.
  3. `git push origin <your-branch>`.
  4. `git merge origin/main` into your branch and re-test, fixing conflicts there (agree with the owner if it's their code).
  5. Merge to `main`.
  6. Add an entry below. Flag anyone whose files or contracts you touched with `⚠️ Conflicts: @name`.
- **Log every completed task here,** not just merges: who (@name), date + time, what. Push it to `main` straight away.
- **Shared docs** (CLAUDE.md, `BLACKNAUGHT.md`, `DATATHON-CONTEXT.md`, briefs, research ledger) are **never** committed to `main`. Every edit is published to the `context` branch with `bash scripts/publish-context.sh "what changed"`, and everyone's agent pulls it on its next prompt.
- **Docs** (PRD, briefs, design notes) are git-ignored and shared on Discord/Drive. Only this file and `README.md` live on GitHub.

**LinuxONE VM** (`ssh linux1@148.100.78.95`, with your own SSH key):
- **Never log into GitHub on the VM.** It's one shared `linux1` user. The VM only **pulls**.
- **`~/BlackNaught`** is the **deploy copy**, always on `main`, and it runs the live app.
  - Don't edit code there.
  - After a merge to `main`: `cd ~/BlackNaught && git pull --ff-only && sudo docker compose -f infra/docker-compose.yml restart app`. When a compose file changed, use `up -d` with the same `-f`.
  - Say so in Discord first.
- **`~/work/<name>`** is your own clone for testing your branch on real s390x. One-time setup:
  ```bash
  git clone https://github.com/saliha006/BlackNaught.git ~/work/<name> && cd ~/work/<name> && git checkout <your-branch>
  ln -sfn ~/BlackNaught/secrets ~/work/<name>/secrets && ln -sfn ~/data ~/work/data   # compose needs ../secrets and ../../data/raw
  ```
  Then test with `cd backend && sudo docker compose -f compose.backend.yml run --rm --no-deps -e BN_WORKERS=0 app pytest -o addopts="" -q`.
  - The test DB is shared and reset per run, so **one person tests at a time**.
- **Jupyter** is at `http://148.100.78.95:38888` (token from Sali; never in screenshots).
  - Files go in `~/shared`.
  - Training data is in `~/data/raw/` (ENWL 312,936 + UKPN IIS 316,435, with SHA256SUMS).
- **Evidence:** `bash ~/BlackNaught/scripts/proof.sh` rewrites `evidence/`. The training notebook is at Jupyter → `shared/blacknaught/train_on_linuxone.ipynb`.

## Latest
- **The volatile facts live here only:** current commit, test counts, what's merged vs local-only, and the VM status.
- **As of 2026-10-18 08:02:**
  - `main`: full backend live on the VM + home-sensor probe; 222 backend tests green on s390x, 96% coverage; frontend 141 tests, 92%. Live UI: https://148-100-78-95.sslip.io:8443 (proof.sh re-run 05:10). README for judges is live.
  - **VM:** reachable (s390x, z17 9175, NNPA flag present, Ubuntu 24.04.5, 3 vCPU / 7.8 GiB, 45 GB free). Docker 29.8 + Compose v5 installed; Jupyter (`notebook`) on :38888 with a custom token; IBM lab image pulled; backend stack `bn-backend` (postgres:17 + app) running.
  - Shared docs (CLAUDE.md, `BLACKNAUGHT.md`, briefs, research) live on the `context` branch, never on `main`.

---

### 2026-10-17 21:40 — repo scaffold — @sali
- Shipped: `.gitignore` keeps every doc local except `progress.md` and `README.md`. It also excludes data, models and secrets. Added this conflict board.
- Touched: `.gitignore`, `progress.md`
- ⚠️ Conflicts: @rama: the `Rama-Frontend` branch predates this `.gitignore`. Rebase on `main` before adding files, so docs and data don't get committed by accident.
- Conflict status: resolved by @rama 2026-10-18 (main merged into Rama-Frontend; its .gitignore now matches main)

### 2026-10-17 21:50 — VM access for Sali — @sali
- Shipped: used the team key once to add Sali's own ed25519 public key to `linux1`'s `authorized_keys`; Sali now logs in with their own key (`ssh datathon`). Probe saved above. No other VM change.
- Touched: VM `~/.ssh/authorized_keys` (append only). Nothing removed.
- ⚠️ Conflicts: @ahmed: you own VM keys. Nothing of yours was changed, and the team key + your key are still there. Still yours: remove the leaked team key once everyone has their own, delete the Drive link, and change the portal password (it was in the form). Docker isn't installed yet; tell Sali if you want them to run HANDOFF §3.1.
- Conflict status: key part resolved by @sali 2026-10-18 (leaked key removed); Drive link + portal password still open with @ahmed

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

### 2026-10-17 22:42 — SSE stream (task 15) — @sali
- Shipped: `GET /stream` (sse-starlette) with outage, triage, grade, source_health, audit_checkpoint and stats events; per-client bounded queues with drop-oldest + resync, Last-Event-ID replay from a 2,000-message ring, 50-viewer cap, 15 s ping, `X-Accel-Buffering: no`. 169 tests on s390x.
- Touched: `backend/app/{sse,runtime,main,triage,grading,bus}.py`, `backend/app/ingest/poller.py`
- ⚠️ Conflicts: @rama: `new EventSource('/stream')`; on `resync` refetch the REST endpoints; `triage` events only carry counts, so refetch `/api/triage` on them. @ahmed: nginx needs `proxy_buffering off` + `proxy_read_timeout 1h` on `/stream` (system-design-choices §14).
- Conflict status: open

### 2026-10-17 22:44 — SSE id fix — @sali
- Shipped: SSE event ids are strings (sse-starlette rejected ints and the stream crashed on its first event, caught on the VM); tests now encode every message with `ServerSentEvent`. Live check: stats + triage events streaming, 0 errors. 169 tests on s390x.
- Touched: `backend/app/sse.py`, `backend/tests/test_sse.py`
- ⚠️ Conflicts: none
- Conflict status: none

### 2026-10-17 22:47 — k≥11 map cells (task 16) — @sali
- Shipped: `backend/app/suppression.py` (primary + complementary suppression across L1/L2/L3, banding from 20), `cellpub.py` publishing every 15 min into `cell_snapshot`, live `/api/cells?level=1..3` with bounds and the worst active outage scale per cell; no bbox/point queries. Property test over 500 random trees. 174 tests on s390x.
- Touched: `backend/app/{suppression,cellpub,main,runtime}.py`, `db/migrations/0007_cells.sql`
- ⚠️ Conflicts: @rama: `/api/cells` is live; `patients` is an int or "suppressed", and `bounds` is a closed [lat,lon] ring. Never draw homes; only these cells.
- Conflict status: open

### 2026-10-17 22:49 — /areas/risk baseline (task 17) — @sali
- Shipped: `backend/app/arearisk.py`: per-district, per-month fault rates fitted on the VM from ENWL 1997–2026 (`backend/models/climatology_enwl.json`); `/api/areas/risk?date=` (default tomorrow, UK) returns expected faults and P(≥3) labelled `BASELINE`. New `BASELINE` label in the contract. 178 tests on s390x.
- Touched: `backend/app/{arearisk,main,schemas,config}.py`, `backend/models/climatology_enwl.json`, `contracts/*`
- ⚠️ Conflicts: @nate: M8 replaces `arearisk.area_risk(model, day)` (same output shape: district, expected, p_ge_k); your Brier skill should be measured against this climatology. @rama: risk is per ENWL district name (12 districts), not per cell yet.
- Conflict status: open

### 2026-10-17 22:52 — CAP 1.2 export (parked task 18) — @sali
- Shipped: `backend/app/cap.py` (CAP 1.2 builder: status Exercise, convex-hull polygon or circle, outward codes only, no Z timestamps), export on approval in `decisions.export_cap` (built once, signed when `BN_SIGNER_URL` is set, audited), `GET /api/alerts/cap/{id}` (403 until approved). Tests validate against the official OASIS CAP-v1.2.xsd (`backend/tests/data`). 185 tests on s390x.
- Touched: `backend/app/{cap,decisions,main,config}.py`, `db/migrations/0008_cap.sql`, `backend/tests/data/CAP-v1.2.xsd`
- ⚠️ Conflicts: @ahmed: your `draft_cap_alert` tool should call `decisions.create(db, 'draft_cap_alert', {outage_id, headline, description, instruction}, rationale)`; headline text from Granite is capped at 140 chars. @rama: preview the XML from `/api/alerts/cap/{decision_id}` after approval.
- Conflict status: open

### 2026-10-17 22:55 — /me/home (parked task 19) — @sali
- Shipped: `GET /api/me/home` (household session only, no id parameter; power state via the postcode blind index, own reserve clock, next action, frequency context, never an ETA), `me_home_patients()` SECURITY DEFINER function, `python -m app.seed --households N` (passphrases written only to the VM's git-ignored `backend/secrets/households.txt`), `/api/health` now reports the loaded model. 188 tests on s390x.
- Touched: `backend/app/{home,main,seed}.py`, `db/migrations/0009_me_home.sql`
- ⚠️ Conflicts: @rama: `/api/me/home` needs a household login (`home-1..3` on the VM; ask Sali for passphrases). `voltage` stays empty until @ahmed's sensor simulator feeds households.
- Conflict status: open

### 2026-10-17 22:58 — IODA wide-area signal (parked task 20) — @sali
- Shipped: `backend/app/ingest/ioda.py`: ping-slash24 dip detector (latest 2 windows below 0.9× the trailing 2 h median; calibrated on the real Sri Lanka 9 Feb 2025 blackout, recorded as a fixture), control countries FR/DE/US to discard IODA-wide artifacts (≥3 countries at once), polled every 10 min; dips go to the bus (`ioda_signal`) and SSE (`ioda`). 194 tests on s390x.
- Touched: `backend/app/ingest/{ioda,sources}.py`, `backend/app/runtime.py`, `fixtures/feeds/ioda_lk_blackout.json`
- ⚠️ Conflicts: @ahmed: `ioda_signal` events (region = ISO country, value = ratio) are the wide-area input for your evidence combiner's region/system scale.
- Conflict status: open

### 2026-10-18 02:01 — LinuxONE evidence + training notebook — @sali
- Shipped: `scripts/proof.sh` writes `evidence/01–06_*.txt` (platform s390x/9175/NNPA, all containers s390x, training logs, 194 tests on s390x, live service incl. 150 graded UKPN predictions with Brier 0.186 at 2 h, audit verify, 401 without login, NIST AES-GCM, roles, firewall); `notebooks/train_on_linuxone.ipynb` executed in Jupyter on the VM. Triage reason wording fix.
- Touched: `evidence/`, `scripts/proof.sh`, `notebooks/`, `backend/app/harm.py`
- ⚠️ Conflicts: @ahmed @rama: `bash ~/BlackNaught/scripts/proof.sh` re-captures everything for the proof slide; the notebook is at Jupyter → `shared/blacknaught/train_on_linuxone.ipynb`.
- Conflict status: open

### 2026-10-18 02:25 — VM deploy copy reset to main + team workflow — @sali
- Shipped: the VM's `~/BlackNaught` was a stale `sali-backend` checkout with synced, untracked files. It's now a clean checkout of `main` tracking `origin/main`, so `git pull` works there. Before switching, every untracked file was checked against `main` (103 identical). `secrets/`, `backend/secrets/` and the live app were kept; the app was restarted healthy. Added "How we work" at the top of this file.
- Touched: VM `~/BlackNaught` (git state only), `progress.md`
- ⚠️ Conflicts: @ahmed @nate @rama: use `~/BlackNaught` only as the deploy copy (pull + restart), and clone `~/work/<name>` for your own testing. @ahmed: Nate's and Rama's SSH keys still need adding.
- Conflict status: open

### 2026-10-18 02:36 — team onboarding fixes — @sali
- Shipped:
  - "Start here" section above;
  - `scripts/git-hooks/commit-msg` (blocks AI co-author trailers; enable it with `git config core.hooksPath scripts/git-hooks`);
  - `contracts/model.md` (the backend's model interface);
  - `fixtures/api/cap_alert_sample.xml` + `stream_sample.txt` (all fixtures checked against the live response models);
  - `contracts/*.md` is now allowed in git.
  - The docs bundle (CLAUDE.md, briefs with dated status updates, PRD, design doc, skills, research, handoff; scanned, no secrets) is going out on Discord.
- Touched: `progress.md`, `.gitignore`, `contracts/model.md`, `fixtures/api/*`, `scripts/git-hooks/`
- ⚠️ Conflicts:
  - @nate: `contracts/model.md` is your file, drafted from the backend side; the M2 live-feature list is open with Sali.
  - @ahmed: build edge, signer and granite into the running `bn-backend` stack (no second Postgres); agree it with Sali.
  - @rama: merge `origin/main` into `Rama-Frontend` (42 commits behind).
  - All: the freeze time in your briefs predates the team starting; Sali will confirm a new one.
- Conflict status: open

### 2026-10-18 03:01 — individual SSH keys on the VM — @sali
- Shipped: added labelled keys for `ahmed`, `nate` and `rama` to `linux1`'s `authorized_keys` (backed up first). Test with `ssh linux1@148.100.78.95 "hostname; uname -m"` → `datathon4musketeers s390x`.
- Touched: VM `~/.ssh/authorized_keys` (append only)
- ⚠️ Conflicts:
  - @ahmed: once all three of you confirm you can log in, the leaked `Generated-by-Nova` key gets removed. Also: turn off the Drive link and change the portal password. Is the unlabelled key `SHA256:2rIcU3uJ…MHHI` yours? If nobody claims it, it goes too.
  - @rama: your key was labelled from its `G.R.P.Bhaskara2@newcastle.ac.uk` comment; say if that's wrong.
- Conflict status: resolved by @sali 2026-10-18 (see the next entry)

### 2026-10-18 03:09 — leaked shared VM key removed — @sali
- Shipped: removed the leaked `Generated-by-Nova` key (the `DatathonKey1.pem` from the Drive link) and one unlabelled key nobody claimed from `linux1`'s `authorized_keys`.
  - The VM now accepts only individual keys: `006saliha@gmail.com`, `ahmed`, `nate`, `rama`.
  - Verified: the old `.pem` gets `Permission denied`, and individual keys log in. SSH log confirms Sali, Ahmed and Nate.
  - Backup on the VM: `~/.ssh/authorized_keys.bak-20261018020911`.
- Touched: VM `~/.ssh/authorized_keys`
- ⚠️ Conflicts:
  - @rama: your key is installed but hasn't logged in yet. Run `ssh linux1@148.100.78.95 "hostname; uname -m"`; if it's refused, resend your public key to Sali.
  - @ahmed: still yours: **turn off the Drive link** to the `.pem` and **change the L1CC portal password** (both were in the form). If the removed unlabelled key was yours, you don't need it, since your labelled key works.
  - Anyone still using the old `.pem`: it no longer works; use your own key.
- Conflict status: open

### 2026-10-18 04:02 — home-sensor precursor probe — @sali
- Shipped: `backend/app/probe_precursor.py` run on the VM over a real Accra GridWatch week: own-sensor model ROC AUC 0.668, PR AUC 0.089 (4.2× base), top-1% alerts 19.7% true (9.3× the 2.1% base); district context adds a little (0.684); low voltage alone ≈ chance (0.514). Evidence in `evidence/07_precursor_probe.txt`; no-leakage tests. 198 tests on s390x.
- Touched: `backend/app/probe_precursor.py`, `backend/tests/test_probe_precursor.py`, `evidence/07_precursor_probe.txt`; VM `~/data/raw/accra/` (7 days, identifying columns removed)
- ⚠️ Conflicts: @nate: this is the starting point for the home-sensor layer of the new headline (see your brief); stripped Accra data is in `~/data/raw/accra/` on the VM. @rama @ahmed: the headline is now 'predict blackouts before they happen + protect the most vulnerable'. Pitch layer 2 as 'flags the homes most likely to lose power in the next 30 min (1 in 5 top alerts, 9× chance)', never 'predicts every blackout'.
- Conflict status: open

### 2026-10-18 04:24 — docs merged + `context` branch auto-sync — @sali
- Shipped:
  - **Docs consolidated:**
    - `BLACKNAUGHT.md` = NOW (decisions in force, pending, active tasks) + Part A spec (was the PRD) + Part B backend design (§B1–§B21) + Parked + History;
    - `DATATHON-CONTEXT.md` = rules, judging, what wins, why Blacknaught.
  - **Archived (local `_archive/`):** off-vision material, i.e. other ideas' plans and research §7–§8.
  - **New `context` branch** (docs only) + `scripts/sync-context.sh` (pull, report changes) + `scripts/publish-context.sh` (publish, refuses to clobber newer edits or credentials).
  - **CLAUDE.md** now makes every agent sync at the start of every prompt.
- Touched: `scripts/sync-context.sh`, `scripts/publish-context.sh`, `progress.md`; new branch `context`
- ⚠️ Conflicts: @ahmed @nate @rama: run `bash scripts/sync-context.sh` once in your clone (after `git pull` on `main`). Your briefs now point at `BLACKNAUGHT.md`; old `BLACKNAUGHT-PRD.md` / `system-design-choices.md` copies on your machine are stale, so delete them.
- Conflict status: open

### 2026-10-18 04:28 — rule: publish every doc edit + log every task — @sali
- Shipped:
  - **CLAUDE.md now requires:** any edit to a shared doc is published to `context` in the same turn (so every agent gets it next prompt); shared docs never go to `main`.
  - **Every completed task** gets a `progress.md` entry with name, date and time, pushed to `main` straight away.
  - Published to `context`.
- Touched: `progress.md` ("How we work"); `CLAUDE.md` on `context`
- ⚠️ Conflicts: @ahmed @nate @rama: your agents follow this from their next sync. Log your finished tasks here.
- Conflict status: open

### 2026-10-18 04:42 — briefs brought in line with the new rules — @sali
- Shipped:
  - **All four briefs** now say: sync `context` first on every prompt; log **every** finished task here (name, date, time) and push to `main` straight away; publish doc edits with `scripts/publish-context.sh`, never to `main`.
  - **Sali's brief:** new prioritised ▶ Current tasks block (unblock team → submission blockers → risk-level feature → freeze + evidence → pitch + submit). Build tasks 1–20 kept below as done.
  - Published to `context` (deb0d7a).
- Touched: `builder-file-{sali,ahmed,nate,rama}.md` on `context`; `progress.md` (Latest)
- ⚠️ Conflicts: @ahmed @nate @rama: your brief changed; your agent picks it up on its next sync. No task of yours changed.
- Conflict status: open

### 2026-10-18 04:54 — team blockers cleared — @sali
- Shipped:
  - **GitHub:** `meep-boop`, `aldrichbanas07`, `rama0623` all have Write access.
  - **Team name chosen; Sali is the registered team leader**, so Sali submits.
  - **IBM labs 01 + 02** done by @ahmed (his task 5 ✅).
  - **#helpdesk NNPA-timing question** handed to @ahmed (added to his brief).
  - New freeze time: deferred, Sali decides later.
- Touched: briefs (Sali, Ahmed) + `BLACKNAUGHT.md` NOW on `context` (54f8f79)
- ⚠️ Conflicts: @ahmed: new task in your brief (ask #helpdesk, post the answer here).
- Conflict status: open

### 2026-10-18 05:07 — VM ML checks: GO (brief task 3) — @nate
- Shipped:
  - `ml/vm_checks.py`, run in the Jupyter `notebook` container on the VM. All GO:
    - XGBoost `survival:aft` and `count:poisson` train;
    - XGBoost JSON and `.keras` round-trips give identical predictions on s390x;
    - `ibm-zdnn-plugin` 2.3.0 kernels load;
    - pandas 3.0.6 handles ENWL-shaped data.
  - Output: `evidence/08_ml_stack_checks.txt`. Both files are on `nate-ml` (17fda21), **not merged**.
  - VM: `~/work/nate` (tests) and `~/shared/nate` (Jupyter) track `nate-ml`. Raw data is hard-linked into `~/shared/nate/data/` (git-ignored, no extra disk, SHA256 OK).
  - **Decision (Nate): M2 uses live fields only** (start time, customers affected, voltage with "unknown"). The full ENWL whitelist (cause, primary substation, district) is an offline benchmark only if time allows. The exact list goes into `contracts/model.md`.
- Touched: `ml/vm_checks.py`, `evidence/08_ml_stack_checks.txt` (both on `nate-ml`); VM `~/work/nate`, `~/shared/nate`
- ⚠️ Conflicts:
  - @sali:
    - **M2 features (above):** `triage.py` will need to pass `features` into `predict(features, elapsed_h)`, as `contracts/model.md` already says.
    - **Bug in your Elexon ingest:** Elexon published 182 readings of **0 Hz** on 2026-08-06, 11:13–12:54 UTC. `parse_elexon` stores whatever arrives, and `stress.state(0)` returns EMERGENCY, so a repeat during the demo shows a false GB emergency. Dropping readings outside 45–55 Hz fixes it.
    - **Doc accuracy:**
      - UKPN IIS's 316,435 rows are restoration stages (180,059 incidents), not outages.
      - My brief's `predict()` return (`p_exceeds_reserve, eta_h, interval`) differs from `contracts/model.md` (`quantiles, surv[24]`). I'm following `model.md`.
      - My brief §5 "waiting on" lines are all done.
  - @ahmed: the zDNN plugin adds **no TF device** (`list_physical_devices()` shows only CPU); check for `_z_ops.so` instead. No NNPA benchmark run, pending your #helpdesk answer (ToU §5).
- Conflict status: resolved by @sali 2026-10-18 (Sali's part)


### 2026-10-18 05:07 — event contract frozen (task 6) — @ahmed
- Shipped: ✅ `contracts/events.schema.json` as it stands. All seven kinds are there, plus `source_state`; the `sim` and `accra_replay` sources and the `SIMULATED` / `REPLAY` labels cover the simulator and the Accra replay.
  - Decision (Ahmed): a sensor's type (home, anchor or control) and the link from a home sensor to its enrolled household go in a new `sensors` table, not in event payloads. Heartbeats stay small (about 5k a minute), and the home link is stored once.
- Touched: nothing (the contract is unchanged)
- ⚠️ Conflicts:
  - @sali: 📨 Ahmed needs a `sensors` table in `/db` before F2 (the simulator): `sensor_id` (PK), `type` (home, anchor or control), `household_id` (null for anchors and controls), `cell_l1`. Your migration and naming; tell Ahmed if you'd shape it differently.
  - @nate: event payloads don't change; read a sensor's type from that table.
- Conflict status: resolved by @sali 2026-10-18 (Sali's part)


### 2026-10-18 05:10 — compose layout chosen (task 7) — @ahmed
- Shipped: decision (Ahmed): `infra/docker-compose.yml` will `include:` `backend/compose.backend.yml`, keep the project name `bn-backend`, and add `edge`, `signer` and `granite`. The running db, app and `pgdata` volume carry on as they are: no second Postgres, and your compose file stays yours. Nothing gets built until you agree.
- Touched: nothing yet
- ⚠️ Conflicts: @sali: 📨 please OK this layout (your 02:36 ask). Once it lands, the VM deploy becomes `cd ~/BlackNaught && sudo docker compose -f infra/docker-compose.yml up -d`, and `restart app` takes the same `-f`.
- Conflict status: resolved by @sali 2026-10-18 (Sali's part)

### 2026-10-18 05:12 — commit-msg hook now runs on Mac and Linux — @ahmed
- Shipped: `scripts/git-hooks/commit-msg` was committed without its executable bit (mode 100644), so git on Mac and Linux skipped it silently and AI trailers got through there. It's 100755 now; Windows behaves as before.
- Touched: `scripts/git-hooks/commit-msg` (file mode only)
- ⚠️ Conflicts: @sali: your hook, mode change only. @nate @rama: on Mac or Linux, `git pull` and the hook starts working.
- Conflict status: open

### 2026-10-18 05:15 — secret scan before every commit (task 1, part) — @ahmed
- Shipped: `scripts/git-hooks/pre-commit` runs gitleaks on staged changes and blocks a commit that adds something that looks like a secret. The repo is public, so this is the last point where a leak can still be stopped. Without gitleaks it only warns. `scripts/test-git-hooks.sh` runs real commits through both hooks in a throwaway repo: 4/4 pass.
- Touched: `scripts/git-hooks/pre-commit` (new), `scripts/test-git-hooks.sh` (new)
- ⚠️ Conflicts: @sali @nate @rama: your next commit runs this hook (you already use `scripts/git-hooks`). Install gitleaks for the scan: `winget install Gitleaks.Gitleaks` or `brew install gitleaks`. A false positive: add its `Fingerprint` line to `.gitleaksignore`.
- Conflict status: open

### 2026-10-18 05:15 — new task for Ahmed: public alert broadcast, mocked — @ahmed
- Shipped: decision (Ahmed, from a team idea): Ahmed adds an Amber-alert-style public alert. For the demo it's a mock: an operator-approved CAP alert reaches Ahmed's Android phone (developer settings on). The sending side sits behind a channel interface, so a government alerting service can replace the phone later.
- Touched: nothing yet
- ⚠️ Conflicts:
  - @sali: 📨 please add this to Ahmed's brief and NOW. It reuses your CAP 1.2 export and the operator approval (CAP alerts already need a human OK).
  - @rama: the phone receiving the alert could be a shot in the video.
  - Pitch wording: "Blacknaught drafts standard CAP 1.2 alerts that a government alerting service can broadcast; in the demo a phone stands in for that channel." Not "we send alerts to the public".
- Conflict status: resolved by @sali 2026-10-18 (Sali's part)

### 2026-10-18 05:15 — README for judges + fresh evidence — @sali
- Shipped:
  - **`README.md`** rewritten for judges and senior devs: problem, what it does, triage + architecture + outage-lifecycle diagrams (Mermaid), why LinuxONE, live results (grades, Accra probe), data + licences, stack, how to run, endpoints, what went wrong, limits, team, open-source list.
  - **Evidence re-run** with `scripts/proof.sh` on the VM (05:10): 198 tests / 96%, 5 sources LIVE, audit chain OK. `evidence/01–06` refreshed.
  - **Decision (Sali): home dashboard = option C** (Low / Elevated / High headline + three layer gauges). Rules still being confirmed.
  - **Team name: The 4 Musketeers**; Sali is team leader and submits.
- Touched: `README.md`, `evidence/01–06_*.txt`; `BLACKNAUGHT.md` NOW, briefs (Sali, Rama), `DATATHON-CONTEXT.md`, CLAUDE.md on `context`
- ⚠️ Conflicts:
  - @rama: option C changes the "my home" view (badge + three gauges); spec in your brief. The `risk` field lands in `/api/me/home` after the rules are confirmed.
  - @ahmed @nate @rama: the README's Team row, status and "Known limits" describe your parts as in progress. Update your row when your part lands on `main`.
  - @ahmed: seen your `sensors` table + compose layout asks; Sali is answering next. @nate: seen the Elexon 0 Hz bug; fix queued.
- Conflict status: open

### 2026-10-18 05:31 — publish-context.sh can undo other people's edits — @ahmed
- Shipped: nothing; this is a bug report. Ahmed's 05:08 publish put back an old copy of Nate's brief and wiped Nate's 05:07 Done-log move. Sorry, Nate, and thanks for restoring it at 05:28.
  - Why: the script publishes every shared doc from your local copies, and it only refuses when a file changed both on `context` and locally. A file someone else changed since your last sync, that you didn't touch, silently goes back to your stale copy. A doc someone added that you haven't synced yet gets dropped the same way.
  - Fix: start from the current `context` tree and replace only the files you changed locally, keeping the both-changed refusal.
- Touched: nothing
- ⚠️ Conflicts:
  - @sali: 📨 it's your script. OK for Ahmed to make that fix, or would you rather? Until then Ahmed syncs right before each publish and checks the published commit against its parent.
  - @nate @rama: same risk on your publishes until it's fixed; sync just before you publish.
- Conflict status: resolved by @sali 2026-10-18 (Sali's part)

### 2026-10-18 05:31 — signer design chosen (task 9) — @ahmed
- Shipped: decisions (Ahmed), now being built on `ahmed-platform`:
  - The ML-DSA-65 key is a file in `secrets/`, like the stack's other secrets, made once by a script that never overwrites it. It never goes in git, an image or an env var.
  - `/sign` needs a per-caller token, and the signer sits on a private network shared only with `app` and the agent. `/verify` stays open, since checking a signature can't forge one.
- Touched: nothing yet
- ⚠️ Conflicts: @sali: 📨 `HttpSigner` will need to send `Authorization: Bearer <token>`, read from a new secret `signer_token_app`, and `app` needs `BN_SIGNER_URL=http://signer:8100`. Nothing changes before then: `BN_SIGNER_URL` is unset, so checkpoints stay unsigned as today. The exact contract lands in `contracts/signer.md` with the signer.
- Conflict status: open

### 2026-10-18 05:31 — mock alert channel chosen — @ahmed
- Shipped: decision (Ahmed): the mock public alert reaches Ahmed's phone over ADB from his laptop (USB debugging on), not by SMS. No third-party app, no texts from a SIM, no real phone numbers.
- Touched: nothing yet
- ⚠️ Conflicts: @sali: 📨 for Ahmed's brief, with the alert task (05:15 entry).
- Conflict status: resolved by @sali 2026-10-18 (Sali's part)

### 2026-10-18 05:34 — context publish can no longer undo teammates' edits (fix on `nate-ml`) — @nate
- Shipped:
  - **Found:** Ahmed's 05:08 publish (`683d4e9`) silently restored an old copy of Nate's brief, undoing Nate's 05:06 Done-log move.
    - Not Ahmed's fault. `publish-context.sh` uploads **every** shared doc from the publisher's local copy, and only refuses when both sides edited the same file. So any stale copy overwrites newer work.
    - Nate's move is re-applied and republished (`65983dd`, Nate's brief only).
  - **Fix on `nate-ml` (`5f4f727`), for @sali to review and merge:**
    - Publish starts from what's on `context` and sends only the files you changed since your last sync. Stale copies can't overwrite anything, and docs added after your sync are kept.
    - Unless `git config blacknaught.builder` is `sali`, publish refuses any change except your own `builder-file-<name>.md`.
    - Sync copies an unpublished local edit to `.git/context-backup/` before replacing it, instead of silently overwriting it.
    - Both scripts set `MSYS_NO_PATHCONV=1`, because Git Bash on Windows mangles `rev:.claude/...` arguments.
    - `scripts/test-context-scripts.sh` replays tonight's clobber on a throwaway remote: the current scripts **fail** it, the fixed ones **pass**.
  - **Proposed CLAUDE.md rule (§2a).** CLAUDE.md is Sali's, so please publish it if you agree:
    > **Only Sali edits more than one brief, and nobody wipes another builder's entries.** `scripts/publish-context.sh` enforces the first part: unless `git config blacknaught.builder` is `sali`, it refuses any change except your own `builder-file-<name>.md`. For the second part, anyone tidying a brief for consistency (Sali included) syncs first, then only adds, annotates or moves items. Never delete or reword another builder's task, Done-log line or status note; superseded items go to Archived with the reason. If publish refuses because a file changed on both sides, re-sync (your copy is saved in `.git/context-backup/`), re-apply your edit on top and publish again, keeping every line from the other side.
- Touched: `scripts/publish-context.sh`, `scripts/sync-context.sh`, `scripts/test-context-scripts.sh` (on `nate-ml`); `builder-file-nate.md` on `context`
- ⚠️ Conflicts:
  - @sali:
    - **Your scripts:** please review and merge `5f4f727`. After the merge, everyone runs `git config blacknaught.builder <name>` once (publish refuses until it's set); please add that line to "Start here" step 1.
    - **Security:** the credential guard in `publish-context.sh` (unchanged by me) seems to contain fragments of real credentials, in a public repo. Rotate those or match on shape instead.
  - @ahmed: your 05:08 publish restored an old copy of Nate's brief. That's the script bug, not you. Until the fix lands, sync right before you publish.
- Conflict status: resolved by @sali 2026-10-18 (Sali's part)

### 2026-10-18 05:42 — Elexon 0 Hz readings dropped — @sali
- Shipped: `parse_elexon` drops readings outside 45–55 Hz, so a repeat of the 6 Aug run of 0 Hz can't show a fake GB emergency. Test added. Found by @nate.
- Touched: `backend/app/ingest/feeds.py`, `backend/tests/test_ingest.py`
- ⚠️ Conflicts: none
- Conflict status: resolved

### 2026-10-18 05:42 — `sensor` table for the simulator — @sali
- Shipped: migration `0010_sensor.sql`, applied on the VM. `sensor_id` PK, `type` (home / anchor / control), `household_id` (required for home sensors only, CHECK), `cell_l1`. Named `sensor` to match `patient`, `freq_reading`. `bn_ingest` reads + writes, `bn_agent` reads.
- Touched: `db/migrations/0010_sensor.sql`
- ⚠️ Conflicts: @ahmed: this is the table you asked for (05:07), singular name. @nate: read a sensor's type from it.
- Conflict status: resolved by @ahmed 2026-10-18

### 2026-10-18 05:42 — home risk level in `/api/me/home` (option C) — @sali
- Shipped: a `risk` block: `level` (low / elevated / high / unknown), `reason`, and three `layers` (home 30 min, area tomorrow, grid now) with source, horizon and updated time. Rules: High = home flagged or grid EMERGENCY; Elevated = area in the top third or grid STRESSED; Low only when all three layers report; otherwise unknown. Grid older than 5 min counts as no data. Live on the VM; reads "unknown" until the home model is served. 208 tests green on s390x.
- Touched: `backend/app/home.py`, `backend/app/schemas.py`, `contracts/openapi.yaml` (`MyHome.risk`), `backend/tests/test_home.py`
- ⚠️ Conflicts: @rama: new field in `/api/me/home`, spec in your brief (task 12). @nate: your home-sensor model fills the home layer.
- Conflict status: open

### 2026-10-18 05:42 — context publish fix adopted + credential guard cleaned — @sali
- Shipped: merged @nate's context scripts (only files you changed are published; teammates can publish only their own brief; sync backs up unpublished edits). The credential guard now matches the shape of a secret; it used to contain fragments of real ones in this public repo.
- Touched: `scripts/publish-context.sh`, `scripts/sync-context.sh`, `scripts/test-context-scripts.sh`; "Start here" step 1
- ⚠️ Conflicts:
  - @ahmed @nate @rama: run `git config blacknaught.builder <name>` once, or publish refuses.
  - @ahmed: **urgent:** the fragments are still in git history. Change the portal password and turn off the Drive link.
- Conflict status: open

### 2026-10-18 05:42 — README tightened, diagrams fixed — @sali
- Shipped: README is about a third shorter; both Mermaid diagrams validated with mermaid-cli, so they render on GitHub.
- Touched: `README.md`
- ⚠️ Conflicts: none
- Conflict status: resolved

### 2026-10-18 05:42 — briefs synced with progress — @sali
- Shipped: Ahmed's brief gets the mocked public alert task, the compose OK and the `sensor` table. Nate's brief gets the Elexon and publish-fix outcomes. **Rama's brief is reorganised by backend coverage:** 13 features he must show, each with its endpoint, and his own design choices kept. CLAUDE.md now says every logged task is also marked ✅ in its brief.
- Touched: all four briefs, `BLACKNAUGHT.md` NOW, CLAUDE.md on `context` (d87b07b)
- ⚠️ Conflicts: @rama: please push your frontend work to `Rama-Frontend` and mark what's done in your brief; right now nobody can see it.
- Conflict status: resolved by @rama 2026-10-18 06:05 (frontend pushed to Rama-Frontend and merged to main)

### 2026-10-18 05:46 — M2 contract settled + ENWL/UKPN prep (brief tasks 2 and 4) — @nate
- Shipped:
  - **`contracts/model.md`: M2 features final (option A1).**
    - Inputs: start hour, weekday and month (Europe/London); log(1 + customers); voltage LV/HV/unknown.
    - Trained on ENWL only; UKPN is the cross-operator test, never trained on.
    - Voltage is hidden on a third of training rows, so UKPN's missing voltage gets a trained answer.
    - The backend passes `{started_at, customers, feeder}` straight from the `outage` row; the model maps them.
    - Training-data facts corrected: UKPN's rows are restoration stages, and ENWL's label caveat is written down.
  - **`ml/prep.py`, run on the VM** (`evidence/train_log_prep.txt`):
    - Both sources cut at 5 min. UKPN stages are rolled into incidents. ENWL is split 2000–22 / 2023 / 2024–26, with storms kept whole.
    - ENWL: 306,251 kept (train 269,170 · validate 9,828 · test 27,253; median 3.5 h). UKPN: 178,864 kept (median 2.8 h).
    - 5 tests pass on s390x, 83% coverage (the rest is the CLI entry).
- Touched: `contracts/model.md`, `ml/prep.py`, `ml/tests/test_prep.py`, `evidence/train_log_prep.txt`; VM `~/shared/nate/data/prepared/`
- ⚠️ Conflicts: @sali: the M2 feature list in `contracts/model.md` is final. When M2 lands, `Scorer` needs to pass `{started_at, customers, feeder}` into `predict(features, elapsed_h)`. I'll ping again when the model itself is ready.
- Conflict status: open


### 2026-10-18 05:55 — ML-DSA-65 signer on main, not wired yet (task 9, part 1) — @ahmed
- Shipped: `signer/` (Python standard library + OpenSSL 3.5 on `python:3.13-slim-trixie`): `POST /sign` with a per-caller token, `POST /verify`, `GET /health`, as `contracts/signer.md` describes. 29 tests, 97% coverage, green on s390x (OpenSSL 3.5.7). On the VM the production container signed, verified, and refused a request without a token. `scripts/make-signer-secrets.sh` makes the key and the two tokens once and never overwrites them.
  - The first push to `main` (30fdbc9) went out with a test failing about 1 run in 3 on Windows, because a check was skipped. Cause: some requests were refused before their body was read, so the OS reset the connection and the caller saw an error instead of the 401 or 404. Fixed in 19e4cdf with a regression test; 0 failures in 10 runs since.
- Touched: `signer/` (new), `contracts/signer.md` (new), `scripts/make-signer-secrets.sh` (new)
- ⚠️ Conflicts: @sali: 📨 the signer contract you were waiting for is `contracts/signer.md`.
  - For the app: `HttpSigner` sends `Authorization: Bearer <secrets/signer_token_app>`, and `app` gets `BN_SIGNER_URL=http://signer:8100` plus that secret. Land both together: `Checkpointer.maybe_checkpoint` raises today if signing fails, so a missing token would stop checkpoints. Your call whether a failed signing should store the checkpoint unsigned instead.
  - `HttpSigner.sign` labels CAP signatures `purpose: "audit_checkpoint"` too. Only the log label is off, since purpose isn't signed.
- Conflict status: open

### 2026-10-18 05:58 — M1 baselines and both M2 models trained on the VM (brief tasks 5–7) — @nate
- Shipped:
  - `ml/m2.py`, plus `ml/notebooks/m2_duration.ipynb` executed in Jupyter on the VM (also at Jupyter → `shared/nate-runs/m2_duration.ipynb`). Scores are in `evidence/m2_metrics.json`.
  - **ENWL 2024–26** (27,253 outages). Integrated Brier over 24 h (lower is better), against the live KM stand-in's 0.121:
    - KM per cause: 0.109, C-index 0.64. Best, but cause isn't live.
    - XGBoost AFT: 0.114, C 0.60 (Brier at 2 h 0.223 vs 0.233).
    - Hazard MLP: 0.117.
    - Log-linear: 0.122 (no gain).
  - **UKPN cross-check** (178,864 outages, never trained on), against KM's 0.138: AFT 0.149 (7% worse), MLP 0.141 (2% worse), log-linear 0.139.
  - **What it means:** the live fields carry little signal and cause carries the most. Trained on ENWL, M2 doesn't transfer to UKPN without recalibration.
  - README "Results" and "Limits" updated to say exactly this.
  - Artifacts stay on the VM (not in git): `~/shared/nate-runs/models/m2_aft.json` and `m2_hazard.keras`.
  - **Not done yet:** the brief's 5-prediction laptop spot-check (this laptop has no XGBoost/TF), and NNPA timing (waiting on #helpdesk, ToU §5).
- Touched: `ml/m2.py`, `ml/tests/test_m2.py` (10 tests pass on s390x), `ml/make_m2_notebook.py`, `ml/notebooks/m2_duration.ipynb`, `evidence/m2_metrics.json`, `README.md` (my rows)
- ⚠️ Conflicts:
  - @sali: **don't wire M2 into triage yet.** On UKPN, where most live grades come from, it scores worse than KM. Nate is choosing the next step. README edits are limited to the M2 results block and the duration limit line.
  - @ahmed: the Keras hazard model is at `~/shared/nate-runs/models/m2_hazard.keras` for signing and NNPA, but it isn't meant to be served yet (see above).
- Conflict status: open


### 2026-10-18 06:00 — M2 served behind the contract, recalibrated on UKPN (brief task 8) — @nate
- Shipped:
  - `ml/m2_serve.py`: `M2Model.predict(features, elapsed_h)` → `{quantiles, surv[24]}`, worked out in closed form from the AFT model's log-normal (conditional on time already off). `label = REAL`; one JSON artifact (`load()` hashes it for `sha256`). 6 tests, 16 in all pass on s390x.
  - Recalibrated on UKPN Apr 2021–Mar 2024 (134,193 outages), tested on Apr 2024–Mar 2025 (44,671). Log: `evidence/train_log_m2_serve.txt`.
  - **Result: still not better than KM on UKPN.** Integrated Brier: calibrated M2 0.143, KM (live) 0.131. The live fields can't rank UKPN outages (C-index 0.50), so recalibration can't fix it. On ENWL 2024–26 M2 still wins (0.116 vs 0.121).
  - Side finding: KM refitted on UKPN 2021–24 beats today's ENWL KM on that holdout year (0.130 vs 0.131; Brier at 2 h 0.249 vs 0.256).
  - Artifact on the VM: `~/shared/nate-runs/models/m2_aft_ukpncal_v1.json` (not in git). README "Results" updated.
- Touched: `ml/m2_serve.py`, `ml/tests/test_m2_serve.py`, `evidence/train_log_m2_serve.txt`, `README.md` (M2 results line)
- ⚠️ Conflicts: @sali: M2 is ready to load but **still shouldn't replace KM live**. Nate is deciding what (if anything) changes in triage. If it's wired later, `ml/` isn't mounted in the app container (only `backend/`), so loading it needs a mount or a copy; to agree first.
- Conflict status: open

### 2026-10-18 06:05 — app wired to the signer — @sali
- Shipped: `HttpSigner` sends the bearer token from `signer_token_app` on `/sign` and a purpose per call (`audit_checkpoint`, `cap_alert`), per `contracts/signer.md`. Tested on the VM against Ahmed's signer image with a throwaway key: sign OK, verify OK, tampered → false, wrong token → 401. Off until `BN_SIGNER_URL` is set. 208 tests green.
- Touched: `backend/app/audit.py`, `backend/app/decisions.py`, `backend/app/runtime.py`, `backend/tests/test_audit.py`
- ⚠️ Conflicts: @ahmed: to switch it on, your infra compose gives `app` `BN_SIGNER_URL=http://signer:8100`, the `signer_token_app` secret and the signer's network (details in your brief).
- Conflict status: resolved by @ahmed 2026-10-18

### 2026-10-18 06:05 — triage passes M2's live features — @sali
- Shipped: `Scorer` sends `{started_at, customers, feeder}` into `predict(features, elapsed_h)` as `contracts/model.md` settles. KM ignores them, so live output is unchanged.
- Touched: `backend/app/triage.py`, `backend/app/survival.py`, `backend/tests/test_triage.py`
- ⚠️ Conflicts: @nate: M2 still needs a loader the backend can call (`load(path)` → object with `predict`, `model_id`, `sha256`, `label`); proposal in your brief.

### 2026-10-18 06:05 — VM login + frontend pushed (brief tasks 1–2) — @rama
- Shipped: VM login works with Rama's key (`ssh linux1@148.100.78.95 "uname -m"` → `s390x`). The frontend is on `Rama-Frontend` and merged to `main`; `git config blacknaught.builder rama` is set.
- Touched: `Rama-Frontend`, `main`
- ⚠️ Conflicts: none
- Conflict status: none

### 2026-10-18 06:05 — frontend: map, landing page, control panel (brief tasks 3, 7, 9; 6 and 8 partly) — @rama
- Shipped, one commit per feature on `Rama-Frontend`:
  - **Map (task 3):** Vite + TS + MapLibre 3D night-city map. Outages by scale as light beams with a sensor sweep on the operator's centroid (never a home), k≥11 cells, and an outage list. Outages with no location yet stay in the list, marked, with no marker: the contract allows a null `centroid`, `customers`, `priority_customers` and `cell_l1`, and the live feed sends them.
  - **Landing page:** the simple public entry. "Open the live map" dives into the most urgent outage; Back and the browser's back button return to it.
  - **Control panel toggles:** operators, escalations only (from triage), map layers, live updates. They filter the map, the list and the charts together.
  - **Predict strip (task 7):** area tomorrow (BASELINE), homes in the next 30 min ("not served yet", with the Accra probe result), grid now (LIVE).
  - **Analysis rail:** outage length against 312,936 ENWL outages; prediction accuracy with graded count, Brier trend and Brier by operator and horizon (task 8, grading half); tomorrow's risk per district; feed health with a status per feed (task 9).
  - **Live updates (task 6, partly):** `/stream` refetches only what changed, at most once a second per kind, and shows events/s. No ping animation yet.
  - Rama's design calls: dark monochrome with colour only for severity, IBM Plex; map plus analysis rail; hand-built SVG charts (no chart library), each with a table view.
- Touched: `frontend/` (new). Reads `/api/outages`, `/cells`, `/triage`, `/agent/grades`, `/areas/risk`, `/grids/gb/stress`, `/sources/health` and `/stream`. No backend or contract changes.
- ⚠️ Conflicts:
  - @sali: two live-data oddities for ingest: an SSEN fault reports `priority_customers` 28 with `customers` 18, and one NPg fault has been listed active for 619 h.
  - @ahmed: `npm run build` makes a live `dist/` for the edge. The app calls `/api/*` and `/stream` on the same origin.
- Conflict status: open

### 2026-10-18 06:10 — live KM curve refitted on UKPN, ready to drop in (decision C) — @nate
- Shipped:
  - **Decision (Nate): live triage keeps a Kaplan–Meier model, with its curve refitted on UKPN's own outages.** Option C: M2 stays offline because it loses to KM on UKPN, where most live grades come from.
  - `ml/artifacts/km_ukpn.json` (`m1-km-ukpn`), built with the backend's own `survival.fit`, so `survival.load` reads it unchanged. 178,864 UKPN outages, Apr 2021–Mar 2025.
  - Faster restorations than ENWL: S(1 h) 0.794 vs 0.823, S(4 h) 0.404 vs 0.448. An outage 1 h old now gets q50 3.1 h (was 3.5 h).
  - **Measured gain:** fitted on UKPN 2021–24 and tested on Apr 2024–Mar 2025, integrated Brier is 0.1297 vs ENWL KM's 0.1311, and Brier at 2 h is 0.249 vs 0.256. The shipped curve refits on all four years.
  - Log: `evidence/train_log_km_ukpn.txt`. Code: `ml/km_refit.py` (+ test; 17 in all pass on s390x).
  - Checked: `triage.py` now passes `{started_at, customers, feeder}`, which matches `contracts/model.md`, so `ml/m2_serve.py` can load later without changes.
- Touched: `ml/km_refit.py`, `ml/tests/test_km_refit.py`, `ml/artifacts/km_ukpn.json`, `evidence/train_log_km_ukpn.txt`
- ⚠️ Conflicts:
  - @sali: 📨 please swap the live curve when you're ready:
    1. copy `ml/artifacts/km_ukpn.json` to `backend/models/km_ukpn.json`;
    2. set `BN_MODEL_PATH=/srv/models/km_ukpn.json` for `app`;
    3. restart (say so in Discord).
    - Caveat: it also scores NPg and SSEN outages, which have no history of their own. Grades will show `m1-km-ukpn` separately from `m1-km-enwl`, side by side.
- Conflict status: resolved by @sali 2026-10-18 (Sali's part)

### 2026-10-18 06:14 — two-houses card (brief task 4) — @rama — done
- Shipped: the demo centrepiece floats bottom-left of the map. It picks the highest-ranked fault where one patient escalates and another only gets an SMS check (concentrator and ventilator first) and shows both: backup left, expected case, the range the decision used, verdict and `why` lines, all SIMULATED. "Show on map" flies to the fault. With no such pair it says so rather than faking one.
- Touched: `frontend/` only (`twoHouses.ts`, `devices.ts`, `main.ts`, styles). Reads `/api/triage`.
- ⚠️ Conflicts:
  - @sali: 📨 Rama needs the two-houses pair seeded on a fresh live fault (`python -m app.seed --two-houses <outage_id>`). Live triage right now has 45 patients on 3 faults, and every one escalates, so the card shows its empty state.
- Conflict status: resolved by @sali 2026-10-18 (Sali's part)

### 2026-10-18 06:17 — frontend fixes: Escalate contrast + escaped API strings — @rama — done
- Shipped: the red Escalate pill now uses near-black text (5.3:1; white was 3.7:1, under AA). Source, device, scale and status names from the API are escaped before they go into HTML templates, so a feed can't inject markup.
- Touched: `frontend/src/{styles.css,format.ts,landing.ts,outageList.ts}` and tests
- ⚠️ Conflicts: none
- Conflict status: none

### 2026-10-18 06:22 — audit checkpoints are signed on the live stack (task 7 part 1, task 9 wiring) — @ahmed
- Shipped: the VM now runs `infra/docker-compose.yml`, deployed after a Discord heads-up. Sali's `db` and `app` carry on as before (same Postgres container and data). `signer` sits on an internal network shared only with `app`, with no published port and a read-only filesystem. `app` gets `BN_SIGNER_URL` and its token, and waits for a healthy signer. The first signed checkpoint was seq 109 at 05:20 UTC: `/api/audit/verify` shows `sig_ok: true` (signer `key_id` bda7ac1f8fd6c9d2). `infra/test-compose.sh` checks that boundary: 8/8.
- Touched: `infra/docker-compose.yml`, `infra/signer.yml`, `infra/test-compose.sh` (new); VM `~/BlackNaught/secrets/signer_*` (new, 0600); README run commands, "Start here" step 6, the "How we work" deploy line
- ⚠️ Conflicts: @sali @nate @rama: deploy and restart with `-f infra/docker-compose.yml` from now on, because an `up` from `backend/` turns signing off. In `~/work/<name>` clones use only `run --rm`. @sali: your 06:05 ask is done.
- Conflict status: resolved by @sali 2026-10-18 (Sali's part)

### 2026-10-18 06:32 — home-sensor early warning (layer 2), served model on the VM — @nate
- Shipped:
  - `ml/home_sensor.py` reuses Sali's probe features on the Accra week. Days 1–4 train, day 5 calibrates the probability and sets the "elevated" threshold (top 1% by raw score), days 6–7 test, with a 5-run bootstrap over sensors.
  - **Test result:** flags 0.96% of home-windows; **18.8% ± 1.1% of flagged homes lose power within 30 min, 8.9× the 2.1% base rate**. ROC AUC 0.666 ± 0.005. This backs the headline "1 in 5, 9×" with the served model. README updated.
  - Artifact on the VM: `~/shared/nate-runs/models/home_sensor_accra_v1.json` (one JSON file; isotonic calibration stored as breakpoints, so no sklearn is needed to serve). `score(window)` → `{"p_off_30min", "value": "elevated" | "normal"}`, where `window` holds the probe's feature names (`probe_precursor.OWN`).
  - 20 tests pass on s390x. Log: `evidence/train_log_home_sensor.txt`.
- Touched: `ml/home_sensor.py`, `ml/tests/test_home_sensor.py`, `evidence/train_log_home_sensor.txt`, `README.md` (home-sensor results)
- ⚠️ Conflicts:
  - @sali: `home.risk()` can take the home layer from this model: `"elevated"` / `"normal"`, which fits your `headline()`. It needs a per-home feature window from a sensor stream; Accra replay homes have one, GB demo homes only once the simulator feeds them.
  - @ahmed: (1) the Accra replay can score each home with `score()`; the feature code is `probe_precursor.features`. (2) **Brief task 9 (LR table + household distributions) is deferred** because time is short (brief fallback order: M2 → layer 2 → M8 → M4). For now the simulator keeps `seed.DEVICES` (PRD §2 backup hours; the device shares are assumptions), and the combiner should use the quorum rule with LR = 1 for anything unlisted.
- Conflict status: open

### 2026-10-18 06:39 — live duration curve swapped to UKPN's — @sali
- Shipped: Nate's `m1-km-ukpn` curve copied to `backend/models/km_ukpn.json`, `BN_MODEL_PATH` set for `app`, deployed with `infra/docker-compose.yml`. `/api/health` reports `m1-km-ukpn`; signing stays on (`sig_ok: true`). Test checks the live curve is the UKPN one. README says which curve is live and why.
- Touched: `backend/models/km_ukpn.json`, `backend/compose.backend.yml`, `backend/tests/test_triage.py`, `README.md`
- ⚠️ Conflicts: @nate: grades now come in under `m1-km-ukpn` next to `m1-km-enwl`.
- Conflict status: resolved

### 2026-10-18 06:39 — seed can add just the two-houses pair; pair live — @sali
- Shipped: `python -m app.seed --per-outage 0 --two-houses <id>` used to insert nothing. Fixed + test (210 green). Pair seeded on live UKPN fault 133: the oxygen concentrator (2.6 h left) escalates on q75, the ventilator (13.6 h) gets an SMS check on q50.
- Touched: `backend/app/seed.py`, `backend/tests/test_crypto_seed.py`; VM DB (2 synthetic patients)
- ⚠️ Conflicts: @rama: your card now has a pair to show.
- Conflict status: resolved

### 2026-10-18 06:39 — Sali covers the frontend while Rama's Claude usage is out — @sali
- Shipped: `Rama-Frontend` synced with `main` (0 behind / 0 ahead; nothing of Rama's was left unmerged). Checked his work: `npm test` 111/111, 89.7% lines covered, `npm run build` passes. Sali continues Rama's brief §3 on `Rama-Frontend`, keeping his design choices; open rows: 5, 6, 8, 10, 11, 12, 13, then 14–16.
- Touched: `Rama-Frontend` (merge only); briefs (Rama, Sali, Nate, Ahmed), `BLACKNAUGHT.md` NOW, CLAUDE.md on `context` (c00938f)
- ⚠️ Conflicts: @rama: when you're back, sync and read entries from here on before continuing; your brief has a note at the top. @ahmed: frontend / nginx `dist/` questions go to Sali for now.
- Conflict status: open


### 2026-10-18 06:43 — public HTTPS edge with post-quantum TLS on LinuxONE (task 7 part 2, task 17 part 1) — @ahmed
- Shipped: `edge` (nginx 1.26.3 on `debian:trixie`, OpenSSL 3.5.7) in `infra/docker-compose.yml`, live at **https://148.100.78.95:8443**. TLS 1.3 offers `X25519MLKEM768` first, with classic X25519 for older clients. It serves the UI (`frontend/dist`, built from `main`) and proxies `/api` and `/stream`; the stream is unbuffered with a 1 h timeout. It looks the app up per request, so the edge survives an app restart. Checked from outside: a client offering only the post-quantum group gets TLS 1.3 (`evidence/09_edge_pq_tls.txt`); the UI, `/api/health` and `/stream` all work through it. The dry run created only `edge`, so app, db and signer were not restarted.
  - The certificate is **self-signed** for now (decision, Ahmed: self-signed first, then Let's Encrypt for `148-100-78-95.sslip.io` as an upgrade), so browsers warn once.
- Touched: `infra/edge/` (new), `infra/docker-compose.yml`, `infra/test-compose.sh` (10/10), `scripts/make-edge-cert.sh` (new), `evidence/09_edge_pq_tls.txt`; VM `~/BlackNaught/secrets/edge_*.pem`, `~/BlackNaught/frontend/dist`
- ⚠️ Conflicts: @sali: the public demo entry is live. After a frontend change, rebuild `dist` (`npm run build`) and copy it to `~/BlackNaught/frontend/dist` on the VM; nginx serves it without a restart. If the Let's Encrypt upgrade works, the demo URL can become `https://148-100-78-95.sslip.io:8443`, which changes a NOW decision, so you'd mirror it there.
- Conflict status: open

### 2026-10-18 06:50 — M8 weather fault risk trained on the VM (brief task 11, prediction layer 1) — @nate
- Shipped:
  - `ml/m8.py`: each area's training-years average for that month, × a weather effect learned by XGBoost Poisson from Open-Meteo ERA5 history (gusts, rain, temperature, snow) at the area's centre. Trained 2010–22, validated 2023, tested 2024–26. History starts in 2010 because Open-Meteo's free tier rate-limits long downloads.
  - **Test 2024–26:** P(≥3 faults), Brier 0.1993 vs climatology 0.2101 = **+5.1% skill** (2023: +3.4%).
  - **Storm Éowyn** (Cumbria, 24 Jan 2025, 226 faults): M8 expected 27, climatology 7.6. 21–22 Jan 2024: 22–26 vs 7.6. It still under-calls extremes.
  - **Data finding:** ENWL redrew its northern districts in 2024. Penrith, Workington, Barrow and Lancaster took territory from Carlisle and Kendal (Carlisle: 1,437 faults in 2023 → 7 in 2025). M8 merges these into one "Cumbria" with continuous history, so it covers 7 areas, not 12.
  - `area_risk(day)` returns the same `{district, expected, p_ge_k}` items and fetches tomorrow's Open-Meteo forecast live. Artifact: `~/shared/nate-runs/models/m8_weather_enwl_v1.json` (VM).
  - 24 tests pass on s390x. Log: `evidence/train_log_m8.txt`. README updated.
- Touched: `ml/m8.py`, `ml/tests/test_m8.py`, `evidence/train_log_m8.txt`, `README.md` (area-risk row, results, limits)
- ⚠️ Conflicts:
  - @sali:
    - **The live baseline has the district-split bug.** `arearisk.fit` averages 1997–2026 by district name, so Penrith and Workington look low-risk and Carlisle looks risky when it barely exists now.
    - **To serve M8:** `/api/areas/risk` would call `ml.m8.load(path).area_risk(day)` (forecast fetched live; label `LIVE`). `ml/` isn't mounted in `app`, so it needs a mount or a copy; to agree.
  - @rama: M8's areas are Ashton, Blackburn, Bolton, Cumbria, Manchester, Preston, Stockport. "Cumbria" replaces the six northern names.
- Conflict status: open

### 2026-10-18 06:49 — edge has a trusted certificate; new demo URL (task 17 done) — @ahmed
- Shipped: a Let's Encrypt certificate for `148-100-78-95.sslip.io` is live on the edge, so browsers no longer warn. Checked from outside: `Verify return code: 0 (ok)` together with `Negotiated TLS1.3 group: X25519MLKEM768` (`evidence/09_edge_pq_tls.txt`). It was tried against Let's Encrypt's staging service first, then issued for real and installed with an nginx reload (no downtime). Port 80 was opened only for the check and is closed again. The self-signed files are kept as `secrets/edge_*.selfsigned.pem`.
  - The certificate lasts until 2027-01-16 and won't auto-renew (port 80 stays closed), which is fine for the event.
- Touched: VM `~/BlackNaught/secrets/edge_cert.pem` + `edge_key.pem`, certbot installed on the VM host; `evidence/09_edge_pq_tls.txt`
- ⚠️ Conflicts: @sali: 📨 **the demo URL is now https://148-100-78-95.sslip.io:8443** (decision, Ahmed). The old https://148.100.78.95:8443 still answers but shows a certificate warning, since the certificate names the hostname. Please mirror it in NOW and the README, and Rama's recordings should use it.
- Conflict status: open

### 2026-10-18 07:10 — M4 grid stress replay on NESO 1-s data (brief task 12, prediction layer 3) — @nate
- Shipped:
  - `ml/m4.py`: a rule, not a trained model. It warns when frequency is below 49.8 Hz and, at the last 5 s rate of fall, would reach LFDD (48.8 Hz) within 60 s × fragility (GB = 1). The thresholds were committed (`9efd852`) before the replay was scored.
  - **9 Aug 2019** (NESO 1-s): LFDD at 16:53:49 BST. The M4 rule and live STRESSED (< 49.8) both warn at 16:52:35, which is **74 s** ahead. Live EMERGENCY (< 49.5) warns at 16:52:38, 71 s ahead.
  - **False alarms over Oct 2025 – Sep 2026** (12 months, 8,760 h of 1-s data, no LFDD, lowest reading 49.594 Hz): STRESSED fires **11.1 times a month**, EMERGENCY **0**, M4 **0.4** (5 in the year).
  - **Honest read:** M4 gains 3 s over the live EMERGENCY band and costs 5 false alarms a year, so **the live band rule stays** and `stress.py` is unchanged. The lead exists only on 1-s data: Elexon's live 15 s feed, about 1.5 min late, would show red after LFDD. It is one event.
  - 30 tests pass on s390x. Log with the data hashes: `evidence/train_log_m4.txt`. README updated (layer row, results table, data row, limit).
- Touched: `ml/m4.py`, `ml/tests/test_m4.py`, `evidence/train_log_m4.txt`, `README.md`. NESO files are on the VM in `~/shared/nate/data/neso/` (git-ignored).
- ⚠️ Conflicts: @sali: none in code. One fact for NOW and the pitch: **"74 seconds of warning on 9 Aug 2019, from 1-second data; the live band rule matches it."** Keep "seconds, not minutes."
- Conflict status: open

### 2026-10-18 07:16 — README home-sensor row and stale mirrors — @nate
- Shipped: README home-sensor layer row now gives the served model's result (18.8% of top-1% alerts come true, 8.9× base) instead of "served model in progress"; Open-Meteo data row no longer says "in progress".
- Touched: `README.md` (two of Nate's lines)
- ⚠️ Conflicts: @sali: 📨 stale lines that aren't Nate's to edit:
  - `BLACKNAUGHT.md` NOW, the layer table: M8 is trained (+5.1%, not wired in), the home-sensor model is served in `ml/home_sensor.py`, and M4 is done (74 s, band rule stays). The Pending list still says "M2 live-feature list, waiting on Nate"; that closed at 05:46 (`contracts/model.md`, A1).
  - README: line 32 says the home risk level "is being built now" (live per NOW 06:00), and the mermaid diagram plus the stack table still mark the edge (live with a trusted cert), agent and frontend "(in progress)".
  - Demo risk: GB demo homes have no sensor window, so the headline level reads "unknown" under the 06:00 rules (Low needs all three layers). Worth checking before recording.
- Conflict status: open

### 2026-10-18 07:17 — agent loop v1 is live (task 14, F6) — @ahmed
- Shipped: `backend/app/agent.py`, running as its own `agent` service (`infra/agent.yml`). It runs as role `bn_agent`, signs with its own signer token, and publishes no port. Every 60 s it does this:
  - It reads the latest triage and the feeds' health.
  - It fills 5 responders' 120-min rounds with a greedy knapsack on harm-hours avoided per minute. Visits take 45 min without backup and 20 min with it. Whoever runs out before power is likely back goes first.
  - It acts only through `decisions.create()`. Every tool call is ML-DSA-signed first, so no signature means no action (retried next tick). The signature is added to the audit chain under the decision's id.
  - Escalations, CAP drafts and texts to more than 10 carers (`bulk_sms`) wait for an operator. A feed with no good poll for 3 intervals gets `mark_source_stale`; its patients are judged on q90 and re-ranked.
  - Memory lives in `agent_memory`, so a restart repeats nothing (tested).
- First live tick: 47 signed decisions. That's 5 rounds covering 15 visits, and 17 patients waiting, so 1 `bulk_sms`, 13 supply requests, 25 escalations and 2 CAP drafts. The `bulk_sms`, escalations and drafts are awaiting approval. Plus 1 sitrep. 12 tests (93% of the module), full suite 222 passed on s390x.
- Not yet: `field_briefing` and the Granite text (task 15), `recalibrate` (task 16).
- Deployed with `sudo docker compose -f infra/docker-compose.yml up -d agent` from `~/BlackNaught`. A dry run first showed it only creates the agent container; app, db, signer and edge weren't touched.
- Touched: `backend/app/agent.py` (new), `backend/tests/test_agent.py` (new), `infra/agent.yml` (new), `infra/docker-compose.yml`, `infra/test-compose.sh`, README run commands (also the missing `make-edge-cert.sh` line).
- ⚠️ Conflicts:
  - @sali: a new module in `backend/app/`; no file of yours changed. `bn_agent` can't read `v_triage_latest`, so the agent reads `triage_snapshot`, `patient` and `outage` and repeats the view's `P-xxxxxx` expression to show the same ref. Keep them in step, or grant the view to `bn_agent` and I'll switch. 28 decisions now wait in the control room.
  - @sali (covering frontend): `/api/agent/decisions` has real rows now. Two CAP drafts are ready to approve: outages 35 (TN26, TN30) and 53 (DA12).
- Conflict status: open

### 2026-10-18 07:25 — frontend: triage + approvals, agent & audit, previews, my home (Rama's rows 5, 6, 8, 10–13) — @sali — done
- Shipped (on `Rama-Frontend`, merged to `main`, live behind Ahmed's nginx):
  - Side panel tabs: **Power cuts** (Rama's view, unchanged) / **Triage** / **Agent & audit**; **My home** in the top bar.
  - Triage: rank, expected case then the q50–q90 range, rule used, harm-hours, reasons; Approve / Reject behind the operator sign-in; SMS template preview on a phone.
  - Agent & audit: Ahmed's decision feed with Approve / Reject, CAP alert phone preview once approved, audit verify (red + first bad row on tamper, checkpoint signature state).
  - My home: household sign-in, option C level over the three layer gauges, reserve clock, next action, never an ETA.
  - New-fault ping (outline pulse + "new", none under reduced motion); SIMULATED labels on cells, triage and SMS.
- Review: ui-audit + an independent review agent with a research ledger (`## Frontend accessibility + dialog pass` in the research doc). Applied: native `<dialog>` (focus, inert background, Escape), a single status line instead of list-wide live regions, top-bar sign-out, landing Brier fetched live, the UKPN curve in the charts, re-renders that keep open rows and focus, 409 shown as "already decided".
- Tests: 137 frontend (92% lines), build OK; backend 222 green.
- Touched: `frontend/src/*` (new: `triage`, `agent`, `preview`, `myHome`, `modal`, `tabs`, `dom`), `frontend/index.html`, `frontend/src/styles.css`, `fixtures/api/me_home.json`, `fixtures/api/agent_decisions.json`; VM `frontend/dist`
- ⚠️ Conflicts: @rama: your list is done up to row 13 and your own views are untouched; row 14 still needs the performance pass and a real-browser look. @ahmed: the UI reads your decisions' `args.patient` / `args.outage_id`; keep those names.
- Conflict status: open

### 2026-10-18 07:25 — triage rows link the agent's escalate decisions — @sali
- Shipped: `/api/triage` fills `decision_id` with the newest `escalate` decision for that patient and fault (it was still hard-coded null from before the agent existed). 25 of 32 live rows linked. Test added.
- Touched: `backend/app/main.py`, `backend/tests/test_triage.py`
- ⚠️ Conflicts: @ahmed: relies on `args.patient` + `args.outage_id` in escalate decisions.
- Conflict status: open


### 2026-10-18 07:34 — sensor simulator live on the real fault footprints (task 11, F2) — @ahmed
- Shipped: `backend/app/simulator.py`, one more worker inside the app (4 lines in `runtime.py`).
  - Each live DNO fault with geocoded postcodes gets 3 home fuse-box sensors and 2 anchors per postcode, plus 2 controls one cell away. Capped at 5,000.
  - An affected sensor sends a last gasp at the fault's real start and stays silent until the real restoration. Heartbeats come every 60 s.
  - Noise: about 75% comms uptime, with ~7 min gaps that the tracker marks `dropout`, never `down`. 8% of sensors are fitted behind a backup. 1 fault in 4 is partial, where only 1 home in 3 loses power.
  - Events go on the bus as source `sim`, label `SIMULATED`.
- Live: 2,199 sensors on 17 faults (1,299 home, 866 anchor, 34 control). 1,952 last gasps are stamped at the real fault starts, and 238 sensors are reporting. 5 tests (95% of the module), full suite 227 passed on s390x.
- Not yet: the Accra replay (real GridWatch sensors), linking home sensors to enrolled households, and feeding `/api/me/home`'s `voltage` (still `[]`).
- Deployed with `restart app` from `~/BlackNaught`, about 5 s of API downtime.
- Touched: `backend/app/simulator.py` (new), `backend/tests/test_simulator.py` (new), `backend/app/runtime.py` (+4 lines), `backend/tests/test_runtime.py` (the worker set now includes `sim`).
- ⚠️ Conflicts: @sali:
  - `runtime.py` and `test_runtime.py` are yours: 4 lines start and stop the simulator, and the worker-set assertion gains `"sim"`. The first round waits one heartbeat (60 s), so it can't race that test.
  - The simulator writes `sensor` as `bn_ingest` (as 0010 intended). The tracker writes its transitions as usual.
  - FYI: the app log had 4 "ASGI callable returned without completing response" errors in the 10 min before my restart and none after. Probably SSE viewers dropping.
- Conflict status: open

### 2026-10-18 07:35 — results notebook for screenshots and the video — @nate
- Shipped: `ml/make_results_notebook.py` builds `~/shared/nate-runs/blacknaught_results.ipynb`, executed in Jupyter on the VM. Nothing is retrained; it loads the saved models and re-scores all three prediction layers on held-out data. It shows `s390x`, big-endian and NNPA present, then four charts: Storm Éowyn (M8 vs climatology), tomorrow's live area risk from the Open-Meteo forecast, home-sensor flags (18.8% ± 1.1% vs the 2.1% base), and 9 Aug 2019 frequency with the 74 s warning shaded. The numbers match the evidence logs.
- Touched: `ml/make_results_notebook.py`; VM `~/shared/nate-runs/blacknaught_results.ipynb`
- ⚠️ Conflicts: @sali @rama: free to use the charts in the video and slides. Open the notebook in Jupyter (`nate-runs/`); don't show the URL bar (token).
- Conflict status: open

### 2026-10-18 07:42 — confirm step before approvals — @sali — done
- Shipped: decision (Sali): approving or rejecting an escalation, public alert or bulk SMS opens a confirm dialog naming what happens ("Send the 999 context packet for P-BA1699 (0 min of backup left)"), with Cancel focused. Verified in a real (headless) browser on the live site.
- Touched: `frontend/src/modal.ts`, `frontend/src/agent.ts`, `frontend/src/main.ts`, `frontend/src/styles.css` (+ tests)
- ⚠️ Conflicts: @ahmed: the wording reads `args.patient`, `args.outage_id`, `args.area` from your decisions.
- Conflict status: open

### 2026-10-18 07:42 — row 14: real-browser check + performance measurements — @sali
- Shipped: headless Chromium pass at 375 / 768 / 1280 px on the live site. Fixed what it found in my code: sign-in bar showing while signed out, the audit heading style, raw JSON in decision rows. Measured: desktop LCP 1.1 s; phone (4× CPU, slow 4G) LCP 3.4 s, CLS 0.13; CLS 0.16–0.30 from the two-houses card resizing; nginx serves JS uncompressed (1,066 KiB vs ~302 kB gzipped). Phone layout: tabs and My home are covered.
- Touched: `frontend/src/agent.ts`, `frontend/src/styles.css`
- ⚠️ Conflicts: @ahmed: nginx gzip + cache headers proposed (your brief), not applied. @rama: phone layout issues are in your views (two-houses card, Predict strip); proposals pending with Sali.
- Conflict status: open


### 2026-10-18 07:52 — public alert relay to a phone, a mocked broadcast (Sali's 06:05 item) — @ahmed
- Shipped: `alerting/relay.py`, which runs on Ahmed's laptop and needs only the Python standard library.
  - It polls `/api/agent/decisions` for approved `draft_cap_alert`s and fetches each from `GET /api/alerts/cap/{id}`.
  - It checks the ML-DSA-65 signature (`X-Signature-ML-DSA-65`) against the pinned signer key. Only then does it post the alert to the Android phone over ADB, as an "EXERCISE: ..." notification. An unsigned or tampered alert is refused and never shown.
  - Each alert goes out once (`alerting/.sent`). If the phone or the network drops, the next poll retries it.
  - The phone sits behind a `Channel` interface, so a government alerting service can take its place.
- The signer's public key is published now: `contracts/signer_pub.pem` (key_id `bda7ac1f8fd6c9d2`). Anyone with OpenSSL 3.5 can check our signatures.
- Tested: 6 tests on the laptop. They cover accepting and rejecting with a real ML-DSA key, hostile text staying one shell argument, and once-only across restarts. A real notification also reached the phone (Samsung, Android 13). Still to do: the end-to-end run with an operator's approval, to be filmed.
- Pitch line (Sali's): "Blacknaught drafts standard CAP 1.2 alerts that a government alerting service can broadcast; in the demo a phone stands in for that channel." Never "we send alerts to the public".
- Touched: `alerting/relay.py`, `alerting/tests/test_relay.py`, `contracts/signer_pub.pem` (all new), `contracts/signer.md`, `.gitignore`. Also the README run commands, and its diagram (edge and agent no longer "(in progress)").
- ⚠️ Conflicts: @sali @rama, to film it: run the relay on Ahmed's laptop with the phone plugged in, then approve a CAP draft in Agent & audit. The phone buzzes within about 10 s, showing the same alert as the UI's phone mock-up.
- Conflict status: open

### 2026-10-18 07:52 — Granite is live: it words the agent's text, never its choices (task 15, F8) — @ahmed
- Decision (Ahmed): Granite 3.3 2B Instruct BE, **Q4_K_M**, in its own container.
- Shipped: `backend/app/granite.py` and `infra/granite.yml`.
  - One process holds the model, and it won't load unless the GGUF's SHA-256 matches the pinned one (checked against Hugging Face's: `1f91f281...`).
  - It sits on an internal `writing` network only the agent joins: no published port and no route out.
  - It uses `llama_cpp` 0.3.36 from the lab image, with 2 threads, at most 200 tokens, temperature 0, and a cache.
- How the agent uses it:
  - Every decision is made first. Then Granite words the CAP description, the sitrep and new field briefings (`field_briefing` is a new auto tool).
  - A number check rejects text carrying any number, in digits or words, that isn't in the decision's facts; the template is kept instead. A test shows the decisions are identical with and without Granite.
  - One fresh text takes about 80 s on the z17's CPU, so the agent asks for one per tick. The rest keep their template, and repeats come from the cache. The first live sitrep wording had all 5 numbers grounded.
- Memory: Granite was at 330 MiB right after loading (weights are mapped lazily), and the VM had 5.9 GB available after the deploy.
- Tests: 19 agent and Granite tests, full suite 234 on s390x, 17 compose checks. The agent was restarted live and resumed from its memory (67 keys, after tick 35).
- Not yet: the welfare-call script, and Q8_0 with zDNN (2.7 GB) for NNPA.
- Touched: `backend/app/granite.py`, `backend/tests/test_granite.py`, `infra/granite.yml` (all new); `backend/app/agent.py`, `backend/tests/test_agent.py`, `infra/agent.yml`, `infra/docker-compose.yml`, `infra/test-compose.sh`; VM `~/models/` (the GGUF, read-only).
- ⚠️ Conflicts:
  - @sali: text decisions now carry `writer` (`granite` or `template`), and `draft_cap_alert` carries `description`, which `cap.build` already reads. There's a new tool name, `field_briefing`, in the feed.
  - @nate: Granite holds up to about 2 GB once warm. Please keep the Jupyter kernels stopped around the demo, as the brief's guardrail says.
- Conflict status: open

### 2026-10-18 08:02 — UI load time and layout shift fixed (row 14) — @sali — done
- Shipped: nginx gzip for JS/CSS/JSON (not `/stream`) and a year's cache on hashed `/assets/`; MapLibre in its own chunk; the app hidden under the landing overlay until the fade starts; the landing page's stacked triage card made near-solid with a fog band over the chart.
- Measured (headless Chromium, same conditions before/after): phone (4× CPU, slow 4G) LCP 3.4 s → 2.1 s (3 runs); desktop 1.14 → 0.84 s; CLS 0.13 / 0.30 / 0.16 → 0.016 / 0.002 / 0.004; JS transferred 1,066 → 438 KiB.
- Touched: `infra/edge/nginx.conf` (edge rebuilt on the VM), `frontend/src/main.ts`, `frontend/src/landing.ts`, `frontend/src/landing.css`
- ⚠️ Conflicts: @ahmed: your nginx.conf changed (gzip block + `/assets/` location); restart with `up -d --build edge`. @rama: row 17 (globe intro) dropped by Sali.
- Conflict status: open


### 2026-10-18 08:13 — self-correction live: the agent checks itself against the overnight grades (task 16) — @ahmed
- Shipped: `recalibrate` in `backend/app/agent.py`, run every hour. For each horizon and model, it fits a monotone (isotonic) correction on the older two thirds of the GB grades and judges it on the newer third, so before and after are measured on predictions the fit never saw. If the correction saves at least 0.005 of Brier, it's kept in agent memory. Every check is a signed decision either way (`applied` true or false, with both scores).
- Live result on the overnight grades (`m1-km-enwl`):
  - +2 h, 458 graded: 0.1215 → 0.1198, not enough gain.
  - +4 h, 352 graded: 0.1374 → 0.1630, which would be worse.
  - So both are `applied: false` and the model is left as it is. That's the honest version of on-screen decision 3: the agent checked and declined, with its reasons logged.
- I backdated the agent's `recalibrate_at` memory key once, so the first logged check ran now instead of at 09:08.
- Not yet: the triage scorer doesn't apply a kept correction (Sali's file). With no drift found, there's nothing to apply today.
- Tests: 17 agent tests, full suite 237 on s390x.
- Touched: `backend/app/agent.py`, `backend/tests/test_agent.py`
- ⚠️ Conflicts: @sali: the feed now shows `recalibrate` decisions about once an hour. If you want the scorer to use a kept correction later, it's in `agent_memory` under `calibration:<model>:<h>`.
- Conflict status: open

### 2026-10-18 08:13 — welfare-call script on each carer notification (task 15's last text) — @ahmed
- Shipped: each `notify_carer` now carries a `script` for the volunteer's call. It includes only what the record holds (the patient's ref, the device and the reserve left), never a restoration time, and ends with "call 999 now" if breathing gets worse.
- It stays a template. Granite's one text a tick goes to the CAP text, the sitrep and the briefings. Wording a call script first would hold up the escalations made after it.
- Touched: `backend/app/agent.py`, `backend/tests/test_agent.py`
- ⚠️ Conflicts: @sali: `args.script` is new on `notify_carer`, if the Triage SMS preview wants it.
- Conflict status: open

### 2026-10-18 08:15 — NNPA on/off timing, firewall and image scan (task 18), README platform section (task 22) — @ahmed
- NNPA, using Nate's M2 (`m2_hazard.keras`, 6,444 params, read only). Same VM, NNPA on vs `NNPA_DEVICES=0`, each mode in a fresh `docker run` of bn-app, median of 15 graph-mode runs:
  - batch 1: level (0.34 ms);
  - batches 256 and 4,096: NNPA about 1.2× faster;
  - batch 65,536: NNPA about 2.2× slower.
  - The zDNN precheck shows 9 `zdnn_matmul_transpose_op` (DLFLOAT16) calls with NNPA on and none with it off.
  - Honest read: this model is too small for the NNPA to matter much. Never compared against x86. **Not for the video until #helpdesk confirms (ToU §5).**
  - Files: `scripts/nnpa_timing.py`, `evidence/nnpa_timing.csv`, `evidence/nnpa_timing.txt`, `evidence/zdnn_precheck.txt`.
- Firewall (`evidence/10_firewall.txt`): the public ports are 22, 8443 and **38888 (Jupyter, token-protected, with an explicit INPUT rule)**. App 8000 and Postgres 5432 are on 127.0.0.1 only. The signer and Granite sit on internal networks.
- Trivy v0.76.0 (checksum-verified) can't open its database on big-endian ("invalid database"). So the SBOM was built on the VM and matched off it: 0 critical, 6 high, in keras, urllib3, jaraco.context and wheel from the base image, all with fixes (`evidence/11_trivy_app.txt`).
- README: a new "Platform, agent and proof" section covers the stack, edge, signer, agent, simulator, Granite and relay, each with its evidence. The limits now name what isn't done or is demo-grade. The NNPA line no longer claims the Keras model is served. `scripts/proof.sh` now writes `evidence/12_platform.txt`.
- Touched: the files above, `README.md`, `scripts/proof.sh`, `.gitignore` (`!evidence/nnpa_timing.csv`).
- ⚠️ Conflicts:
  - @sali: the README has a new section after Architecture, and your lines are untouched. Three of them are stale and yours to update: "198 tests pass… 96%" (it's 237 now), "That part is being built now", and the "Control-room UI (in progress)" diagram node.
  - @sali FYI: your gzip also covers JSON. That's fine here, since no response body holds a secret, and BREACH needs one.
  - @nate: the timing reads your model and doesn't change it.
  - @all: Jupyter 38888 is public. Say if it should be closed after the recordings.
- Conflict status: open

### 2026-10-18 08:16 — audit checkpoints published off the box (task 19) — @ahmed
- Shipped: `offbox/publish.py`. It runs on Ahmed's laptop, because the VM never gets GitHub credentials. Every 10 minutes it reads the new signed checkpoint rows over SSH (a read-only query in the db container; the public API exposes only `seq` and `sig_ok`).
  - It rebuilds each signed payload byte for byte and checks the ML-DSA-65 signature against the pinned `contracts/signer_pub.pem`. Then it commits one JSON line per checkpoint to the **`audit-checkpoints`** branch and pushes.
  - Nothing new is published while the server's own chain check fails. A checkpoint that doesn't verify stops publishing at that point; it isn't skipped.
- Live: checkpoints 109 to 302 are on GitHub (24 so far), all verified. The loop is running on the laptop.
- Tests: 11 (78%; the rest is the live SSH and API path, which the real runs cover).
- Touched: `offbox/publish.py`, `offbox/tests/test_publish.py` (new); branch `audit-checkpoints`; README platform section.
- ⚠️ Conflicts: @sali: none in code. The audit API doesn't expose checkpoint heads or signatures, so the publisher reads them over SSH. If you'd rather expose `GET /api/audit/checkpoints`, I'll switch to it. Don't delete the `audit-checkpoints` branch along with `context` before submission: it's the evidence.
- Conflict status: open

### 2026-10-18 07:22 — why the "Updates" chip reads 0.0 events/s — @nate
- Shipped: nothing; a diagnosis from the live stream (read-only).
  - The stream works. But `stats.events_per_s` is the bus count over the last **5 s** (`runtime.stats`, `STATS_S = 5`), while the simulator sends every heartbeat (~270 sensors) in **one burst a minute** (`Simulator.run`). So 11 of every 12 readings are 0.0 and one is a spike (seen live: 0.0, 0.0, 0.0, 53.8, 0.0). DNO events come only when a fault changes (2-min polls).
  - The app was also restarted at 07:16 and 07:18 (docker `restart`, exit 0, no OOM, so not a crash). The simulator waits 60 s after each start, so the chip sits at 0.0 for longer.
- Touched: nothing
- ⚠️ Conflicts: 📨 @sali (runtime.py) / @ahmed (simulator): before recording, either **A**: report a 60 s rolling rate in `stats` (it would read a steady ~4.5 events/s; one line), or **B**: stagger each sensor's heartbeat across the minute. Nate suggests A now.
- Conflict status: open

### 2026-10-18 08:22 — Accra replay of real sensors is live (task 11 done) — @ahmed
- Shipped: `backend/app/replay.py`, one more worker in the app (4 lines in `runtime.py`; the worker set in `test_runtime.py` gains `"replay"`).
  - A week of real nLine GridWatch readings plays at 10× speed, starting from the current time of day: 429 plug-in sensors in Accra, 1–7 June 2021, 4.76 M readings (CC BY-NC 4.0).
  - Each 2-minute bin is one event: a heartbeat while the sensor has power, a last gasp when it loses it, silence while it's off.
  - The week is loaded once with Sali's `probe_precursor.load`, in a short-lived child process, so pandas never enters the app (it peaks at about 80 MB).
  - Events use source `accra_replay` and label `REPLAY`. The sensors are registered as `anchor`, since they're anonymous premises, not register households. The data has no coordinates, so they share one cell at Accra's centre.
- Live: 429 sensors registered. In the first 3 minutes they made 129 last gasps and 329 power-on transitions, next to the GB simulator's. API healthy.
- Tests: 9 (6 replay, 3 runtime), full suite 243 on s390x.
- Deployed with `restart app` from `~/BlackNaught`, about 5 s of API downtime. The replay starts 60 s after the app does.
- Touched: `backend/app/replay.py` and `backend/tests/test_replay.py` (new), `backend/app/runtime.py` (+4), `backend/tests/test_runtime.py`, README platform section.
- ⚠️ Conflicts: @sali: `runtime.py` and `test_runtime.py` are yours: 4 more lines, as with the simulator. @nate: it reads the Accra week with Sali's loader, the same data as your home-sensor model, and changes nothing.
- Conflict status: open
