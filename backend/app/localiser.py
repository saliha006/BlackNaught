"""Scores the F3 combiner's "outage here" calls against the real DNO footprints (Ahmed) → evidence/localiser.json.

Read-only, against the live database as bn_ingest. What it measures, honestly: the GB sensors are SIMULATED on those
same footprints, with comms dropouts, sensors fitted behind a backup and partial faults. So this is how well the
combiner recovers a footprint from noisy sensors, not real-world accuracy. The DNO feed is left out of the calls,
or every footprint cell would score P ≈ 1.0 by construction. The Accra REPLAY sensors are real but have no DNO
footprint, so their cell is reported on its own.

Run: python -m app.localiser > evidence/localiser.json
"""
import asyncio
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime

from . import combiner, simulator
from .cells import cell_id
from .db import Db

THRESHOLD = 0.5
LATEST = """
SELECT DISTINCT ON (t.sensor_id) t.sensor_id, t.state, t.at, t.label, s.type, s.cell_l1
FROM sensor_transition t JOIN sensor s USING (sensor_id)
ORDER BY t.sensor_id, t.at DESC
"""
FOOTPRINT = """
SELECT DISTINCT g.postcode, g.lat, g.lon FROM outage o CROSS JOIN unnest(o.postcodes) AS pc(postcode)
JOIN postcode_geo g ON g.postcode = pc.postcode
WHERE o.status = 'active' AND o.source IN ('ukpn', 'npg', 'ssen') AND g.valid
"""


def ratio(a: int, b: int) -> float | None:
    return round(a / b, 3) if b else None


async def evaluate(db: Db) -> dict:
    now = datetime.now(UTC)
    # only the fleet the simulator still drives: a fault that left the feed keeps its sensors' last rows forever
    tracked = {r["outage_id"] for r in await db.rows(simulator.FAULTS, cut=now - simulator.RESTORED_KEEP)}
    cells: dict[str, list[combiner.Reading]] = defaultdict(list)
    accra: list[combiner.Reading] = []
    for r in await db.rows(LATEST):
        reading = combiner.Reading(r["type"], r["state"], r["at"])
        if r["label"] == "REPLAY":
            accra.append(reading)
        elif r["label"] == "SIMULATED" and int(r["sensor_id"].split("-")[1]) in tracked:  # ids: <kind>-<outage>-...
            cells[r["cell_l1"]].append(reading)
    footprint = {r["postcode"]: cell_id(r["lat"], r["lon"]) for r in await db.rows(FOOTPRINT)}
    sensed, truth = set(cells), set(footprint.values()) & set(cells)
    called = {c for c, readings in cells.items() if combiner.p_outage(readings) >= THRESHOLD}
    tp, fp, fn = len(called & truth), len(called - truth), len(truth - called)
    postcodes = [c for c in footprint.values() if c in sensed]
    states = Counter(r.state for r in accra)
    return {
        "generated_at": now.isoformat(),
        "measures": "how well the combiner recovers real DNO footprints from SIMULATED sensors placed on them, with "
                    "comms dropouts, backup-fitted sensors and partial faults. Not real-world accuracy. The DNO "
                    "feed is left out of the calls.",
        "caveats": ["the negatives are mostly control cells and restored faults, whose simulated sensors never fail, so"
                    " precision is easy here",
                    "a miss is a cell where under 60% of the reporting sensors gasped, as in the simulator's partial"
                    " faults (one home in three), which the DNO feed covers in the live system"],
        "threshold": THRESHOLD,
        "hand_set_ratios": {"prior": combiner.PRIOR, "quorum": combiner.LR_QUORUM, "some_gasps": combiner.LR_SOME_GASPS,
                            "all_up": combiner.LR_ALL_UP, "ioda": combiner.LR_IODA, "stress": combiner.LR_STRESS},
        "gb_simulated": {
            "sensed_cells": len(sensed), "footprint_cells": len(truth), "called": len(called),
            "true_positive": tp, "false_positive": fp, "false_negative": fn,
            "true_negative": len(sensed - truth - called),
            "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
            "footprint_postcodes": len(postcodes), "postcode_recall": ratio(sum(c in called for c in postcodes),
                                                                             len(postcodes)),
            "scales": dict(Counter(combiner.scale(cells).values())),
        },
        "accra_replay": {
            "note": "real nLine GridWatch sensors, one cell (no coordinates in the data), no DNO footprint to score",
            "sensors": len(accra), "states": dict(states), "scale": combiner.cell_scale(accra),
            "p_outage": round(combiner.p_outage(accra), 4),
        },
    }


async def main() -> None:
    db = Db("bn_ingest")
    try:
        print(json.dumps(await evaluate(db), indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
