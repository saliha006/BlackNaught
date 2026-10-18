from datetime import datetime, timezone

import numpy as np
import pytest

from ml import m2, m2_serve
from ml.tests.test_m2 import outages

FEATURES = {"started_at": datetime(2024, 11, 3, 18, 30, tzinfo=timezone.utc), "customers": 120,
            "feeder": {"type": "HV_N"}}


@pytest.fixture(scope="module")
def model() -> m2_serve.M2Model:
    train, valid = outages(1500, 1), outages(300, 2)
    aft = m2.Aft(train, valid, 100.0, np.random.default_rng(0))
    return m2_serve.M2Model(aft.booster[: aft.booster.best_iteration + 1], 100.0, 0.0, aft.sigma, "test")


def test_voltage_comes_from_the_feeder_type():
    assert [m2_serve.voltage_of(f) for f in ({"type": "LV"}, {"type": "HV_S"}, {"type": "HV"}, {}, None)] == \
        ["LV", "HV", "HV", None, None]


def test_predict_meets_the_contract(model):
    out = model.predict(FEATURES, 1.5)
    surv, q = out["surv"], out["quantiles"]
    assert len(surv) == 24 and all(0 <= s <= 1 for s in surv)
    assert all(a >= b for a, b in zip(surv, surv[1:]))
    assert 0 <= q["q50"] <= q["q75"] <= q["q90"]


def test_conditional_survival_matches_the_closed_form(model):
    out = model.predict(FEATURES, 0.0)
    mu = model.mu(m2_serve.pd.DataFrame({"start": [m2_serve.pd.Timestamp(FEATURES["started_at"])],
                                         "customers": [120], "voltage": ["HV"]}))[0]
    assert np.isclose(out["surv"][1], m2_serve.norm.sf((np.log(2) - mu) / model.sigma), atol=1e-6)
    assert np.isclose(out["quantiles"]["q50"], np.exp(mu), atol=0.01)


def test_missing_fields_still_predict(model):
    out = model.predict({"started_at": FEATURES["started_at"], "customers": None, "feeder": None}, 30.0)
    assert len(out["surv"]) == 24 and out["quantiles"]["q90"] <= m2_serve.MAX_REMAINING_H


def test_calibration_shift_moves_the_median(model):
    table = outages(300, 4)
    shifted = m2_serve.calibrate(model, table.assign(duration_h=table["duration_h"] * 2), "shifted")
    base = m2_serve.calibrate(model, table, "base")
    assert np.isclose(shifted.mu_shift - base.mu_shift, np.log(2), atol=1e-6)


def test_artifact_round_trip_is_exact(model, tmp_path):
    path = tmp_path / "m2.json"
    model.save(path)
    again = m2_serve.load(path)
    assert again.predict(FEATURES, 2.0) == model.predict(FEATURES, 2.0)
    assert len(again.sha256) == 64 and again.label == "REAL"
