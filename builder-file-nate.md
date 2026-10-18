# Nate: Data & ML (datasets, models trained on LinuxONE, grid configs, evaluation)
**GitHub:** `aldrichbanas07` · **Branch:** `nate-ml` · **Brief last updated:** 2026-10-17 22:30 by Sali
**Spec:** `BLACKNAUGHT.md` (NOW at the top, then Part A spec, Part B backend design); the § numbers below refer to it.

## 0. How the agent reads this brief (every task)
0. **First, every prompt: `bash scripts/sync-context.sh`** (CLAUDE.md). If it says UPDATED, read `BLACKNAUGHT.md` → NOW and
   this brief again, and tell the user what changed before working.
1. Read the project `CLAUDE.md` in full, then this brief. Follow both.
2. **Only action `▶ Current tasks`**, top to bottom.
3. Before starting: `git fetch`, then read the new `progress.md` entries. Handle any open `⚠️ Conflicts: @nate` first.
4. **Ship sequence for each feature:**
   1. `no-slop`
   2. tests with coverage
   3. push `nate-ml`
   4. `git merge origin/main` into the branch and re-test
   5. merge to `main`
   6. add a `progress.md` entry
   - **Every completed task, not just features:** add a `progress.md` entry with your name, date and time, and push it
     to `main` straight away.
   - **Doc edits:** you may only move your own finished task into Archived. Publish it with
     `bash scripts/publish-context.sh "what changed"`. Never commit shared docs to `main`.

   Use the `debug` skill on every issue.

---

## 1. Ownership
**Owns:**
- `/ml`:
  - data prep
  - **M1** baselines
  - **M2** duration survival
  - **M8** area fault risk
  - **M3** recalibration logic
  - the **M4** stress rule
  - the **M5** LR table
  - **M9** Accra brownout/outage quorum
  - evaluation and fairness numbers
- `grids/*.yaml` (§5): every value with its source and year.
- `contracts/model.md`: `predict(features, elapsed_h) → {quantiles, p_exceeds_reserve, eta_h, interval}` and `area_risk(district, date) → {p_ge_k, expected}`.
- `data/` (git-ignored) and the synthetic-household statistics, which Ahmed's simulator uses.

**Does NOT touch:** `/backend` and `/db` (@sali), `/frontend` (@rama), `/infra` and `/agent` (@ahmed).

## 2. Contract & Guardrails
**Scope contract.** Nate is building:
- **M2, trained ON THE LINUXONE VM** inside IBM's image: XGBoost AFT + a Keras discrete-time hazard MLP (24 bins), on ENWL; cross-operator check on UKPN. The Keras model goes to Ahmed for NNPA serving.
- **M8, tomorrow's area fault risk:** P(≥k faults in each ENWL district tomorrow), using XGBoost Poisson on Open-Meteo ERA5 weather + season + base rate. Scored by Brier skill against climatology.
- The conditional survival and expected-harm-hours functions behind `predict()`.
- The grid YAMLs, the LR table, and the evaluation numbers in `docs/results.json`.

**Out of scope:**
- Kaggle fault simulations
- waveform classifiers
- OpenDSS
- PGCB/Bangladesh M3 (parked)
- the HMM
- the grid-difference panel (parked)

