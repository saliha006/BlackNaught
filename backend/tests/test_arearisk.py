import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from app import arearisk
from app.main import app

MODEL = json.loads(Path("/srv/models/climatology_enwl.json").read_text())


def test_poisson_tail():
    assert arearisk.p_at_least(0, 2.0) == pytest.approx(1.0)
    assert arearisk.p_at_least(1, 2.0) == pytest.approx(1 - 2.718281828 ** -2, rel=1e-6)
    assert arearisk.p_at_least(3, 0.0) == pytest.approx(0.0)


def test_fit_follows_the_2024_district_split(tmp_path):
    rows = ["﻿incident_date_time;district_name"]

    def faults(district, y, m, n):
        rows.extend(f"{y}-{m:02d}-01T10:00:00+00:00;{district}" for _ in range(n))

    for y, m in [(2025, mm) for mm in range(1, 13)] + [(2026, mm) for mm in range(1, 7)]:
        faults("Kendal", y, m, 30)
    for y, m in [(2025, mm) for mm in range(7, 13)] + [(2026, mm) for mm in range(1, 7)]:
        faults("Penrith", y, m, 31)
    for m in range(1, 4):
        faults("Carlisle", 2025, m, 40)  # retired before the last 12 months
    faults("Barrow", 2025, 9, 3)  # stray rows
    rows.append("2026-06-15T10:00:00+00:00;Kendal")  # the export stops mid-June
    rows.append(";Kendal")
    csv_path = tmp_path / "enwl.csv"
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    doc = arearisk.fit(csv_path)
    assert set(doc["rates"]) == {"Kendal", "Penrith"} and doc["years"] == [2025, 2026]
    assert doc["rates"]["Kendal"]["1"] == round(60 / 62, 4)
    # Penrith only existed from July 2025, so its January rate is one January, not diluted across Kendal's two
    assert doc["rates"]["Penrith"]["1"] == 1.0
    # the partial last month (June 2026) is left out rather than read as a quiet one
    assert doc["rates"]["Kendal"]["6"] == 1.0


def test_winter_is_riskier_than_summer_in_real_history():
    winter = {r["district"]: r["p_ge_k"] for r in arearisk.area_risk(MODEL, date(2026, 1, 15))}
    summer = {r["district"]: r["p_ge_k"] for r in arearisk.area_risk(MODEL, date(2026, 7, 15))}
    assert sum(winter.values()) > sum(summer.values())
    # today's districts: the 2024 split's Penrith and Workington in, the retired Carlisle out
    assert {"Penrith", "Workington"} <= set(winter) and "Carlisle" not in winter
    assert winter["Penrith"] > 0.3 * max(winter.values())


@pytest.mark.anyio
async def test_areas_risk_api_is_labelled_baseline():
    async with app.router.lifespan_context(app):
        app.state.weather_risk = None  # no live forecast in tests; the weather path has its own tests
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            tomorrow = (await c.get("/api/areas/risk")).json()
            jan = (await c.get("/api/areas/risk?date=2026-01-15")).json()
    assert tomorrow and all(r["label"] == "BASELINE" and 0 <= r["p_ge_k"] <= 1 for r in tomorrow)
    assert {r["district"] for r in jan} == set(MODEL["rates"])
