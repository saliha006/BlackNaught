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
# ENWL redrew its districts in mid-2024 (Carlisle split into Penrith and Workington), and a few stray rows carry other
# names. A month with fewer faults than this is stragglers, not a district covering ground, so it isn't averaged in:
# averaging a 2024 district over 30 years made Penrith and Workington look ~10× safer than they are.
ACTIVE_MONTH_MIN = 10
# A district needs this many faults in the last 12 months to still be on today's map (drops Carlisle, Barrow, Lancaster).
CURRENT_MIN = 100


def fit(csv_path: Path) -> dict:
    counts: dict[str, dict[tuple[int, int], int]] = defaultdict(lambda: defaultdict(int))
    last = ""
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            started = row["incident_date_time"][:10]
            district = row["district_name"].strip()
            if not started or not district:
                continue
            counts[district][(int(started[:4]), int(started[5:7]))] += 1
            last = max(last, started)
    end = int(last[:4]) * 12 + int(last[5:7]) - 1

    def month_of(t: int) -> tuple[int, int]:
        return t // 12, t % 12 + 1

    recent = {month_of(end - i) for i in range(12)}
    partial = month_of(end)  # the export stops mid-month, so its last month would read as a quiet one

    rates = {}
    for district, cells in counts.items():
        if sum(n for ym, n in cells.items() if ym in recent) < CURRENT_MIN:
            continue
        active = [ym for ym, n in cells.items() if n >= ACTIVE_MONTH_MIN and ym != partial]
        per_month = {}
        for m in range(1, 13):
            months = [ym for ym in active if ym[1] == m]
            days = sum(calendar.monthrange(y, m)[1] for y, _ in months)
            per_month[str(m)] = round(sum(cells[ym] for ym in months) / days, 4) if days else 0.0
        rates[district] = per_month
    first = min(y for cells in counts.values() for y, _ in cells)
    return {"model_id": "climatology-enwl", "k": K, "years": [first, int(last[:4])], "rates": rates}


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
