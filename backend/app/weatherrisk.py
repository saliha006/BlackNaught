"""Tomorrow's fault risk from the weather forecast: Nate's M8, served live behind the baseline's contract.

M8 multiplies each district's climatology by a weather effect XGBoost (Poisson) learned from ENWL faults and Open-Meteo
history (ml/m8.py; +5.1% Brier skill over climatology on 2024-26, evidence/train_log_m8.txt). Here it only scores:
the trained booster, the climatology it was fitted on and the district centres all come from one JSON artifact.
The redrawn Cumbrian districts are one "Cumbria" in M8, because their merged history is continuous.

The forecast is fetched once per hour for all centres in one Open-Meteo call. If that fails, area_risk returns None
and the API serves the climatology baseline instead, so a weather outage never takes the endpoint down.
"""
import hashlib
import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import xgboost as xgb

from .arearisk import p_at_least

log = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
# The daily variables M8 was trained on, in its feature order (ml/m8.py DAILY)
DAILY = ["wind_gusts_10m_max", "precipitation_sum", "temperature_2m_min", "temperature_2m_max", "snowfall_sum"]
REFRESH = timedelta(hours=1)
TIMEOUT_S = 8.0


class WeatherRisk:
    def __init__(self, path: Path):
        raw = path.read_bytes()
        doc = json.loads(raw)
        self.booster = xgb.Booster()
        self.booster.load_model(bytearray(json.dumps(doc["booster"]).encode()))
        self.climatology: dict[str, dict[str, float]] = doc["climatology"]
        self.centres: dict[str, list[float]] = doc["centres"]
        self.k: int = doc["k"]
        self.model_id: str = doc["model_id"]
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self._forecast: pd.DataFrame | None = None
        self._fetched_at = datetime.min.replace(tzinfo=UTC)

    def predict(self, forecast: pd.DataFrame, day: date) -> list[dict]:
        """Same items as arearisk.area_risk, from a forecast frame with district, day and the DAILY columns."""
        rows = forecast[forecast["day"] == pd.Timestamp(day)].sort_values("district")
        month = rows["day"].dt.month
        x = rows[DAILY].astype(float).copy()
        # Seasonality as a circle, so December and January sit next to each other, exactly as in training
        x["month_sin"], x["month_cos"] = np.sin(2 * np.pi * month / 12), np.cos(2 * np.pi * month / 12)
        x["weekend"] = (rows["day"].dt.weekday >= 5).astype(float)
        base = np.maximum([self.climatology[d][str(m)] for d, m in zip(rows["district"], month)], 1e-6)
        mu = self.booster.predict(xgb.DMatrix(x, base_margin=np.log(base)))
        return [{"district": d, "expected": round(float(m), 2), "p_ge_k": round(p_at_least(self.k, float(m)), 4)}
                for d, m in zip(rows["district"], mu)]

    async def _fetch(self, client: httpx.AsyncClient) -> pd.DataFrame:
        names = list(self.centres)
        resp = await client.get(FORECAST_URL, timeout=TIMEOUT_S, params={
            "latitude": ",".join(str(self.centres[d][0]) for d in names),
            "longitude": ",".join(str(self.centres[d][1]) for d in names),
            "daily": ",".join(DAILY), "timezone": "Europe/London", "forecast_days": 3,
        })
        resp.raise_for_status()
        body = resp.json()
        # One location comes back as an object, several as a list in request order
        places = body if isinstance(body, list) else [body]
        frames = [pd.DataFrame(p["daily"]).rename(columns={"time": "day"}).assign(district=d)
                  for d, p in zip(names, places)]
        frame = pd.concat(frames, ignore_index=True)
        frame["day"] = pd.to_datetime(frame["day"])
        return frame

    async def area_risk(self, client: httpx.AsyncClient, day: date, now: datetime | None = None) -> list[dict] | None:
        now = now or datetime.now(UTC)
        if self._forecast is None or now - self._fetched_at >= REFRESH:
            try:
                self._forecast, self._fetched_at = await self._fetch(client), now
            except (httpx.HTTPError, KeyError, ValueError) as e:
                log.warning("weather forecast unavailable, serving the climatology baseline: %s", e)
                return None
        items = self.predict(self._forecast, day)
        # The forecast only covers three days; a date outside it falls back rather than inventing weather
        return items or None
