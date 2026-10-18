"""Refit the live Kaplan-Meier stand-in on UKPN's own outages (decision C, 2026-10-18).

The trained M2 models can't rank UKPN outages, but UKPN restores faster than ENWL, so its own empirical curve scored
better on UKPN's newest year (IBS 0.1297 vs 0.1311). The file is built with the backend's survival.fit, so
survival.load reads it unchanged. Run on the VM: python -m ml.km_refit <prepared-dir> <out.json>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import survival  # noqa: E402  (the backend's own fit keeps the artifact format identical)

from ml import m2  # noqa: E402


def build(prepared: Path) -> dict:
    _, ukpn = m2.load(prepared)
    return {"model_id": "m1-km-ukpn",
            "source": "UK Power Networks IIS, Apr 2021-Mar 2025, restoration stages rolled up to incidents, 5-min cut",
            "n": len(ukpn), "curve": [round(s, 8) for s in survival.fit(ukpn["duration_h"].tolist())]}


if __name__ == "__main__":
    doc = build(Path(sys.argv[1]))
    out = Path(sys.argv[2])
    out.write_text(json.dumps(doc) + "\n")
    model = survival.load(out)
    p = model.predict(1.0)
    print(f"{doc['model_id']}: {doc['n']:,} outages; S(1h)={doc['curve'][1]:.3f} S(4h)={doc['curve'][4]:.3f}; "
          f"1 h in -> q50 {p['quantiles']['q50']} h, P(still off +2 h) {p['surv'][1]:.3f}")
