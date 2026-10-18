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
6. **Ahmed, one stack only:** the backend already runs `postgres:17` + `app` from `backend/compose.backend.yml` (project `bn-backend`).
   - **Don't start a second Postgres.** Add edge, signer and granite as services to that stack, or `include:` it from `/infra`.
   - Reuse the `secrets/` names.
   - Agree it with Sali first.
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
  - After a merge to `main`: `cd ~/BlackNaught && git pull --ff-only && cd backend && sudo docker compose -f compose.backend.yml restart app`.
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
- **As of 2026-10-18 05:42:**
  - `main`: full backend live on the VM + home-sensor probe; 208 tests green on s390x, 96% coverage (proof.sh re-run 05:10). README for judges is live.
  - **VM:** reachable (s390x, z17 9175, NNPA flag present, Ubuntu 24.04.5, 3 vCPU / 7.8 GiB, 45 GB free). Docker 29.8 + Compose v5 installed; Jupyter (`notebook`) on :38888 with a custom token; IBM lab image pulled; backend stack `bn-backend` (postgres:17 + app) running.
  - Shared docs (CLAUDE.md, `BLACKNAUGHT.md`, briefs, research) live on the `context` branch, never on `main`.

---

### 2026-10-17 21:40 — repo scaffold — @sali
- Shipped: `.gitignore` keeps every doc local except `progress.md` and `README.md`. It also excludes data, models and secrets. Added this conflict board.
- Touched: `.gitignore`, `progress.md`
- ⚠️ Conflicts: @rama: the `Rama-Frontend` branch predates this `.gitignore`. Rebase on `main` before adding files, so docs and data don't get committed by accident.
- Conflict status: open

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
- Conflict status: open

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
- Conflict status: open

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
