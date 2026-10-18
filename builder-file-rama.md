# Rama: Frontend (control-room UI, two-houses card, previews, "my home", video edit)
**GitHub:** `rama0623` · **Branch:** `Rama-Frontend` · **Brief last updated:** 2026-10-17 22:30 by Sali
**Spec:** `BLACKNAUGHT.md` (NOW at the top, then Part A spec, Part B backend design); the § numbers below refer to it.

## 0. How the agent reads this brief (every task)
0. **First, every prompt: `bash scripts/sync-context.sh`** (CLAUDE.md). If it says UPDATED, read `BLACKNAUGHT.md` → NOW and
   this brief again, and tell the user what changed before working.
1. Read the project `CLAUDE.md` in full, then this brief. Follow both.
2. **Only action `▶ Current tasks`**, top to bottom.
3. Before starting: `git fetch`, then read the new `progress.md` entries. Handle any open `⚠️ Conflicts: @rama` first. **One is open now:** rebase `Rama-Frontend` on `main` to pick up the new `.gitignore`.
4. **Ship sequence for each feature:**
   1. `no-slop`
   2. tests
   3. push `Rama-Frontend`
   4. `git merge origin/main` into the branch and re-test
   5. merge to `main`
   6. add a `progress.md` entry
   - **Every completed task, not just features:** add a `progress.md` entry with your name, date and time, and push it
     to `main` straight away.
   - **Doc edits:** you may only move your own finished task into Archived. Publish it with
     `bash scripts/publish-context.sh "what changed"`. Never commit shared docs to `main`.
5. **Front-end skills:**
   - `design-direction` (UI)
   - `motion` / `motion-review` (pings)
   - `ui-audit` before calling anything done
   - `frontend-performance` if anything janks

---

## 1. Ownership
**Owns:** `/frontend`.
- **Stack:** Vite + TypeScript + **MapLibre GL JS v5**, built **statically on your laptop**. Hand `dist/` to Ahmed's nginx edge. Never run Vite on the VM.
- **Views** (§15):
  1. Map with outage areas by scale, fixed k≥11 cells and a risk overlay for tomorrow
  2. Triage list
  3. **Two-houses card**
  4. Agent panel (live tool-call feed + grades)
  5. Grid gauge
  6. Audit view
  7. CAP alert preview + SMS template preview
  8. **"My home"**
  9. Optional globe intro (30 min max)

**Does NOT touch:** `/backend` (@sali), `/ml` (@nate), `/infra` and `/agent` (@ahmed). **Shared:** `contracts/openapi.yaml` (as consumer), `fixtures/*`.

## 2. Contract & Guardrails
**Scope contract.** A control-room UI that tells the demo story in 3 minutes (§17), recorded against `http://148.100.78.95:<port>` so the IP shows.

**Out of scope:** a mobile app, an SMS console, panels beyond §15, the grid-difference panel (parked).

**Guardrails:**
- **Privacy:**
  - Never render an individual home on the shared map.
  - Only fixed k≥11 cells from `/cells`; no client-side bbox aggregation.
  - "My home" shows **only the logged-in household's own data**.
- **Labels are mandatory:**
  - **LIVE:** GB feeds
  - **SIMULATED:** sensors, patients
  - **REPLAY:** real data replayed (NESO, Accra)
  - **TRANSFERRED:** GB-trained durations used elsewhere
- **Patients never see an ETA.** They get actions plus a reserve clock. Staff see the expected case first, then the range.
- Build against **fixtures first**. Never block on the backend.

---

