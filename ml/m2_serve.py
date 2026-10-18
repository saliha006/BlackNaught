"""The M2 duration model the backend calls (brief task 8): XGBoost AFT, recalibrated on UKPN, behind contracts/model.md.

The AFT model says log(duration) ~ Normal(mu(x), sigma), so conditional survival and remaining-time quantiles have
closed forms. Trained on ENWL, it ran long on UKPN, which restores faster; a location shift and spread fitted on UKPN
Apr 2021-Mar 2024 correct that, and UKPN Apr 2024-Mar 2025 checks the correction on outages it never saw.

Build on the VM: python -m ml.m2_serve <prepared-dir> <m2_aft.json> <m2_metrics.json> <out-artifact.json>
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import norm

from ml import m2

HORIZON_BINS = 24
MAX_REMAINING_H = 720.0          # same ceiling as the KM stand-in's quantile search
MIN_SURVIVAL = 1e-9
CALIBRATION_CUTOFF = pd.Timestamp("2024-04-01", tz="UTC")   # UKPN regulatory years 2021-24 fit, 2024-25 test


def voltage_of(feeder: dict | None) -> str | None:
    # NPg reports LV / HV_N / HV_S, SSEN LV / HV; UKPN sends no feeder type at all
    kind = (feeder or {}).get("type") or ""
    if kind == "LV":
        return "LV"
    return "HV" if kind.startswith("HV") else None


class M2Model:
    label = "REAL"

    def __init__(self, booster: xgb.Booster, customers_median: float, mu_shift: float, sigma: float, model_id: str,
                 sha256: str = ""):
        self.booster, self.customers_median = booster, customers_median
        self.mu_shift, self.sigma = mu_shift, sigma
        self.model_id = self.name = model_id
        self.sha256 = sha256

    def mu(self, table: pd.DataFrame) -> np.ndarray:
        x = m2.features(table, self.customers_median)
        return np.log(self.booster.predict(xgb.DMatrix(x))) + self.mu_shift

    def surv(self, table: pd.DataFrame, hours: np.ndarray) -> np.ndarray:
        return norm.sf((np.log(hours)[None, :] - self.mu(table)[:, None]) / self.sigma)

    def predict(self, features: dict, elapsed_h: float) -> dict:
        row = pd.DataFrame({"start": [pd.Timestamp(features["started_at"])], "customers": [features.get("customers")],
                            "voltage": [voltage_of(features.get("feeder"))]})
        mu, elapsed = float(self.mu(row)[0]), max(float(elapsed_h), 0.0)
        still_off = norm.sf((np.log(elapsed) - mu) / self.sigma) if elapsed > 0 else 1.0
        still_off = max(still_off, MIN_SURVIVAL)
        later = norm.sf((np.log(elapsed + np.arange(1, HORIZON_BINS + 1)) - mu) / self.sigma) / still_off

        def remaining(q: float) -> float:
            # solve S(elapsed + u) = (1 - q) * S(elapsed) for u
            return min(float(np.exp(mu + self.sigma * norm.isf((1 - q) * still_off))) - elapsed, MAX_REMAINING_H)

        return {"quantiles": {f"q{int(q * 100)}": round(max(remaining(q), 0.0), 2) for q in (0.5, 0.75, 0.9)},
                "surv": [round(min(float(s), 1.0), 6) for s in later]}

    def save(self, path: Path) -> None:
        doc = {"model_id": self.model_id, "customers_median": self.customers_median, "mu_shift": self.mu_shift,
               "sigma": self.sigma, "booster": json.loads(self.booster.save_raw("json"))}
        path.write_text(json.dumps(doc))


def load(path: Path) -> M2Model:
    raw = path.read_bytes()
    doc = json.loads(raw)
    booster = xgb.Booster()
    booster.load_model(bytearray(json.dumps(doc["booster"]).encode()))
    return M2Model(booster, doc["customers_median"], doc["mu_shift"], doc["sigma"], doc["model_id"],
                   hashlib.sha256(raw).hexdigest())


def calibrate(model: M2Model, table: pd.DataFrame, model_id: str) -> M2Model:
    residual = np.log(table["duration_h"].to_numpy()) - model.mu(table)
    return M2Model(model.booster, model.customers_median, model.mu_shift + float(residual.mean()),
                   float(residual.std()), model_id)


def build(prepared: Path, aft_path: Path, metrics_path: Path, out_path: Path) -> pd.DataFrame:
    enwl, ukpn = m2.load(prepared)
    meta = json.loads(metrics_path.read_text())
    booster = xgb.Booster(model_file=str(aft_path))
    booster = booster[: int(booster.attr("best_iteration")) + 1]
    raw = M2Model(booster, meta["customers_median"], 0.0, meta["aft_sigma"], "M2 AFT, ENWL only")
    fit, holdout = ukpn[ukpn["start"] < CALIBRATION_CUTOFF], ukpn[ukpn["start"] >= CALIBRATION_CUTOFF]
    served = calibrate(raw, fit, "m2-aft-ukpncal-v1")
    km = m2.Km(enwl.loc[enwl["split"] == "train", "duration_h"])
    board = m2.scoreboard([km, raw, served], {"UKPN Apr 2024-Mar 2025": holdout,
                                               "ENWL 2024-26": enwl[enwl["split"] == "test"]})
    served.save(out_path)
    print(f"calibrated on {len(fit):,} UKPN outages: mu shift {served.mu_shift:+.3f}, sigma {served.sigma:.3f}")
    return board


if __name__ == "__main__":
    print(build(*map(Path, sys.argv[1:5])).to_string(index=False))
