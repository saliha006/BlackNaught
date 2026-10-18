# Sali: Backend (API, database, ingest, triage, grading, audit, security plumbing)
**GitHub:** `saliha006` (repo owner, docs owner) · **Branch:** `sali-backend` · **Tool:** Claude Code · **Brief last updated:** 2026-10-17 23:05 by Sali
**Spec:** `BLACKNAUGHT.md` (NOW at the top, then Part A spec, Part B backend design); the § numbers below refer to it. **How to build each piece:** Part B (§B1–§B21). Each section ends with a **Spec**; build from that.

## 0. How the agent reads this brief (every task)
0. **First, every prompt: `bash scripts/sync-context.sh`** (CLAUDE.md). If it says UPDATED, read `BLACKNAUGHT.md` → NOW and
   this brief again, and tell the user what changed before working.
1. Read the project `CLAUDE.md` in full, then this brief. Follow both. Verbosity is **Level 0**.
2. **Only action `▶ Current tasks`**, top to bottom.
3. **Every prompt:** `git fetch`, then read the new `progress.md` entries with `git diff HEAD..origin/main -- progress.md`. If an open `⚠️ Conflicts` line names @sali:
   - tell Sali who flagged what;
   - propose a fix, or ask Sali to agree one with that builder before touching the area.
4. **Ship sequence for each feature (mandatory):**
   1. `no-slop`
   2. pytest with coverage (happy path, edge cases, failure paths), run **on the VM**
   3. push `sali-backend`
   4. `git merge origin/main` into `sali-backend`, then re-test, fixing any conflict on the branch
   5. merge to `main` and push
   6. append a `progress.md` entry (CLAUDE.md §2b)
   - **Every completed task, not just features:** add a `progress.md` entry with your name, date and time, and push it
     to `main` straight away.
   - **Doc edits:** you may only move your own finished task into Archived. Publish it with
     `bash scripts/publish-context.sh "what changed"`. Never commit shared docs to `main`.

   Use the `debug` skill on every issue. Commit as `saliha006`, with **no AI co-author trailer**.
5. **Off-plan request** → ⛔ stop and ask which teammates agreed (CLAUDE.md §2). Anything marked 🟠 is a decision for Sali.

**Conflict tags:** `[⚠ conflicts with @name: what]` means the task touches someone else's area or a shared contract. Agree with them before merging.

---

## 1. Ownership
**Owns:**
- `/backend`:
  - the FastAPI app under `/api`, plus SSE
  - the event schema and the two in-process queues
  - the writer task
  - ingest: UKPN, SSEN, NPg and Elexon (P0); IODA (P1)
  - the postcode geocode cache
  - the triage scorer task, the horizon grader, `/sources/health`
  - the CAP export (P1), and `/me/home` (P1, only if ahead)
- `/db`:
  - schema `bn` and its roles (`bn_migrator`, `bn_ingest`, `bn_api`, `bn_agent`)
  - the migration runner and views
  - the fixed WGS84 cells with k≥11 suppression
  - the audit hash chain (`SECURITY DEFINER` append)
  - AES-GCM field encryption (libcrypto via ctypes) and the HMAC blind index
  - operator auth
- `contracts/openapi.yaml` (author) and `contracts/events.schema.json` (co-author with Ahmed).
- **Docs owner:** `BLACKNAUGHT.md`, `DATATHON-CONTEXT.md`, all briefs (published to the `context` branch), the vault Log and `progress.md` hygiene.

**Does NOT touch:**

| Area | Owner | Why |
|---|---|---|
| `/frontend` | @rama | UI |
| `/ml`, `grids/*.yaml`, `contracts/model.md` | @nate | Models, configs |
| `/infra`, `/agent`, signer, simulator, nginx, Compose, LUKS, VM keys | @ahmed | Platform + agent |

**Shared** (flag edits in `progress.md` `⚠️ Conflicts`): `contracts/*`, `fixtures/*`, `docker-compose.yml`.

