# Blacknaught: the project doc
*IBM Z Datathon 2026 · Manchester hub · repo `github.com/saliha006/BlackNaught` · merged 2026-10-18 from the PRD, the backend design doc and the parked v2 sections.*

**How to read this:** **NOW** is what's true and in progress today; start there. **Part A** is the spec (product, data, models, architecture, security, demo). **Part B** is the backend design per feature. **Parked** holds options that were doable but not chosen. **History** says how we got here.
- Rules, judging and event context: `DATATHON-CONTEXT.md`.
- Evidence ledger: `DATATHON INFO/research-and-codebase.md`.
- Your own tasks: `builder-file-<name>.md`.
- Live status and conflicts: `progress.md` on GitHub.
- Superseded originals: `_archive/` (local only).

---

## NOW (updated 2026-10-18 07:25)

### Headline
**Blacknaught predicts blackouts before they happen and protects the people they'd hurt most.**

| Layer | Predicts | Honest lead time | Status |
|---|---|---|---|
| Area fault risk | Districts likely to have faults tomorrow | Hours to days | Climatology baseline **live** (`/api/areas/risk`); Nate's M8 adds weather |
| Home sensors (fuse box / meter) | Homes most likely to lose power in the next 30 min | Minutes | **Probe on real Accra data:** top-1% alerts come true 1 in 5 (9× the 2.1% base), ROC AUC 0.67. Nate builds the served model |
| Grid stress | Grid-wide frequency collapse | Seconds | Live gauge (band rule); NESO replay validation is Nate's M4 |
| **Protect** | Who runs out of backup first, then alert carers, health workers and responders | During the cut | **Live:** triage, grading, approvals, CAP, `/me/home` |

**Never pitch:** "predicts every blackout", "minutes ahead from frequency", "voltage dips warn of blackouts" (≈ chance in the probe), or "every country".

### Decisions in force
Full records with the rejected options: Sali's vault Log (Sali); the summary is here for everyone.

