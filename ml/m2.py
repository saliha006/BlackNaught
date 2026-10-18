"""M1 baselines and the two M2 duration models (brief tasks 5-7), trained on ENWL and scored on ENWL 2024-26 and the
UKPN cross-check. Every model answers the same question: S(t) = P(power still off t hours after the fault starts).

Run on the VM through ml/m2_duration.ipynb, or: python -m ml.m2 <prepared-dir> <out-dir>
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import norm

HORIZONS_H = (2, 4, 8)
GRID_H = np.arange(1, 25)   # integrated Brier and the C-index risk score both use the first 24 hours
BINS = 24                   # brief: 24 hourly hazard bins; class 24 holds everything longer
HIDE_VOLTAGE = 1 / 3        # decision A1: UKPN has no voltage, so the models must learn "unknown"
SEED = 7


def load(prepared: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    def read(name: str) -> pd.DataFrame:
        table = pd.read_csv(prepared / f"{name}.csv.gz", low_memory=False)
        table["start"] = pd.to_datetime(table["start"], utc=True, format="ISO8601")
        table["duration_h"] = table["duration_min"] / 60
        return table
    return read("enwl"), read("ukpn")


def features(table: pd.DataFrame, customers_median: float, hide_share: float = 0.0,
             rng: np.random.Generator | None = None) -> pd.DataFrame:
    local = table["start"].dt.tz_convert("Europe/London")
    voltage = table["voltage"].map({"LV": "LV", "HV": "HV", "EHV": "HV"}).fillna("unknown")
    if hide_share:
        voltage = voltage.mask(rng.random(len(voltage)) < hide_share, "unknown")
    hour, month = local.dt.hour, local.dt.month
    return pd.DataFrame({
        "hour_sin": np.sin(2 * np.pi * hour / 24), "hour_cos": np.cos(2 * np.pi * hour / 24),
        "month_sin": np.sin(2 * np.pi * month / 12), "month_cos": np.cos(2 * np.pi * month / 12),
        "weekend": (local.dt.weekday >= 5).astype(float),
        "log_customers": np.log1p(table["customers"].fillna(customers_median).astype(float)),
        "volt_lv": (voltage == "LV").astype(float),
        "volt_hv": (voltage == "HV").astype(float),
        "volt_unknown": (voltage == "unknown").astype(float),
    }, index=table.index)


class Km:
    name = "M1 Kaplan-Meier"

    def __init__(self, durations_h: np.ndarray):
        # every outage in both sources has a restoration, so KM is the plain empirical survival curve
        self.sorted = np.sort(np.asarray(durations_h, dtype=float))

    def curve(self, hours: np.ndarray) -> np.ndarray:
        return 1 - np.searchsorted(self.sorted, hours, side="right") / len(self.sorted)

    def surv(self, table: pd.DataFrame, hours: np.ndarray) -> np.ndarray:
        return np.tile(self.curve(hours), (len(table), 1))


class KmByCause(Km):
    name = "M1 Kaplan-Meier per cause"

    def __init__(self, train: pd.DataFrame):
        super().__init__(train["duration_h"])
        self.by_cause = {cause: Km(group["duration_h"]) for cause, group in train.groupby("cause")}

    def surv(self, table: pd.DataFrame, hours: np.ndarray) -> np.ndarray:
        out = super().surv(table, hours)
        # cause isn't known live or in UKPN, so those rows fall back to the overall curve
        for cause, km in self.by_cause.items():
            out[(table["cause"] == cause).to_numpy()] = km.curve(hours)
        return out


class LogNormal:
    name = "M1 log-linear"

    def __init__(self, train: pd.DataFrame, customers_median: float):
        self.customers_median = customers_median
        x = self._design(train)
        y = np.log(train["duration_h"].to_numpy())
        self.beta = np.linalg.lstsq(x, y, rcond=None)[0]
        self.sigma = float(np.std(y - x @ self.beta))

    def _design(self, table: pd.DataFrame) -> np.ndarray:
        x = features(table, self.customers_median).drop(columns="volt_unknown").to_numpy()
        return np.column_stack([np.ones(len(x)), x])

    def surv(self, table: pd.DataFrame, hours: np.ndarray) -> np.ndarray:
        mu = self._design(table) @ self.beta
        return norm.sf((np.log(hours)[None, :] - mu[:, None]) / self.sigma)


class Aft:
    name = "M2 XGBoost AFT"
    params = {"objective": "survival:aft", "aft_loss_distribution": "normal", "aft_loss_distribution_scale": 1.0,
              "eval_metric": "aft-nloglik", "tree_method": "hist", "max_depth": 6, "learning_rate": 0.05,
              "nthread": 3, "seed": SEED}

    def __init__(self, train: pd.DataFrame, valid: pd.DataFrame, customers_median: float, rng: np.random.Generator):
        self.customers_median = customers_median
        dtrain = self._matrix(train, features(train, customers_median, HIDE_VOLTAGE, rng))
        dvalid = self._matrix(valid, features(valid, customers_median))
        self.booster = xgb.train(self.params, dtrain, num_boost_round=600, evals=[(dvalid, "validate")],
                                 early_stopping_rounds=25, verbose_eval=100)
        # the training scale is a loss setting; the spread used for probabilities is measured on held-out data
        self.sigma = float(np.std(np.log(valid["duration_h"].to_numpy()) - np.log(self._predict(dvalid))))

    @staticmethod
    def _matrix(table: pd.DataFrame, x: pd.DataFrame) -> xgb.DMatrix:
        matrix = xgb.DMatrix(x)
        matrix.set_float_info("label_lower_bound", table["duration_h"].to_numpy())
        matrix.set_float_info("label_upper_bound", table["duration_h"].to_numpy())
        return matrix

    def _predict(self, matrix: xgb.DMatrix) -> np.ndarray:
        return self.booster.predict(matrix, iteration_range=(0, self.booster.best_iteration + 1))

    def surv(self, table: pd.DataFrame, hours: np.ndarray) -> np.ndarray:
        mu = np.log(self._predict(xgb.DMatrix(features(table, self.customers_median))))
        return norm.sf((np.log(hours)[None, :] - mu[:, None]) / self.sigma)


class HazardMlp:
    name = "M2 Keras hazard MLP"

    def __init__(self, train: pd.DataFrame, valid: pd.DataFrame, customers_median: float, rng: np.random.Generator,
                 epochs: int = 12):
        import tensorflow as tf
        tf.keras.utils.set_random_seed(SEED)
        self.customers_median = customers_median
        x_train = features(train, customers_median, HIDE_VOLTAGE, rng).to_numpy("float32")
        x_valid = features(valid, customers_median).to_numpy("float32")
        scale = tf.keras.layers.Normalization()
        scale.adapt(x_train)
        self.model = tf.keras.Sequential([
            tf.keras.Input((x_train.shape[1],)), scale,
            tf.keras.layers.Dense(64, activation="relu"), tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dense(BINS + 1, activation="softmax"),
        ])
        self.model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy")
        self.history = self.model.fit(
            x_train, self.classes(train), validation_data=(x_valid, self.classes(valid)), epochs=epochs,
            batch_size=4096, verbose=2,
            callbacks=[tf.keras.callbacks.EarlyStopping(patience=2, restore_best_weights=True)])

    @staticmethod
    def classes(table: pd.DataFrame) -> np.ndarray:
        return np.minimum(np.floor(table["duration_h"].to_numpy()), BINS).astype("int32")

    def surv(self, table: pd.DataFrame, hours: np.ndarray) -> np.ndarray:
        p = self.model.predict(features(table, self.customers_median).to_numpy("float32"), batch_size=8192, verbose=0)
        # class k means the power came back in hour k, so P(still off at hour h) is the mass from class h onward
        cdf = np.cumsum(p, axis=1)
        return 1 - cdf[:, np.asarray(hours, dtype=int) - 1]


def c_index(risk: np.ndarray, durations_h: np.ndarray, sample: int = 3000, seed: int = SEED) -> float:
    """Harrell's C on a fixed random sample: P(longer predicted outage | longer actual outage); 0.5 = no skill."""
    pick = np.random.default_rng(seed).choice(len(risk), size=min(sample, len(risk)), replace=False)
    r, t = risk[pick], durations_h[pick]
    comparable = t[:, None] < t[None, :]
    score = (r[:, None] < r[None, :]) + 0.5 * (r[:, None] == r[None, :])
    return float(score[comparable].mean())