## 2. LinuxONE: what Sali does on the VM vs. what only Ahmed can do
- **VM:** `148.100.78.95`, user `linux1`, key-only.
- ✅ **Your key is on it** (added 23:25), and the `datathon` alias is set up in `~/.ssh/config`.
- Then add this to your own `~/.ssh/config`: `Host datathon` / `HostName 148.100.78.95` / `User linux1` / `IdentityFile ~/.ssh/id_ed25519` / `ServerAliveInterval 30`.
- **Never** use the `.pem` or password shared in the form. They are being rotated.

**You can (after your key is added):**
- `ssh datathon "cd ~/BlackNaught && git pull && docker compose restart app"`
- run pytest inside the app container: tests must run on s390x
- apply migrations (`bn_migrator`)
- `psql` checks
- tail logs
- record the overnight grading log
- curl the live feeds from the VM to record fixtures

**Only Ahmed:** portal restarts, key rotation, `authorized_keys`, the iptables policy, the LUKS unlock, the Jupyter token, the signer key.

**Why it counts:** every endpoint, the DB, the grader and the tests run on the z17. That is the evidence judges check (IP, `docker ps`, packages).

## 3. Contract & Guardrails
**Scope contract.** Sali is building:
- **Ingest:** live UKPN/SSEN/NPg faults (geocoded, deduped, "vanished" ≠ "restored") and Elexon frequency, into one outage schema.
- **Triage:** a scorer task that batches every at-risk household × outage into one `predict()` call (NNPA via Ahmed's serving) and serves a consistent ranked snapshot. A Kaplan–Meier fallback ships first, labelled as such.
- **Grading:** horizon grading at +2 h/+4 h against real restorations, censoring-safe, **running overnight from ~00:30**.
- **The DB:**
  - least-privilege roles
  - AES-GCM sensitive columns (CPACF)
  - a tamper-evident audit chain over decisions, approvals and tool calls
  - fixed k≥11 cells with complementary suppression
- **The API:** REST + SSE for Rama, with operator login for approvals.

**Out of scope:**
- mTLS, Redis, Kafka, LISTEN/NOTIFY, WebSockets
- PostGIS/TimescaleDB, an ORM, Alembic
- storing every heartbeat
- the target-grid shortage model
- storing any national ID

**Guardrails:**
- **No real personal or health data on the VM** (ToU §9). Patients are synthetic.
- **No arbitrary-bbox or point endpoint.** Fixed cells only.
- **A fault missing from a feed is "vanished", never "restored".** Grade only on explicit restores.
- **pg8000: one connection per role, each on its own 1-thread executor.** Never use `asyncio.to_thread` with a shared connection.
- Pip installs on top of the image only, with `-c` against the image freeze: `fastapi uvicorn pg8000 sse-starlette`. Test-only: `pytest pytest-cov xmlschema`. **Never** cryptography, psycopg2, pyarrow, numpy or pandas.
- Secrets go through `*_FILE` env vars and compose secrets. gitleaks. `.env.example` only.
- CAP `status` is always **`Exercise`**, never `Actual`, on synthetic data.

---

## 4. ▶ Current tasks (2026-10-18 04:40), in priority order
**Headline (18 Oct):** "Blacknaught **predicts blackouts before they happen** and **protects the people they'd hurt most**."
- **Backend build tasks 1–20 are done and live** (list below, kept for reference).
- What's left is unblocking the team, submission blockers, one small feature, then evidence and the pitch.
- Deadline: **submit 09:30** (hard stop 10:00).

**A. Unblock the team (do first, ~15 min)**
1. ✅ *(done 04:55: all three have Write)* **GitHub → Settings → Collaborators:** `meep-boop`, `aldrichbanas07`, `rama0623` must have **Write**. Without it they can't push.
2. ⏸ *(deferred 04:55: Sali decides later)* **Set and announce the freeze time** on Discord (proposal: features 06:30, video 07:00–09:00, submit 09:30). Then update `BLACKNAUGHT.md` → NOW and the briefs.
3. ✅ *(05:40: Sali chose **C**; rules = draft A, confirmed 06:00)* **🟠 Decide the home-dashboard risk display** (A three gauges / B stacked model / C risk level + gauges; recommended C). This unblocks Rama's "Predict" strip and task 9.
4. ⬜ **🟠 Agree the M2 live-feature list with Nate** (`contracts/model.md`). This unblocks Nate's main model. *Waiting on Nate: Sali passes it on when he's done.*
5. ⬜ **Pings:**
   - Rama: test the VM login.
   - Ahmed: turn off the Drive link + change the portal password.
   - Everyone: `git pull` on `main`, then `bash scripts/sync-context.sh`.

**B. Submission blockers (by ~06:00)**
6. ✅ **Team: The 4 Musketeers; Sali is team leader** (submits). Title `[The 4 Musketeers_IBM Z Datathon 2026 Project]`; no Hack2Skill number needed.
7. ✅ *(done by Ahmed)* **IBM labs 01 + 02** run and screenshotted.
8. ➡ *(moved to Ahmed 04:55)* **#helpdesk question:** can the video show NNPA on/off timing of our own model (ToU §5)?

**C. Build (05:00–06:30)**
- ✅ *(06:00)* **Ahmed's asks:** `sensor` table shipped (0010, applied on the VM); compose layout OK'd; public-alert task added to his brief.
- ✅ *(06:00)* **Elexon 0 Hz bug:** readings outside 45–55 Hz dropped.
- ✅ *(06:00)* **Context publish clobber:** took Nate's fix; the credential guard now matches shapes, not fragments.
- ⬜ **Signer wiring** when Ahmed's `contracts/signer.md` lands: bearer token from `signer_token_app` + `BN_SIGNER_URL=http://signer:8100`.
- ⬜ **M2 wiring** when Nate says it's ready: pass `features` into `predict()` in `triage.py`.
- ⬜ **Re-seed** patients + the two-houses pair on a fresh fault right before recording (reserves drain over time).
9. ✅ *(06:00, live on the VM)* add a `risk` block to `/api/me/home` (level + the three layer gauges with source and horizon) and tests. Ship it.
10. ⬜ **Integration support:**
    - Ahmed: nginx `:8443` → `/api`, `/stream` (no buffering), `BN_SIGNER_URL`.
    - Nate: swap `KmModel` for M2; serve the home-sensor model.

**D. Freeze + evidence (06:30–07:00)**
11. 🟡 *(05:40: no freeze yet, Sali's call; grades checked + proof.sh re-run + evidence committed)* **Backend freeze.**
    - Check the overnight grades (`/api/agent/grades`).
    - Re-run `bash ~/BlackNaught/scripts/proof.sh`.
    - Screenshots: the Jupyter training notebook with the IP visible, the terminal proof, and `/api/docs` once the edge is up.
12. ✅ *(05:40)* **README for judges** (main, public):
    - problem; data + licences; architecture;
    - how to run on LinuxONE; results (grades, probe);
    - choices + failures; who did what; next steps;
    - open-source list.

**E. Pitch + submit (07:00–09:30)**
13. ⬜ **Your video segment + one line;** deck PDF with a "proof it runs on LinuxONE" slide; the open-source list.
14. ⬜ **Delete the `context` branch** right before submitting: `git push origin --delete context` (the repo is public).
15. ⬜ **Submit by 09:30** (team leader), then screenshot the confirmation.
16. ⬜ **Keep the VM + app running until 28 Oct** (judges may ask for proof).

---
### Build tasks 1–20 (done; reference)
#### Original list: (2026-10-17 v3), in order
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*

1. ✅ **Register on ENWL + UKPN and download both.** Done 22:16 via API keys **straight onto the VM**: `~/data/raw/enwl_unplanned-outages.csv` (312,936 rows) and `ukpn_ukpn-iis.csv` (316,435), plus `SHA256SUMS`. The keys are in `~/.ssh/*_apikey` (laptop) and `secrets/*_apikey` (VM).
2. ✅ **VM access** (23:25): Sali's own key added via the team key; the `datathon` alias (own key, `IdentitiesOnly`) works and reports s390x/NNPA. The team key lives at `~/.ssh/DatathonKey1.pem`; don't use it again.
3. ✅ **Contract freeze** (§B3, §B13). `[⚠ shared with ALL: agree before anyone codes]`
   - **`contracts/openapi.yaml`** (all under `/api`):
     - `/health`, `/auth/login`, `/auth/logout`
     - `/grids/{id}/stress`, `/outages`, `/cells?level&cell_id`, `/areas/risk?date`
     - `/triage`, `/decisions/{id}/approve`
     - `/agent/decisions`, `/agent/grades`
     - `/alerts/cap/{id}`, `/me/home`
     - `/sources/health`, `/audit/verify`
     - SSE `/stream`
   - **`contracts/events.schema.json`** with Ahmed: a discriminated union on `kind`, with a deterministic `event_id`.
   - **`fixtures/*.json`.**
   - *Done when:* Rama, Nate and Ahmed have each ✅'d it in `progress.md`.
4. ✅ **FastAPI skeleton serving fixtures** (one uvicorn worker), so Rama is never blocked.
   - *Done when:* every endpoint returns its fixture, and the OpenAPI test passes.
5. ✅ **Schema, roles, migration runner** (§B6)
   - Schema `bn`, owned by NOLOGIN `bn_owner`; the 4 login roles.
   - Numbered SQL files plus a checksum table.
   - Tables: outages, `postcode_geo`, `state_transitions`, `minute_counts`, households (encrypted columns), predictions, grades, decisions, `source_health`, `audit_log`, sessions.
   - `bn_api` reads views only.
   - *Done when:* migrations apply on the VM, and role-permission tests pass (`\dp` screenshot → `evidence/`).
   - `[⚠ @ahmed: Postgres runs on Ahmed's LUKS volume; agree the data path]`
6. ✅ **Writer task + queues** (§B2–§B3)
   - `critical` (never dropped) and `bulk` (drops the oldest heartbeat).
   - Batches every 250 ms or 500 rows, as `INSERT … SELECT FROM unnest() ON CONFLICT`.
   - Shutdown via a sentinel.
7. ✅ **F1 ingest, P0** (§B4–§B5)
   - One `httpx.AsyncClient`. Polling: UKPN, SSEN and NPg every 120 s; Elexon every 30 s, with from/to.
   - Retries: 3 tries, full jitter, cap 30 s; honour `Retry-After`; back off after 5 failures. Timeouts 5/15/5 s.
   - Upsert on `(source, source_ref)` with a content hash.
   - UKPN naive local time → UTC.
   - Missing from 2 polls → `vanished`.
   - postcodes.io bulk (≤100), cached, falling back to the feed's coordinates.
   - Record the live responses as fixtures tonight.
   - *Done when:* live GB faults show at `/api/outages` on the VM.
8. ✅ **🎯 Walking skeleton by 00:30** `[⚠ shared with ALL]`: ingest → DB → API → Rama's map, live on the VM.
9. ✅ **`/sources/health`** (§B17): ok → stale (>3× interval) → down (>6×), pushed on SSE. `[⚠ @ahmed: the agent's source-failure input]`
10. ✅ **F5 triage scorer** (§B7)
    - Runs every 30 s and on any new outage.
    - Makes one batched `predict()` call on a dedicated executor (Nate's stub first, then a KM fallback, then real M2).
    - Ranks by expected harm-hours, with the escalation rule from PRD §5.
    - `/api/triage` serves the snapshot. Patients never get an ETA.
    - `[⚠ @nate model contract; @ahmed NNPA serving + agent reads the snapshot]`
11. ✅ **F7 grading, started by ~00:30 and left running overnight** (§B8)
    - Log one prediction per outage every 15 min.
    - A grader runs every 60 s with a fixed-horizon binary outcome at +2 h/+4 h.
    - UKPN is primary; SSEN approximate; NPg excluded.
    - Censored rows (vanished or stale) are excluded, counted and bounded.
    - Brier by region → `/api/agent/grades`.
    - `[⚠ @ahmed recalibration reads grades]`
12. ✅ **AES-GCM via libcrypto ctypes + HMAC blind index** (§B18)
    - Check NIST test vectors **on the VM** (big-endian).
    - Encrypt the sensitive household columns; key from the compose secret.
    - 🟠 Fallback if libcrypto isn't in the image: the signer-side apt `cryptography`.
    - `[⚠ @ahmed: key wrapping by the signer]`
13. ✅ **Audit hash chain** (§B12)
    - `audit_log(seq, body, prev_hash, hash)` with a `SECURITY DEFINER` append under an advisory lock.
    - REVOKE plus UPDATE/DELETE/TRUNCATE triggers.
    - `/api/audit/verify`, with a tamper-test fixture (red).
    - Checkpoint every 500 rows or 5 min, sent to Ahmed's signer.
    - `[⚠ @ahmed signs + publishes checkpoints off-box]`
14. ✅ **Operator login + approvals** (§B16)
    - argon2id; an opaque token stored as a hash; HttpOnly SameSite=Strict cookie; 30 min idle / 8 h absolute; lockout after 5 failures.
    - `POST /api/decisions/{id}/approve` requires it.
    - `[⚠ @rama login UI; @ahmed agent waits on approvals]`
15. ✅ **SSE `/api/stream`** (§B14)
    - sse-starlette with a broadcaster: a 256-message queue per client, a 2,000-event ring for `Last-Event-ID`, a 15 s ping, max 50 clients.
    - Stats coalesced once a second.
    - `[⚠ @rama consumes; @ahmed nginx proxy_buffering off]`
16. ✅ **Fixed cells + k≥11** (§B10)
    - WGS84 grid at 3 nested levels; primary suppression of 1–10; complementary suppression per parent; 15-min publish; banding from 20.
    - *Done when:* the property test shows no hidden count can be back-calculated.
17. ✅ **`/api/areas/risk`** wraps Nate's `area_risk()` for Rama's overlay (P1). `[⚠ @nate]`
18. ✅ **F15 CAP 1.2 export (🅿 parked: build if time allows)** (§B15)
    - ElementTree; `status=Exercise`; polygon = convex hull of the affected postcodes; XSD-validated in tests.
    - `GET /api/alerts/cap/{id}`; approval-gated.
    - `[⚠ @ahmed draft_cap_alert tool; @rama preview]`
19. ✅ **`/me/home` (🅿 parked: build if time allows):** the session login from task 14, own data only, no ID in the URL, no ETA. `[⚠ @rama]`
20. ✅ **IODA ingest (🅿 parked: build if time allows):** every 10 min, province level; run our own detector on the raw signal, since the curated event list missed Sri Lanka 2025.
21. ⬜ **06:00 backend freeze.** Sali codes from 00:30 to 07:00, with 06:00–07:00 for fixes and iteration only. **Keep the API contract stable after 03:00**: Rama and Ahmed freeze then, so after 03:00 only add new endpoints, never change existing shapes. Confirm the grader is running.
22. ⬜ **06:00–07:00 (fix + reiterate):** check the overnight grading log has real closures; capture evidence (`\dp`, audit verify, test coverage report from the VM).
23. ⬜ **Video, 07:00–09:15:** your segment plus one line. README backend section, plus the open-source list. **Submit at 09:30 (team leader).**

## 5. Done log (newest first)
- ✅ 2026-10-17 23:05: **all build tasks 1–20 shipped to `main`, 194 tests green on s390x (98% coverage), everything running live on the VM.** Commits, problems and fixes: vault [[BlackNaught — Build Log]].
  - **Live stack:** `bn-backend`, started with `cd ~/BlackNaught/backend && sudo docker compose -f compose.backend.yml up -d`.
  - **Polling:** UKPN/NPg/SSEN/Elexon/IODA.
  - **KM model** fitted on the VM from ENWL; triage every 30 s.
  - **Grading** running since 21:28 UTC.
  - **Audit chain, operator login, SSE, k≥11 map, area-risk baseline, CAP export and `/me/home` are all live.**
- ✅ 2026-10-17 23:25: VM access with Sali's own key; probe logged in `progress.md`.
- ✅ 2026-10-17 21:40: repo scaffold. Added a `.gitignore` (docs stay local) and the `progress.md` conflict board. `sali-backend` created; merged to `main` (4799307).

## 6. Waiting on / owed to others
- 📤 **Owed to @nate:** ENWL + UKPN downloads (now).
- 📤 **Owed to @rama:** fixtures + API by about 23:30; SSE; `/alerts/cap`; `/me/home` if it ships.
- 📤 **Owed to @ahmed:** tables for events, decisions, grades and source health; geocoded faults; checkpoint payloads.
- 📥 **Waiting on @ahmed:** VM key; Compose skeleton; LUKS path; signer interface.
- 📥 **Waiting on @nate:** `contracts/model.md` + stub `predict()`/`area_risk()` (hour 1), real versions by about 01:30.

## 7. Open 🟠 decisions (Sali's call; recommendations from `BLACKNAUGHT.md` Part B)
1. ✅ **AES-GCM route: ctypes → libcrypto** (decided) / signer-side apt `cryptography` / pycryptodome (loses CPACF).
2. **Storage:** heartbeats in memory, transitions in the DB *(rec.)* / every event a row.
3. **`/me/home` auth:** server session with argon2id *(rec.)* / nginx Basic / stateless HMAC.
4. ✅ **Operator auth for approvals: a single operator login** (decided) / none (anyone on the public IP could approve).
5. **Off-box checkpoints:** a separate repo with a scoped deploy key *(rec.)* / manual / none.
6. ✅ **Demo URL: HTTPS :8443 with PQ TLS** (decided; a Vercel mirror is 🟠 open, see the vault Log) / http plus a terminal handshake.
7. **Cells:** WGS84 grid *(rec.)* / OSGB / postcode sectors.
8. **Grading scope:** UKPN primary, SSEN approximate, NPg excluded *(rec.)*.
9. **CAP status:** `Exercise` *(rec.)*.
10. ✅ **New dependencies (approved):**
    - runtime: fastapi, starlette, pydantic(-core), uvicorn, sse-starlette, pg8000 (+ scramp, asn1crypto), opentelemetry-api
    - test: pytest, pytest-cov, xmlschema
11. **Scope (decided by Sali):** nothing is cut. CAP, `/me/home` and IODA are **parked**; build them in that order if time allows.

## 8. Reference (no secrets)
- **UKPN:** `ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-live-faults/records` (`limit` ≤ 100; `fullpostcodedata`, `restoreddatetime`)
- **NPg:** `northernpowergrid.opendatasoft.com` `live-power-cuts-data`
- **SSEN:** `ssen-powertrack-api.opcld.com/gridiview/reporter/info/livefaults` (gzip; feeder IDs; `priorityCustomerCount`)
- **Elexon:** `https://data.elexon.co.uk/bmrs/api/v1/system/frequency?from=…&to=…`
- **postcodes.io:** bulk `POST /postcodes`
- **IODA:** `api.ioda.inetintel.cc.gatech.edu/v2/`
- **CAP 1.2:** OASIS spec + XSD
- **Ledger:** `research-and-codebase.md` §12.1, §13, and the "Backend system-design pass"
- **Handoff:** `DATATHON INFO/IBMZ_Datathon_ClaudeCode_Handoff/HANDOFF.md` §2–3, §9

---
── Archived (superseded 2026-10-17 — do NOT action) ──
- **The v2 task list (19 items):**
  - credential rotation with Ahmed, ENWL/UKPN registration
  - contract freeze, FastAPI fixtures, schema + roles (`ingest` / `api_read` / `agent`, psycopg 3)
  - Elexon ingest, SSEN + NPg ingest, skeleton by 18:00
  - triage endpoint, k≥11 cells, audit chain, SSE
  - IODA ingest, **BPDB PDF parser**
  - horizon grading from 22:00, `/sources/health`, 23:00 freeze, video
- **Why superseded:** PRD v3 + the backend design (now `BLACKNAUGHT.md` Part B).
  - pg8000 replaces psycopg 3; UKPN live is added.
  - The BPDB parser is parked (Bangladesh parked).
  - Added: AES-GCM via ctypes, operator auth, CAP export, `/me/home`, the writer task with queues, and censoring rules.
  - Credential rotation moved to Ahmed.
  - The freeze moves to 03:00.
