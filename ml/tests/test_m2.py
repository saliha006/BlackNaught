import numpy as np
import pandas as pd

from ml import m2


def outages(n: int = 400, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    customers = rng.integers(1, 2000, n)
    return pd.DataFrame({
        "start": pd.date_range("2021-01-01", periods=n, freq="7h", tz="UTC"),
        # bigger outages last longer, so a model that reads customers should beat the plain curve
        "duration_h": np.exp(0.2 + 0.25 * np.log(customers) + rng.normal(0, 0.4, n)),
        "customers": customers,
        "voltage": rng.choice(["LV", "HV", "EHV"], n),
        "cause": rng.choice(["Companies", "Weather and Environment"], n),
    })


def test_features_map_voltage_and_fill_customers():
    table = pd.DataFrame({"start": pd.to_datetime(["2024-07-01 12:00", "2024-07-06 12:00", "2024-12-01 00:00"], utc=True),
                          "customers": [10, None, 0], "voltage": ["EHV", None, "LV"]})
    x = m2.features(table, customers_median=4)
    assert x[["volt_lv", "volt_hv", "volt_unknown"]].to_numpy().tolist() == [[0, 1, 0], [0, 0, 1], [1, 0, 0]]
    assert np.isclose(x["log_customers"].iloc[1], np.log1p(4))
    assert x["weekend"].tolist() == [0, 1, 1]
    hidden = m2.features(table, 4, hide_share=1.0, rng=np.random.default_rng(0))
    assert hidden["volt_unknown"].eq(1).all()


def test_km_is_the_empirical_curve_and_per_cause_falls_back():
    km = m2.Km(np.array([1.0, 2.0, 3.0, 4.0]))
    assert km.curve(np.array([0.5, 2, 4])).tolist() == [1.0, 0.5, 0.0]
    train = pd.DataFrame({"duration_h": [1.0, 1.0, 9.0, 9.0], "cause": ["a", "a", "b", "b"]})
    by_cause = m2.KmByCause(train)
    rows = by_cause.surv(pd.DataFrame({"cause": ["a", "b", None]}), np.array([5]))
    assert rows[:, 0].tolist() == [0.0, 1.0, 0.5]


def test_c_index_scores_order_only():
    t = np.array([1.0, 2.0, 3.0, 4.0])
    assert m2.c_index(t, t) == 1.0
    assert m2.c_index(-t, t) == 0.0
    assert m2.c_index(np.zeros(4), t) == 0.5


def test_hazard_classes_cap_at_the_last_bin():
    assert m2.HazardMlp.classes(pd.DataFrame({"duration_h": [0.5, 3.2, 30.0]})).tolist() == [0, 3, 24]


def test_models_give_valid_survival_and_beat_the_plain_curve():
    train, valid, test = outages(1500, 1), outages(300, 2), outages(300, 3)
    median = float(train["customers"].median())
    rng = np.random.default_rng(0)
    models = [m2.Km(train["duration_h"]), m2.LogNormal(train, median), m2.Aft(train, valid, median, rng),
              m2.HazardMlp(train, valid, median, rng, epochs=3)]
    for model in models:
        s = model.surv(test, m2.GRID_H)
        assert s.shape == (len(test), len(m2.GRID_H))
        assert ((s >= -1e-6) & (s <= 1 + 1e-6)).all()
        assert (np.diff(s, axis=1) <= 1e-6).all(), f"{model.name} survival must not increase"
    scores = {m.name: m2.evaluate(m, test) for m in models}
    assert scores["M1 Kaplan-Meier"]["c_index"] == 0.5
    assert scores["M1 log-linear"]["c_index"] > 0.6
    assert scores["M2 XGBoost AFT"]["c_index"] > 0.6
    assert scores["M2 XGBoost AFT"]["brier_2h"] < scores["M1 Kaplan-Meier"]["brier_2h"]
