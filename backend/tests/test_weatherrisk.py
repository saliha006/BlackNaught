from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pandas as pd
import pytest

from app.main import app
from app.weatherrisk import DAILY, WeatherRisk

M8 = WeatherRisk(Path("/srv/models/m8_weather_enwl_v1.json"))
DAY = date(2026, 1, 15)


def forecast(gusts: float, rain: float) -> pd.DataFrame:
    rows = [{"district": d, "day": pd.Timestamp(DAY), "wind_gusts_10m_max": gusts, "precipitation_sum": rain,
             "temperature_2m_min": 1.0, "temperature_2m_max": 6.0, "snowfall_sum": 0.0} for d in M8.centres]
    return pd.DataFrame(rows)


def open_meteo(calls: list, status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url)
        if status != 200:
            return httpx.Response(status)
        days = [(DAY + timedelta(days=i)).isoformat() for i in range(3)]
        place = {"daily": {"time": days, **{v: [10.0, 60.0, 20.0] for v in DAILY}}}
        return httpx.Response(200, json=[place for _ in M8.centres])
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_scores_every_district_with_valid_probabilities():
    items = M8.predict(forecast(40.0, 5.0), DAY)
    assert [i["district"] for i in items] == sorted(M8.centres)
    assert all(0 <= i["p_ge_k"] <= 1 and i["expected"] > 0 for i in items)


def test_a_stormy_day_is_riskier_than_a_calm_one():
    calm = sum(i["expected"] for i in M8.predict(forecast(15.0, 0.0), DAY))
    storm = sum(i["expected"] for i in M8.predict(forecast(95.0, 30.0), DAY))
    assert storm > calm


@pytest.mark.anyio
async def test_fetches_once_an_hour_and_falls_back_when_the_forecast_fails():
    calls: list = []
    model = WeatherRisk(Path("/srv/models/m8_weather_enwl_v1.json"))
    async with open_meteo(calls) as client:
        now = datetime(2026, 1, 14, 12, tzinfo=UTC)
        first = await model.area_risk(client, DAY, now)
        assert first and len(first) == len(M8.centres) and len(calls) == 1
        assert await model.area_risk(client, DAY + timedelta(days=1), now + timedelta(minutes=30)) and len(calls) == 1
        # outside the three forecast days there's no weather to score, so the caller falls back
        assert await model.area_risk(client, DAY + timedelta(days=9), now + timedelta(minutes=31)) is None
    async with open_meteo(calls, status=503) as failing:
        assert await WeatherRisk(Path("/srv/models/m8_weather_enwl_v1.json")).area_risk(failing, DAY) is None


@pytest.mark.anyio
async def test_api_serves_m8_as_live_and_the_baseline_when_it_cannot():
    class Fixed:
        def __init__(self, items):
            self.items = items

        async def area_risk(self, client, day):
            return self.items

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            app.state.weather_risk = Fixed([{"district": "Cumbria", "expected": 4.2, "p_ge_k": 0.79}])
            live = (await c.get("/api/areas/risk")).json()
            app.state.weather_risk = Fixed(None)
            fallback = (await c.get("/api/areas/risk")).json()
    assert live == [{"district": "Cumbria", "expected": 4.2, "p_ge_k": 0.79, "label": "LIVE"}]
    assert fallback and all(r["label"] == "BASELINE" for r in fallback)
