"""Tomorrow's fault risk per ENWL district — climatology baseline until Nate's weather model (M8) lands.

For each district and calendar month: the mean number of unplanned faults per day over ENWL's history. P(≥k
faults) comes from a Poisson with that mean. It's the baseline M8 has to beat (Brier skill vs climatology), and
it's labelled BASELINE so no one mistakes it for a weather forecast. M8 replaces `area_risk` behind this contract.
Fit on the VM: python -m app.arearisk /data/raw/enwl_unplanned-outages.csv /srv/models/climatology_enwl.json
"""
import calendar
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

K = 3  # "≥3 faults in a district tomorrow": 39% of district-days in ENWL 1997–2026 (measured on the VM)


def fit(csv_path: Path) -> dict:
    per_month: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    years: set[int] = set()
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            started = row["incident_date_time"][:10]
            district = row["district_name"].strip()
            if not started or not district:
                continue
            y, m = int(started[:4]), int(started[5:7])
            years.add(y)
            per_month[district][m] += 1
    span = range(min(years), max(years) + 1)
    days_in = {m: sum(calendar.monthrange(y, m)[1] for y in span) for m in range(1, 13)}
    rates = {d: {str(m): round(per_month[d][m] / days_in[m], 4) for m in range(1, 13)} for d in per_month}
    return {"model_id": "climatology-enwl", "k": K, "years": [span.start, span.stop - 1], "rates": rates}


def p_at_least(k: int, mean: float) -> float:
    return 1 - sum(math.exp(-mean) * mean ** i / math.factorial(i) for i in range(k))


def area_risk(model: dict, day: date) -> list[dict]:
    month = str(day.month)
    return [{"district": district, "expected": rates[month], "p_ge_k": round(p_at_least(model["k"], rates[month]), 4)}
            for district, rates in sorted(model["rates"].items())]


if __name__ == "__main__":
    doc = fit(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(doc) + "\n")
    print(f"{len(doc['rates'])} districts, years {doc['years']}")
