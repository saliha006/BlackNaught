"""Kaplan–Meier fallback duration model fitted on ENWL's historic unplanned outages.

Every ENWL record has a restoration, so there's no censoring and KM reduces to the empirical survival curve.
Triage uses it until Nate's M2 (XGBoost AFT + hazard MLP) is signed and served; the contract is the same.
Fit on the VM: python -m app.survival /data/raw/enwl_unplanned-outages.csv /srv/models/km_enwl.json
"""
import csv
import hashlib
import json
import sys
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

GRID_H = 168        # one week of hourly survival points; longer outages use the geometric tail
HORIZON_BINS = 24   # contract: conditional survival for the next 24 hourly bins
MIN_SURVIVAL = 1e-9


def fit(durations_h: list[float]) -> list[float]:
    """S(h) for h = 0..GRID_H: share of outages still off after h hours."""
    ordered = sorted(durations_h)
    n = len(ordered)
    return [(n - bisect_right(ordered, h)) / n for h in range(GRID_H + 1)]


def _at(curve: list[float], t: float) -> float:
    """Survival at any t ≥ 0, linear between hourly points, geometric beyond the grid."""
    if t >= GRID_H:
        last, prev = curve[GRID_H], curve[GRID_H - 1]
        ratio = last / prev if prev > 0 else 0.0
        return last * ratio ** (t - GRID_H)
    lo = int(t)
    return curve[lo] + (curve[lo + 1] - curve[lo]) * (t - lo)


@dataclass(frozen=True)
class KmModel:
    curve: list[float]
    model_id: str
    sha256: str
    label: str = "FALLBACK_KM"

    def conditional(self, elapsed_h: float, u: float) -> float:
        """P(T > elapsed + u | T > elapsed)."""
        base = max(_at(self.curve, elapsed_h), MIN_SURVIVAL)
        return min(1.0, _at(self.curve, elapsed_h + u) / base)

    def remaining_quantile(self, elapsed_h: float, q: float) -> float:
        """Remaining hours t such that P(still off after t more hours) = 1 − q."""
        target = 1 - q
        lo, hi = 0.0, 24.0 * 30
        for _ in range(50):
            mid = (lo + hi) / 2
            if self.conditional(elapsed_h, mid) > target:
                lo = mid
            else:
                hi = mid
        return round(hi, 2)

    def predict(self, elapsed_h: float) -> dict:
        return {
            "quantiles": {f"q{int(q * 100)}": self.remaining_quantile(elapsed_h, q) for q in (0.5, 0.75, 0.9)},
            "surv": [round(self.conditional(elapsed_h, h), 6) for h in range(1, HORIZON_BINS + 1)],
        }


def load(path: Path) -> KmModel:
    raw = path.read_bytes()
    doc = json.loads(raw)
    return KmModel(curve=doc["curve"], model_id=doc["model_id"], sha256=hashlib.sha256(raw).hexdigest())


def fit_from_enwl(csv_path: Path) -> dict:
    durations = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            minutes = row["incident_duration"]
            if minutes:
                durations.append(float(minutes) / 60)
    return {"model_id": "m1-km-enwl", "source": "ENWL Historic Unplanned Outages (CC BY 4.0)",
            "n": len(durations), "curve": [round(s, 8) for s in fit(durations)]}


if __name__ == "__main__":
    doc = fit_from_enwl(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(doc) + "\n")
    print(f"fitted on {doc['n']} outages; S(1h)={doc['curve'][1]:.3f} S(4h)={doc['curve'][4]:.3f}")
