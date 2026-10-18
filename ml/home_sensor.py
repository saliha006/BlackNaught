"""Layer 2, the served home-sensor early warning: will this home lose power in the next 30 minutes?

Builds on Sali's probe (backend/app/probe_precursor.py), reusing its loading and features so the numbers stay
comparable. Real nLine GridWatch Accra data, one week: days 1-4 train, day 5 calibrates the probability and sets the
"elevated" threshold (the top 1% of scores), days 6-7 test. /api/me/home shows "elevated" or "normal".

Run on the VM: python -m ml.home_sensor <accra-dir> <out-artifact.json>
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import probe_precursor as probe  # noqa: E402  (same features as the published probe)

FEATURES = probe.OWN          # the home's own last hour; the headline number is for this model
FLAG_SHARE = 0.01             # "elevated" = the top 1% of calibration-day scores, the probe's precision@1%
BOOTSTRAP_RUNS = 5            # brief: a 5-run bootstrap for ± figures
SEED = 7
PARAMS = {"objective": "binary:logistic", "eval_metric": "aucpr", "max_depth": 5, "learning_rate": 0.05,
          "subsample": 0.8, "colsample_bytree": 0.8, "nthread": 3, "seed": SEED}


class HomeSensorModel:
    def __init__(self, booster: xgb.Booster, calib_x: list[float], calib_y: list[float], threshold: float,
                 model_id: str, sha256: str = ""):
        self.booster, self.threshold, self.model_id, self.sha256 = booster, threshold, model_id, sha256
        self.calib_x, self.calib_y = np.asarray(calib_x), np.asarray(calib_y)

    def probability(self, x: pd.DataFrame) -> np.ndarray:
        raw = self.booster.predict(xgb.DMatrix(x[FEATURES]))
        # isotonic calibration stored as its breakpoints, so serving needs no sklearn
        return np.interp(raw, self.calib_x, self.calib_y)

    def score(self, window: dict) -> dict:
        """One home's latest feature values (the probe's names) -> what the home layer shows."""
        p = float(self.probability(pd.DataFrame([window]))[0])
        return {"p_off_30min": round(p, 4), "value": "elevated" if p >= self.threshold else "normal"}

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({
            "model_id": self.model_id, "features": FEATURES, "threshold": self.threshold,
            "calib_x": self.calib_x.tolist(), "calib_y": self.calib_y.tolist(),
            "booster": json.loads(self.booster.save_raw("json"))}))


def load(path: Path) -> HomeSensorModel:
    raw = path.read_bytes()
    doc = json.loads(raw)
    booster = xgb.Booster()
    booster.load_model(bytearray(json.dumps(doc["booster"]).encode()))
    return HomeSensorModel(booster, doc["calib_x"], doc["calib_y"], doc["threshold"], doc["model_id"],
                           hashlib.sha256(raw).hexdigest())


def fit(train: pd.DataFrame, calib: pd.DataFrame, model_id: str) -> HomeSensorModel:
    booster = xgb.train(PARAMS, xgb.DMatrix(train[FEATURES], label=train["label"]), num_boost_round=300)
    raw = booster.predict(xgb.DMatrix(calib[FEATURES]))
    iso = IsotonicRegression(out_of_bounds="clip").fit(raw, calib["label"])
    calibrated = np.interp(raw, iso.X_thresholds_, iso.y_thresholds_)
    threshold = float(np.quantile(calibrated, 1 - FLAG_SHARE))
    return HomeSensorModel(booster, iso.X_thresholds_.tolist(), iso.y_thresholds_.tolist(), threshold, model_id)


def metrics(y: np.ndarray, p: np.ndarray, flagged: np.ndarray) -> dict:
    return {"roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
            "precision_top1pct": probe.precision_at(y, p, FLAG_SHARE),
            "flag_rate": float(flagged.mean()), "flag_precision": float(y[flagged].mean()) if flagged.any() else 0.0,
            "base_rate": float(y.mean())}


def evaluate(model: HomeSensorModel, test: pd.DataFrame) -> dict:
    y = test["label"].to_numpy()
    p = model.probability(test)
    point = metrics(y, p, p >= model.threshold)
    # resample whole sensors: rows from one home aren't independent, so a row bootstrap would be too narrow
    rng = np.random.default_rng(SEED)
    sites = test["site_id"].unique()
    runs = []
    for _ in range(BOOTSTRAP_RUNS):
        pick = test["site_id"].isin(rng.choice(sites, size=len(sites), replace=True))
        runs.append(metrics(y[pick.to_numpy()], p[pick.to_numpy()], (p >= model.threshold)[pick.to_numpy()]))
    return {k: {"value": round(v, 4), "sd": round(float(np.std([r[k] for r in runs])), 4)} for k, v in point.items()}


def build(accra: Path, out: Path) -> dict:
    table = probe.features(probe.per_site_grid(probe.load(accra)))
    days = sorted(table["bin"].dt.normalize().unique())
    day = table["bin"].dt.normalize()
    train, calib, test = table[day < days[4]], table[day == days[4]], table[day > days[4]]
    model = fit(train, calib, "home-sensor-accra-v1")
    model.save(out)
    result = {"rows": {"train": len(train), "calibrate": len(calib), "test": len(test)},
              "sites": int(table["site_id"].nunique()), "threshold_p": round(model.threshold, 4),
              "test_days": [str(days[5])[:10], str(days[-1])[:10]], "test": evaluate(model, test)}
    return result


if __name__ == "__main__":
    print(json.dumps(build(Path(sys.argv[1]), Path(sys.argv[2])), indent=1))
