import numpy as np
import pandas as pd

from ml import home_sensor


def windows(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = pd.DataFrame({f: rng.normal(1.0, 0.05, n) for f in home_sensor.FEATURES})
    x["flicker60"] = rng.poisson(0.3, n)
    x["hour"] = rng.integers(0, 24, n)
    # a home whose power already blinked is likelier to go off, as in the Accra probe
    x["label"] = (rng.random(n) < 0.02 + 0.3 * (x["flicker60"] > 1)).astype(float)
    x["site_id"] = rng.integers(0, 40, n)
    return x


def test_fit_flags_the_riskiest_homes_and_scores_them():
    model = home_sensor.fit(windows(4000, 1), windows(1500, 2), "test")
    result = home_sensor.evaluate(model, windows(1500, 3))
    assert result["roc_auc"]["value"] > 0.6
    assert result["flag_precision"]["value"] > result["base_rate"]["value"]
    assert set(result["roc_auc"]) == {"value", "sd"}
    quiet = {f: 1.0 for f in home_sensor.FEATURES} | {"flicker60": 0, "hour": 3}
    blinking = quiet | {"flicker60": 4}
    assert model.score(quiet)["value"] == "normal"
    assert model.score(blinking)["p_off_30min"] > model.score(quiet)["p_off_30min"]


def test_probability_is_calibrated_and_monotone_in_the_raw_score():
    model = home_sensor.fit(windows(4000, 1), windows(1500, 2), "test")
    assert (np.diff(model.calib_y) >= 0).all()
    p = model.probability(windows(500, 4))
    assert ((p >= 0) & (p <= 1)).all()


def test_artifact_round_trip_is_exact(tmp_path):
    model = home_sensor.fit(windows(2000, 1), windows(800, 2), "test")
    path = tmp_path / "home.json"
    model.save(path)
    again = home_sensor.load(path)
    window = {f: 1.0 for f in home_sensor.FEATURES} | {"flicker60": 3}
    assert again.score(window) == model.score(window)
    assert again.threshold == model.threshold and len(again.sha256) == 64