## 3. ▶ Current tasks (2026-10-18 06:05), in order
**▶ 2026-10-18 06:39 (from Sali): Sali is continuing this list while Rama's Claude usage is out.**
- Sali works on **`Rama-Frontend`** (synced with `main` at 06:39, 0 behind / 0 ahead) and follows this table. Everything Rama built stays as it is; Sali ticks rows here as they land and logs each in `progress.md` as @sali.
- Checked at handover: `npm test` 111/111 pass, 89.7% lines covered; `npm run build` passes.
- ✅ **Two-houses pair seeded** on live UKPN fault 133 (Rama's 06:14 ask): the oxygen concentrator escalates, the ventilator gets an SMS check. Re-seeded on a fresh fault right before recording.
- **When Rama is back:** run the sync, read the `progress.md` entries since 06:39, then carry on from whatever is still ⬜ / 🟡.

**How you build it is your call.** Layout, components, visual direction and how each view looks are your decisions: keep making them, and log the big ones in `progress.md` so Sali can mirror them. What this list fixes is **coverage**: every backend feature below needs a place in the UI before the recordings, because the video and the README promise them.

**Keep this list honest:** when you finish a task, mark it ✅ here (your one self-edit), publish with `bash scripts/publish-context.sh "..."`, and add a `progress.md` entry with your name, date and time. **Push your work to `Rama-Frontend` as you go.** Right now the branch has no frontend code on it, so nobody, Sali included, can see what's already done. Run `git config blacknaught.builder rama` once (publish refuses without it).

**Setup**
1. ✅ Merge `main` into `Rama-Frontend` *(done 05:13)*. ✅ SSH key on the VM *(added by Sali 03:09)*. ✅ Test the login: `ssh linux1@148.100.78.95 "uname -m"` should print `s390x`; post it in `progress.md`. *(done 06:05: s390x)*
2. ✅ **Push what you have** to `Rama-Frontend` and log which of the views below already work. *(done 06:05; also merged to `main`)*

**Backend → frontend coverage** (each needs a home in the UI; build against `fixtures/api/*.json` if the VM is unreachable)

| # | Feature | Endpoint(s) | Must show | Status |
|---|---|---|---|---|
| 3 | Map | `GET /api/outages`, `GET /api/cells?level=1` (or 2, 3) | Live outages by scale (home / street / area / region / system); fixed k≥11 cells only, never a home | ✅ 06:05 |
| 4 | **Two-houses card** (demo centrepiece) | `GET /api/triage`; Sali seeds the pair on a fresh real fault with `python -m app.seed --two-houses <outage_id>` | Same fault, different answers: one escalates, one gets an SMS check. Readable in under 10 s | ✅ 06:14: card built; live shows "no pair yet" until Sali seeds one (📨 in progress.md) *(Sali 06:39: pair seeded on UKPN 133)* |
| 5 | Triage list + approvals | `GET /api/triage`; `POST /api/auth/login` (operator); `POST /api/decisions/{id}/approve` | Rank; expected case then range (`remaining_h` q50 / q75 / q90 and `q_used`); harm-hours; the `why` lines; escalate flag; approve button behind the operator login | ⬜ ✅ *(Sali 07:25: on `main` and live at https://148-100-78-95.sslip.io:8443; ui-audit fixes applied)* |
| 6 | Live updates | SSE `GET /stream` (sample: `fixtures/stream_sample.txt`) | New outages and re-ranks appear without a reload, with a small ping | 🟡 06:05: refetch on `/stream` + events/s; ping not yet ✅ *(Sali 07:25: on `main` and live at https://148-100-78-95.sslip.io:8443; ui-audit fixes applied)* |
| 7 | **Predict strip** (top of the control room) | `GET /api/areas/risk`, `GET /api/grids/gb/stress`; home layer from Nate later | The three layers with honest lead times: area tomorrow (label BASELINE), grid now, homes at risk in 30 min ("no data" until Nate's model is served) | ✅ 06:05 |
| 8 | Agent + grading panel | `GET /api/agent/decisions`, `GET /api/agent/grades` | Decision feed; "graded N real restorations"; Brier by operator and horizon (`by_horizon`) and the hourly `trend` | 🟡 06:05: grading done (count, trend, by operator + horizon); decision feed not yet ✅ *(Sali 07:25: on `main` and live at https://148-100-78-95.sslip.io:8443; ui-audit fixes applied)* |
| 9 | Source health | `GET /api/sources/health` | A LIVE / stale badge per feed (UKPN, NPg, SSEN, Elexon, IODA) | ✅ 06:05 |
| 10 | Audit view | `GET /api/audit/verify` | Verify: green with row count and last checkpoint. Tamper: red with `first_bad_seq` | ⬜ ✅ *(Sali 07:25: on `main` and live at https://148-100-78-95.sslip.io:8443; ui-audit fixes applied)* |
| 11 | CAP alert + SMS preview | `GET /api/alerts/cap/{decision_id}` (sample: `fixtures/cap_alert_sample.xml`) | Phone mock-up of the alert "awaiting approval"; SMS template with actions and the reserve clock. Ahmed's real phone receiving it can be a video shot | ⬜ ✅ *(Sali 07:25: on `main` and live at https://148-100-78-95.sslip.io:8443; ui-audit fixes applied)* |
| 12 | **"My home"** (household login) | `POST /api/auth/login` (household, from `households.txt`); `GET /api/me/home` | Power state, reserve clock, next action, grid line "the same for everyone", and the **option C `risk` block: one badge (low / elevated / high / unknown) with the three layer gauges underneath**, each with source, horizon and "updated"; a `null` value means "no data". Never an ETA. Shape: `contracts/openapi.yaml` → `MyHome.risk` | ⬜ ✅ *(Sali 07:25: on `main` and live at https://148-100-78-95.sslip.io:8443; ui-audit fixes applied)* |
| 13 | Labels everywhere | the `label` field in responses | LIVE / SIMULATED / REPLAY / TRANSFERRED / BASELINE badges on every panel that shows data | 🟡 06:05: on outage list, Predict strip and charts; more as panels land ✅ *(Sali 07:25: on `main` and live at https://148-100-78-95.sslip.io:8443; ui-audit fixes applied)* |

**Finish**
14. 🟡 `ui-audit` + `frontend-performance`; build statically and hand `dist/` to Ahmed's nginx (`:8443`). *(Sali 07:25: ui-audit done (static, no browser here; independent review + research ledger in the research doc), fixes applied; `dist/` built on the laptop and live behind Ahmed's nginx. Still open: `frontend-performance` (Vite warns the main chunk is over 500 kB, mostly MapLibre) and a look in a real browser at 375 / 768 / 1280 px)*
15. ⬜ **Recordings** at 1080p in a browser showing the VM IP: map, two-houses, triage + approve, Predict strip, my home, audit tamper, CAP preview.
16. ⬜ **Video edit lead:** captions burned in, ≤3:00, everyone on screen. Ready by 09:15 (Sali submits at 09:30).
17. ⬜ *(P2, cut first)* Globe intro, 30 min max.

## 4. Done log (newest first)
- (empty)

## 5. Waiting on / owed to others
- 📥 **Waiting on @sali:** fixtures + API (by about 23:30), SSE, `/me/home`, `/alerts/cap`.
- 📥 **Waiting on @nate:** `docs/results.json`, the risk GeoJSON.
- 📥 **Waiting on @ahmed:** the decision-log format; nginx serving `dist/`.
- 📤 **Owed to ALL:** UI recordings by 07:00; the video edit by 09:15.

## 6. Working-style notes for the agent
- Clarity for judges over feature count. One idea per panel.
- Verbosity Level 0.

## 7. Reference
- **MapLibre globe:** `map.setProjection({type:'globe'})`.
- **CAP 1.2:** https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2.html
- **Demo script:** PRD §17. **Privacy:** PRD §14.

---
── Archived (superseded 2026-10-17 — do NOT action) ──
- **The v2 task list (17 items):**
  - contract freeze, design direction, shell + map, gauge, skeleton by 18:00
  - triage, two-houses card on SSEN, SSE, agent panel
  - the "how different are these grids?" panel, audit view
  - globe intro (1 h), SMS preview + field briefing page
  - ui-audit, 23:00 freeze, recordings, video edit
- **Why superseded:** PRD v3. The grid-difference panel is parked. Added: CAP preview, "my home", the risk overlay, and the agent tool-call feed. Freeze moves to 03:00.

── Archived (superseded 2026-10-18 06:05 — do NOT action) ──
- **Why superseded:** the task list is now organised by backend coverage, keeping Rama's own design choices; the old times (00:30 skeleton, 03:00 freeze) predate the team starting.

#### Old list (2026-10-17 v3, with the 02:40 and 05:40 status notes)
**Status update 2026-10-18 02:40 (from Sali)**
**🔄 Headline changed 2026-10-18 (ADR):** "Blacknaught **predicts blackouts before they happen** and **protects the people they'd hurt most**."
- **Prediction layers:**
  - area fault risk (hours to days);
  - home sensors (minutes): flags homes likely to lose power in 30 min; real Accra probe: 1 in 5 top alerts true, 9× chance;
  - grid stress (seconds, NESO).
- **Triage + alerting** of electricity-dependent people stay the core of "who this helps".
- **Never say:** "predicts every blackout", "minutes ahead from frequency", "voltage dips warn of blackouts" (the probe shows ≈ chance).
- **▶ 2026-10-18 05:40 (from Sali): home-dashboard risk = option C.** "My home" shows one headline badge (**Low / Elevated / High**) with the three layer gauges underneath: home (next 30 min), area (tomorrow), grid (now). Each gauge shows its source, horizon and "updated" time; a layer with no data shows "no data", never Low. It arrives as a `risk` block in `/api/me/home` (shape in `contracts/openapi.yaml` once Sali ships it; exact rules still being confirmed).
- **UI implication:** a "Predict" strip on top of the control room, with the three layers and their honest lead times: tomorrow's district risk (`/api/areas/risk`), homes at risk in the next 30 min (once Nate's layer 2 is served), grid stress (`/api/grids/gb/stress`). Then the existing "Protect" views below: triage, two-houses, approvals, CAP.
- **Start with `progress.md` → "Start here"** on GitHub (clone, hooks, `scripts/sync-context.sh`, VM access).
- ⚠ **Times in this brief (00:30 skeleton, 03:00 freeze) predate the team starting.** Sali will confirm a new freeze time on Discord; until then, prioritise top-down.
- **The backend API is live on the VM.**
  - Every endpoint is under `/api/*`, plus SSE `/stream`; interactive docs at `/api/docs`.
  - Reach it with a tunnel once your key is on the VM: `ssh -N -L 8000:localhost:8000 linux1@148.100.78.95` → `http://localhost:8000`.
- **Mocks:**
  - `fixtures/api/*.json` are validated against the live response models;
  - new samples: `cap_alert_sample.xml` and `stream_sample.txt` (every SSE event type).
- **Logins:**
  - **operator** (approvals): password in the VM's `~/BlackNaught/secrets/operator_pw`;
  - **households** (`/api/me/home`): `~/BlackNaught/backend/secrets/households.txt`.
  - Logins are cookie sessions on `/api`.
- **Your branch `Rama-Frontend` is 42 commits behind `main`:** run `git merge origin/main` first (an open `progress.md` item).

1. ⬜ **Send your public SSH key to Sali** (or Ahmed). Rebase `Rama-Frontend` on `main` (new `.gitignore`) and resolve the `progress.md` conflict entry.
2. ⬜ **Contract freeze:** review `contracts/openapi.yaml` + fixtures; ✅ them in `progress.md`. `[⚠ shared with ALL]`
3. ⬜ **Design direction:** a control-room look, dark-first, colour-blind-safe severity palette, readable at 1080p.
4. ⬜ **App shell + map:** MapLibre on GB, with outage areas by scale (home / street / area / region / system) and fixed cells from fixtures.
5. ⬜ **🎯 Walking skeleton by 00:30:** the map pulls live `/outages` from Sali's API on the VM. `[⚠ @sali API up]`
6. ⬜ **🌟 Two-houses card, the demo centrepiece.** On one **real** live fault:
   - **House A:** oxygen concentrator, cylinder with 4 h left, P(still off in 4 h | already 1 h) → **escalate**.
   - **House B:** ventilator with 15 h → expected case, SMS check, no alarm.
   - Readable in under 10 s.
7. ⬜ **Triage list:** ranked by harm-hours; expected case → range → "why ranked here"; an approve button (POST `/decisions/{id}/approve`). `[⚠ @sali]`
8. ⬜ **Agent panel:**
   - a live feed of tool calls from `/agent/decisions` (e.g. "assign_visit: 5 workers, 12 patients, 3 waiting, why");
   - "Graded N real GB restorations since 02:00", with a Brier trend and calibration by region.
   - `[⚠ @sali + @ahmed]`
9. ⬜ **SSE live updates** from `/stream`, with pings on new outages and re-ranks. `[⚠ @sali SSE]`
10. ⬜ **Audit view:** verify button, tamper → red, the checkpoint hash. `[⚠ @sali /audit/verify]`
11. ⬜ **CAP alert preview** (phone mock-up, "awaiting approval") and **SMS template preview** (actions + reserve clock). `[⚠ @sali /alerts/cap]`
12. ⬜ **Risk overlay for tomorrow (P1):** district choropleth from `/areas/risk`. `[⚠ @nate + @sali]`
13. ⬜ **"My home" view (P1):** login, own power state, own voltage with brownout bands, reserve clock, next action, and a frequency line labelled "grid health: same for everyone". `[⚠ @sali /me/home auth]`
14. ⬜ **Grid gauge (P1):** stress state + LIVE/REPLAY badges.
15. ⬜ **Globe intro (P2, 30 min max).** Cut it first.
16. ⬜ **`ui-audit` + `frontend-performance`.** Build statically and hand `dist/` to Ahmed.
17. ⬜ **03:00 freeze.** Sleep in shifts.
18. ⬜ **06:00–07:00:** screen-record the UI segments at 1080p in a browser showing the VM IP.
19. ⬜ **Video edit lead, 07:00–09:15:** captions burned in, ≤3:00, everyone on screen.

