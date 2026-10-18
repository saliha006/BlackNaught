"""Feasibility probe: can a home's own sensor predict its power cut before it happens?

Real data: nLine GridWatch Accra (CC BY-NC 4.0), plug-in sensors reporting voltage + power state every ~2 min.
Label: does this sensor lose power within the next HORIZON minutes? Trained on days 1..N-2, tested on the
last 2 days (time split, no shuffling). Model A uses only the home's own last hour; model B adds how much of
the same district has already gone dark. Both are compared with the base rate and with simple rules.
Run on the VM: python -m app.probe_precursor /data/raw/accra
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_auc_score

HORIZON_MIN = 30
HISTORY_MIN = 60
NOMINAL_V = 230.0
SAG_PU = 0.9
BIN = "2min"


def load(folder: Path) -> pd.DataFrame:
    frames = [pd.read_csv(f, usecols=["time", "site_id", "voltage", "frequency", "district", "is_powered",
                                      "was_moved"]) for f in sorted(folder.glob("accra_*.csv.gz"))]
    df = pd.concat(frames, ignore_index=True)
    df = df[df["was_moved"].astype(str).str.lower() != "true"]
    df["time"] = pd.to_datetime(df["time"], utc=True, format="ISO8601")
    df["powered"] = df["is_powered"].astype(str).str.lower() == "true"
    return df.dropna(subset=["site_id", "time"])


def per_site_grid(df: pd.DataFrame) -> pd.DataFrame:
    """One row per site per 2-minute bin; gaps stay NaN (a silent sensor is unknown, not 'off')."""
    df = df.assign(bin=df["time"].dt.floor(BIN))
    g = (df.groupby(["site_id", "bin"])
           .agg(voltage=("voltage", "mean"), frequency=("frequency", "mean"), powered=("powered", "min"),
                district=("district", "first"))
           .reset_index())
    out = []
    for site, s in g.groupby("site_id"):
        s = s.set_index("bin").asfreq(BIN)
        s["site_id"], s["district"] = site, s["district"].ffill().bfill()
        out.append(s)
    return pd.concat(out).reset_index().rename(columns={"index": "bin"})


def features(grid: pd.DataFrame) -> pd.DataFrame:
    steps_hist = HISTORY_MIN // 2
    steps_half = steps_hist // 2
    steps_ahead = HORIZON_MIN // 2
    parts = []
    for _, s in grid.groupby("site_id"):
        s = s.sort_values("bin").copy()
        on = s["powered"].astype("float")
        v = s["voltage"].where(s["powered"] == True)  # noqa: E712 (NaN-aware)
        pu = v / NOMINAL_V
        onset = (on.shift(1) == 1) & (on == 0)
        s["label"] = (onset.rolling(steps_ahead, min_periods=1).max().shift(-steps_ahead) == 1).astype("float")
        s["v_last"] = pu
        s["v_min30"] = pu.rolling(steps_half, min_periods=5).min()
        s["v_mean60"] = pu.rolling(steps_hist, min_periods=10).mean()
        s["v_std60"] = pu.rolling(steps_hist, min_periods=10).std()
        s["sag_share60"] = (pu < SAG_PU).astype("float").where(pu.notna()).rolling(steps_hist, min_periods=10).mean()
        s["v_slope30"] = pu - pu.shift(steps_half)
        s["flicker60"] = onset.astype("float").rolling(steps_hist, min_periods=1).sum()
        s["coverage60"] = on.notna().astype("float").rolling(steps_hist, min_periods=1).mean()
        s["freq_last"] = s["frequency"]
        s["hour"] = s["bin"].dt.hour
        parts.append(s[s["powered"] == True])  # noqa: E712 — only predict for homes that still have power
    f = pd.concat(parts)
    # district context: share of the district's other reporting sensors already without power at this moment
    dark = grid.assign(off=(grid["powered"] == False).astype("float"), rep=grid["powered"].notna().astype("float"))  # noqa: E712
    d = dark.groupby(["district", "bin"])[["off", "rep"]].sum().reset_index()
    f = f.merge(d, on=["district", "bin"], how="left")
    # the scored home is powered and reporting, so "others" is everyone reporting minus itself
    f["district_dark_share"] = f["off"] / (f["rep"] - 1).clip(lower=1)
    return f.dropna(subset=["label", "v_mean60"])


OWN = ["v_last", "v_min30", "v_mean60", "v_std60", "sag_share60", "v_slope30", "flicker60", "coverage60",
       "freq_last", "hour"]
WITH_DISTRICT = OWN + ["district_dark_share"]


def precision_at(y: np.ndarray, score: np.ndarray, share: float) -> float:
    k = max(1, int(len(score) * share))
    top = np.argsort(-score)[:k]
    return float(y[top].mean())


def evaluate(f: pd.DataFrame) -> dict:
    days = sorted(f["bin"].dt.normalize().unique())
    split = days[-2]
    train, test = f[f["bin"] < split], f[f["bin"] >= split]
    y_tr, y_te = train["label"].to_numpy(), test["label"].to_numpy()
    result = {"rows_train": len(train), "rows_test": len(test), "sites": int(f["site_id"].nunique()),
              "base_rate_test": round(float(y_te.mean()), 4), "train_days": [str(days[0])[:10], str(days[-3])[:10]],
              "test_days": [str(days[-2])[:10], str(days[-1])[:10]], "horizon_min": HORIZON_MIN}
    for name, cols in (("own_sensor", OWN), ("own_plus_district", WITH_DISTRICT)):
        model = xgb.XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8,
                                  colsample_bytree=0.8, eval_metric="aucpr", n_jobs=3)
        model.fit(train[cols], y_tr)
        p = model.predict_proba(test[cols])[:, 1]
        result[name] = {"roc_auc": round(roc_auc_score(y_te, p), 3), "pr_auc": round(average_precision_score(y_te, p), 4),
                        "precision_top1pct": round(precision_at(y_te, p, 0.01), 3),
                        "top_features": sorted(zip(cols, model.feature_importances_.round(3).tolist()),
                                               key=lambda x: -x[1])[:4]}
    for name, score in (("rule_recent_flicker", test["flicker60"].to_numpy()),
                        ("rule_low_voltage", -test["v_min30"].fillna(1).to_numpy()),
                        ("rule_district_dark", test["district_dark_share"].fillna(0).to_numpy())):
        result[name] = {"roc_auc": round(roc_auc_score(y_te, score), 3),
                        "pr_auc": round(average_precision_score(y_te, score), 4)}
    return result


if __name__ == "__main__":
    folder = Path(sys.argv[1])
    raw = load(folder)
    print(f"loaded {len(raw):,} readings from {raw['site_id'].nunique()} sensors", flush=True)
    f = features(per_site_grid(raw))
    print(json.dumps(evaluate(f), indent=1, default=str))