def evaluate(model, table: pd.DataFrame) -> dict:
    t = table["duration_h"].to_numpy()
    at = model.surv(table, np.array(HORIZONS_H))
    grid = model.surv(table, GRID_H)
    result = {f"brier_{h}h": float(np.mean((at[:, i] - (t > h)) ** 2)) for i, h in enumerate(HORIZONS_H)}
    result["ibs_24h"] = float(np.mean((grid - (t[:, None] > GRID_H[None, :])) ** 2))
    result["c_index"] = c_index(grid.sum(axis=1), t)
    result["n"] = len(table)
    return result


def scoreboard(models: list, tests: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = [{"model": m.name, "test": name, **evaluate(m, table)} for m in models for name, table in tests.items()]
    return pd.DataFrame(rows).round(4)


def run(prepared: Path, out: Path) -> pd.DataFrame:
    enwl, ukpn = load(prepared)
    train, valid, test = (enwl[enwl["split"] == s] for s in ("train", "validate", "test"))
    median = float(train["customers"].median())
    rng = np.random.default_rng(SEED)
    models, seconds = [], {}
    for build in (lambda: Km(train["duration_h"]), lambda: KmByCause(train), lambda: LogNormal(train, median),
                  lambda: Aft(train, valid, median, rng), lambda: HazardMlp(train, valid, median, rng)):
        t0 = time.perf_counter()
        model = build()
        seconds[model.name] = round(time.perf_counter() - t0, 1)
        models.append(model)
        print(f"trained {model.name} in {seconds[model.name]} s", flush=True)
    board = scoreboard(models, {"ENWL 2024-26": test, "UKPN cross-check": ukpn})
    out.mkdir(parents=True, exist_ok=True)
    models[3].booster.save_model(out / "m2_aft.json")
    models[4].model.save(out / "m2_hazard.keras")
    (out / "m2_metrics.json").write_text(json.dumps({
        "customers_median": median, "aft_sigma": models[3].sigma, "train_seconds": seconds,
        "rows": {"train": len(train), "validate": len(valid), "test": len(test), "ukpn": len(ukpn)},
        "scores": board.to_dict(orient="records")}, indent=1))
    return board


if __name__ == "__main__":
    print(run(Path(sys.argv[1]), Path(sys.argv[2])).to_string(index=False))
