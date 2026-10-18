# Model contract

**Owner:** Nate (amend freely). This file is the backend's side: what `backend/app` calls today, so M2 and M8 can replace the stand-ins without touching triage or the API.

## Outage duration (M2 replaces the KM fallback)
**Called by** `backend/app/triage.py` (`Scorer`):
- once per active outage, every 30 s and on every new fault;
- from one dedicated thread, so a blocking `model.predict` (TF graph mode on NNPA) is fine.

**The object must have:**

| Member | Type | Meaning |
|---|---|---|
| `model_id` | `str` | e.g. `m2-hazard-v1`; stored on every prediction and grade |
| `sha256` | `str` | hash of the artifact file. The scorer refuses unsigned or tampered models once Ahmed's signer is in |
| `label` | `str` | `REAL` for M2, `FALLBACK_KM` for the stand-in; shown in the UI |
| `predict(elapsed_h: float) -> dict` | method | see below |

**`predict` returns:**
```json
{
  "quantiles": {"q50": 3.54, "q75": 8.34, "q90": 16.69},
  "surv": [0.95, 0.84, "…24 values…"]
}
```
- `quantiles` are **remaining** hours, given the outage has already lasted `elapsed_h`.
- `surv[i]` is P(still off after `i+1` more hours | already off `elapsed_h`), for i = 0..23. It must be non-increasing, in [0, 1].
- Grading uses `surv[1]` (+2 h) and `surv[3]` (+4 h) directly, and triage integrates `surv` for expected harm-hours.

**Reference implementation:** `backend/app/survival.py` (`KmModel`), fitted on all 312,936 ENWL outages. The artifact is `backend/models/km_enwl.json`.

**⚠ Open item: features (Nate + Sali to agree).** Today `predict` gets only `elapsed_h`, because KM ignores features. M2 needs outage features, so the call becomes `predict(features: dict, elapsed_h: float)`. Only fields available **live** can be used:

| Live field (`outage` table) | Sources | Notes |
|---|---|---|
| `started_at` → hour, weekday, month/season | all | UTC; convert with Europe/London |
| `customers` | all | NPg falls back to the predicted count |
| `cardinality(postcodes)` | all | footprint size |
| `lat`, `lon` → nearest ENWL district | all | for the district effect |
| `feeder.type` | NPg (`LV`/`HV_N`/`HV_S`), SSEN (`LV`/`HV`) | maps to ENWL `voltage` |
| `source` | all | the DNO itself |

ENWL columns that **don't** exist live (`direct_cause`, `main_equipment_involved_*`) can't be model inputs. Never use `total_customer_minutes_lost` or the restoration columns: they leak the answer.

**Artifact format:**
- XGBoost JSON or `.keras`, **never pickle** (s390x is big-endian).
- Signed by Ahmed's signer.
- Loaded from `BN_MODEL_PATH`.

## Area fault risk (M8 replaces the climatology baseline)
**Called by** `backend/app/main.py` → `/api/areas/risk` as `area_risk(model: dict, day: date) -> list[dict]`. Each item:
```json
{"district": "Bolton", "expected": 4.24, "p_ge_k": 0.80}
```
- One item per ENWL district.
- `expected` is the faults expected that day; `p_ge_k` is P(≥ k faults), with k = 3 today.
- The API adds `"label": "BASELINE"`. M8 should return `"label": "LIVE"` once it uses the live Open-Meteo forecast.

**Reference:** `backend/app/arearisk.py` (per-district monthly climatology, ENWL 1997–2026), artifact `backend/models/climatology_enwl.json`. M8's Brier skill should be reported against this baseline.

## Training data on the VM
- `~/data/raw/enwl_unplanned-outages.csv` (312,936 rows; `;`-separated; `incident_duration` is in minutes)
- `~/data/raw/ukpn_ukpn-iis.csv` (316,435 rows)
- `~/data/raw/SHA256SUMS`

Train on the VM (Jupyter on :38888, or `docker compose run app`), so the training is evidence.
