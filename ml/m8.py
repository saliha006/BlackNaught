"""M8, tomorrow's fault risk per ENWL district from the weather (brief task 11, prediction layer 1).

Each district's fault rate for the day is its climatology (district x month, fitted on the training years only)
multiplied by a weather effect that XGBoost Poisson learns from Open-Meteo history (ERA5) at the district's centre.
P(>= K faults) comes from a Poisson with that mean, the same output as backend/app/arearisk.py, so M8 is scored
against that baseline by Brier skill on 2024-26 outages neither model trained on.

Run on the VM: python -m ml.m8 <enwl-raw.csv> <weather-cache-dir> <out-artifact.json>
"""
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import poisson

K = 3                     # "3 or more faults in a district tomorrow", as in the live baseline
DAILY = ["wind_gusts_10m_max", "precipitation_sum", "temperature_2m_min", "temperature_2m_max", "snowfall_sum"]
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"
FIRST_DAY, TRAIN_LAST_YEAR, VALIDATE_YEAR = "2000-01-01", 2022, 2023
PARAMS = {"objective": "count:poisson", "max_depth": 4, "learning_rate": 0.05, "subsample": 0.8,
          "colsample_bytree": 0.8, "nthread": 3, "seed": 7}


def load_faults(path: Path) -> tuple[pd.DataFrame, dict[str, list[float]]]:
    """District-day fault counts, zero days included, plus each district's centre from its outages' coordinates."""
    raw = pd.read_csv(path, sep=";", usecols=["incident_date_time", "district_name", "geometry"], low_memory=False)
    raw["district"] = raw["district_name"].str.strip()
    raw["day"] = pd.to_datetime(raw["incident_date_time"], utc=True, format="ISO8601").dt.tz_convert("Europe/London") \
        .dt.normalize().dt.tz_localize(None)
    coords = raw["geometry"].str.split(",", expand=True).astype(float)
    centres = {d: [round(float(c[0].median()), 4), round(float(c[1].median()), 4)]
               for d, c in coords.groupby(raw["district"])}
    raw = raw[raw["day"] >= FIRST_DAY]
    days = pd.date_range(FIRST_DAY, raw["day"].max(), freq="D")
    grid = pd.MultiIndex.from_product([sorted(centres), days], names=["district", "day"])
    counts = raw.groupby(["district", "day"]).size().reindex(grid, fill_value=0).rename("faults").reset_index()
    return counts, centres


def fetch(url: str, lat: float, lon: float, **extra) -> pd.DataFrame:
    query = {"latitude": lat, "longitude": lon, "daily": ",".join(DAILY), "timezone": "Europe/London", **extra}
    with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(query)}", timeout=120) as response:
        daily = json.load(response)["daily"]
    return pd.DataFrame(daily).rename(columns={"time": "day"}).assign(day=lambda f: pd.to_datetime(f["day"]))


def weather_history(centres: dict, start: str, end: str, cache: Path) -> pd.DataFrame:
    cache.mkdir(parents=True, exist_ok=True)
    frames = []
    for district, (lat, lon) in centres.items():
        path = cache / f"{district.replace(' ', '_')}_{start}_{end}.csv"
        if not path.exists():
            fetch(ARCHIVE, lat, lon, start_date=start, end_date=end).to_csv(path, index=False)
            time.sleep(1)   # Open-Meteo's free tier asks for gentle use
        frames.append(pd.read_csv(path, parse_dates=["day"]).assign(district=district))
    return pd.concat(frames, ignore_index=True)


def design(frame: pd.DataFrame) -> pd.DataFrame:
    month = frame["day"].dt.month
    x = frame[DAILY].astype(float).copy()
    x["month_sin"], x["month_cos"] = np.sin(2 * np.pi * month / 12), np.cos(2 * np.pi * month / 12)
    x["weekend"] = (frame["day"].dt.weekday >= 5).astype(float)
    return x


