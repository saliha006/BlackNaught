import json

import pandas as pd

from ml import km_refit


def test_refit_curve_loads_in_the_backend(tmp_path, monkeypatch):
    ukpn = pd.DataFrame({"duration_h": [0.5, 1.5, 2.5, 3.5]})
    monkeypatch.setattr(km_refit.m2, "load", lambda prepared: (None, ukpn))
    doc = km_refit.build(tmp_path)
    assert doc["n"] == 4 and doc["curve"][0] == 1.0 and doc["curve"][2] == 0.5
    path = tmp_path / "km.json"
    path.write_text(json.dumps(doc))
    model = km_refit.survival.load(path)
    assert model.model_id == "m1-km-ukpn" and model.label == "FALLBACK_KM"
    assert len(model.predict({}, 1.0)["surv"]) == 24
