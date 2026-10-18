import numpy as np
import pandas as pd

from app import probe_precursor as probe


def site_series(power: list[bool], voltage: float = 235.0, district: str = "Accra") -> pd.DataFrame:
    times = pd.date_range("2021-06-01T00:00Z", periods=len(power), freq="2min")
    return pd.DataFrame({"bin": times, "site_id": 1, "voltage": voltage, "frequency": 50.0,
                         "powered": power, "district": district})


def test_label_looks_only_forward_within_the_horizon():
    steps_ahead = probe.HORIZON_MIN // 2
    onset = 100
    power = [True] * onset + [False] * 20 + [True] * 80
    f = probe.features(site_series(power)).set_index("bin")
    labels = f["label"]
    times = pd.date_range("2021-06-01T00:00Z", periods=len(power), freq="2min")
    # inside the 30 min before the cut: positive; further back: negative
    assert labels[times[onset - 1]] == 1 and labels[times[onset - steps_ahead]] == 1
    assert labels[times[onset - steps_ahead - 1]] == 0
    # nothing is scored while the home is already dark
    assert not any(t in labels.index for t in times[onset:onset + 20])


def test_features_never_see_the_future():
    power = [True] * 200
    base = probe.features(site_series(power)).set_index("bin")
    changed = site_series(power)
    changed.loc[150:, "voltage"] = 120.0  # a big future change
    after = probe.features(changed).set_index("bin")
    early = base.index[base.index < changed["bin"][150]]
    cols = ["v_last", "v_min30", "v_mean60", "v_std60", "sag_share60", "v_slope30"]
    assert np.allclose(base.loc[early, cols].fillna(-1), after.loc[early, cols].fillna(-1))


def test_district_share_counts_dark_neighbours():
    a = site_series([True] * 60)
    b = site_series([True] * 30 + [False] * 30).assign(site_id=2)
    f = probe.features(pd.concat([a, b]))
    late = f[(f["site_id"] == 1) & (f["bin"] >= a["bin"][40])]
    assert (late["district_dark_share"] == 1.0).all()  # site 2 is dark; site 1 is the one being scored


def test_precision_at_top_share():
    y = np.array([1, 0, 0, 0, 1, 0, 0, 0, 0, 0])
    score = np.array([0.9, 0.8, 0.1, 0.1, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1])
    assert probe.precision_at(y, score, 0.2) == 0.5