class M8Model:
    def __init__(self, booster: xgb.Booster, climatology: dict[str, dict[str, float]], centres: dict, model_id: str,
                 sha256: str = ""):
        self.booster, self.climatology, self.centres = booster, climatology, centres
        self.model_id, self.sha256 = model_id, sha256

    def base(self, frame: pd.DataFrame) -> np.ndarray:
        rates = [self.climatology[d][str(m)] for d, m in zip(frame["district"], frame["day"].dt.month)]
        return np.maximum(np.asarray(rates, dtype=float), 1e-6)

    def expected(self, frame: pd.DataFrame) -> np.ndarray:
        matrix = xgb.DMatrix(design(frame), base_margin=np.log(self.base(frame)))
        return self.booster.predict(matrix)

    def area_risk(self, day: date, forecast: pd.DataFrame | None = None) -> list[dict]:
        """Same items as arearisk.area_risk; `forecast` (district, day, DAILY...) is fetched live when not given."""
        if forecast is None:
            forecast = pd.concat([fetch(FORECAST, lat, lon, forecast_days=3).assign(district=d)
                                  for d, (lat, lon) in self.centres.items()])
        rows = forecast[forecast["day"] == pd.Timestamp(day)].sort_values("district")
        mu = self.expected(rows)
        return [{"district": d, "expected": round(float(m), 2), "p_ge_k": round(float(poisson.sf(K - 1, m)), 4)}
                for d, m in zip(rows["district"], mu)]

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({"model_id": self.model_id, "k": K, "centres": self.centres,
                                    "climatology": self.climatology,
                                    "booster": json.loads(self.booster.save_raw("json"))}))


def load(path: Path) -> M8Model:
    raw = path.read_bytes()
    doc = json.loads(raw)
    booster = xgb.Booster()
    booster.load_model(bytearray(json.dumps(doc["booster"]).encode()))
    return M8Model(booster, doc["climatology"], doc["centres"], doc["model_id"], hashlib.sha256(raw).hexdigest())


def climatology(train: pd.DataFrame) -> dict[str, dict[str, float]]:
    rates = train.groupby(["district", train["day"].dt.month])["faults"].mean()
    return {d: {str(m): round(float(r), 4) for m, r in g.droplevel(0).items()} for d, g in rates.groupby(level=0)}


def fit(train: pd.DataFrame, valid: pd.DataFrame, centres: dict, model_id: str) -> M8Model:
    clim = climatology(train)
    model = M8Model(None, clim, centres, model_id)
    dtrain = xgb.DMatrix(design(train), label=train["faults"], base_margin=np.log(model.base(train)))
    dvalid = xgb.DMatrix(design(valid), label=valid["faults"], base_margin=np.log(model.base(valid)))
    booster = xgb.train(PARAMS, dtrain, num_boost_round=800, evals=[(dvalid, "validate")],
                        early_stopping_rounds=40, verbose_eval=200)
    model.booster = booster[: booster.best_iteration + 1]
    return model


def brier_skill(model: M8Model, frame: pd.DataFrame) -> dict:
    y = (frame["faults"] >= K).to_numpy()
    p_model = poisson.sf(K - 1, model.expected(frame))
    p_clim = poisson.sf(K - 1, model.base(frame))
    b_model, b_clim = float(np.mean((p_model - y) ** 2)), float(np.mean((p_clim - y) ** 2))
    return {"n": len(frame), "event_rate": round(float(y.mean()), 4), "brier_m8": round(b_model, 4),
            "brier_climatology": round(b_clim, 4), "brier_skill": round(1 - b_model / b_clim, 4)}


def build(raw_csv: Path, cache: Path, out: Path) -> dict:
    counts, centres = load_faults(raw_csv)
    weather = weather_history(centres, FIRST_DAY, counts["day"].max().strftime("%Y-%m-%d"), cache)
    frame = counts.merge(weather, on=["district", "day"], how="inner")
    year = frame["day"].dt.year
    train, valid, test = frame[year <= TRAIN_LAST_YEAR], frame[year == VALIDATE_YEAR], frame[year > VALIDATE_YEAR]
    model = fit(train, valid, centres, "m8-weather-enwl-v1")
    model.save(out)
    worst = test.assign(expected=model.expected(test), clim=model.base(test)) \
        .sort_values("faults", ascending=False).head(5)
    return {"districts": len(centres), "rows": {"train": len(train), "validate": len(valid), "test": len(test)},
            "validate": brier_skill(model, valid), "test": brier_skill(model, test),
            "worst_test_days": [{"district": r.district, "day": r.day.strftime("%Y-%m-%d"), "faults": int(r.faults),
                                 "gust_kmh": r.wind_gusts_10m_max, "m8_expected": round(float(r.expected), 1),
                                 "climatology_expected": round(float(r.clim), 1)} for r in worst.itertuples()]}


if __name__ == "__main__":
    print(json.dumps(build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), indent=1, default=str))
