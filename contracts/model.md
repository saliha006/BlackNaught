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
| `predict(features: dict, elapsed_h: float) -> dict` | method | see below |

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

**Features (decided 2026-10-18 by Nate: live fields only, option A1).** The call is `predict(features, elapsed_h)`. The backend passes three columns of the `outage` row as they are, and the model does all the mapping:
```python
features = {"started_at": row["started_at"],  # tz-aware datetime
            "customers": row["customers"],    # int | None (NPg falls back to the predicted count)
            "feeder": row["feeder"]}          # the jsonb dict | None
```

| Model input | From | Mapping |
|---|---|---|
| hour, weekday, month | `started_at` | Europe/London local time |
| log(1 + customers) | `customers` | missing → the ENWL training median, stored in the model artifact |
| voltage: LV / HV / unknown | `feeder.type` | NPg `LV` → LV, `HV_N`/`HV_S` → HV; SSEN `LV`/`HV` as is; UKPN (no voltage) and anything else → unknown |

- **Trained on ENWL only:** 2000–22 train, 2023 validate, 2024–26 test, with each storm (`exceptional_event_id`) kept in one split. ENWL 6.6/11 kV → HV; 33/132 kV (0.2% of rows) also → HV, because no live feed reports EHV.
- **Voltage is hidden on a random third of training rows**, so "unknown" (every UKPN outage) gets a trained answer, not an extrapolation.
- **No operator feature.** UKPN, NPg and SSEN outages are scored by the ENWL-trained model. The UKPN cross-check (Apr 2021–Mar 2025, never trained on) measures how well that transfers; M3 recalibration from live grades corrects the rest.
- **Not inputs:** `cardinality(postcodes)` (ENWL has no equivalent), the nearest ENWL district (meaningless outside the North West), cause and equipment (not live). Never `total_customer_minutes_lost` or the restoration columns: they leak the answer.
- **Offline benchmark only, if time allows:** the full ENWL whitelist (adds cause, primary substation, district). Never served.
- **Backend change (Sali):** `Scorer._at_risk` also selects `customers` and `feeder`; `Scorer._predict` passes the dict above.

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
- `~/data/raw/enwl_unplanned-outages.csv`: 312,936 outages, 2000–2026 plus 3 stray rows from 1997–98; `;`-separated.
  - The label is `incident_duration` (minutes), as in the KM stand-in. It appears to run to the last customer restored: for staged restorations, customer-minutes are below customers × duration.
  - In 19% of rows `restoration_date_time` is later than start + `incident_duration`; the label still follows `incident_duration`.
- `~/data/raw/ukpn_ukpn-iis.csv`: 316,435 **restoration-stage** rows = 180,059 incidents, Apr 2021–Mar 2025; `;`-separated.
  - Rolled up per `incident_reference`: first stage start → last stage end; customers summed over stages that aren't re-interruptions.
- `~/data/raw/SHA256SUMS`
- Both sources are cut at 5 minutes (brief). `python -m ml.prep ~/data/raw <out>` writes the prepared tables. Run of 2026-10-18 (`evidence/train_log_prep.txt`): ENWL 306,251 kept (train 269,170 · validate 9,828 · test 27,253; median 3.5 h); UKPN 178,864 kept (median 2.8 h).

Train on the VM (Jupyter on :38888, or `docker compose run app`), so the training is evidence.