**Guardrails:**
- **Train on the VM** (it's evidence for judges). Save `evidence/train_log_*.txt` plus metrics JSON.
- **Never pip-install numpy, pandas, TF or torch.** Never pickle across endianness: save XGBoost JSON and `.keras`. Spot-check 5 predictions against the laptop.
- **ENWL feature whitelist:** cause, start time, season, voltage, primary substation, district, customers at start. **Never** customer-minutes or restoration columns, since they leak the answer.
- Use a time split (2000–22 train / 2023 validate / 2024–26 test) plus group-by-event. Never a random row split.
- Fix the stress thresholds **before** replaying 9 Aug 2019.
- Report every margin honestly. **No CSV/parquet over 100 MB in git.**
- **Accra data is CC BY-NC.** Coarsen GPS **off-box** to district or ~1 km before it reaches the VM.

---

## 3. ▶ Current tasks (2026-10-17 v3), in order
**▶ 2026-10-18 06:39 (from Sali)**
- ✅ **Your UKPN curve is live** (`m1-km-ukpn`): copied to `backend/models/km_ukpn.json`, `BN_MODEL_PATH` set in the app's compose, deployed with `infra/docker-compose.yml`. The grader now scores it next to `m1-km-enwl` by model id. README Results + Limits say which curve is live and why.
- 📌 **Home-sensor layer:** noted. `home.risk()` takes `"elevated"` / `"normal"` once a home has a sensor window; GB demo homes don't yet, so their home layer stays "no data".

**▶ New 2026-10-18 06:05 (from Sali)**
- ✅ **Triage is ready for M2** (on `main`): `Scorer` now selects `customers` and `feeder` and calls `model.predict({"started_at", "customers", "feeder"}, elapsed_h)` exactly as `contracts/model.md` says. KM accepts and ignores the dict, so nothing changed live.
- 📨 **One integration gap to close before the swap:** the backend loads its model with `survival.load(BN_MODEL_PATH)`, which only understands the KM JSON. M2 needs a loader that returns an object with `predict(features, elapsed_h)` → `{quantiles: q50/q75/q90, surv[24]}` plus `model_id`, `sha256` and `label` (`REAL`). Proposal: you ship it (it knows your artifact format) as `backend/app/m2.py` with `load(path)`, built only on what the IBM image already has (XGBoost / TF, no pickle); Sali then dispatches on the file type in one line. Say in `progress.md` if you'd rather Sali writes it.
- 📌 Ping Sali in `progress.md` when M2 is ready; the grader compares it to KM's live Brier (UKPN +2 h 0.165, +4 h 0.156) automatically, by `model_id`.

**▶ 2026-10-18 06:05 (from Sali)**
- ✅ **Elexon 0 Hz bug fixed** (your 05:07 find): readings outside 45–55 Hz are dropped in `parse_elexon`, with a test. On `main`.
- ✅ **Your context-script fix is merged** (`5f4f727`), with one change: the credential guard now matches the *shape* of a secret instead of fragments of real ones. Run once: `git config blacknaught.builder nate`.
- 📌 **M2 features:** noted, live fields only (start time, customers affected, voltage with "unknown"). Tell Sali in `progress.md` when M2 is ready and the final list is in `contracts/model.md`; Sali wires `features` into `predict(features, elapsed_h)` in `triage.py`.
- 📌 **The home-sensor model feeds the "home" layer** of the new `risk` block in `/api/me/home` (option C). Until it's served, that layer reads "no data" and the headline level stays "unknown".

**Status update 2026-10-18 02:40 (from Sali)**
**🔄 Headline changed 2026-10-18 (ADR):** "Blacknaught **predicts blackouts before they happen** and **protects the people they'd hurt most**."
- **Prediction layers:**
  - area fault risk (hours to days);
  - home sensors (minutes): flags homes likely to lose power in 30 min; real Accra probe: 1 in 5 top alerts true, 9× chance;
  - grid stress (seconds, NESO).
- **Triage + alerting** of electricity-dependent people stay the core of "who this helps".
- **Never say:** "predicts every blackout", "minutes ahead from frequency", "voltage dips warn of blackouts" (the probe shows ≈ chance).
- **New, now headline-critical (your area):**
  - **Layer 1, M8 weather fault risk.** This is the "days ahead" prediction; beat the climatology baseline (Brier skill).
  - **Layer 2, the home-sensor early-warning model.** Start from Sali's probe: `backend/app/probe_precursor.py`, with results in `evidence/07_precursor_probe.txt` and data in `~/data/raw/accra/` on the VM (7 days, GPS and ids already stripped). Ideas:
    - more days (stream more with the same stripping script; ask Sali);
    - a 5-run bootstrap for ± figures;
    - 15/60-min horizons;
    - calibration.
    - Then score the Accra replay (F13) so the demo shows live early warnings.
  - **Layer 3, M4 grid stress on the NESO 9 Aug 2019 replay** (F12): honest seconds of lead.
  - Order if short on time: M2 → layer 2 → M8 → M4.
- **Start with `progress.md` → "Start here"** on GitHub (clone, hooks, `scripts/sync-context.sh`, VM access).
- ⚠ **Times in this brief (00:30 skeleton, 03:00 freeze) predate the team starting.** Sali will confirm a new freeze time on Discord; until then, prioritise top-down.
- **The training data is already on the VM:**
  - `~/data/raw/enwl_unplanned-outages.csv` (312,936 rows) and `ukpn_ukpn-iis.csv` (316,435), with `SHA256SUMS`;
  - task 4 no longer waits on Sali.
- **The backend runs today on stand-ins you replace:**
  - a KM duration model (`backend/app/survival.py`, fitted on all of ENWL);
  - a climatology area-risk model (`backend/app/arearisk.py`).
- **The interface is written down:** `contracts/model.md`. ⚠ **Open item:** M2 needs outage features, so `predict(features, elapsed_h)`. Agree the live feature list with Sali (it's in that file).
- **Live grading is already scoring the KM model** (150+ real UKPN predictions, Brier ≈ 0.19 at 2 h). Your M2 gets graded the same way, side by side.
- **Training notebook pattern:** `notebooks/train_on_linuxone.ipynb` (executed in Jupyter on the VM, which is the evidence).

9. ⬜ **M5 LR table** (hand-set and documented; only the GB DNO-feed weight is learnable), plus household distributions (device, reserve, backup) for Ahmed's simulator. `[⚠ @ahmed]`
10. ⬜ **`grids/gb.yaml`** plus the target-grid YAMLs (§5, once countries are confirmed). Fields per PRD §5, including `labels_source`.
11. ⬜ **M8 area fault risk (P1, first in)**
    - Aggregate ENWL to district-day counts.
    - Join to Open-Meteo archive daily weather (max gust, precipitation, min/max temperature) at each district centroid.
    - Fit XGBoost Poisson; compute Brier skill against climatology on the time split.
    - `area_risk()` uses tomorrow's Open-Meteo forecast.
    - `[⚠ @sali /areas/risk; @rama map layer]`
12. ⬜ **M4 stress rule (P1).** `t_to_rung × fragility`. NESO 1-s replay of 9 Aug 2019: lead time to 48.8 Hz, plus false alarms per month over 12 normal months. `[⚠ @ahmed replay hook]`
13. ⬜ **M9 target-grid replay (P1)**
    - Request a key through the nLine form; fall back to the bucket with credit.
    - Take one week of 2021 Accra data and coarsen the GPS off-box.
    - Run the brownout detector (V/V0 < `vmin_pu`) and the outage quorum against `is_powered`.
    - Add a Ghana/target YAML.
14. ⬜ **Evaluation + fairness → `docs/results.json`:**
    - calibration per region; miss rate
    - a 5-run event bootstrap
    - a not-worst-case replay
    - the honest-limits text
15. ⬜ **03:00 freeze.** Then sleep in shifts.
16. ⬜ **06:00–07:00:** check the overnight grades and finalise the numbers.
17. ⬜ **Video:** your segment (model + risk map) and one line.

## 4. Done log (newest first)
- ✅ **Layer 2, home-sensor early warning (served)** (done 2026-10-18 06:32): `ml/home_sensor.py` on the Accra week (train days 1–4, calibrate day 5, test 6–7, 5-run bootstrap). Flags 0.96% of windows; 18.8% ± 1.1% come true, 8.9× the 2.1% base; AUC 0.666 ± 0.005. Artifact `~/shared/nate-runs/models/home_sensor_accra_v1.json`. Not yet: more Accra days, 15/60-min horizons, scoring the live Accra replay (F13). Task 9 deferred (time).
- ✅ **8. The real `predict()`** (done 2026-10-18 06:00): `ml/m2_serve.py`, closed-form conditional survival + quantiles from the AFT log-normal, recalibrated on UKPN 2021–24. Artifact `~/shared/nate-runs/models/m2_aft_ukpncal_v1.json`. Still worse than KM on UKPN 2024–25 (IBS 0.143 vs 0.131; C 0.50), so **not live**. Harm-hours stay in Sali's `harm.py`, which integrates `surv`.
- ✅ **7. Keras hazard MLP** (done 2026-10-18 05:58): 24 bins, trained on the VM; `~/shared/nate-runs/models/m2_hazard.keras` offered to Ahmed for signing/NNPA (not to be served yet).
- ✅ **6. XGBoost AFT** (done 2026-10-18 05:58): ENWL 2024–26 IBS 0.114 vs KM 0.121 (−5.5%, C 0.60); UKPN cross-check 0.149 vs 0.138 (worse). Notebook `ml/notebooks/m2_duration.ipynb`.
- ✅ **5. M1 baselines** (done 2026-10-18 05:58): KM, KM per cause (best on ENWL, 0.109, offline only), log-linear (no gain). Brier 2/4/8 h, IBS, C-index in `evidence/m2_metrics.json`.
- ✅ **4. ENWL + UKPN prep** (done 2026-10-18 05:46): `ml/prep.py` on the VM. 5-min cut, UKPN stages rolled into incidents, ENWL split 2000–22 / 2023 / 2024–26 with storms kept whole. ENWL 306,251 kept, UKPN 178,864. Tables in `~/shared/nate/data/prepared/`; log `evidence/train_log_prep.txt`.
- ✅ **2. Contract freeze** (done 2026-10-18 05:46): M2 features final in `contracts/model.md` (option A1: start time, customers, voltage LV/HV/unknown; ENWL-trained, UKPN cross-check). Sali wires `features` into `predict()` when M2 lands.
- ✅ **3. VM ML checks** (done 2026-10-18 05:07): all GO in the `notebook` container. XGBoost `survival:aft` + `count:poisson` train; JSON and `.keras` round-trips are exact on s390x; pandas 3.0.6 works. The zDNN plugin adds **no TF device**: it loads NNPA kernels from `tensorflow/core/kernels/_z_ops.so`, which is the check. Evidence: `evidence/08_ml_stack_checks.txt` (`nate-ml`); go/no-go posted in `progress.md`.
- ✅ **1. SSH key** (done 2026-10-18 03:01): Sali installed the `nate` key on `linux1`; login confirmed.

## 5. Waiting on / owed to others
- 📥 **Waiting on @sali:** ENWL + UKPN downloads.
- 📥 **Waiting on @ahmed:** VM access and the Jupyter container.
- 📤 **Owed to @sali:** stub `predict()` / `area_risk()` (hour 1), the real versions by about 01:30.
- 📤 **Owed to @ahmed:** the `.keras` model, the LR table, household distributions.
- 📤 **Owed to @rama:** `docs/results.json` and the risk-layer GeoJSON.

## 6. Working-style notes for the agent
- Explain s390x and NNPA gotchas. Keep stats rigorous and honest, and flag leakage loudly.
- Verbosity Level 0.

## 7. Reference
- **ENWL:** Open Net Zero `unplanned-outages1` (CC BY 4.0; login to download). **UKPN:** `ukpn-iis`.
- **Open-Meteo:** `archive-api.open-meteo.com/v1/archive` and `api.open-meteo.com/v1/forecast` (keyless; 10k calls a day).
- **NESO:** 1-s system frequency.
- **nLine:** https://nline.io/public-data/gridwatch
- **Method precedent:** Glasgow district-day fault forecasting (arXiv 2603.01653).
- **Ledger:** `research-and-codebase.md` §12.3, §12.2 and §13.

---
── Archived (superseded 2026-10-17 — do NOT action) ──
- **The v2 task list (18 items):**
  - contract freeze, VM checks
  - gb/bd/pk YAMLs, ENWL prep, M1, M2 AFT + Keras, `predict()`
  - M4 stress, M5 LRs
  - **M3 Bangladesh PGCB model**, CAIDI transfer ratios
  - the §3.4 grid-comparison panel, HMM grid-state bands
  - evaluation, 23:00 freeze
- **Why superseded:** PRD v3. Bangladesh/Pakistan are parked (they fail the free-healthcare filter). M8 area risk and M9 Accra replay are added. Training on the VM is explicit. The freeze moves to 03:00.
