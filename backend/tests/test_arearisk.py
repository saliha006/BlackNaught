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


def test_fit_from_csv(tmp_path):
    csv_path = tmp_path / "enwl.csv"
    csv_path.write_text("﻿incident_date_time;district_name\n"
                        "2020-01-05T10:00:00+00:00;Bolton\n2020-01-06T10:00:00+00:00;Bolton\n"
                        "2020-07-01T10:00:00+00:00;Wigan\n;Bolton\n2020-02-01T00:00:00+00:00; \n", encoding="utf-8")
    doc = arearisk.fit(csv_path)
    assert set(doc["rates"]) == {"Bolton", "Wigan"} and doc["years"] == [2020, 2020]
    assert doc["rates"]["Bolton"]["1"] == round(2 / 31, 4) and doc["rates"]["Wigan"]["1"] == 0


def test_winter_is_riskier_than_summer_in_real_history():
    winter = {r["district"]: r["p_ge_k"] for r in arearisk.area_risk(MODEL, date(2026, 1, 15))}
    summer = {r["district"]: r["p_ge_k"] for r in arearisk.area_risk(MODEL, date(2026, 7, 15))}
    assert len(winter) == 12 and sum(winter.values()) > sum(summer.values())


@pytest.mark.anyio
async def test_areas_risk_api_is_labelled_baseline():
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            tomorrow = (await c.get("/api/areas/risk")).json()
            jan = (await c.get("/api/areas/risk?date=2026-01-15")).json()
    assert tomorrow and all(r["label"] == "BASELINE" and 0 <= r["p_ge_k"] <= 1 for r in tomorrow)
    assert {r["district"] for r in jan} == set(MODEL["rates"])