| Date | Decision |
|---|---|
| 18 Oct | **Frontend cover (06:39):** Rama's Claude usage ran out; Sali continues Rama's list on `Rama-Frontend`, keeping his design choices. Backend paused but live |
| 18 Oct | **Live duration curve = `m1-km-ukpn`** (Nate, decision C): M2 stays offline because it loses to Kaplan–Meier on UKPN; the KM curve refitted on UKPN wins (integrated Brier 0.1297 vs 0.1311). Live since 06:39 |
| 18 Oct | **Home dashboard = option C:** one headline risk level (Low / Elevated / High) from simple worst-signal rules, with the three layer gauges (home 30 min, area tomorrow, grid now) underneath, each with source + horizon. No blended probability. Rules (Sali, 06:00): **High** = home flagged OR grid EMERGENCY; **Elevated** = area in the top third OR grid STRESSED; **Low** only when all three layers report and none flags; otherwise **unknown**. Live in `/api/me/home` → `risk` |
| 18 Oct | **Sali, 06:00:** `sensor` table as Ahmed asked (0010); Ahmed's `infra/docker-compose.yml` layout OK'd; Elexon readings outside 45–55 Hz dropped; Ahmed's mocked public alert (CAP → his phone over ADB) approved; Nate's context-script fix adopted (teammates publish only their own brief; `git config blacknaught.builder <name>`) |
| 18 Oct | **Headline = predict + protect** (the line above). Reverses 17 Oct "triage only"; triage stays as the co-headline |
| 18 Oct | **Shared docs live on the public repo's `context` branch** and auto-sync to every agent each prompt (`scripts/sync-context.sh`). Only Sali publishes. **Delete the branch before submission.** Reverses 17 Oct "docs never on GitHub" |
| 18 Oct | **Docs merged:** `BLACKNAUGHT.md` + `DATATHON-CONTEXT.md`; off-vision material archived locally |
| 18 Oct | **Individual SSH keys** for all four. The leaked shared `.pem` was removed from the VM. Ahmed still needs to turn off the Drive link and change the portal password |
| 17 Oct | **Countries:** GB is the proving ground; **Ghana** is the lead target (OOP 26.7%, real nLine sensor data); **Sri Lanka** second (OOP 54.8%, stated); South Africa is a reference; Bangladesh and Pakistan are parked. Free healthcare = free at the point of use **and** OOP < 30% |
| 17 Oct | **Training data:** ENWL (312,936 outages) + UKPN IIS (316,435), downloaded **onto LinuxONE** via API keys. Non-commercial data (nLine Accra) is accepted and credited |
| 17 Oct | **Models:** M2 duration survival + M8 area fault risk. No Kaggle simulated-fault classifier. OpenDSS physics sim is roadmap only (no s390x build) |
| 17 Oct | **Household view:** login-gated "my home", own data only, never an ETA. Map cells k≥11 only |
| 17 Oct | **Stack:** IBM lab image + FastAPI/uvicorn + pg8000 + Postgres 17. AES-256-GCM via libcrypto (CPACF). Operator login for approvals. Demo URL `https://148.100.78.95:8443` (post-quantum TLS, Ahmed's edge). Dependencies approved (Part B §B21) |
| 17 Oct | **Docs stay local** (git-ignored); only `progress.md`, `README.md` and `contracts/*.md` go to GitHub. Docs are shared as a bundle |
| 17 Oct | **Park, don't cut:** CAP, `/me/home`, IODA were parked, then built since time allowed |
| 17 Oct | **Build-time choices:** q90 = no second source AND reserve < 2 h; KM fallback until M2; area risk labelled BASELINE until M8; CAP status `Exercise`; signing key never inside the app; IODA ping-slash24 < 0.9 for 2 windows, ignored when ≥3 countries dip together; synthetic patients only on faults < 6 h old |

### Pending decisions
- **New freeze time.** Briefs still say 03:00; the team started later. Deferred: Sali decides later.
- **M2 live-feature list** (Nate + Sali; `contracts/model.md`). Waiting on Nate.
- **NNPA on/off timing in the video:** Ahmed is asking #helpdesk (ToU §5 bans benchmarks).
- **Off-box audit-checkpoint publishing** (Ahmed).
- **Vercel mirror of the UI:** optional; the demo stays on the VM IP.

### Active tasks (executing now; details in each brief)
| Who | Now |
|---|---|
| **Sali** | Backend live (signing, `m1-km-ukpn`, option C, triage↔decision link). **Frontend (Rama's list):** rows 5–13 ✅ live at https://148-100-78-95.sslip.io:8443; row 14 🟡 (performance pass + real-browser check). Then recordings, video segment, submit 09:30 |
| **Ahmed** | Edge (nginx, PQ TLS, public `:8443`); signer (`/sign`, `/verify`); agent loop via `decisions.create()`; sensor sim + Accra replay; NNPA serving; **mocked public alert to his phone**; ask #helpdesk about NNPA timing; Drive link + portal password (**urgent: fragments were in a public script, now removed**). Labs 01+02 ✅ |
| **Nate** | M2 (replaces KM behind `contracts/model.md`); home-sensor early-warning model (from `backend/app/probe_precursor.py`); M8 weather risk; M4 NESO stress |
| **Rama** | **Claude usage out since ~06:50; Sali continues his list.** Brief reorganised 06:05 by backend coverage (13 features), his design choices kept; **push work to `Rama-Frontend`**. Control-room UI on the live `/api/*` + `/stream`: a "Predict" strip on top, then "Protect" views (triage, two-houses, approvals, CAP preview, my home); recordings; video edit |

### Blockers only humans can clear
- ~~Team name; team leader~~ ✅ **The 4 Musketeers**; **Sali is team leader** and submits. Title: `[The 4 Musketeers_IBM Z Datathon 2026 Project]`.
- ~~IBM labs 01 + 02~~ ✅ done by Ahmed.
- ~~README for judges~~ ✅ on `main` (teammates: update your row in its status/limits as your part lands).
- ~~GitHub collaborators with Write~~ ✅ all three.
- Rama to test VM login.

---

# Part A: Product spec

## 0. One page

**One-liner (headline as of 2026-10-18):** Blacknaught **predicts blackouts before they happen** and **protects the people they would hurt most**.
- An AI model trained on grid fault history, and on sensors at the home's fuse box or meter, flags where power is likely to fail.
- When a cut does happen, it ranks which electricity-dependent patients run out of backup first, and alerts carers, health workers and responders.
- An agent plans who gets reached, acts, and grades itself against what really happened.
- All of it runs on LinuxONE.

**How far ahead "before" honestly reaches** (ADR 2026-10-18; never claim more):

| Layer | Predicts | Lead time | Data / status |
|---|---|---|---|
| Area fault risk | Which districts are likely to have faults tomorrow | Hours to days | ENWL 1997–2026 history (baseline live); M8 adds weather |
| Home sensors (fuse box / meter) | Which homes are most likely to lose power in the next 30 min | Minutes | **Probe on real Accra GridWatch data (2026-10-18):** ROC AUC 0.67; top-1% alerts come true 1 in 5 (9× the 2.1% base). Signal = unstable supply + time of day; low voltage alone ≈ chance. Pitch: "flags", never "predicts every blackout" |
| Grid stress | A grid-wide frequency collapse | Seconds | NESO 1-s replay (9 Aug 2019) + live Elexon |
| **Then protect** | Who runs out of backup first, and who to alert | During the cut | Triage + agent + CAP alerts (live) |

**Where it came from.** It started as **Dark Hours**: "during a power cut, tell the welfare team which medically dependent households will run out of backup before the power returns." v3 keeps that core. It adds the team's pivot:
- a sensor at the fuse box;
- localising faults to a home, an area or a region;
- predicting which areas are likely to fail, from history;
- amber-alert-style public warnings;
- working on any grid through configuration.

**What is real tonight (not a mock-up):**
1. **Live GB faults with real locations.** UKPN, Northern Powergrid and SSEN publish postcodes, lat/long and feeder IDs, with no key needed. Live GB frequency comes from Elexon.
2. **A duration model trained on LinuxONE** on **312,936 real outages** (ENWL, CC BY 4.0, 2000–2026). It is validated on a second operator, UKPN, and served on the **Telum NNPA**.
3. **An area fault-risk forecast for tomorrow:** ENWL fault history joined to real weather from Open-Meteo, following a published Glasgow method.
4. **The localiser is scored against real fault footprints.** Simulated fuse-box sensors are placed in the real affected postcodes of real faults, with realistic noise, and graded against the network operator's own record.
5. **Real household sensor data from a recurring-outage grid:** nLine GridWatch Accra, 1,300 plug-in sensors measuring voltage, frequency and power state.
6. **An agent that ran overnight**, grading its predictions against real GB restorations.

**Novelty line:** *Outage maps say a street is off. Priority-service registers say someone vulnerable lives there. Restoration-time models guess when power returns. None of them asks whether this person's oxygen lasts longer than this outage. Blacknaught does, then acts on it: it ranks people by the calibrated chance that this outage outlasts their backup, allocates scarce responders, and grades itself live. It runs on LinuxONE, where the patient register is encrypted.*

**Track:** Theme 1 (Real-Time AI for Critical Decisions). Theme 2 is built in: an encrypted register, signed models, a tamper-evident audit trail and post-quantum TLS.

---

## 1. Vision (start to finish)

**The 3-year picture:**
- A national health authority (the NHS in GB, or a ministry of health elsewhere) runs Blacknaught as a **decision service**.
- Electricity-dependent patients are enrolled at hospital discharge, with consent.
- A small sensor at each enrolled home's fuse box, plus a few anchor sensors per street, reports power state every few seconds.
- The grid operator shares its fault feed through an API.
- When power fails:
  1. Blacknaught knows within about a minute **whether it's one home, a street, an area or the whole grid**.
  2. It predicts **how long** the outage will last and **who runs out of backup first**.
  3. It **acts**: an SMS to the carer, a task list for field workers, a cylinder request to the oxygen supplier, a pre-filled escalation to emergency services. For big events it drafts an **area-wide public alert** in the standard Common Alerting Protocol (CAP 1.2) format, ready for the government's cell-broadcast channel.
  4. Every action is logged and signed, and every prediction is graded against what really happened.
- **Between outages**, it forecasts which areas are likely to fail tomorrow, so preparation happens before the dark.

**How it grows to other countries (honestly):** the pipeline is grid-agnostic. Adding a grid needs four things:
1. a config file (frequency, voltage, threshold ladder, load-shedding stages, timezone, weekend, seasons);
2. some local labelled history, **or a few weeks of our own sensor data**, since sensors generate the labels that countries lack;
3. a grid-data agreement;
4. a health partner holding the register.

"Every country" is not the claim. The claim is that **any recurring-failure grid can be added through config plus local labels**. §5 lists the first target grids.

**Business model (one line):** a per-district SaaS licence paid by health authorities or donors. Sensor fleets are funded by pilots.

---

## 2. Problem and evidence (ledger §1, §9–§13)

**People who die in power cuts:**
- **The core device is home oxygen.**
  - A static concentrator has no battery and stops with the mains.
  - Cylinder backup lasts about 8–20 h, depending on flow.
  - Ventilator batteries last about 15 h on modern models (Trilogy Evo) and about 6 h on older ones.
  - Home dialysis is mostly CAPD, which needs no power, so it is not a headline case.
- **UK coroners, 2026:**
  - Peter Coates: a power-dependent man alone in a power cut rang 999 and got a Category 2 response. The system "cannot tell that a caller's medical devices have lost power".
  - Janette Palmer: a supported-living block was missing from the Priority Services Register.
  - ⚠️ Never say "a welfare call would have saved him".
- **Ofgem, Storm Arwen:** people were cut off for 2.5–11 days, and most people on the register recalled no proactive contact. Which? found that digital landlines and telecare fail in power cuts.

**Why sensing matters:**
- Official figures undercount outages. Independent sensors in Accra logged about **2× the outages the utility recorded** (Klugman, IPSN 2021).
- Pakistan's regulatory statistics exclude generation and transmission outages.

**Prior art, named openly:**
- US HHS emPOWER (including emPOWER AI)
- the UK Priority Services Register
- Australia's NERR life-support rules (enforcement shows the registers fail on admin)
- DNO outage maps and the networks' national outage view for government

None of them ranks individual patients by P(outage outlasts their reserve) or acts on that ranking. **That gap is the novelty claim, and the only one.**

**Frequency truth** (the team's ±1 Hz assumption; ledger §12.7). It is partly right:
- Big frequency swings do mean grid-wide trouble.
- But ±1 Hz is **late**. Automatic load-shedding (LFDD) starts at 48.8 Hz in GB and 49.0 Hz in Continental Europe. In GB in 2019, LFDD cut 1.1 M customers and there was still no blackout.
- Some blackouts start on **over-frequency or voltage**: Pakistan 2023 rose to 50.75 Hz, and Iberia 2025 was voltage-led.
- **Frequency is identical across a synchronous grid**, so a feeder, transformer or house fault leaves no trace in it. ENWL alone logs about 12k local faults a year, while GB's LFDD has fired twice since 2008.

**So:** frequency is used as a **system-stress layer**. Local outages are detected by **fault feeds and sensors**, and predicted from **fault history plus weather**.

---

## 3. Goals, non-goals, success metrics

**Goals:**

| Goal | What it means |
|---|---|
| G1 Detect | Classify every outage by scale (home / street / area / region / system) within about 2 min of the data arriving |
| G2 Predict | Give a calibrated remaining-duration distribution for each outage, and tomorrow's fault risk for each area |
| G3 Decide | Rank patients by expected harm-hours, with a capacity-aware plan for field workers |
| G4 Act | Draft and send the actions: SMS templates, task lists, supplier requests, escalations, CAP area alerts. Anything sent to more than one person, or any escalation, waits for human approval |
| G5 Learn | Grade every prediction at +2 h and +4 h against real restorations, and recalibrate |
| G6 Trust | Keep the register encrypted, models signed, the audit trail tamper-evident, and links post-quantum. Never show a patient on a map |

**Non-goals (v3):**
- Fault detection from raw waveforms (no real open labels exist).
- Minutes-ahead blackout prediction from frequency.
- Real patient data (Marist ToU §9).
- Physics simulation on the VM: OpenDSS has no s390x build.
- "Every country in the world".

**Success metrics for the demo:**

| Metric | Target or evidence |
|---|---|
| M2 duration model | Brier at 2/4/8 h, C-index. Beats or matches Kaplan–Meier on the 2024–26 time split, with the margin stated honestly. Cross-operator check on UKPN |
| Area fault risk | Brier skill score > 0 against district climatology on a time split |
| Localiser | Postcode precision and recall against real DNO footprints, under injected noise |
| Agent | N real GB restorations graded overnight; 3 logged decisions; memory survives a restart |
| LinuxONE | Training logs from the VM; NNPA inference live; signed-model refusal; post-quantum handshake; audit-tamper demo |

---

## 4. Users, journeys and outputs

| Actor | Gets | Decision |
|---|---|---|
| **Control room** (district health office, data controller) | Dashboard: map, triage list, agent panel, approvals | Approve escalations, CAP alerts and bulk SMS |
| **Field health worker** (GB community nurse; Ghana community health officer, CHPS) | A capacity-allocated visit list and an English briefing written by Granite | Who to visit or call first, and what to bring |
| **Patient / carer** | Fixed translated SMS templates plus a **"my home" view** | "Power is off. Your cylinder lasts until about 02:00. Switch to it now. Reply 2 if you need help." **Never an ETA** |
| **Hospital / emergency services** | An escalation recommendation with a context packet; a human approves it | Dispatch |
| **Public** (area-level) | A CAP 1.2 alert drafted by the agent, approved by a human, and handed to the government's broadcast channel | Prepare, check on neighbours |
| **Grid operator** | Aggregates only (k≥11) plus sensor-confirmed outages they may have missed | Prioritise restoration |

**Patient journey ("Ama", oxygen at 2 L/min, cylinder 10 h):**
1. Ama is enrolled at hospital discharge, with consent.
2. Power drops at 21:40. Her fuse-box sensor sends a "last gasp".
3. **2 of the 3 anchor sensors on her street** are also silent, so the scale is **street**. A DNO fault in her postcode arrives at 21:46, so it is **confirmed**.
4. The model says P(still off in 10 h | already 6 min) = 0.04, so it sends an SMS check and doesn't raise an alarm.
5. At 02:10 a feed goes stale and the outage is now 4.5 h old. The re-ranked probability of outlasting her remaining 5.5 h of reserve is 0.41.
6. The agent puts her on the 07:00 visit list with a cylinder and messages the oxygen supplier. A human approves.
7. The power comes back at 05:52. The agent grades its +2 h and +4 h predictions.

**"My home" view** (team ask, made privacy-safe):
- It is login-gated and shows **only that household's own data**: power state, its own voltage over time with brownout bands, its reserve clock, and the next action.
- National frequency appears as a context line labelled "grid health: the same for everyone".
- It is never on the shared map and has no lookup by area or coordinate. This rests on the GDPR right of access (Art. 15); k≥11 governs what *others* see.

---

## 5. Countries and grids

**Approach:** prove everything on **Great Britain's** open data, which has the richest outage history in the world that's open. Then calibrate for target grids through `grids/<id>.yaml` plus local data.

**Country filter (team requirement):** frequent outages **and** free or universal public healthcare, with open data usable tonight. If a candidate fails on healthcare, say so.

**Target set (confirmed by Sali 2026-10-17; ledger §13).** The healthcare rule is: free at the point of use **and** out-of-pocket (OOP) spending below 30%.

| Role | Grid | Outages | Healthcare | Open data tonight | Use in the build |
|---|---|---|---|---|---|
| **Proving ground** | **Great Britain** | ~12k local faults/yr (ENWL alone); storms | NHS (free) | ENWL, UKPN, live DNO feeds, NESO, Elexon | Everything trained and graded live |
| **Lead target** | **Ghana** | 73.8% of firms report outages (2023); dumsor 2024; Apr 2026 outages after the Akosombo substation fire | NHIS + Free Primary Healthcare (Apr 2026, 150 districts); **OOP 26.7%** | **nLine GridWatch Accra:** real household voltage, frequency and power state, 2-min resolution, 2018–Jun 2024, including the 2024 dumsor | F13 replay: real sensors drive the classifier and brownout detector; config-only onboarding |
| **Second target** | **Sri Lanka** | National collapse 9 Feb 2025 (4.5 h, then 4 days of rotating cuts); Dec 2023 blackout; 2022 cuts of 13 h/day | Free public care, **but OOP 54.8%** (say so) | PUCSL 2025 collapse timeline; verified UFLS relay settings; IODA raw signal (an ~18% dip on 9 Feb 2025) | `grids/lk.yaml` with a real UFLS ladder; system-event replay (stress + IODA) |
| Reference | South Africa | 205/332 load-shedding days in 2022/23; **none since 16 May 2025** | OOP 6.7% | eskom-calendar area schedules (CC BY-NC-SA, archived); Eskom portal (licence not stated) | Staged-shedding model in the YAML (NRS 048-9, stages 1–16); pitch only |
| Parked | Bangladesh, Pakistan | Severe | OOP 79.3% / 52.9%, so they fail the filter | PGCB / NEPRA | "The same method applies"; `BLACKNAUGHT-PRD-v2-parked.md` |

**YAML seeds:**
- **Ghana:** 50 Hz, 230 V ±10% (PURC), Africa/Accra, Sat–Sun weekend. The threshold ladder is ⚠ UNVERIFIED (the grid-code PDF was blocked), so mark it unverified.
- **Sri Lanka:** 50 Hz ±0.5%, 230 V ±6%, Asia/Colombo. UFLS (CEB 2015 scheme, PUCSL 2016) sheds at 48.75 / 48.50 / 48.25 / 48.00 / 47.5 Hz, plus a 49.0 Hz with df/dt < −0.85 Hz/s stage. The scheme was revised in 2018, so mark it ⚠. Inverters trip at 47 Hz. **The grid collapsed 22 s after the fault.**
- **South Africa:** 50 Hz, 230 V (tolerance ⚠), Africa/Johannesburg, stages 1–16 of about 6.25% of demand each.

**Kaggle:** there is no Ghana data. The South Africa and Sri Lanka uploads re-license or omit their sources, so they are **DO NOT USE** (§13). Non-commercial data (nLine, eskom-calendar) is accepted and stated in the README.

**Per-grid config (`grids/<id>.yaml`):** no constants in code. Every value carries its source and year:
- `nominal_hz`, `nominal_v`
- `thresholds[]`: the ordered ladder, including over-frequency rungs
- load-shedding stages
- subregions / synchronous areas
- IANA timezone
- weekend days
- seasons
- reliability definition
- fragility profile
- `telco_backup_hours`
- `labels_source`: where local outage labels come from

A 60 Hz or 240 V grid needs only a new file.

**Normalisation (kept from v2 §3.2):**
- Frequency in per-unit.
- **Stress = time to this grid's own next protection rung**, multiplied by its fragility.
- A robust z-score for the "unusual for this grid" flag (display only).
- Voltage in per-unit, compared with the statutory band and each device's `vmin_pu`.
- Every outage series is harmonised to **one 5-minute threshold** before any comparison.
- Regulatory statistics are treated as a lower bound.

**Clinical, not regional, caution (v2 §3.3 kept):**

| Patient situation | Quantile used | Why |
|---|---|---|
| No backup | 90th percentile | A miss costs a life |
| Reserve > 2× the median remaining outage | Median | Avoids alert fatigue |
| Everything else | 75th percentile | — |

A region is never treated worse just because it is usually bad. The median never overrides an escalation driven by the 90th percentile.

---

## 6. Features

Owners: **S** Sali (backend) · **A** Ahmed (platform + agent) · **N** Nate (data/ML) · **R** Rama (frontend)

Priority:
- **P0** must ship before the freeze (03:00)
- **P1** ship if time allows
- **P2** roadmap (slide only)

| # | Feature | What it does | Real or simulated | Pri | Owner |
|---|---|---|---|---|---|
| F1 | **Live grid ingest** | **P0:** UKPN, SSEN and NPg every 120 s; Elexon every 30 s (from/to set); postcodes.io bulk geocoding with a cache (30-day TTL). One outage schema with deterministic `event_id`s. A record missing from 2 polls is marked **"vanished", never "restored"**. Restore times: UKPN explicit, SSEN approximate, NPg detection-only. **P1:** IODA every 10 min. Open-Meteo lives in Nate's daily M8 job | LIVE | P0 | S |
| F2 | **Fuse-box sensor simulator, driven by real faults** | Synthetic sensors (heartbeat 60 s, last gasp) sit at enrolled homes plus 2–3 anchor sensors per street. Each real fault's affected postcodes go silent at the real start and return at the real restoration. Control postcodes stay on. Noise: about 74% uptime, dropouts, sensors behind backup, "1 in 3 homes" partial outages. About 5k sensors normally; a **load-test mode** (60–120k sensors) gives the measured events/s we quote. Heartbeats stay in memory; only state transitions are stored | SIM, on real footprints | P0 | A |
| F3 | **Scale classifier + evidence combiner** ("is it just my house?") | Quorum rule: home / street / area / region / system / BROWNOUT / unresolved. A naive-Bayes combiner with **hand-set** likelihood ratios fuses sensors, DNO feeds, IODA and grid stress into P(outage) per cell. A DNO-declared fault in the postcode gives ≈1.0; otherwise the prior is the historical fault rate. A stale source has LR = 1. **Silence never means "no outage"** | LIVE + SIM | P0 | A (combiner), N (LR table) |
| F4 | **Outage-duration model M2** | XGBoost AFT plus a Keras discrete-time hazard MLP (24 hourly bins), trained **on the VM** on ENWL and validated on UKPN. Conditional P(T > t + r \| T > t). The Keras model is served in batches on **NNPA** | REAL data | P0 | N (A serves) |
| F5 | **Triage: expected harm-hours** | E[harm] = severity × P(no other backup) × E[max(0, T_remaining − r)]. Escalate if Q_q(remaining) > r, with q from §5. A single unanswered welfare check escalates on its own. SMS can escalate but can never de-escalate a no-backup patient | REAL model, SIM people | P0 | S (N's predict) |
| F6 | **The agent** (§9) | A 60 s loop: perceive → assess → plan → act → observe → learn. Tools include allocate, notify, escalate, draft_cap_alert, write_sitrep and recalibrate. SMS goes to a **simulated outbox**. Memory in Postgres survives restarts. It runs overnight | LIVE | P0 | A (S tables) |
| F7 | **Horizon grading** | Logs one prediction per outage every 15 min, from about 00:30, starting with the Kaplan–Meier fallback. Grades at +2 h and +4 h against real restorations. **UKPN is primary; SSEN is marked approximate; NPg is excluded.** Rows that vanish or go stale before a horizon are censored: excluded, counted and bounded. Writes Brier scores by region | LIVE | P0 | S |
| F8 | **Granite actions** | On the VM, Granite 3.3 2B BE runs through the lab image's `llama_cpp_python`. It writes an English field briefing, a welfare-call script, a situation report and the text of the CAP alert. A validator rejects any number that isn't in the decision record. **Delete Granite and every decision stays the same** | LIVE | P0 | A |
| F9 | **Security core** | Signed models (ML-DSA-65, in a separate signer container), and the scorer refuses tampered ones. AES-256-GCM columns through **libcrypto via ctypes** (CPACF; the image has no `cryptography`; NIST test vectors). An HMAC blind index on postcodes. Hash-chained audit, appended only through a `SECURITY DEFINER` function, with ML-DSA checkpoints every 500 rows or 5 min. Least-privilege DB roles. **Operator login for approvals.** LUKS on the VM host. iptables default-deny. Custom Jupyter token | REAL | P0 | A + S |
| F10 | **Control-room UI** | MapLibre map (fixed k≥11 cells, never homes); live outage areas by scale; triage list; **two-houses card on a real fault**; agent panel; audit-verify view | — | P0 | R |
| F11 | **Area fault-risk tomorrow (M8)** | P(≥k faults in each ENWL district tomorrow). XGBoost Poisson on Open-Meteo ERA5 weather, season and base rate. Brier skill against climatology. The live run uses tomorrow's forecast and shows as a map overlay | REAL | P1 (first in) | N (S endpoint, R layer) |
| F12 | **Grid stress (M4)** | A rule: time to the grid's next rung × fragility. NESO 1-s replay of 9 Aug 2019 (thresholds fixed beforehand) plus live Elexon. Says "seconds of lead, not minutes" | REAL replay | P1 | N (A replay) |
| F13 | **Target-grid replay** | Real sensor data (Accra GridWatch, GPS coarsened off-box) drives the same classifier plus a brownout detector. Shows "a new grid added by config + its sensor data" | REAL sensors | P1 | N + A |
| F14 | **"My home" view** | §4: own voltage, reserve clock, next action, frequency context. Session login (argon2id, HttpOnly cookie, no ID in the URL). **🅿 Parked: built if backend time allows** | SIM / Accra | P1 | R (S endpoint) |
| F15 | **CAP 1.2 area alert** | The agent drafts a CAP XML for area- or region-scale events with vulnerable people inside. A human approves it, and it is exported for the authority's channel. The XML is hand-written with ElementTree: `status=Exercise`, polygon = convex hull of the affected postcodes, XSD-validated in tests. The UI previews it as a phone alert. **🅿 Parked: built if backend time allows** | REAL format | P1 | S (A drafts) |
| F16 | **Target-grid shortage model** | A load-shedding episode or stage model for the target grid (§5). No open long-run series exists for Ghana or South Africa | — | P2 (roadmap slide) | — |
| F17 | Physics-sim fault location (OpenDSS, off-box) · smart-meter last-gasp integration · Pakistan/Bangladesh layer · public app | Roadmap | — | P2 | — |

---

## 7. Detection and localisation: how "where" works

Frequency can't localise. Three tiers can:

| Tier | Source | Resolution | Latency | Where it's real |
|---|---|---|---|---|
| 1. Operator feed | UKPN `fullpostcodedata`, NPg `postcode[]` + lat/long, SSEN feeder/transformer IDs | Unit postcode / feeder | Minutes | **GB live, tonight** |
| 2. Our sensors | A fuse-box sensor at each enrolled home plus 2–3 anchors per street; quorum ≥2 | Home / street | ~1–2 min | SIM on real footprints (GB); **real sensors** (Accra replay) |
| 3. Wide-area | IODA internet outages (province); load-shedding schedules/stages; grid stress from frequency | Region / system | 5–10 min | Live / replay |

**The fuse-box decision flow** (from the team's form, now formalised):
1. A sensor goes silent or sends a last gasp. Is a patient enrolled there? If so, their record is flagged.
2. Check neighbouring and anchor sensors in the same cell:
   - ≥60% silent within 5 min → **street/area event**;
   - several cells, plus an IODA dip or a shedding stage → **region**;
   - stress in EMERGENCY plus mass silence → **system**.
3. Only this home is silent while its anchors report → **"your home only"**. The action is an electrician or a prepaid top-up, and the **priority is not lowered**: no crew will come, so it can last longer.
4. Fuse the feeds. A DNO fault declared in this postcode → P ≈ 1.0. Otherwise the probability comes from the combiner, with the historical fault rate for that area and time (F11) as the prior.
5. Fewer than 2 anchors reporting → **scale unresolved**, shown honestly, with the patient's priority unchanged.

**Deployment notes:**
- Sensors sit **upstream of any UPS, IPS or solar backup**.
- Patient phones are used for SMS only, never as sensors (Android kills background apps).

---

## 8. Prediction models

| # | Model | Data | Trained where | Served where | Metric |
|---|---|---|---|---|---|
| M1 | Baselines: Kaplan–Meier per cause, log-linear | ENWL | VM CPU | CPU | Brier 2/4/8 h, C-index |
| M2 | **Duration:** XGBoost AFT + Keras discrete-time hazard MLP (24 bins) | ENWL 2000–22 train · 2023 val · 2024–26 test; UKPN cross-operator | **VM CPU** (the lab image) | **NNPA** (Keras, graph mode `model.predict`), with XGBoost on CPU | Brier, C-index, calibration per region |
| M3 | Recalibration: isotonic per horizon | Overnight grades | VM | CPU | Brier before/after |
| M4 | Grid stress: a rule | NESO 1-s, Elexon | — | CPU stream | Lead time to 48.8 Hz; false alarms per month |
| M5 | Evidence combiner: naive Bayes, hand-set LRs (GB DNO-feed weight learned) | Feeds + sensors | — | CPU | Scale accuracy against real footprints |
| M8 | **Area fault risk tomorrow:** XGBoost Poisson | ENWL faults × Open-Meteo ERA5 by district-day | **VM CPU** | CPU | Brier skill against climatology |
| M9 | Brownout / outage quorum on real sensors | Accra GridWatch | — | CPU | Agreement with `is_powered`; brownout rate |
| M7 | Granite 3.3 2B Instruct BE (Q4_K_M; Q8_0 if NNPA is tested) | — | — | VM (`llama_cpp_python`, zDNN build) | The number validator passes |

**Rules:**
- **Feature whitelist for ENWL:** cause, start time, season, voltage, primary substation, district, customers at start. **Never** customer-minutes or restoration columns, since those leak the answer.
- Time split plus group-by-event. 5-run event bootstrap.
- Models are saved as **XGBoost JSON and `.keras`**, never pickles across endianness. Spot-check predictions against the laptop.
- **Anti-wrapper rule:** "Language never decides. The survival model on NNPA and the agent do."

---

## 9. The agent (the agentic core)

**Why it's an agent, not a cron job:** it has a goal (minimise expected harm-hours under limited responders), it chooses among tools, it acts within guardrails, it observes outcomes and changes its own behaviour, and it keeps memory.

**Loop (every 60 s, `asyncio`, memory in Postgres):**
1. **Perceive:** new sensor events, feed updates, source health, approvals, SMS replies.
2. **Assess:** scale classification (F3) → duration (M2, NNPA batch over every at-risk household × outage) → harm-hours (F5).
3. **Plan:** a greedy knapsack on harm-hours avoided per unit of responder time. For example, 5 workers and 12 patients: who waits, and why.
4. **Act** (tools, each call logged and signed):

   | Tool | Effect | Guardrail |
   |---|---|---|
   | `notify_carer(patient)` | SMS template | Auto for a single person |
   | `assign_visit(worker, patients)` | Signed task list | Auto |
   | `request_supplier(patient, item)` | Cylinder request | Auto, logged |
   | `escalate(patient, service)` | 999 / hospital context packet | **Human approval** |
   | `draft_cap_alert(area)` | CAP 1.2 XML + Granite text | **Human approval** |
   | `write_sitrep()` / `field_briefing()` | Granite text, number-validated | Auto |
   | `mark_source_stale(src)` | LR → 1, widen intervals, re-rank | Auto |
   | `recalibrate(horizon)` | Isotonic correction (GB only), fitted on the ENWL validation split. Overnight grades are drift-checked; there are too few to refit on | Auto, logged before/after |

5. **Observe:** at +2 h and +4 h, grade predictions against real restorations (F7), using the feed's explicit restored status. A record disappearing from the feed is not treated as a restoration.
6. **Learn:** if Brier drifts, apply a horizon-specific recalibration and log it.

**The three decisions it makes on screen:**
1. Capacity allocation: who is dropped, and why.
2. Source failure: a stale feed widens the interval, and a patient crosses the threshold and is re-ranked.
3. Self-correction: overnight grades lead to recalibration.

**Guardrails:** humans approve anything sent to more than N people or escalated. Only signed task lists leave the box. SMS "power back" never de-escalates a no-backup patient on its own. Memory survives a restart (shown on screen).

---

## 10. Data

| Role | Dataset | Licence / access | Verdict |
|---|---|---|---|
| **Train M1/M2/M8** | **ENWL Historic Unplanned Outages**: 312,936 events, 2000–2026; fields incident/restoration time, cause, district, primary substation, voltage, customers | CC BY 4.0; free registration (**blocking: do it first**) | KEEP |
| Validate M2 | **UKPN Interruptions Incentive Scheme**: 316,435 events | CC BY 4.0, registration | KEEP |
| Live faults | **UKPN live faults** (unit postcodes, geopoint, restored time), **Northern Powergrid** (postcodes, lat/long), **SSEN PowerTrack** (lat/long, feeder/transformer IDs, `priorityCustomerCount`) | UKPN CC BY 4.0 · NPg Open Data Licence v1.0 · SSEN anonymous | KEEP |
| Geocoding | postcodes.io (ONS-based), cached | Open, keyless | KEEP |
| Weather (M8) | **Open-Meteo** archive (ERA5) + forecast | CC BY 4.0, keyless, free non-commercial | KEEP |
| Grid stress | **NESO 1-s frequency** (2014–2026) · **Elexon** `/system/frequency` (15 s, live) | NESO Open Data · Elexon keyless | KEEP |
| Real sensors | **nLine GridWatch Accra**: 2-min voltage, frequency, power state, 2018–2024 | CC BY-NC 4.0; request a key, bucket as fallback; **coarsen GPS off-box** | KEEP |
| Wide-area | IODA (province level) | Free, research use | KEEP |
| Simulator load shapes | London Smart Meters (Kaggle `jeanmidev`) | ODbL | KEEP (narrow use) |
| Target grids | See §5 | — | — |
| **Do not use** | Kaggle "electrical fault detection" (MATLAB-simulated); Kaggle "Electrical System Fault Diagnosis" (motor rotor/stator faults); Kaggle re-uploads with rewritten licences; ESPENI CC0 relabel; SERL (secure lab only); PSML for "real" claims (simulated) | — | DO NOT USE |

**IBM data:** no IBM grid datasets exist on Kaggle, Hugging Face or DAX. We state this openly.

---

## 11. System architecture

```
Laptop (dev)            GitHub (main + builder branches)          Judges' browser
   │ git push                 │ git pull                                  │ http://148.100.78.95:<port>
   ▼                          ▼                                           ▼
┌──────────────────── LinuxONE VM 148.100.78.95 · z17 · s390x · 3 vCPU / 8 GB · Docker Compose ─────────────────────┐
│ edge  nginx:stable (trixie, OpenSSL 3.5, X25519MLKEM768 PQ TLS :8443) ── static UI + /api/* + SSE, no buffering    │
│                                                                                                                    │
│ app   FROM jupyterlab-image-s390x (+ pip fastapi uvicorn pg8000 sse-starlette, constrained) — ONE asyncio process  │
│   ├ ingest:  ukpn·npg·ssen (120s) → geocode cache │ elexon (30s) │ ioda (10m) │ open-meteo (daily)                │
│   ├ sim:     fuse-box + anchor sensors on real fault footprints (heartbeats 60s, noise) · NESO / Accra replay      │
│   ├ queue →  stress rule → evidence combiner → scale classifier                                                   │
│   ├ scorer:  M2 Keras hazard, batched per tick on NNPA (graph mode) · XGBoost AFT/M8 on CPU · refuses unsigned    │
│   ├ agent:   60s loop perceive→assess→plan→act→observe→learn · tools · memory in Postgres                          │
│   ├ grader:  +2h/+4h horizon grading vs real restorations                                                          │
│   ├ api:     FastAPI REST + SSE /stream                                                                             │
│   └ crypto:  AES-GCM via libcrypto (ctypes, CPACF) · writer task batches DB writes (250 ms / 500 rows)            │
│ signer python:3.13-slim-trixie · OpenSSL 3.5 ML-DSA-65 (models, task lists, audit checkpoints) · key 0400          │
│ granite  llama_cpp_python server (lab image, zDNN build) · Granite 3.3 2B BE · threads 2 · ~2.5 GB                  │
│ db    postgres:17 on a LUKS2 volume (host) · 127.0.0.1 only · roles migrator/ingest/api/agent · api reads views only │
│ train (one-off) `docker compose run app python -m ml.train` → XGBoost JSON + .keras → signed → model store        │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
Off-box: audit checkpoint hashes committed to GitHub every N min.
```

**Memory budget (8 GB):** steady state is about 5.6 GB (app ~2.5, Granite ~2.5, Postgres ~0.5, edge and signer ~0.1). A training run or a live Jupyter kernel on top exceeds 8 GB. So:
- set `mem_limit` on every service;
- **train with Granite stopped**;
- add a 4 GB swapfile;
- stop the Jupyter container before demos.

**Contracts, frozen first:**
- `contracts/openapi.yaml`
- `contracts/events.schema.json`: heartbeat, last-gasp, DNO fault, frequency reading, SMS reply, IODA event, shedding stage
- `contracts/model.md`: `predict(features, elapsed_h) → {quantiles, p_exceeds_reserve, eta_h, interval}`, plus `area_risk(district, date) → {p_ge_k, expected}`
- `grids/*.yaml`
- `fixtures/*.json`

**Core API, all under `/api`** (backend detail: Part B). Approvals need the operator login:
- `/auth/login`, `/auth/logout`
- `/health`
- `/grids/{id}/stress`
- `/outages`
- `/cells?level&cell_id`
- `/areas/risk?date`
- `/triage`
- `/decisions/{id}/approve`
- `/agent/decisions`
- `/agent/grades`
- `/alerts/cap/{id}`
- `/me/home` (auth)
- `/sources/health`
- `/audit/verify`
- SSE `/stream`

---

## 12. Tech stack (checked for s390x; handoff §9 wins)

| Layer | Choice | Notes |
|---|---|---|
| Base | **IBM `jupyterlab-image-s390x`**: Python 3.12; TF 2.18.1 + `ibm-zdnn-plugin`; torch 2.11 + `torch_nnpa`; XGBoost 3.4.1; scikit-learn 1.9; pandas 3.0; `llama_cpp_python` 0.3.36 (zDNN) | Never pip-install numpy, pandas, TF or torch |
| API | FastAPI + plain uvicorn (pip, pure Python) | Not uvicorn[standard] |
| DB driver | **pg8000** (pure Python) | psycopg2 has no s390x wheel |
| DB | `postgres:17` (s390x image; **not** `-bookworm`, which lacks s390x) | No TimescaleDB, PostGIS image or MongoDB |
| Spatial | Fixed cells and postcode lookups in Python | No h3 |
| Agent | asyncio loop in `app` | No LangGraph |
| LLM | Granite 3.3 2B Instruct BE GGUF via the lab image's `llama_cpp_python` | No ghcr image (CPU-only); no external LLM APIs |
| Crypto | **Signer container** (python:3.13-slim-trixie, OpenSSL 3.5): ML-DSA-65. **Edge** `nginx:stable` (trixie, OpenSSL 3.5): X25519MLKEM768. **AES-GCM**: libcrypto via ctypes in `app` (CPACF) | `cryptography` has no s390x wheel and isn't in the image. Ubuntu's OpenSSL 3.0 has no PQC |
| Frontend | Vite + TypeScript + MapLibre GL JS v5; **built on the laptop**, served statically by nginx | Never run Vite on the VM |
| Data files | CSV / `.npz` | No pyarrow, parquet, polars or DuckDB |
| Ops | Docker CE + compose; Trivy scan; iptables; **LUKS2 on the VM host**, unlocked manually after a reboot | — |
| Tests | pytest + coverage + anyio plugin + `httpx.ASGITransport`; a `blacknaught_test` DB; recorded feed fixtures; run on the VM | Test-only pip: pytest, pytest-cov, xmlschema |

**Hour-1 VM checks (go/no-go):**
- `uname -m`
- `lscpu | grep -i nnpa`
- `free -h`
- XGBoost `survival:aft` runs in the image
- the TF zDNN device is listed
- `llama_cpp_python` loads the BE GGUF
- inside the image: OS release, `python -c "import ssl;print(ssl.OPENSSL_VERSION)"`, and whether libcrypto, libpq and gcc are present (settles the AES-GCM route)
- `openssl version` in trixie

---

## 13. How LinuxONE is used (the primary judging criterion)

1. **Training on LinuxONE.** M1, M2 and M8 are trained **on the VM's CPU** inside IBM's image, on 313k real outages. The training log, metrics JSON and signed artefacts are saved to `evidence/`.
2. **Inference on Telum NNPA.** On each tick, the Keras hazard model scores every at-risk household × outage as one batch through `model.predict` (zDNN graph mode). We show `ZDNN_ENABLE_PRECHECK=true` op logs and the NNPA device.
3. **In the path, at volume.** Every event is **classified on arrival**. Duration risk is **one NNPA batch per tick** over all at-risk households × outages. We quote the events/s **measured** in a load-test replay. This is the transaction-scoring pattern banks use, applied to life safety.
4. **GenAI on the box.** Granite runs locally through the zDNN-built `llama_cpp_python`. No external AI APIs are used.
5. **Security in the core:**
   - CPACF AES-GCM
   - a LUKS volume
   - ML-DSA-signed models and task lists
   - ML-KEM post-quantum TLS
   - a tamper-evident audit trail
   - least-privilege roles
   - iptables default-deny
   - a Trivy scan
6. **Reliability.** Compose restart policies; agent memory survives a restart.

**Evidence and the benchmark question:**
- The IBM handoff asks for CPU-vs-NNPA timing. Marist ToU §5 forbids publishing benchmarks.
- **Rule:** we measure **our own model, on the same VM, with NNPA on vs off** (`NNPA_DEVICES=0`), in the same way as IBM's own lab notebook. We save the numbers to `evidence/`. We never compare against x86 or other platforms.
- Confirm in #helpdesk before showing the numbers in the video (§20).

**One uncut terminal take for the video:**
1. `uname -m` → s390x, plus the IP
2. the NNPA `lscpu` line
3. `docker compose ps`
4. the training log tail
5. the event counter
6. a signed model verified, then a tampered one refused
7. the post-quantum handshake
8. audit tamper → red
9. agent restart with memory intact
10. delete Granite → decisions unchanged

Never show the IP and a token in the same frame.

---

## 14. Security and privacy

- **Roles:** the health authority is the controller and Blacknaught the processor. Explicit, recorded consent. A DPIA is required. **Synthetic people only on the VM** (ToU §9). Accra GPS is coarsened off-box.
- **At rest:** AES-256-GCM columns, with the key wrapped by a KEK held only by the signer. Postgres runs on a LUKS2 volume. Production would use an HSM.
- **In transit:** nginx with X25519MLKEM768. Internal services bind to 127.0.0.1.
- **Integrity:**
  - The audit trail covers **decisions, approvals and tool calls**, not telemetry.
  - It is a hash chain: `sha256(prev ‖ canonical JSON)`, appended through a `SECURITY DEFINER` function under an advisory lock. UPDATE/DELETE/TRUNCATE are revoked, with triggers.
  - ML-DSA-65 signs models, task lists and checkpoints (every 500 rows or 5 min). Checkpoints are published off-box (🟠 the method is pending).
  - We call it "tamper-evident", never "inquest-grade".
- **Least privilege:** DB roles `ingest` (INSERT), `api_read` (views), `agent` (triage SELECT + decisions INSERT). No superuser from the app.
- **Map privacy:**
  - A WGS84 grid at 3 nested levels (~1.1 / 5.5 / 27 km).
  - Counts of 1–10 are hidden; 0 is published. Complementary suppression per parent cell.
  - Published every 15 min; counts banded from 20.
  - A property test proves no hidden count can be back-calculated. No point API.
- **Insider-first threat model:** catchment scoping, break-glass with justification, no national ID stored, expiring task lists, reviewed access logs.
- **Secrets:**
  - **Rotate the leaked VM credentials (blocking):** the password and the key link were shared in a form.
  - Each member gets their own SSH key. Custom Jupyter token. gitleaks. `.env.example` only.

---

## 15. Frontend / UX

- **Control-room look:** dark-first, colour-blind-safe severity palette, readable at 1080p on video.
- **Views:**
  1. **Map:** outage areas by scale, fixed cells, an area-risk overlay for tomorrow (F11), pings on new events.
  2. **Triage list:** expected case first, then the range, then "why ranked here", then approve.
  3. **Two-houses card:** a real fault, two synthetic patients, different answers.
  4. **Agent panel:** a live decision feed (tool calls), overnight grades, a Brier trend, calibration by region.
  5. **Grid gauge:** the stress state with LIVE / SIMULATED / TRANSFERRED badges.
  6. **Audit view:** verify, tamper → red.
  7. **CAP alert preview** (phone mock-up) and **SMS template preview**.
  8. **"My home"** (login).
  9. Optional globe intro, timeboxed to 30 min.
- **Labels are mandatory everywhere:** LIVE, SIMULATED, REPLAY (real data), TRANSFERRED.

---

## 16. Evaluation

| Question | Evidence |
|---|---|
| Does M2 beat the baselines? | ENWL time split: Brier at 2/4/8 h and C-index against KM and log-linear, with the margin stated honestly; UKPN cross-operator |
| Does area risk have skill? | Brier skill score against climatology, 2024–26 |
| Does the localiser work? | Postcode precision/recall against real footprints under injected noise |
| Is the agent real? | Overnight grades; 3 logged decisions; restart keeps memory |
| Is it fair? | Calibration within region (primary); miss rate; time to first contact; coverage; sensor density. Kleinberg's trade-off shown |
| Is not-worst-case safe? | Synthetic replay: harm-hours and alert counts against first-come, severity-only and worst-case policies |
| Is it stable? | Event bootstrap, mean ± standard deviation |

---

## 17. Demo (≤3:00, recorded against `https://148.100.78.95:8443`)

Use PQ TLS, with the CA trusted on the recording laptop. The fallback is `http://` plus a terminal `s_client` handshake (🟠 pending).

| Time | Beat |
|---|---|
| 0:00 | **Hook:** "A static oxygen concentrator has no battery." The coroner line, framed correctly |
| 0:20 | Problem + data on screen (ENWL 313k, live feeds, licences) |
| 0:35 | **Live GB:** a real fault from the operator's feed; fuse-box sensors on its real postcodes go dark; the scale reads "street" and is confirmed |
| 0:55 | **Two houses, same fault, different answers:** an oxygen concentrator on a 4 h cylinder → escalate; a ventilator with 15 h → SMS check |
| 1:15 | **Agent:** a stale feed re-ranks a patient; capacity of 5 workers for 12 patients; a Granite briefing; a CAP alert awaiting approval; "graded N real restorations overnight" |
| 1:45 | **Tomorrow's risk map** (weather × history) + **target grid replay** (real sensors, config-only) |
| 2:05 | **LinuxONE:** trained here, NNPA live, signed models, PQ TLS, audit tamper |
| 2:35 | **Honest limits + next steps:** synthetic patients, transferred durations, government/DNO/health agreements |
| 2:50 | Team, one line each |

---

## 18. Team, timeline, cut order

| Who | Owns |
|---|---|
| **Sali** (backend; repo + docs owner) | Contracts, schema and roles, ingest (F1), triage (F5), grading (F7), cells/k≥11, audit chain, AES-GCM, operator auth, API + SSE. CAP export after 02:20; `/me/home` only if ahead |
| **Ahmed** (platform + agent; VM owner) | VM access and keys, Compose, edge PQ TLS, LUKS, signer, sensor sim (F2), combiner (F3), agent (F6), Granite (F8), NNPA serving, proof take |
| **Nate** (data/ML) | ENWL/UKPN prep, M1/M2/M8, LR table, grid YAMLs, stress rule, target-grid replay, evaluation numbers |
| **Rama** (frontend; video edit lead) | All views (§15), two-houses card, CAP/SMS previews, "my home", screen recordings |

**Timeline:** superseded by NOW → Active tasks and the freeze decision (the original 17 Oct schedule is in History).

**Cut order (first → last):**
1. Pakistan/Bangladesh layer
2. Globe
3. "My home" view
4. Target-grid shortage model (F16)
5. CAP preview polish
6. Target-grid replay (F13)
7. Grid stress replay (F12)
8. PQ TLS edge
9. Area risk (F11)
10. NNPA (fall back to CPU and say so)

**Never cut:** live GB ingest, M2 trained on the VM, the two-houses card, the agent with overnight grading, signed models + audit.

---

## 19. Risks and judge questions

| Question | Answer |
|---|---|
| Can frequency find faults? | No: it is the same everywhere on a grid. We use it for system stress. Location comes from operator feeds and our sensors |
| Why not Kaggle fault data? | The popular sets are MATLAB simulations or motor faults. We train on 313k real operator records |
| Does a UK model transfer? | Not raw. Each grid gets its own config and local labels. Transferred parts are labelled TRANSFERRED with wide intervals. Our sensors generate the labels a country lacks (nLine's Accra fleet found 2× the utility's count) |
| What's real in the demo? | The faults, locations, restorations and weather. The patients are synthetic by law. The sensors are simulated on real footprints, plus real Accra sensor data |
| Just a cron job? | It chooses among tools under a capacity constraint, handles source failure, grades and corrects itself, and keeps memory across restarts |
| Doesn't this run on a laptop? | The code would. The deployment requirement wouldn't: the encrypted register stays beside the models; scoring is in-path on NNPA; models are signed; links are PQ; availability is the product |
| What does NNPA accelerate? | Batched inference of the hazard model. Training is on the VM's CPU. We compare NNPA on vs off for our own model only |
| Amber alerts? | We produce a standard CAP 1.2 alert; a human approves it; the government's channel broadcasts it. We don't send mass alerts ourselves |
| Can the map reveal patients? | No: fixed cells, k≥11, complementary suppression, no point API |
| Why not assume the worst? | Alert fatigue. Caution scales with clinical criticality, and unanswered checks escalate |
| "Only government access stops you"? | The software runs on open data today. Deployment needs three agreements: grid data, a health register, a sensor pilot |

---

## 20. Open items / decisions pending
See **NOW → Pending decisions** and **Blockers**.

## 21. Key sources
- **Data:**
  - [ENWL](https://www.opennetzero.org/electricity-north-west/unplanned-outages1)
  - [UKPN IIS](https://opennetzero.org/uk-power-networks/interruptions-incentive-scheme)
  - [UKPN live](https://ukpowernetworks.opendatasoft.com/explore/dataset/ukpn-live-faults/)
  - [NPg live](https://northernpowergrid.opendatasoft.com/explore/dataset/live-power-cuts-data/)
  - SSEN PowerTrack
  - [NESO frequency](https://www.neso.energy/data-portal/system-frequency-data)
  - [Elexon](https://data.elexon.co.uk/bmrs/api/v1/system/frequency)
  - [Open-Meteo](https://open-meteo.com)
  - [nLine GridWatch](https://nline.io/public-data/gridwatch)
  - [postcodes.io](https://postcodes.io)
- **Methods:**
  - [Glasgow district-day fault forecasting (arXiv 2603.01653)](https://arxiv.org/html/2603.01653v1)
  - [Klugman et al. IPSN 2021](https://web.eecs.umich.edu/~prabal/pubs/papers/klugman21watching.pdf)
  - Yurdakul & Naranjo 2020
- **Problem:**
  - [Peter Coates PFD](https://www.judiciary.uk/prevention-of-future-death-reports/peter-coates-prevention-of-future-deaths-report/)
  - [Janette Palmer PFD](https://www.judiciary.uk/prevention-of-future-death-reports/janette-palmer-prevention-of-future-deaths-report/)
- **Platform:**
  - [jupyter-lab-ml](https://github.com/linuxone-community-cloud/jupyter-lab-ml)
  - [IBM TF on Z](https://github.com/IBM/ibmz-accelerated-for-tensorflow)
  - [OpenSSL ML-DSA](https://docs.openssl.org/3.5/man7/EVP_SIGNATURE-ML-DSA/)
  - [OASIS CAP 1.2](https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2.html)


---

# Part B: Backend design (per feature)

## How to use this

- **Building?** Read the summary table, then only your feature's section. Each B-section ends with **Spec**, the part to build from.
- **🟠 markers** are open team decisions. Each has a recommendation, but nothing marked 🟠 is decided until the team picks.
- **Evidence:** every load-bearing claim was checked tonight against PyPI JSON, Docker Hub, official docs, or a live curl of the feed (~21:27 BST). The source ledger is at the bottom.
- **Hard constraints this is designed for:**
  - s390x, big-endian, 3 vCPU / 8 GB;
  - **one asyncio process** (uvicorn, 1 worker);
  - about 4.8 h to the 03:00 freeze;
  - demo load of 1–2k events/s;
  - judged by IBM on security.

### Verified facts that shape everything
| Fact | Evidence |
|---|---|
| The lab image **already has `httpx 0.28.1`, `anyio 4.15.1`, `h11`, `argon2-cffi`, `PyYAML`, `tzdata`, `jsonschema`, `defusedxml`**. It has **no** `fastapi`, `starlette`, `pydantic`, `uvicorn`, `cryptography`, `pytest` or `lxml` | `reference/jupyter-lab-ml_packages.txt` |
| `pydantic-core 2.50.1` ships a **cp312 manylinux s390x wheel**. fastapi 0.143.3, starlette 1.8.0, uvicorn 0.54.0, pg8000 1.31.5, scramp, asn1crypto, sse-starlette 3.5.0 and opentelemetry-api (a new hard dependency of fastapi) are **all pure Python** | PyPI JSON, 2026-10-17 |
| **`cryptography` 50.0.2 has no s390x wheel** (it ships ppc64le, aarch64 and x86_64 only), so pip would need a Rust source build. **`pycryptodome` has no s390x wheel either** | PyPI JSON; handoff §9.1 |
| **`openssl enc` cannot do GCM**: "does not support authenticated encryption modes like CCM and GCM" | OpenSSL `openssl-enc(1)` man page |
| `postgres:17`, `debian:trixie`, `nginx:stable` and `python:3.13-slim-trixie` all have s390x images. (`postgres:17-bookworm` does **not**: don't pin that tag) | Docker Hub tags API |
| **The official `nginx:stable` image is built `FROM debian:trixie-slim`** (nginx 1.30.6), and trixie ships OpenSSL 3.5.7. **So the stock nginx image can do X25519MLKEM768, with no custom build** | nginx/docker-nginx Dockerfile; sources.debian.org |
| `llama_cpp.server` needs the `[server]` extras: uvicorn, fastapi, pydantic-settings, sse-starlette, starlette-context and PyYAML. All are pure or have s390x wheels | PyPI `llama-cpp-python` requires_dist |
| Live feeds as probed at 21:27 BST: UKPN 62 records (`limit` ≤ 100 per call), NPg 92, SSEN 7 (each with a postcode list), Elexon `from`/`to` working, postcodes.io bulk working, IODA v2 working | curl probes |

---

## Summary: feature → choice → why

| # | Feature | Choice | One-line why |
|---|---|---|---|
| 1 | DB driver + async bridge | **pg8000 1.31.5, native API**, with one connection per role, each on its **own single-thread executor** | Pure Python. pg8000 is "one thread per connection", so a 1-thread executor makes that true by construction |
| 2 | Write path | **One writer task**, batching every 250 ms or 500 rows, with one round trip per batch (`INSERT … SELECT FROM unnest(...) ON CONFLICT`) | 2k rows/s as single-row inserts means 2k round trips; batching is ~8 per second |
| 3 | Event bus | **Two `asyncio.Queue`s**: `critical` (never dropped, 50k) and `bulk` (10k, drop-oldest heartbeats). No LISTEN/NOTIFY, no Redis | One process, so an in-memory queue is enough. NOTIFY adds a DB round trip per event; Redis costs RAM and a service |
| 4 | Event schema | Pydantic v2 discriminated union on `kind`, with a deterministic `event_id` | Validation at the boundary, plus idempotent replays |
| 5 | F1 ingest | One `httpx.AsyncClient`; polls UKPN/NPg/SSEN at 120 s, Elexon at 30 s, IODA at 10 min, Open-Meteo daily, each with jitter. Upserts keyed on `(source, source_ref)` with a content hash | Matches feed cadence; dedupe is exact on the natural key |
| 6 | Geocoding | `postcode_geo` table cache. postcodes.io bulk POST (≤100), 30-day TTL, 1-day negative cache | Keyless, ONS-based, and one call per 100 postcodes |
| 7 | Postgres schema + roles | Schema `bn`, owned by NOLOGIN `bn_owner`. Login roles `bn_migrator`, `bn_ingest`, `bn_api`, `bn_agent`. No superuser from the app | The least-privilege story judges can check with `\dp` |
| 8 | Migrations | **Hand-rolled runner** (~40 LOC) applying numbered SQL files, with a checksum table | Alembic would pull in SQLAlchemy; we have no ORM |
| 9 | F5 triage | **A scorer task every 30 s** (and on any new outage) batches every at-risk household × outage into one `predict()` call on a dedicated executor. `/triage` serves the latest snapshot | Keeps NNPA batching, stops HTTP requests from triggering model calls, and gives a consistent ranking |
| 10 | F7 grading | A grader every 60 s. Fixed-horizon binary outcome. **Censored = vanished or stale before the horizon**: excluded, counted, and bounded both ways. UKPN is primary (explicit `restoreddatetime`) | Honest under informative censoring, and simple enough to ship |
| 11 | Cells + k≥11 | **A fixed WGS84 degree grid** at 3 nested levels (~1.1 km / 5.5 km / 27 km), integer-indexed. Primary suppression of 1–10, then complementary suppression per parent, a 15-min publish cadence and banding | Corners are plain lat/lon for MapLibre and CAP; no projection library needed |
| 12 | Audit chain | `audit_log(seq, body text, prev_hash, hash)`. Appended only through a `SECURITY DEFINER` function under an advisory lock. `hash = sha256(prev ‖ body)`. REVOKE plus BEFORE UPDATE/DELETE/TRUNCATE triggers. ML-DSA-65 checkpoint every 500 rows or 5 min | Ordering is enforced in the DB. Tampering is caught by the chain, and a superuser rewrite is caught by the signed off-box head |
| 13 | REST API | FastAPI under `/api/*`, cursor pagination, Pydantic response models; `openapi.yaml` is generated, then frozen | The contract is what Rama builds against |
| 14 | SSE `/stream` | **sse-starlette 3.5.0** with a broadcaster: per-client queue of 256, a ring buffer of 2,000 for `Last-Event-ID`, 15 s ping. nginx sets `proxy_buffering off` | Same library llama_cpp.server already needs; handles pings and disconnects |
| 15 | F15 CAP 1.2 | **Hand-written** with `xml.etree.ElementTree`. Tests validate against the OASIS XSD using `xmlschema` (pure Python, test-only) | No maintained CAP writer exists on PyPI |
| 16 | `/me/home` auth | **Server-side session**: argon2id passphrase (argon2-cffi is already in the image), then a 256-bit opaque token, stored as a SHA-256 hash, in an HttpOnly + SameSite=Strict cookie. 30 min idle / 8 h absolute. No ID in the URL | Revocable, no IDOR, no new dependency; follows the OWASP numbers |
| 17 | `/sources/health` | Per-source state machine ok → stale (>3× interval) → down (>6×), fed by every poll, also pushed on SSE | It's the agent's "source failure" decision input |
| 18 | Field encryption | 🟠 **AES-256-GCM via `ctypes` → the image's libcrypto EVP** (OpenSSL uses CPACF/KMA on s390x), plus an HMAC blind index on postcodes | Without `cryptography`, this is the only route that keeps the CPACF claim true and adds no dependency |
| 19 | Secrets/config | `*_FILE` env vars pointing to compose secret files generated on the VM. Non-secret config in `config/app.toml` (stdlib `tomllib`) + `grids/*.yaml` | Secrets never enter git or `docker inspect` |
| 20 | Testing | pytest 9 + coverage 7 (pure wheels) + anyio's built-in pytest plugin + `httpx.ASGITransport`. A `blacknaught_test` DB in the same container. Recorded feed fixtures | No extra services; runs on the VM (big-endian) |
| 21 | Deploy | `git pull` on the VM. **Code bind-mounted read-only into the app image**, so a change is a `restart` (seconds), not a rebuild. `pip -c` against the image's freeze | Fast loop for 5 hours; pip can't upgrade the image's compiled stack |

---

## B1. Database driver and the asyncio bridge

**Options**
- **A. pg8000 (pure Python) with blocking calls bridged to asyncio.**
- **B. psycopg 3 in pure-Python mode with `AsyncConnection`.** It's async-native, but **needs libpq on the system** (apt `libpq5` in the Dockerfile), and nobody has checked that the image has it.
- **C. SQLite on the LUKS volume.** Zero services, but there are no roles (so the least-privilege story dies), it is single-writer, and the agent and API would contend.

**Choice: A, pg8000 1.31.5, native API (`pg8000.native.Connection`).**

**Why:**
- Pure Python, with dependencies scramp → asn1crypto (both pure) and python-dateutil (already in the image).
- The handoff (§7.8, §9.1) and Part A (§12) already name it.
- The native API has `:name` parameters, COPY, and `Connection.notifications` (pg8000 README).
- Handoff §9 marks psycopg 3 pure as SAFE too, so B is the fallback if pg8000 misbehaves. It still needs `libpq5` from apt.

**Rejected:**
- B for tonight: an extra system package plus an untested libpq on the image.
- C: no roles, and every judge-visible DB security claim would be lost.
- asyncpg: not s390x-safe (research §9.8).

**How blocking pg8000 runs inside asyncio:**
- pg8000: "designed to be used with one thread per connection… threads may share the module but not connections."
- So **each connection gets its own `ThreadPoolExecutor(max_workers=1)`**, and every call is `await loop.run_in_executor(conn_exec, fn)`.
- `asyncio.to_thread` is **not** used for DB calls. It uses the shared default pool, so two calls could hit one connection from two threads.

| Connection | Role | Executor | Used by |
|---|---|---|---|
| `writer` | `bn_ingest` | 1 thread | the writer task only (all ingest/sim/stream inserts) |
| `api_1`, `api_2` | `bn_api` | 1 thread each | API reads, behind an `asyncio.Semaphore(2)` round-robin |
| `agent` | `bn_agent` | 1 thread | agent, scorer, grader writes (triage snapshots, decisions, grades, memory) |
| `audit` | `bn_ingest` (EXECUTE on `audit_append` only) | 1 thread | audit appends and checkpoints |

**Failure modes:**
- **Connection drop** (Postgres restart): wrapper catches `pg8000.exceptions.InterfaceError` or `DatabaseError` with a connection-class SQLSTATE, reconnects with backoff 0.5 → 8 s, and retries the statement **once** only if it is idempotent (all our writes are `ON CONFLICT`).
- **Slow query:** `timeout=10` on connect, and `SET statement_timeout = '5s'` per session (`'30s'` for the agent).
- **Executor thread stuck:** the API semaphore times out after 3 s → 503 with `Retry-After: 2`.

**Libraries:** `pg8000==1.31.5`, `scramp==1.4.17`, `asn1crypto==1.5.1`.

## B2. Write path (1–2k events/s)

**Options:**
- **A. One INSERT per event** through the executor. That is 2k round trips/s on one thread: at ~0.3–0.5 ms each over loopback, the thread is near-saturated, with no headroom.
- **B. A batching writer task.** It drains an internal `write_q` every **250 ms or 500 rows**, whichever comes first. It makes one round trip per table per batch, using `INSERT … SELECT * FROM unnest(:a::text[], :b::timestamptz[], …) ON CONFLICT … DO NOTHING`. pg8000 sends Python lists as arrays.
- **C. COPY FROM STDIN** via pg8000's `stream=`. It's the fastest, but it can't do `ON CONFLICT`, so it needs a staging table.

**Choice: B.** Use C only if the load test shows B saturating.

🟠 **What is persisted (data decision):**
- **Heartbeats are not stored row-by-row.** They update an in-memory `last_seen[sensor_id]`.
- Only **state transitions** (`up` / `down` / `last_gasp` / `dropout`) go to `sensor_transition`, plus a per-minute counter row (`event_counts(minute, kind, n)`).
- Everything from the DNOs, Elexon, predictions, grades, decisions and the audit log is stored.
- Why: 2k heartbeats/s is 170 M rows/day of "still alive". Transitions carry all the information the classifier and grader need.
- **Consequence to accept:** after a restart, `last_seen` is rebuilt from transitions plus a 2-minute grace period. During that window no sensor is declared silent.

**Failure modes:**
- If `write_q` grows past 20k items, the writer logs it and `/sources/health` shows `db_writer: lagging`. Producers on `bulk` start dropping heartbeats (see §B3), but transitions are never dropped.
- If a batch fails on a bad row, the writer splits it in half recursively, so one bad row can't sink 499 good ones. Bad rows go to the `ingest_reject` log with the reason.

## B3. Event schema and the in-process queue

**Options:**
- **A. `asyncio.Queue`, bounded, in-process.**
- **B. Postgres LISTEN/NOTIFY.** It costs a DB round trip per event. Payloads are capped at 8,000 bytes. With pg8000, notifications arrive only on the native API's `notifications` deque, which must be polled. It's pointless inside one process.
- **C. Redis Streams** (s390x image exists). It adds a service, ~50–100 MB of RAM and a failure point, and only helps multi-process designs.

**Choice: A, with two queues.**
- `critical = asyncio.Queue(maxsize=50_000)`: last-gasp, DNO fault, SMS reply, source-stale. Producers use `await put()`: real backpressure, never dropped.
- `bulk = asyncio.Queue(maxsize=10_000)`: heartbeats, frequency, IODA. The simulator uses `put_nowait()`. On `QueueFull` it drops the **oldest** heartbeat (`get_nowait()` then put) and increments `dropped_total{kind}`.
- The consumer drains `critical` first, then up to 500 from `bulk` per loop turn.
- Docs: `put_nowait` raises `QueueFull` at maxsize. **`Queue.shutdown()` arrived in 3.13 and the image is Python 3.12, so don't use it.** Shut down with a sentinel object instead.
- asyncio queues are **not thread-safe**. Anything producing from a thread (none planned) must use `loop.call_soon_threadsafe`.

**Envelope (`contracts/events.schema.json`, generated from Pydantic):**
```json
{
  "event_id": "hex32",        // deterministic for feed events, uuid4 hex for sim
  "kind": "heartbeat|last_gasp|dno_fault|freq_reading|sms_reply|ioda_signal|shedding_stage|source_state",
  "source": "ukpn|npg|ssen|elexon|ioda|sim|accra_replay|neso_replay",
  "observed_at": "2026-10-17T21:40:00+00:00",   // UTC, from the source
  "received_at": "2026-10-17T21:40:02.120+00:00",
  "label": "LIVE|SIMULATED|REPLAY|TRANSFERRED",
  "payload": { /* per-kind model, extra="ignore" on feed payloads */ }
}
```
- **Idempotency key:**
  - `event_id = sha256(f"{source}|{source_ref}|{content_hash}")[:32]` for feed records;
  - `sha256(f"elexon|{measurementTime}")` for frequency;
  - uuid4 for simulated events.
- The writer's `ON CONFLICT (event_id) DO NOTHING` makes re-polls and replays safe.
- **Validation cost:** Pydantic runs at feed boundaries only. Simulator events are internal `@dataclass(slots=True)` objects with the same field names, so the hot path skips validation.

## B4. F1 ingest (UKPN, NPg, SSEN, Elexon, IODA, Open-Meteo)

**Options:**
- **A. One asyncio task per source, sharing one `httpx.AsyncClient`.**
- **B. APScheduler.** A new dependency, for what is just `while True: poll; sleep`.
- **C. A separate ingest container.** A second process and IPC.

**Choice: A.** httpx is already in the image (0.28.1), so this adds nothing.

**Client settings:**
- `httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=15, write=5, pool=5), headers={"User-Agent": "blacknaught-datathon/0.1"}, limits=httpx.Limits(max_connections=10))`.
- Each whole poll is wrapped in `async with asyncio.timeout(45)`.

**Per-source spec** (field names verified against live responses tonight):

| Source | Endpoint | Interval | Paging | Natural key | Restored signal | Time parsing |
|---|---|---|---|---|---|---|
| UKPN | `ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-live-faults/records` | 120 s | `limit=100&offset=k·100` until `total_count` (API rejects `limit>100`) | `incidentreference` | **explicit**: `powercuttype=="Restored"` / `statusid==5` with `restoreddatetime` | **Naive local strings** (`"2026-10-15T00:49:22"`). Parse as `Europe/London` with `zoneinfo`, then convert to UTC |
| NPg | `northernpowergrid.opendatasoft.com/.../live-power-cuts-data/records` | 120 s | same as UKPN | `reference` | **No restore timestamp in the feed.** `incidentstatus` is coded, mapping unverified. Treat disappearance as `vanished` | `loggedtime`, `updatedate` carry `+00:00` |
| SSEN | `ssen-powertrack-api.opcld.com/gridiview/reporter/info/livefaults` (gzip JSON, `Faults[]`) | 120 s | none (one document) | `reference` | `resolved: true`. Restore time is **approximated** by `updated`, flagged `restored_explicit=false` | `loggedAt` as `+0000`; parse with a tested helper |
| Elexon | `data.elexon.co.uk/bmrs/api/v1/system/frequency?from=…&to=…&format=json` | 30 s | `from = last_seen − 60 s`, `to = now` (without from/to it returns a whole day) | `measurementTime` | n/a | `Z` UTC |
| IODA | `api.ioda.inetintel.cc.gatech.edu/v2/signals/raw/region/{code}?from&until` | 10 min | last 30 min window | `(region, datasource, ts)` | n/a | epoch seconds |
| Open-Meteo | forecast API, many `latitude`/`longitude` lists in one call (ENWL district centroids) | daily 06:00 + startup | one call | `(district, date)` | n/a | `timezone=UTC` |

**Normalised outage row:**
- Fields: `source, source_ref, status (active|restored|vanished|planned), started_at, restored_at, restored_explicit, customers, priority_customers, postcodes[], lat, lon, feeder{primary,hv,lv,tx}`, plus `content_hash`.
- **Planned outages are kept but tagged `planned`.** They're excluded from the duration model and from grading, since they're scheduled, not stochastic.

**Dedupe:**
- **Within a feed:** exact match on `(source, source_ref)`.
- **Changes:** if `content_hash` changes (status, restore, postcodes, customers, ETR), bump `version` and append the raw JSON to `outage_version`. Grading can then prove what was known when.
- **Disappearance:** a record missing from **2 consecutive successful polls** becomes `vanished`, with `last_seen` kept. It is **never** treated as `restored` (Part A §9).
- **Across feeds:** UKPN, NPg and SSEN cover disjoint licence areas, so **there is no merge**.
- **DNO ↔ sensor:** sensor-detected outages are linked to a DNO outage (`linked_outage_id`) when they share a cell and the DNO start is within ±30 min. This is the combiner's job (Ahmed); the backend just stores the link.

**Retry/backoff:**
- Up to 3 attempts per request on timeout, connect error, or 5xx.
- Sleep `random.uniform(0.5, 1.0) × min(30, 2**attempt)` s (full jitter).
- On 429, obey `Retry-After`, capped at 300 s.
- 4xx other than 429: no retry; log it.
- After 5 consecutive failed polls, the interval doubles (max 10 min) until one succeeds.
- Each source's start is jittered ±10% so they never fire in sync.

**Failure handling:**
- A per-record parse failure → `ingest_reject` (source, ref, error, raw), and the poll continues.
- A schema drift (a key field missing in >50% of records) → source status `degraded`, and an SSE `source_health` event fires.

## B5. Postcode geocoding cache

**Options:**
- **A. A Postgres cache table with postcodes.io bulk POST.**
- **B. An in-memory LRU only.** Lost on restart; refetch storms.
- **C. Pre-load the ONS Postcode Directory** (~1 GB CSV). Too big tonight.

**Choice: A.**

- **Normalisation:** upper-case, strip spaces, then insert a space before the last 3 characters (`N13LD` → `N1 3LD`). Validate with regex `^[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}$`.
- **Lookup:**
  1. Read the cache.
  2. Collect misses, de-duplicated across the poll.
  3. `POST https://api.postcodes.io/postcodes {"postcodes":[≤100]}`, with a `Semaphore(2)`.
  4. Upsert the results.
- **Table:** `postcode_geo(postcode PK, lat, lon, lsoa, admin_district, valid bool, fetched_at)`. Valid rows have a 30-day TTL; `valid=false` rows a 1-day TTL.
- **Failure:** if postcodes.io is down, the fault falls back to the feed's own `geopoint` or `lat`/`lng` (all three DNOs give one) for its cell. Patient matching still works, because it uses the postcode itself (blind index, §B18), not coordinates.

## B6. Postgres schema, roles, migrations

**Roles** (`db/init/00_roles.sh`, run once by the postgres entrypoint; passwords read from `/run/secrets/*`):

| Role | Login | Rights |
|---|---|---|
| `bn_owner` | no | owns schema `bn` and every object |
| `bn_migrator` | yes | member of `bn_owner`; used **only** by `python -m app.migrate` |
| `bn_ingest` | yes | INSERT/UPDATE on `outage`, `outage_version`, `freq_reading`, `sensor_transition`, `event_counts`, `source_poll`, `postcode_geo`, `ingest_reject`; EXECUTE `audit_append` |
| `bn_api` | yes | SELECT on views `v_outage_public`, `v_cells_published`, `v_triage_latest`, `v_grades`, `v_decisions`, `v_source_health`, `v_audit` (no raw `patient`); EXECUTE `approve_decision`, `session_*` functions |
| `bn_agent` | yes | SELECT on `patient` (ciphertext columns stay ciphertext), `outage`, `prediction`; INSERT on `prediction`, `grade`, `triage_snapshot`, `decision`, `agent_memory` (+UPDATE), `cap_alert`; EXECUTE `audit_append` |

- `REVOKE ALL ON SCHEMA public FROM PUBLIC`.
- **Nobody** gets UPDATE, DELETE or TRUNCATE on `audit_log`.
- The app never connects as `postgres`.

**DDL sketch** (`db/migrations/0001_init.sql`):
```sql
CREATE SCHEMA bn AUTHORIZATION bn_owner;
SET search_path = bn;

CREATE TABLE schema_migrations (version int PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE outage (
  outage_id        bigserial PRIMARY KEY,
  source           text NOT NULL CHECK (source IN ('ukpn','npg','ssen','sensor','replay')),
  source_ref       text NOT NULL,
  status           text NOT NULL CHECK (status IN ('active','restored','vanished','planned')),
  started_at       timestamptz NOT NULL,
  restored_at      timestamptz,
  restored_explicit boolean NOT NULL DEFAULT false,
  first_seen       timestamptz NOT NULL,
  last_seen        timestamptz NOT NULL,
  customers        int, priority_customers int,
  postcodes        text[] NOT NULL DEFAULT '{}',
  lat double precision, lon double precision,
  cell_l1          text,
  feeder           jsonb,
  label            text NOT NULL DEFAULT 'LIVE',
  content_hash     bytea NOT NULL,
  version          int NOT NULL DEFAULT 1,
  linked_outage_id bigint REFERENCES outage,
  UNIQUE (source, source_ref)
);
CREATE INDEX ON outage (status) WHERE status = 'active';
CREATE INDEX ON outage USING gin (postcodes);

CREATE TABLE outage_version (outage_id bigint REFERENCES outage, version int, observed_at timestamptz NOT NULL, raw jsonb NOT NULL, PRIMARY KEY (outage_id, version));
CREATE TABLE freq_reading (grid text NOT NULL DEFAULT 'gb', measured_at timestamptz, hz numeric(6,3) NOT NULL, PRIMARY KEY (grid, measured_at));
CREATE TABLE sensor_transition (sensor_id text, at timestamptz, state text CHECK (state IN ('up','down','last_gasp','dropout')), cell_l1 text NOT NULL, label text NOT NULL, PRIMARY KEY (sensor_id, at));
CREATE TABLE event_counts (minute timestamptz, kind text, n int NOT NULL, dropped int NOT NULL DEFAULT 0, PRIMARY KEY (minute, kind));
CREATE TABLE source_poll (source text, polled_at timestamptz, ok boolean, http_status int, n_records int, latency_ms int, error text, PRIMARY KEY (source, polled_at));
CREATE TABLE postcode_geo (postcode text PRIMARY KEY, lat double precision, lon double precision, lsoa text, admin_district text, valid boolean NOT NULL, fetched_at timestamptz NOT NULL);
CREATE TABLE ingest_reject (id bigserial PRIMARY KEY, at timestamptz DEFAULT now(), source text, source_ref text, error text, raw jsonb);

-- synthetic register (ToU §9: synthetic only, enforced)
CREATE TABLE patient (
  patient_id uuid PRIMARY KEY, household_id uuid NOT NULL,
  cell_l1 text NOT NULL,
  postcode_bidx bytea NOT NULL,          -- HMAC-SHA256(k_bidx, normalised postcode)
  contact_ct bytea NOT NULL,             -- AES-256-GCM(nonce‖ct‖tag), AAD = patient_id
  device text NOT NULL, flow_lpm numeric, reserve_h numeric NOT NULL,
  other_backup boolean NOT NULL, severity smallint NOT NULL CHECK (severity BETWEEN 1 AND 5),
  synthetic boolean NOT NULL DEFAULT true CHECK (synthetic)
);
CREATE INDEX ON patient (postcode_bidx);

CREATE TABLE prediction (
  pred_id bigserial PRIMARY KEY, outage_id bigint NOT NULL REFERENCES outage,
  patient_id uuid REFERENCES patient, made_at timestamptz NOT NULL, elapsed_h real NOT NULL,
  model_id text NOT NULL, model_sha256 text NOT NULL, horizon_h smallint NOT NULL CHECK (horizon_h IN (2,4)),
  p_still_off real NOT NULL CHECK (p_still_off BETWEEN 0 AND 1), quantiles jsonb NOT NULL,
  UNIQUE (outage_id, made_at, horizon_h, model_id)        -- outage-level preds are what get graded
);
CREATE TABLE grade (pred_id bigint PRIMARY KEY REFERENCES prediction, graded_at timestamptz NOT NULL,
  outcome smallint CHECK (outcome IN (0,1)), censored boolean NOT NULL, reason text NOT NULL, brier real);
CREATE TABLE triage_snapshot (tick_at timestamptz, patient_id uuid, outage_id bigint, rank int, harm real,
  q_used text, q_hours real, escalate boolean, why jsonb, PRIMARY KEY (tick_at, patient_id, outage_id));
CREATE TABLE decision (decision_id uuid PRIMARY KEY, created_at timestamptz NOT NULL, tool text NOT NULL, args jsonb NOT NULL,
  state text NOT NULL CHECK (state IN ('auto_done','awaiting_approval','approved','rejected','exported','expired')),
  approver text, decided_at timestamptz, rationale jsonb, audit_seq bigint);
CREATE TABLE agent_memory (key text PRIMARY KEY, value jsonb NOT NULL, updated_at timestamptz NOT NULL);
CREATE TABLE cap_alert (decision_id uuid PRIMARY KEY REFERENCES decision, identifier text UNIQUE NOT NULL, xml text NOT NULL, sig_b64 text, created_at timestamptz NOT NULL);
CREATE TABLE household_login (household_id uuid PRIMARY KEY, login_name text UNIQUE NOT NULL, pw_hash text NOT NULL, failed int NOT NULL DEFAULT 0, locked_until timestamptz);
CREATE TABLE session (token_sha256 bytea PRIMARY KEY, household_id uuid NOT NULL, created_at timestamptz NOT NULL, last_seen timestamptz NOT NULL, expires_at timestamptz NOT NULL);
-- audit_log / audit_checkpoint: §B12
```

**Migrations:**
- **Options:**
  - A. A hand-rolled runner.
  - B. Alembic: needs SQLAlchemy (an ORM we don't use, and a C-extension wheel question).
  - C. yoyo-migrations: an unverified pg8000 backend.
- **Choice: A.** `app/migrate.py` reads `db/migrations/NNNN_*.sql` in order. Each file runs in one transaction. It records `version` and the file's sha256, and **refuses to start if an applied file's checksum has changed** (drift guard).
- Forward-only (no down migrations tonight); a fix is a new file.
- It runs as `bn_migrator` via `docker compose run --rm app python -m app.migrate` before `up`.

## B7. F5 triage endpoint calling `predict()`

**Options:**
- **A. Call `predict()` per HTTP request.** Latency spikes, HTTP traffic can hammer NNPA, and two viewers can see different rankings.
- **B. A scorer task on a tick.** It runs every 30 s, and immediately when a new outage touches an enrolled postcode (debounced 2 s). It builds one batch of every at-risk household × outage and calls `predict()` once, on a **dedicated single-thread executor** (TF graph-mode `model.predict` is blocking and shouldn't run on the event loop). It writes `triage_snapshot`, and the API serves the latest one.
- **C. The agent computes triage inside its 60 s loop.** Too slow for the "two houses" moment.

**Choice: B.** The agent's 60 s loop **reads** the latest snapshot. Part A §13 "scored in the path" becomes: *every event updates state on arrival; at-risk households are re-scored in one NNPA batch per tick.*

**Contract** (`contracts/model.md`, Nate's side):
```
predict(features: list[dict], elapsed_h: np.ndarray) -> list[{
  "quantiles": {"q50": h, "q75": h, "q90": h},      # remaining hours
  "surv": [S(1),...,S(24)],                          # conditional survival per hourly bin
  "p_exceeds_reserve": float, "eta_h": float, "interval": [lo, hi]
}]
```

**Harm maths** (backend side; pure function, unit-tested):
- `E[max(0, T_rem − r)] = ∫_r^∞ S(u | elapsed) du`. Sum over the 24 hourly bins from `r`.
- Beyond 24 h, use a **geometric tail** with the last bin's hazard: `S(24)·(1−h₂₄)/h₂₄`. The result is capped at 72 h so it stays finite.
- `harm = severity × (0.2 if other_backup else 1.0) × E[(T_rem − r)+]`.
- **Quantile rule (Part A §5):**
  - no backup → `q90`;
  - `reserve > 2 × q50` → `q50`;
  - otherwise `q75`.
- `escalate = Q_q > r_remaining`, **OR** a welfare check is unanswered after 15 min.
- **An SMS can never set `escalate=false` for a no-backup patient.** This is a hard guard in code, with its own test.
- **Ties** break on lower `r_remaining`, then on `patient_id`, so the ordering is deterministic.

**Endpoint:**
```
GET /api/triage?limit=50&cursor=<rank>
200 {"tick_at":"…+00:00","model":{"id":"m2-hazard-v1","sha256":"…","label":"REAL"},
     "items":[{"rank":1,"patient_ref":"P-0007","outage_id":123,"scale":"street",
       "device":"o2_concentrator","reserve_left_h":3.1,"remaining_h":{"q50":2.4,"q75":4.0,"q90":7.9},
       "q_used":"q90","harm":4.6,"escalate":true,
       "why":["no backup → q90","q90 7.9 h > reserve 3.1 h"],
       "decision_id":"…|null"}],
     "next_cursor":51}
```
- `patient_ref` is a display pseudonym. **No name, contact or postcode leaves the API.**

**Failure modes:**
- **Model unsigned or refused** (Ahmed's verifier) → the scorer falls back to **M1 Kaplan–Meier**, sets `model.label = "FALLBACK_KM"`, and the UI shows it.
- **`predict()` raises or takes >10 s** → the last snapshot is kept, marked `stale_since`, and a `source_health` scorer event fires.
- **NNPA unavailable** → same code on CPU (`NNPA_DEVICES=0`), with `label` noting CPU.

## B8. F7 horizon grading

**Options:**
- **A. Fixed-horizon binary outcome with explicit censoring rules**, giving a Brier score on uncensored rows plus a bound.
- **B. IPCW Brier** (Graf et al. 1999, as implemented in scikit-survival's `brier_score`). Statistically right under *independent* censoring. But it needs a censoring-distribution estimate that tonight's handful of grades can't support, and feed disappearance is probably *not* independent of restoration.
- **C. Treat a disappearance as a restoration.** Explicitly banned by Part A §9.

**Choice: A, plus a sensitivity bound.**

**Rule:** a prediction made at `t0` for horizon `h` asks "is this outage still off at `t0+h`?" The grader runs every 60 s on predictions where `t0 + h + 4 min ≤ now` (4 min is two polls of grace).

| Situation at `t0+h` | Outcome |
|---|---|
| `restored_explicit` and `restored_at ≤ t0+h` | `y=0` |
| Status `active`, or `restored_at > t0+h`, and the source's last **successful** poll is after `t0+h` | `y=1` |
| `vanished` before `t0+h`, source stale/down across `t0+h`, or `restored_explicit=false` (SSEN approximated) | **censored**: `outcome NULL`, `reason` set, not in Brier |
| `planned` outage | not predicted, not graded |

- **Grade only outage-level predictions** (one per outage per tick, deduped by `UNIQUE(outage_id, made_at, horizon_h, model_id)`). Patient-level rows are views over the same survival curve.
- **Thin the samples:** log at most **one prediction per outage per 15 min** for grading. Otherwise one long outage dominates the Brier score.
- **Report:** Brier by `{horizon, source, model_id}`, plus `n_graded`, `n_censored`, and a **bound**: Brier with all censored rows set to `y=0`, and again with all set to `y=1`. If the bound is wide, say so on screen.
- **Primary metric = UKPN only** (explicit restored timestamps). SSEN is shown separately as "approx". NPg is used for detection, not grading, until its `incidentstatus` code mapping is verified.

**Start time matters:** start logging **M1 KM predictions as soon as ingest is live (~00:30)**, not at 02:00. Overnight N then roughly doubles, and M2 arrives as a second `model_id` graded alongside.

**Failure modes:**
- Grader crash → it's idempotent (`grade.pred_id` is the primary key), so it just resumes.
- Clock skew → all times are UTC from the sources. `received_at` is logged to measure feed lag.

## B9. Time handling

- **Store `timestamptz` only.** Set the session `TimeZone = 'UTC'` on every connection.
- **Python:** only aware datetimes (`datetime.now(UTC)`). A lint test rejects naive `datetime.now()` and `utcnow()`.
- **Per-source parse rules** (§B4 table) live in one module `app/timeparse.py`, with tests per format:
  - `"2026-10-15T00:49:22"` (UKPN, local);
  - `"+00:00"`;
  - `"+0000"`;
  - `"Z"`;
  - epoch.
- **Display:** the API returns ISO-8601 with `+00:00`. The UI converts to the grid's IANA zone (`grids/gb.yaml: tz: Europe/London`).
- **CAP:** must use the `hh:mm:ss±hh:mm` form, **never `Z`** (CAP 1.2 spec); UTC is written `-00:00`.
- **DST:** UK clocks change on Sun 25 Oct 2026, after the event. The UKPN local-time parse still uses `zoneinfo` with `fold=0`, so it stays correct later.

## B10. Fixed cells with k≥11 and complementary suppression

**Options:**
- **A. A fixed WGS84 degree grid**: integer-indexed and nested.
- **B. The OSGB national grid** (1/5/10 km). Clean metric squares, but corners need an OSGB36→WGS84 transform for MapLibre and CAP, and pyproj on s390x is unverified.
- **C. Postcode sectors and districts.** Irregular polygons that need boundary files, and they vary hugely in size.

**Choice: A.** Integer micro-degrees avoid float drift.

| Level | Cell size | ≈ size in N England | Shown at zoom |
|---|---|---|---|
| L1 | 0.010° lat × 0.016° lon | ~1.1 × 1.1 km | ≥ 12 |
| L2 | 5×5 L1 (0.05° × 0.08°) | ~5.5 km | 9–11 |
| L3 | 5×5 L2 (0.25° × 0.40°) | ~27 km | ≤ 8 |

- `cell_id = f"L{n}:{floor(lat/Δlat)}:{floor(lon/Δlon)}"`. The parent is integer division by 5.
- The server owns the grid. **There is no endpoint that accepts coordinates.**

**Suppression algorithm** (`app/cells.py`, runs every 15 min, not per event, so ticks can't be differenced):
1. Count enrolled patients per L1 cell, and per category if any category breakdown is shown (default: totals only).
2. **Primary:** any count in 1..10 is marked suppressed. **0 is published** (the CMS policy allows zero).
3. **Complementary, per parent** (L2 over its 25 L1 children, L3 over its 25 L2 children):
   - Let `S` = suppressed children with count > 0.
   - If `|S| == 1`, or `sum(S)` is in 1..10, add the **smallest non-zero published sibling** to `S`. Repeat until `sum(S) ≥ 11` or no candidates remain.
   - If no candidates remain, **suppress the parent** too.
4. Apply the same rule upward, L2 → L3. Then re-check L2 children against L3 (one extra pass; it converges because suppression only ever grows).
5. **Banding** of published counts: 11–19 stays exact; at 20+, round to the nearest 5. This protects against differencing between publish cycles.
6. **Utility-facing** aggregates (Part A §4) are lagged by one publish cycle.

**Test (property-based, hand-rolled loop, 500 random trees):** for every parent, `parent_total − Σ published children` must be 0 or ≥ 11, and no published value may be in 1..10.

**Failure mode:** with very few synthetic patients, almost everything gets suppressed. Seed the synthetic register densely in the demo fault areas (≥ 15 per demo L1 cell) so the map isn't empty.

## B11. Fault dedupe across feeds

Covered in §B4. In short:
- exact natural key per feed;
- content-hash versioning;
- `vanished` after two misses;
- **no cross-DNO merge** (disjoint licence areas);
- sensor ↔ DNO outages linked, never merged, within same-cell ±30 min.

The combiner decides the scale; the backend keeps both rows so the localiser can be scored against the DNO's postcode list.

## B12. Hash-chained audit log with signed checkpoints

**Options:**
- **A. Chain computed in the DB.** A `SECURITY DEFINER` function under `pg_advisory_xact_lock` reads the head, computes `sha256(prev ‖ body)` with Postgres's built-in `sha256()`, and inserts. Ordering is serialised by the DB.
- **B. Chain computed in Python by a single audit task.** Also correct in one process, but a second writer (a migration or a psql session) could fork the chain.
- **C. pgaudit or WAL-based.** Logs statements, not domain events; not tamper-evident by itself.

**Choice: A.**

```sql
CREATE TABLE audit_log (
  seq bigint PRIMARY KEY,
  body text NOT NULL,                 -- canonical JSON (app-made): {"at","actor","kind","ref","data"}
  kind text GENERATED ALWAYS AS ((body::jsonb)->>'kind') STORED,
  prev_hash bytea NOT NULL CHECK (length(prev_hash)=32),
  hash bytea NOT NULL UNIQUE CHECK (length(hash)=32)
);
CREATE FUNCTION audit_append(p_body text) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = bn, pg_temp AS $$
DECLARE v_seq bigint; v_prev bytea;
BEGIN
  PERFORM pg_advisory_xact_lock(727274);
  SELECT seq, hash INTO v_seq, v_prev FROM audit_log ORDER BY seq DESC LIMIT 1;
  v_seq  := coalesce(v_seq, 0) + 1;
  v_prev := coalesce(v_prev, decode(repeat('00', 32), 'hex'));
  INSERT INTO audit_log(seq, body, prev_hash, hash)
  VALUES (v_seq, p_body, v_prev, sha256(v_prev || convert_to(p_body, 'UTF8')));
  RETURN v_seq;
END $$;
REVOKE ALL ON audit_log FROM PUBLIC;
CREATE FUNCTION audit_no_change() RETURNS trigger LANGUAGE plpgsql AS
$$ BEGIN RAISE EXCEPTION 'audit_log is append-only'; END $$;
CREATE TRIGGER audit_no_upd_del BEFORE UPDATE OR DELETE ON audit_log FOR EACH ROW EXECUTE FUNCTION audit_no_change();
CREATE TRIGGER audit_no_trunc  BEFORE TRUNCATE ON audit_log FOR EACH STATEMENT EXECUTE FUNCTION audit_no_change();
```
- The trigger shape is allowed: TRUNCATE triggers are statement-level only (Postgres 17 CREATE TRIGGER docs).
- **Canonical body:** `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`.
  - It's stored as **text**, not jsonb, so verification re-hashes the exact bytes. jsonb would re-order keys and normalise numbers.
  - `at`, `actor` and `kind` live **inside** the body, so they're covered by the hash.
- **What gets audited:** every agent tool call; every decision state change; every approval; model load and verify results; CAP export; login success and failure; checkpoint creation; `mark_source_stale`; recalibration before and after.
  - **Not** every heartbeat. The chain is for decisions, not telemetry.

**Checkpoints:**
- Every **500 rows or 5 min**, whichever comes first, the app sends `{"seq":n,"head":hex,"at":…}` (canonical) to **Ahmed's signer**.
  - Signer contract: `POST http://signer:8100/sign {"purpose":"audit_checkpoint","payload_b64":…}` → `{"alg":"ML-DSA-65","key_id":…,"sig_b64":…}`.
- Stored in `audit_checkpoint(seq PK, head, at, alg, key_id, sig_b64, published_ref)`.
- 🟠 **Off-box publication:** see the decisions list.

**Verify** (`GET /api/audit/verify`):
1. Stream rows by `seq` in pages of 5,000. Recompute each hash, and check both `prev_hash` linkage and `seq` contiguity.
2. Check the **latest checkpoint's** signature via the signer's `/verify`, and check its `head` equals the recomputed hash at that `seq`.

```json
{"ok": false, "rows": 18234, "first_bad_seq": 1771, "reason": "hash_mismatch",
 "last_checkpoint": {"seq": 18000, "sig_ok": true, "head_matches": true}, "took_ms": 412}
```

**Threat coverage (honest):**

| Attacker | Result |
|---|---|
| App roles | Can't UPDATE or DELETE (REVOKE + trigger) |
| Table owner | Blocked by the trigger, unless they `DISABLE TRIGGER` |
| Superuser | Can rewrite rows **and** recompute the whole chain. Caught only by the **signed, off-box** checkpoint head. This is why off-box matters, and why we say "tamper-evident", not "tamper-proof" |

**Demo:** as `postgres`, run `ALTER TABLE … DISABLE TRIGGER audit_no_upd_del; UPDATE … SET body = …`. Verify turns red at that seq.

## B13. REST API

**Choice:** FastAPI (pure, needs pydantic-core's s390x wheel), plain uvicorn, **1 worker** (in-memory queues and state).
- Everything is under `/api`; the SSE stream is `/stream`. nginx proxies both.
- Errors are `{"detail": …}` with correct status codes.
- Cursor pagination is `?limit` (≤ 200) and `?cursor`.
- Freeze `contracts/openapi.yaml` by dumping `app.openapi()` once the shapes below exist. Rama mocks from it.

| Endpoint | Role conn | Response (abridged) |
|---|---|---|
| `GET /api/health` | none | `{"ok":true,"db":true,"writer_lag":0,"model":"m2…","uptime_s":…}` |
| `GET /api/sources/health` | api | §B17 |
| `GET /api/outages?status=active&since=` | api | `[{id,source,label,status,started_at,elapsed_h,customers,scale,cell_l1,centroid:[lat,lon],postcode_count}]`. **Postcode lists are returned for public DNO data only, never joined to patients** |
| `GET /api/grids/{id}/stress` | api | `{"grid":"gb","hz":50.02,"measured_at":…,"state":"NORMAL","seconds_to_next_rung":null,"label":"LIVE"}` |
| `GET /api/cells?level=1..3&bbox=` | api | `[{cell_id,level,bounds:[[lat,lon]…],patients:"suppressed"|int,outage_scale,risk_tomorrow}]`. `bbox` only selects cells; nothing is returned at point level |
| `GET /api/areas/risk?date=` | api | `[{district,p_ge_k,expected,label}]` |
| `GET /api/triage` | api | §B7 |
| `POST /api/decisions/{id}/approve` `{"approve":true,"note":"…"}` | api (EXECUTE `approve_decision`) | `{"decision_id","state":"approved","audit_seq"}`. 409 if not `awaiting_approval` |
| `GET /api/agent/decisions?cursor` | api | `[{id,tool,state,created_at,args_summary,rationale}]` |
| `GET /api/agent/grades` | api | `{"by_horizon":[{h:2,model_id,brier,n,n_censored,bound:[lo,hi]}],"trend":[…]}` |
| `GET /api/alerts/cap/{decision_id}` | api | `application/cap+xml` (403 unless approved) + header `X-Signature-ML-DSA-65` |
| `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/me/home` | api | §B16 |
| `GET /api/audit/verify` | api | §B12 |
| `GET /stream` | none | §B14 |

**Approval guard (important):** the control-room UI's approvals need *some* operator auth too. Otherwise anyone on the public IP can approve a 999 escalation. Minimum: a single operator account via the same session mechanism as §B16 (role `operator`).

## B14. SSE `/stream`

**Options:**
- **A. sse-starlette 3.5.0** (pure; starlette ≥ 0.49.1 and anyio ≥ 4.7, both satisfied). It has a 15 s default ping, `send_timeout` and disconnect handling. It's **already required by `llama_cpp.server`**, so there's no extra dependency risk.
- **B. A hand-rolled `StreamingResponse`.** Works, but pings, disconnects and headers are all on us.
- **C. WebSockets.** Needs a websocket implementation: plain uvicorn has none without the `websockets` or `wsproto` package. Bidirectional isn't needed.

**Choice: A.**

**Broadcaster:**
- One `Broadcaster` holds `set[asyncio.Queue(maxsize=256)]` and a `deque(maxlen=2000)` ring of `(id, event, data)`.
- **Events:** `stats` (coalesced, 1/s: events/s, queue depths, dropped), `outage`, `triage` (diff of the top 20 per tick), `decision`, `grade`, `source_health`, `audit_checkpoint`.
- **Never one SSE message per raw sensor event.** At 2k/s that would swamp the browser.
- `id:` is a monotonic int; `retry: 3000`.
- **Resume:** on `Last-Event-ID`, replay from the ring if it's still there. Otherwise send `event: resync`, and the client refetches REST.
- **Slow client** (its queue is full): drop that client's oldest message and flag a `resync` for it.
- Max 50 concurrent clients, then 503.
- `send_timeout=10` kills dead sockets.

**nginx (verified to work):**
- nginx buffers proxied responses by default (`proxy_buffering on`). It honours `X-Accel-Buffering: no`. `proxy_read_timeout` defaults to 60 s *between reads*, so the 15 s ping keeps the stream alive.
- Set the header in the app *and* add belt-and-braces config:
```nginx
location /stream {
  proxy_pass http://app:8000/stream;
  proxy_http_version 1.1;
  proxy_set_header Connection "";
  proxy_buffering off;
  proxy_cache off;
  gzip off;
  proxy_read_timeout 1h;
}
```

## B15. F15 CAP 1.2 export

**Options:**
- **A. Hand-write it with `xml.etree.ElementTree`** (stdlib).
- **B. `capparselib`.** A *parser*, last released 2021, and it pins `lxml==4.6.3`, which would need a source build on s390x. DO NOT USE.
- **C. Jinja2 template.** Jinja2 is in the image, but string templates make it easy to emit invalid XML.

**Choice: A.** Validate in tests only with `xmlschema` (pure) against the vendored OASIS `CAP-v1.2.xsd`.

**Fields** (spec-required elements in **bold**):
- `<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">`
  - **identifier** `blacknaught-<decision_id>`;
  - **sender** from config (`cap_sender`);
  - **sent** `2026-10-18T02:10:00-00:00` (no `Z`);
  - **status** `Exercise` 🟠 (demo/synthetic; never `Actual`);
  - **msgType** `Alert`;
  - **scope** `Public`;
  - `note`: "Draft by Blacknaught agent; approved by <operator>; SIMULATED patients".
- `<info>`:
  - `language en-GB`;
  - **category** `Infra`, plus `Health`;
  - **event** "Power cut affecting electricity-dependent residents";
  - **urgency** `Expected`;
  - **severity** `Moderate|Severe` (Severe if any escalated no-backup patient is inside);
  - **certainty** `Observed` if DNO-confirmed, else `Likely`;
  - `senderName`, `headline` (≤ 140 chars, Granite text validated by Ahmed's number validator), `description`, `instruction`, `web`.
  - `expires` = now + 6 h.
- `<area>`:
  - **areaDesc** from postcode districts (e.g. "N1, N5");
  - `polygon` = the convex hull of the affected postcodes' lat/lon, in `lat,lon` pairs, ≥ 4 pairs, closed (first = last). If there are fewer than 3 distinct points, use `circle` `lat,lon radius_km`.
  - **Never** cell-level patient counts, and no patient locations.

**Flow:**
1. Agent: `draft_cap_alert`. The decision goes to `awaiting_approval`.
2. An operator approves.
3. The backend builds the XML, has the signer sign its SHA-256 (ML-DSA-65), stores it in `cap_alert`, and appends to the audit log.
4. `GET /api/alerts/cap/{id}` serves it.
5. Idempotent: rebuilding returns the stored XML; it's never regenerated after approval.

## B16. `/me/home` auth (own-data view)

**Options:**
- **A. HTTP Basic at nginx.** It sends the password on every request (cleartext if the demo is on plain HTTP). The app would have to trust a `X-Remote-User` header, and there's no logout or lockout.
- **B. A stateless signed token** (HMAC / JWT HS256). No revocation; easy to get the details wrong.
- **C. A server-side opaque session.**

**Choice: C.**
- `POST /api/auth/login {"login":"home-ama","passphrase":"…"}`:
  - verify with `argon2.PasswordHasher().verify` (argon2id; argon2-cffi 25.1.0 is in the image);
  - on success, issue `secrets.token_urlsafe(32)` (256 bits; OWASP says ≥ 128) and store **only its SHA-256** in `session`;
  - set cookie `bn_session; HttpOnly; SameSite=Strict; Path=/api; Secure` (Secure only when served over TLS).
- **Idle 30 min / absolute 8 h.** OWASP's guide is 15–30 min idle for low-risk apps.
- A new token on every login (prevents session fixation).
- `POST /api/auth/logout` deletes the row.
- **Lockout:** 5 failures → `locked_until = now + 15 min`. A per-IP token bucket of 10 per minute. Every success and failure is audited.
- `GET /api/me/home` takes **no ID parameter**. The household comes from the session only (no IDOR possible). It returns:
```json
{"household":"home-ama","label":"SIMULATED","power":"off","since":"…","reserve":{"device":"o2_cylinder","ends_at":"…","hours_left":5.5},
 "voltage":[{"t":"…","pu":0.97}],"bands":{"brownout_pu":0.9},"next_action":"Switch to cylinder now. Reply 2 for help.",
 "grid_context":{"hz":50.01,"note":"grid health: the same for everyone"}}
```
- Note that the response has **no ETA** (Part A §4).
- **Fixture logins:** 2–3 demo households, seeded from a secrets file that's generated on the VM. Passphrases are never in git.
- **CSRF:** SameSite=Strict plus JSON-only POSTs (`Content-Type: application/json` required) is enough here.

## B17. `/sources/health`

- **Per source, in memory, persisted via `source_poll`:**
  - `last_attempt`, `last_success`, `consecutive_failures`, `last_error`, `records_last`, `latency_ms_p50`, `staleness_s = now − last_success`.
- **Status:**
  - `ok`;
  - `stale` if `staleness_s > 3 × interval`;
  - `down` if `> 6 × interval`, or 5 consecutive failures;
  - `degraded` on schema drift (§B4).
- **Also reported:** `db_writer` (queue depth and lag), `scorer` (last tick, model label), `signer` (last OK), and `granite` (last OK; optional).
- **On any status change:** an SSE `source_health` event, plus an `event` on `critical` that the agent consumes for `mark_source_stale` (LR → 1, widen intervals).
```json
{"at":"…","sources":[{"source":"ukpn","status":"ok","interval_s":120,"staleness_s":41,"records_last":62,"consecutive_failures":0,"label":"LIVE"}]}
```

## B18. Field encryption (AES-256-GCM) and the postcode blind index

**The problem:** Part A says "AES-GCM via CPACF", but there is **no `cryptography` package in the image and no s390x wheel**, and the OpenSSL CLI can't do GCM.

**Options:**
- **A. `ctypes` → the image's `libcrypto`** (`EVP_aes_256_gcm`, EVP_Encrypt*/Decrypt*, `EVP_CTRL_GCM_GET_TAG`/`SET_TAG`).
  - About 80 lines, and **no new dependency**.
  - OpenSSL picks CPACF (KMA) on s390x automatically, so the CPACF claim stays true.
  - Tested with **NIST GCM known-answer vectors** on the VM.
- **B. Encrypt and decrypt inside Ahmed's trixie signer**, where `apt install python3-cryptography` exists, built against OpenSSL 3.5. This is clean, but it adds a network hop to every register read and couples the scorer to the signer's uptime.
- **C. Build `pycryptodome` from its sdist.** It needs gcc in the image (unverified). It also uses its own AES code, not OpenSSL, so the **CPACF claim would be false**.

**Recommendation: A** (🟠 for the team: it's a hand-written binding to a crypto library, and that needs Ahmed's review).

- Format: `nonce(12) ‖ ciphertext ‖ tag(16)`, with AAD = `patient_id` bytes. Random 96-bit nonces; volume is far below the 2³² per-key limit.
- **Envelope:** the DEK is wrapped by the signer's KEK at rest, and unwrapped once at app start via `POST signer/unwrap`, so the DEK lives only in app memory.
- **Postcode matching without decrypting:** `postcode_bidx = HMAC-SHA256(k_bidx, normalised_postcode)` (stdlib `hmac`), compared against the HMAC of each DNO postcode.
  - That's an equality join, with no plaintext postcodes in the register.
  - Trade-off: a blind index leaks *equality* (two patients share a postcode), which is accepted.

## B19. Secrets and config

- **Secrets** are generated on the VM with `openssl rand -hex 32` into `~/blacknaught/secrets/` (mode 600, git-ignored):
  - `db_<role>_pw`
  - `dek_wrapped`
  - `bidx_key`
  - `household_seed.json`
  - `operator_pw`
- They're mounted with compose `secrets:` at `/run/secrets/*`. The app reads `BN_DB_PW_FILE`-style variables (the same convention as the postgres image's `POSTGRES_PASSWORD_FILE`), so **values never appear in `docker inspect` or env dumps**.
- **Non-secret config:** `config/app.toml` (stdlib `tomllib`) for intervals, thresholds and the CAP sender, plus `grids/*.yaml` (PyYAML is in the image).
- **Guardrails:**
  - only `.env.example` is committed;
  - `gitleaks` runs before push (laptop);
  - the app refuses to start if any secret file is missing, or if `operator_pw` is under 16 characters.
  - **Never log a secret:** the logger has a redaction filter for keys matching `pw|key|token|secret|passphrase`.

## B20. Testing

- **Tools:** `pytest==9.1.1` and `coverage==7.16.2` (both have pure-Python wheels; coverage falls back to its Python tracer, which is fine) plus `pytest-cov==7.1.0`. **anyio's built-in pytest plugin** handles async tests (anyio is in the image), so no pytest-asyncio is needed.
  - API tests use `httpx.ASGITransport`, with no server.
  - `xmlschema==4.3.2` is used for CAP only.
  - Everything is installed in a `test` requirements file, not in the runtime image layer.
- **Test DB:** `blacknaught_test`, created by the init script in the same postgres container.
  - A session fixture runs every migration from zero (which also tests the migration runner).
  - Each test runs inside a transaction that is rolled back. Audit-chain tests use a fresh schema instead, because the trigger blocks cleanup by design.
- **Must-have tests** (aim for ≥ 80% line coverage on `app/`):
  1. **Feed parsers** against fixtures recorded tonight (`fixtures/ukpn_live.json`, `npg_live.json`, `ssen_live.json`, `elexon.json`, `postcodes_bulk.json`): field mapping, restored detection, the UKPN local-time → UTC conversion, and `vanished` after two misses.
  2. **Dedupe/versioning:** the same record twice → 1 row; a changed status → version 2 plus an `outage_version` row.
  3. **Roles:** `bn_api` can't SELECT `patient`; `bn_ingest` can't UPDATE `audit_log`; the owner's UPDATE is blocked by the trigger.
  4. **Audit:** append 1,000 rows, then verify OK. A superuser edit with the trigger disabled → `first_bad_seq` is correct. Checkpoint signature with a mock signer.
  5. **k-suppression property test** (§B10).
  6. **Harm and escalation:** the two-houses case (4 h cylinder → escalate; 15 h ventilator → SMS), and "SMS can't de-escalate a no-backup patient".
  7. **Grading:** every row of the §B8 outcome table.
  8. **CAP:** validates against the XSD; dates have no `Z`; the polygon is closed.
  9. **AES-GCM:** NIST KAT vectors, a tampered tag → failure, and a wrong AAD → failure. **Run on the VM** (big-endian plus the real libcrypto).
  10. **Auth:** lockout, idle expiry, and no IDOR (`/me/home` ignores any query parameter).
  11. **SSE:** the `Last-Event-ID` resume path and the slow-client resync.
- **Command:** `docker compose run --rm app pytest -q --cov=app --cov-report=term-missing`. Run it on the VM before every merge to `main`. The laptop is for the fast loop only.

## B21. Getting backend code onto the VM

**Options:**
- **A. Rebuild the image on every change.** Minutes per iteration.
- **B. Bake dependencies into the image once, and bind-mount the code read-only.** A change is `git pull && docker compose restart app` (seconds).
- **C. `scp` files.** Bypasses git, and judges read the history.

**Choice: B.**
```dockerfile
# docker/app.Dockerfile
FROM registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest
COPY requirements-app.txt constraints-image.txt /tmp/
# -c pins every package the image already has, so pip can never upgrade numpy/TF/anyio/httpx…
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements-app.txt -c /tmp/constraints-image.txt
WORKDIR /srv
CMD ["/opt/venv/bin/uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1","--proxy-headers"]
```
- `requirements-app.txt`: `fastapi==0.143.3 starlette==1.8.0 pydantic==2.14.1 pydantic-core==2.50.1 uvicorn==0.54.0 sse-starlette==3.5.0 pg8000==1.31.5 scramp==1.4.17 asn1crypto==1.5.1 opentelemetry-api==1.45.1 typing-inspection annotated-types`.
- **httpx is not listed:** it's already in the image.
- `constraints-image.txt` is `reference/jupyter-lab-ml_packages.txt` verbatim.
- **The same image serves Granite.** Add `pydantic-settings==2.16.0 starlette-context==0.5.1` and run `python -m llama_cpp.server --model /models/granite-3.3-2b-instruct-be.Q4_K_M.gguf --n_threads 2 --host 0.0.0.0 --port 8080` as a second service. Never `pip install llama_cpp_python[...]`: that risks rebuilding the zDNN build.

**Compose essentials:**
- `app`: `volumes: ["./app:/srv/app:ro","./contracts:/srv/contracts:ro","./config:/srv/config:ro","./grids:/srv/grids:ro"]`, `expose: ["8000"]` (no `ports:`), `restart: unless-stopped`, `mem_limit: 3g`, healthcheck `/api/health`, `depends_on: db: condition: service_healthy`.
- `db`: `postgres:17`, `volumes: ["/srv/vault/pg:/var/lib/postgresql/data"]` (LUKS mount), `ports: ["127.0.0.1:5432:5432"]` only if needed for psql, `mem_limit: 768m`, `shared_buffers=192MB`, healthcheck `pg_isready`.
- `edge`: `nginx:stable` (trixie, OpenSSL 3.5) is the **only** service with a public port.

**Deploy runbook:**
```
laptop: git push origin sali/<feature>  →  PR/merge to main
VM:     cd ~/blacknaught && git pull --ff-only
        docker compose run --rm app python -m app.migrate     # only if db/migrations changed
        docker compose restart app && docker compose logs -f --tail=50 app
```
Rebuild (`docker compose build app`) only when `requirements-app.txt` changes.

---


---

## Parked (doable, decided not to do; revisit triggers included)

### Options decided against
| Option | Why not (for now) | Revisit if |
|---|---|---|
| Triage-only headline | Team chose predict + protect (18 Oct) | Prediction layers show no skill |
| Bangladesh as lead + PGCB load-shedding model (M3); Pakistan slide | Fails the free-healthcare filter (OOP 79% / 53%); time | The healthcare filter is dropped |
| "UK model, just input their frequency/voltage" | Outage causes differ (load-shedding vs faults); dishonest transfer | Never (use per-grid config + local labels) |
| Kaggle simulated-fault classifier | MATLAB-simulated data, easy to attack | Labelled as simulated, with spare time |
| OpenDSS physics-sim fault location | No s390x build; sim→field gap | Off-box generation is acceptable |
| Waveform fault detection | No real open labelled dataset | One appears |
| Per-home graphs on the shared map | Privacy breach (k≥11) | Never |
| Shared SSH key | Leaked; can't revoke one person | Never |
| Supabase DB / Vercel as the demo URL | Data must stay on LinuxONE; judges check the IP | Vercel only as an extra mirror |
| HMM grid-state cross-check; "how different are the grids" panel; globe intro as P0 | Time | Spare data/ML or frontend hours |
| `cryptography` package; psycopg 3; Redis/LISTEN-NOTIFY; WebSockets | No s390x wheel / needs libpq / extra service / not needed | Part B lists the conditions |

### From Part B's original review (point-in-time, already applied)
#### Doability check of PRD v3 (17 Oct, applied)

**Clock:** 22:15 → 03:00 is about 4.75 h per person.

**The backend load as written (§18 Sali row) is about 6–6.5 h, so it doesn't fit.** The verdicts below assume Sali's order is:
1. contracts + schema;
2. ingest;
3. API/SSE;
4. audit;
5. triage;
6. grading;
7. cells;
8. CAP.

### Features
| # | Verdict | Reduced version / replacement |
|---|---|---|
| F1 ingest | **DOABLE-REDUCED** | P0 is UKPN + SSEN + NPg + Elexon + the postcodes.io cache (~75 min). **IODA → P1** (only the target-grid replay needs it). **Open-Meteo stays with Nate's M8 script** (a daily batch), not the live ingest. NPg is detection-only (no explicit restore). |
| F2 sensor sim | **DOABLE-REDUCED** | Real-footprint sim is fine. But **1–2k events/s needs ~60–120k simulated sensors at a 60 s heartbeat**: live faults alone give a few thousand. Add a **load-test mode** (synthetic fleet or 50× replay) and quote the *measured* rate. |
| F3 combiner + scale | **DOABLE-REDUCED** | Hand-set LRs and the quorum rule; drop the "GB DNO-feed weight learned". |
| F4 M2 | **DOABLE-REDUCED** | XGBoost AFT + Keras 24-bin hazard on the VM, served on NNPA. **UKPN cross-operator check only if UKPN data is downloaded by 00:30.** ENWL registration is on the critical path. |
| F5 triage | **DOABLE** | As §7. ~35 min, with a KM fallback first. |
| F6 agent | **DOABLE-REDUCED** | Tools write to a **simulated SMS outbox** (no SMS provider; that would be a new external service). `recalibrate` is fitted on the ENWL 2023 validation split. Overnight live grades (tens, not hundreds) are *reported* and checked for drift, but too few to refit isotonic regression honestly. |
| F7 grading | **DOABLE** | As §8. **Start logging KM predictions at ~00:30**, so the overnight N is meaningful. UKPN is primary. |
| F8 Granite | **DOABLE** | Same app image plus the `[server]` extras' dependencies (all pure or s390x wheels). Q4_K_M at about 2 GB RSS. Pre-generate on decision; no generation inside the request path. |
| F9 security core | **DOABLE-REDUCED** | ML-DSA signing ✓ (signer container). **AES-GCM via ctypes libcrypto** (the image has no `cryptography`). LUKS ✓ on the host. iptables ✓. Roles ✓. Off-box checkpoints are 🟠 (needs a scoped write credential). Trivy ✓. |
| F10 UI | **DOABLE-REDUCED** | Rama: map + triage + two-houses + agent panel + audit view first. CAP/SMS previews last. |
| F11 M8 area risk | **DOABLE-REDUCED (P1)** | Train on 2015–2026 rather than 2000–26 (fewer Open-Meteo archive calls). Show the map overlay only if BSS > 0. |
| F12 grid stress | **DOABLE-REDUCED (P1)** | Live Elexon gauge + rule ✓. NESO 9 Aug 2019 replay only if the CSV is pulled by 01:00. |
| F13 target-grid replay | **DOABLE-REDUCED (P1)** | One week of Accra data from the bucket fallback; same classifier; brownout counts only. |
| F14 "My home" | **DOABLE-REDUCED (P1)** | The backend is ~45 min (§16), but it's #3 on the cut list. Build it only if CAP is done before 02:45; otherwise cut it. |
| F15 CAP 1.2 | **DOABLE-REDUCED (P1)** | Export endpoint + XML (~35 min), at 02:20–02:55. If late, Ahmed's `draft_cap_alert` stores the draft and the export lands at 06:00 as a fix. |
| F16 shortage model | **NOT DOABLE** tonight | Replacement: a slide in the roadmap, with the target grid's published shedding-stage table. |
| F17 | Roadmap (as written) | — |

### Architecture / stack items
| Item | Verdict | Note / fix |
|---|---|---|
| App `FROM jupyterlab-image-s390x` + pip FastAPI etc. | **DOABLE** | pydantic-core has a cp312 s390x wheel; the rest is pure. **httpx is already in the image (don't pip it)**. Pin with `-c` against the image freeze. fastapi 0.143 now pulls `opentelemetry-api` (pure). |
| pg8000 | **DOABLE** | pure; scramp/asn1crypto pure. |
| `cryptography` in the image | **NOT available** | No s390x wheel on PyPI (50.0.2); not in the image. Replacement: ctypes → libcrypto EVP (CPACF via OpenSSL), or apt `python3-cryptography` inside the trixie signer. `openssl enc` is **not** an option (no GCM). |
| `llama_cpp_python` server in the image | **DOABLE** | `python -m llama_cpp.server` needs uvicorn, fastapi, pydantic-settings, sse-starlette, starlette-context, PyYAML. Pip those **individually**, never `llama_cpp_python[server]`. |
| `postgres:17` s390x | **DOABLE** | ✓ (but `postgres:17-bookworm` has no s390x). |
| `debian:trixie` s390x | **DOABLE** | ✓, but **not needed for nginx**: `nginx:stable` is built `FROM debian:trixie-slim` with OpenSSL 3.5. Keep trixie only for the signer (`python:3.13-slim-trixie`). |
| PQ TLS edge | **DOABLE-REDUCED** | `ssl_ecdh_curve X25519MLKEM768:X25519;` on `nginx:stable`. **But the demo URL is `http://IP:<port>`**, and a self-signed cert on a bare IP shows a browser warning. 🟠: HTTPS on 8443 with a locally-trusted CA on the recording laptop, or show PQ only via `openssl s_client -groups X25519MLKEM768` in the terminal take. |
| SSE through nginx | **DOABLE** | `proxy_buffering off` / `X-Accel-Buffering: no`, HTTP/1.1, read timeout > ping (15 s < 60 s default). |
| LUKS | **DOABLE** (on the host) | `cryptsetup` on a file image "tries to allocate a loopback device" automatically. Do it **on the VM host, not inside a container** (a container would need `--privileged` and `/dev/loop*`). After a VM reboot it needs a manual `cryptsetup open` before `docker compose up` (runbook). |
| CAP 1.2 library | **Hand-write** | No maintained writer on PyPI. `capparselib` is a 2021 parser pinned to lxml 4.6.3 → DO NOT USE. ElementTree + an XSD test via `xmlschema`. |
| Signer "inside app" (§11 diagram) | **NOT DOABLE as drawn** | The app image's OpenSSL is the image's own (very likely Ubuntu 3.0, so no ML-DSA). Signer = **its own `python:3.13-slim-trixie` container** (OpenSSL 3.5), with a small HTTP API on the internal network. |
| Memory budget | **DOABLE-REDUCED** | Steady state is OK: app ~2.5 + Granite ~2.0–2.5 + PG ~0.5 + edge 0.05 + signer 0.05 ≈ 5.6 GB. **But a concurrent `ml.train` (+2–3 GB) or a live Jupyter kernel pushes past 8 GB.** Fixes: set `mem_limit`s; **train with Granite stopped**; add a 4 GB swapfile on the 50 GB disk as an OOM guard; stop the notebook container before demos. |
| 3 vCPU contention | **DOABLE-REDUCED** | Granite at `n_threads=2` saturates 2 of 3 vCPUs while generating. Generate only on decisions, `max_tokens ≤ 200`, cached; never during the load-test take. |
| "1–2k events/s each scored as they arrive" (§13.3) | **NOT DOABLE as worded** | Events are *ingested and classified* on arrival; *scoring* is batched per tick. Re-word, and quote the measured events/s plus the batch size and latency per tick. |
| Contracts frozen by 23:00 | **DOABLE** | `events.schema.json` and `openapi.yaml` are generated from the Pydantic models in §3/§13. |

### PRD fixes (`§ → change`)
1. **§5 → the `<<COUNTRIES>>` placeholder is unfilled.** Fill it from research §13, or replace it with "see Decision Log".
2. **§6 F1 → the polling description.** Make it: "UKPN/NPg/SSEN 120 s, Elexon 30 s (`from`/`to`); IODA 10 min (P1); Open-Meteo daily via M8 job. UKPN restores are explicit; SSEN approximate; **NPg has no restore timestamp → detection only**."
3. **§6 F2 / §13.3 → the event-rate claim.** Replace "about 1–2k events/s … each scored as they arrive" with "events are classified on arrival; at-risk households are re-scored in one NNPA batch per tick; sustained *N* events/s measured in a load-test replay (evidence/)".
4. **§6 F6 / §9 tools → SMS.** `notify_carer` writes to a **simulated SMS outbox** (no SMS gateway). `recalibrate` is fitted on the ENWL validation split; overnight grades are reported and drift-checked.
5. **§6 F9 / §12 Crypto row / §14 → AES-GCM.** "AES-256-GCM via OpenSSL libcrypto (CPACF) through a ctypes binding, *or* in the trixie signer; the lab image has no `cryptography` package and `openssl enc` has no GCM."
6. **§6 F16 → priority.** P2 / slide only (not doable tonight).
7. **§9 step 5 / §6 F7 → grading.** Add: "censored if vanished or stale before the horizon; excluded, counted, and bounded; UKPN primary".
8. **§11 diagram, edge line.** Change to `nginx:stable (official image, built on debian:trixie-slim, OpenSSL 3.5)`: no custom trixie build.
9. **§11 diagram, app line.** Change to `+ pip fastapi uvicorn pg8000 sse-starlette` (httpx is already in the image), pinned with `-c` to the image freeze; **1 uvicorn worker**.
10. **§11 diagram, signer.** Move the signer **out of `app`** into its own `python:3.13-slim-trixie` container (OpenSSL 3.5); the app calls it over the internal network.
11. **§11 diagram, granite line.** Make it "same app image + pip `pydantic-settings sse-starlette starlette-context`; `python -m llama_cpp.server`; never reinstall `llama_cpp_python`".
12. **§11 memory budget.** Add `mem_limit`s, "train with Granite stopped", a 4 GB swapfile, and the Jupyter container stopped (not just kernels).
13. **§11 Core API.** Prefix with `/api`. Add `POST /api/auth/login|logout`. **Approvals need operator auth** (otherwise anyone on the public IP can approve an escalation).
14. **§12 DB row.** Pin `postgres:17` (not `-bookworm`, which has no s390x image).
15. **§12 Ops row.** "LUKS on the VM host (file image → automatic loop device); manual unlock after reboot."
16. **§12 hour-1 checks.** Add `docker run --rm <lab image> sh -c 'cat /etc/os-release; python -c "import ssl;print(ssl.OPENSSL_VERSION)"; ldconfig -p | grep -E "libcrypto|libpq"; which gcc'`. This decides the AES-GCM route.
17. **§13.5 / §17 demo URL.** Decide HTTP vs HTTPS (🟠). "PQ TLS" and "recorded against `http://`" contradict each other.
18. **§14 Integrity.** "Checkpoints every 500 rows or 5 min; published to a separate checkpoints repo with a write-only deploy key" (🟠), and the audit covers decisions, not telemetry.
19. **§14 Map privacy.** Name the algorithm:
    - WGS84 fixed 3-level grid;
    - k≥11 primary suppression (0 published);
    - per-parent complementary suppression;
    - 15-min publish;
    - banding ≥ 20 to the nearest 5.
20. **§18 timeline.** Backend load as listed is about 6 h for one person. Move **CAP export to after 02:20 (P1)** and cut **/me/home** unless it's ahead of schedule. Start **KM prediction logging at 00:30** so the overnight grade count is meaningful.
21. **§4 "my home".** Add: "session login, argon2id, no ID in URL; returns no ETA".

---



### v2 sections (Bangladesh/Pakistan-led version), kept verbatim


#### v2 §0: the old one-liner and target
- "Blacknaught works out, live, whether a home, a feeder, a zone or a whole grid has lost power. It predicts how much longer the outage will last against each medically dependent patient's backup, and gives health workers a capacity-aware list of who to reach first. It grades every prediction against what really happened and corrects itself."
- **Deployment:** running live on Great Britain's open grid data, calibrated for Bangladesh (the lead deployment), with Pakistan as the next step.

#### v2 §1: Bangladesh and Pakistan evidence
- **Bangladesh**
  - Peak load-shedding reached 3,757 MW (10 Aug 2026). Khulna had 13–14 h a day of cuts (Oct 2026).
  - National grid collapse on 4 Oct 2022. IODA logged a 370-minute event (about 6.2 h), and the press reported about 90% of supply back after roughly 7 h.
  - In Apr 2026 Dhaka was spared while rural REB areas took 6–8 h a day of cuts. REB's own figures exceed PDB/PGCB's.
  - In 2014 a 438 MW loss took the grid from 50.33 to 48.65 Hz in 6.8 s. Under-frequency load-shedding cleared only 415 of 1,001 MW, and the country was dark in about 59 s.
  - The grid has no automatic generation control (AGC) and no rate-of-change-of-frequency (RoCoF) relays.
- **Pakistan**
  - K-Electric's very-high-loss feeders average 12 h 14 min of outage a day (NEPRA, Sept 2026).
  - Load-shedding hits residential feeders first and hospital feeders last.
  - SAIDI excludes generation- and transmission-caused outages.
- **No utility register of medically dependent people at home** was found in Bangladesh or Pakistan. Load-shedding exemptions cover facilities only.
- **Out-of-pocket health spending:** Bangladesh 79%, Pakistan 53%. This is why the "free healthcare" filter was dropped in v2, and why v3 re-filtered the countries.
- **Prevalence:** no estimate exists for home oxygen or ventilation in Bangladesh or Pakistan. COVID-era concentrators went to facilities, not homes. We never quote a patient count.
- **IPS backup:** a 350 W concentrator on an IPS gets about 1–3 h (12 V 150 Ah gives about 0.9 kWh usable, roughly 2 h at 410 W). Ask at enrolment; never assume zero.

#### v2 §2: scope table
| Layer | Status |
|---|---|
| GB (live) | Elexon, SSEN, NPg, ENWL/UKPN, NESO 1-s |
| Bangladesh (calibrated) | PGCB hourly episode model (2015–2026, CC BY); live BPDB zone shed; IODA replay of 2022; GB fault durations labelled TRANSFERRED |
| Pakistan (next step) | Calibration constants only: grid-code bands, feeder-class shedding order, NEPRA statistics. No open sub-daily outage dataset exists |
| Cut | Indonesia, Central Asia, "global" claims |

#### v2 §3.1: grid constants table
| Field | GB | Bangladesh | Pakistan |
|---|---|---|---|
| `nominal_hz` | 50 | 50 | 50 |
| `nominal_v` | 230 (+10/−6%) | 220 ⚠ unverified (220–230) | 230 (±5%) |
| Threshold ladder | 49.8–50.2 normal · outside 49.5–50.5 for ≤60 s · LFDD from 48.8 | 49.5 no load increase · 49.3 operator shedding · 49.1 SCADA feeder trips · UFLS 48.9 / 48.8 / 48.7 (2014 scheme) · generators held to 51.5 | target 50 ± 0.05 · sensitive 49.8–50.2 · tolerance 49.5–50.5 · contingency 49.3 |
| Synchronous areas | 1 | 3 river regions balanced separately · India via HVDC (not synchronous) | NTDC + K-Electric (K-Electric islands itself during disturbances) |
| Timezone / weekend | Europe/London, Sat–Sun | Asia/Dhaka (DST in 2009), Fri–Sat | Asia/Karachi (DST 2002–09), configurable by province |
| Seasons | — | Monsoon, cyclone, Boro irrigation, Ramadan ⚠ verify | Regulatory summer 16 Apr–15 Oct |
| Reliability definition | Interruption ≥3 min | ⚠ unknown | Long interruption >5 min; excludes generation and transmission |
| Fragility | High inertia; RoCoF relays | Low inertia (21% reciprocating engines), no AGC, no RoCoF relays, UFLS 41% effective at night, 59 s to collapse | 0.5 Hz governor dead band in practice; 6,133 MW/Hz |

#### v2 §3.4: good/normal/bad bands, diverse training, grid difference
- **Bands:** per-grid percentiles of the stress index (<33rd percentile, 33rd–90th, >90th plus documented events). Sources: GB from NESO 1-s frequency plus demand; Bangladesh from PGCB shed ÷ demand.
- **HMM cross-check:** a 3-state hmmlearn model, states chosen by BIC, reporting the adjusted Rand index. A sanity check only, never proof. Display only, so the labels never become circular.
- **Sampling:** stratified by grid × band × season × hour × cause, with a cap per stratum. StratifiedGroupKFold (group = event) plus a time split. Event bootstrap of 5 XGBoost runs.
- **"How different are the grids?":** run on REAL harmonised durations from ENWL, UKPN and PGCB episodes.
  - Metrics: ECDFs, Wasserstein distance, Cliff's delta, Levene/Brown–Forsythe.
  - PSI uses fixed 10 bins plus a bootstrap null; the 0.1/0.25 cut-offs have no academic basis (Yurdakul & Naranjo 2020).
  - Rule: a large difference means a CAIDI time-ratio transfer labelled TRANSFERRED; a small difference means pool.
  - Never run these statistics on simulated frequency.

#### v2 §5.1: scale classifier (v3 keeps the logic in §7)
| Scale | Rule |
|---|---|
| Scale unresolved | Fewer than 2 anchors reporting; the patient's priority is unchanged |
| House | This sensor is silent, its anchors are reporting, and no schedule matches. Not lower priority for a no-backup patient. The action is an electrician or a prepaid top-up. Bangladesh prepaid meters: about 12% nationally in 2022, about 56% at DESCO, under 4% at BREB |
| Feeder, scheduled / unplanned | ≥60% of the cell silent within 5 min, on a schedule boundary or not |
| Zone | Several cells, plus a BPDB zone shed jump or an IODA province dip |
| Regional island | One BD river region, or the PK NTDC/K-Electric split |
| National/system | IODA drops across ≥2 provinces, plus stress EMERGENCY/SPLIT, plus mass silence |
| BROWNOUT | Powered, but V/V0 is below the device's `vmin_pu` |

#### v2 §5.2: duration regimes
- No published feeder schedules exist for Bangladesh in 2026, so the Bangladesh regime is a **zone shortfall hazard model**. Feeder schedules apply to Pakistan only (K-Electric, LESCO).
- **Regime A, Bangladesh (M3):** survival over PGCB shedding episodes, where an episode is a run of hours with shed ÷ demand above a threshold.
  - Covariates: demand, shortfall, fuel mix, imports, season, hour, day type.
  - BPDB divisional data gives zone offsets.
- **Regime B, GB-trained faults (M2):** used in BD/PK as an uncalibrated shape prior. Its scale is calibrated on IODA durations (BD 2022: 370 min), NEPRA CAIDI (a lower bound) and press events. It is labelled TRANSFERRED, with wide intervals.

#### v2 §5.5: evidence-combiner details kept for Ahmed/Nate
- Heartbeat silence becomes uninformative once outage duration exceeds `telco_backup_hours`.
- IODA: merge fragments less than 30 min apart; drop events that fire in ≥3 unrelated countries within ±10 min.
- A device behind backup contributes a weaker likelihood ratio.

#### v2 §4: workflow details
- **Night chain:** carer → oxygen supplier → 999 / Rescue 1122. Shedding often runs 23:00–04:30, while field workers work days.
- **Field workers:** CHCPs and health assistants in Bangladesh; Lady Health Workers in Pakistan (don't mix them up).
- **Integration:** Bangladesh has run DHIS2 since 2009. Blacknaught acts as a decision service on a DHIS2 Tracker program.
- **Coverage:** opt-in registers under-enrol; PG&E Medical Baseline reaches about 10% of eligible people. Use assisted enrolment at discharge; report coverage by district, sex and urban/rural.
- **Breaches:** Bangladesh 2023 birth-registration leak (about 50 M records); Pakistan NADRA 2019–23 (2.7 M records, with insider help).

#### v2 §16 timeline (superseded by v3 §18)
- Freeze at 23:00; agent overnight from 22:00; submit 09:30.
- **Cut order:** Pakistan → HMM → Granite → globe → PQ TLS → GB recalibration → NNPA.

#### v2 §20: what changed from v1
| Change | Reason |
|---|---|
| Scope cut to ~30%; 3 containers | v1 was ~5× capacity |
| Two-houses moment moved to a real GB fault | v1 was 100% synthetic |
| Stress = time to the grid's own next rung × fragility | v1's z-score made fragile grids look less stressed |
| Conditional survival; horizon grading; overnight run | v1 ignored elapsed time and censoring |
| BD model = PGCB shedding episodes | v1's "overrun" had no target variable |
| CAIDI transfer; NEPRA as a lower bound | No BD/PK fault-duration distribution exists |
| Grid-state bands on real data; HMM as a check only | v1's labels were circular |
| `grid.yaml` per synchronous area | Country-factors pass |
| BROWNOUT and regional-island scales; backup-aware sensing | Country-factors pass |
| Fixed SMS templates; Granite briefings in English only | Granite 3.3 doesn't support Bengali or Urdu |
| Fixed map cells; "tamper-evident"; consent wording | Differencing hole; overclaims |
| Home oxygen as the core device; dialysis dropped | Clinical reality |
| Anchor sensors, ≥2 co-reporters, no patient-phone sensing | Klugman design |
| Patients get actions plus a reserve clock, never an ETA; SMS can escalate but not de-escalate | False reassurance; spoofing |
| A single objective (expected harm-hours) | Internal contradictions |
| Insider-first security; NERR safeguards | Real BD/PK breaches |
| Fairness = calibration within region, plus miss rate, plus coverage | Measurable fairness |
| Novelty narrowed; emPOWER, PSR and NERR named | Overclaim |

---

## History

### The original 17 Oct timeline (superseded)
**Timeline (from Sat ~22:00):**

| When | Milestone |
|---|---|
| 22:00–23:00 | Credentials rotated; everyone's SSH key on the VM; image pulled; hour-1 checks; ENWL/UKPN downloaded; **contracts frozen** |
| 23:00–00:30 | Walking skeleton on the VM: ingest → DB → API → map; M1 baselines trained on the VM |
| 00:30–02:00 | M2 + NNPA serving; triage + two-houses; sensor sim; agent v1 |
| 02:00–03:00 | Grading starts **(must run overnight)**; Granite; security pieces; M8 if green |
| **03:00** | **Feature freeze for frontend, platform and ML** (API contract frozen); sleep in shifts; one person on evidence and README |
| **03:00–06:00** | **Backend keeps building** (Sali codes 00:30–07:00): parked items in order: CAP → `/me/home` → IODA. New endpoints only; no contract changes |
| **06:00** | **Backend freeze**; 06:00–07:00 fixes and iteration |
| 06:00–07:00 | Fixes, evidence screenshots, the uncut terminal take |
| 07:00–09:15 | Video (2 takes), edit, captions, deck PDF |
| **09:30** | **Submit** (team leader) |


### What changed from v2 to v3, and why

| Change | Reason |
|---|---|
| The fuse-box sensor flow, the scale flags and amber-style alerts (as CAP 1.2, human-approved) became features | Team pivot (Google form) |
| Fault localisation is a three-tier design: operator feed + sensors + wide-area | Critique: frequency can't localise; realisation: DNO feeds give postcodes |
| Sensor simulation is driven by real fault footprints, with noise, and scored against the DNO | Realisation pass §12.1 |
| M8 area fault risk for tomorrow (ENWL × Open-Meteo) | The team's "historical analysis / predict" ask, made honest |
| Real sensor data (Accra) and a target-grid replay | Realisation pass §12.2 |
| "My home" view (own data only) | Team ask, made privacy-safe |
| The agent is explicit (tool list, guardrails) | Team: "where is the agentic flow?" |
| Target countries re-filtered on frequent outages + free healthcare | Team requirement |
| Stack aligned to the IBM handoff: pg8000, Granite via the lab image's `llama_cpp_python`, LUKS, Trivy, port rules | The handoff is authoritative on platform facts |
| Freeze moved 23:00 → 03:00 | Nothing was coded by 22:00; follows the handoff timeline |
| Pitch wording: no "±1 Hz predicts blackouts", "minutes ahead", "every country" or "only APIs stop us" | Critique §11, §12.7 |

**Parked from v2 (not deleted):**

| Item | Reason | Revisit if |
|---|---|---|
| Bangladesh as lead deployment + PGCB shedding model M3 | Fails the free-healthcare filter; time | The team drops the healthcare filter, or N is ahead |
| Pakistan calibration slide | Same | Same |
| §3.4 grid-difference panel (ECDF/Wasserstein), HMM cross-check | Time | Spare data/ML hours |
| Globe intro as a P0 | Time | Spare frontend hours |
