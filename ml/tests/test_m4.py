import numpy as np
import pandas as pd

from ml import m4


def series(values, start="2026-01-01 00:00:00") -> pd.Series:
    return pd.Series(np.asarray(values, dtype=float), index=pd.date_range(start, periods=len(values), freq="1s", tz="UTC"))


def test_a_fast_fall_warns_before_lfdd_and_before_the_statutory_band():
    calm = 50 + np.random.default_rng(1).normal(0, 0.01, 300)
    fall = np.linspace(50.0, 48.7, 90)   # 9 Aug 2019 shape: ~1.5 min from 50 Hz to LFDD
    lead = m4.lead_times(series(np.concatenate([calm, fall])))
    assert lead["band_stressed"]["lead_s"] > lead["band_emergency"]["lead_s"] > 0
    assert 0 < lead["m4_warning"]["lead_s"] <= lead["band_stressed"]["lead_s"]


def test_no_lfdd_means_no_lead_time():
    assert m4.lead_times(series(np.full(100, 50.0))) == {"lfdd_at": None}


def test_a_slow_dip_below_the_band_is_stressed_but_not_a_warning():
    dip = np.concatenate([np.full(60, 50.0), np.linspace(50.0, 49.75, 120), np.full(60, 49.75)])
    sig = m4.signals(series(dip))
    assert sig["band_stressed"].any() and not sig["m4_warning"].any()


def test_no_slope_is_taken_across_missing_seconds():
    f = series(np.concatenate([np.full(20, 50.0), np.full(20, 49.7)]))
    f.iloc[18:23] = np.nan   # a 5-s outage in the feed hides the step, so no rate of change can be claimed there
    assert not m4.signals(f)["m4_warning"].any()


def test_alerts_within_a_minute_are_one_episode():
    alert = pd.Series(False, index=series(np.zeros(400)).index)
    alert.iloc[[10, 11, 50, 200, 300]] = True
    assert m4.episodes(alert) == 3
    assert m4.episodes(alert & False) == 0


def test_false_alarms_count_episodes_per_month(tmp_path):
    path = tmp_path / "f.csv"
    pd.DataFrame({"dtm": ["2025-10-01 00:00:00", "2025-10-01 00:00:01", "2025-10-01 00:00:03"],
                  "f": [50.0, 49.7, 49.9]}).to_csv(path, index=False)
    f = m4.load(path)
    assert len(f) == 4 and np.isnan(f.iloc[2])
    out = m4.false_alarms([f, f])
    assert out["months"] == 2 and out["band_stressed"]["episodes"] == 2 and out["band_stressed"]["per_month"] == 1
    assert out["min_hz"] == 49.7 and out["seconds_at_or_below_lfdd"] == 0
