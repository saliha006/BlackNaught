from datetime import date

import numpy as np
import pandas as pd

from ml import m8


def district_days(start: str, end: str, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    days = pd.date_range(start, end, freq="D")
    frame = pd.DataFrame([(d, day) for d in ("Bolton", "Carlisle") for day in days], columns=["district", "day"])
    n = len(frame)
    frame["wind_gusts_10m_max"] = rng.gamma(4, 10, n)
    frame["precipitation_sum"] = rng.gamma(1, 2, n)
    frame["temperature_2m_min"] = rng.normal(5, 4, n)
    frame["temperature_2m_max"] = frame["temperature_2m_min"] + 6
    frame["snowfall_sum"] = 0.0
    base = np.where(frame["district"] == "Bolton", 2.0, 1.0)
    # gusts above ~40 km/h push faults up, as storms do
    frame["faults"] = rng.poisson(base * np.exp(0.04 * (frame["wind_gusts_10m_max"] - 40)))
    return frame


def test_weather_model_beats_climatology_and_serves_area_risk(tmp_path):
    model = m8.fit(district_days("2016-01-01", "2021-12-31", 1), district_days("2022-01-01", "2022-12-31", 2),
                   {"Bolton": [53.58, -2.43], "Carlisle": [54.89, -2.93]}, "test")
    score = m8.brier_skill(model, district_days("2023-01-01", "2023-12-31", 3))
    assert score["brier_skill"] > 0.05
    forecast = district_days("2024-01-01", "2024-01-02", 4)
    stormy = forecast.assign(wind_gusts_10m_max=np.where(forecast["district"] == "Bolton", 110.0, 20.0))
    items = model.area_risk(date(2024, 1, 2), stormy)
    assert [i["district"] for i in items] == ["Bolton", "Carlisle"]
    assert items[0]["p_ge_k"] > items[1]["p_ge_k"] and 0 <= items[1]["p_ge_k"] <= 1
    path = tmp_path / "m8.json"
    model.save(path)
    assert m8.load(path).area_risk(date(2024, 1, 2), stormy) == items


def test_climatology_is_the_district_month_mean():
    train = pd.DataFrame({"district": ["A", "A", "A"], "day": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-02-01"]),
                          "faults": [2, 4, 1]})
    assert m8.climatology(train) == {"A": {"1": 3.0, "2": 1.0}}


def test_fault_counts_include_zero_days_and_district_centres(tmp_path):
    path = tmp_path / "enwl.csv"
    path.write_text("incident_date_time;district_name;geometry\n"
                    "2000-01-01T10:00:00+00:00;Bolton ;53.5, -2.4\n"
                    "2000-01-01T23:30:00+00:00;Bolton;53.7, -2.6\n"
                    "2000-01-03T09:00:00+00:00;Bolton;53.6, -2.5\n", encoding="utf-8")
    counts, centres = m8.load_faults(path)
    assert counts["faults"].tolist() == [2, 0, 1]
    assert centres == {"Bolton": [53.6, -2.5]}
