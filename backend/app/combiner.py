"""F3 evidence combiner and scale classifier (Ahmed, BLACKNAUGHT.md §7): "is it just my house?"

Plain data in, so it runs wherever the sensors' states and the feeds are known; nothing live calls it yet.
- scale(): the fuse-box decision flow. A cell where at least 60% of the sensors went quiet (gasp or dropout) within
  five minutes of each other is a street event. Two such cells under one L2 parent make an area. Three or more, plus
  an IODA dip or a shedding stage, make a region. Grid EMERGENCY while half the sensed cells are quiet makes it the
  whole system. A home that's down while its anchors report is "this home only", which never lowers a patient's
  priority, because no crew will come. A home that's down with fewer than two anchors reporting is "unresolved".
- p_outage(): naive Bayes in odds form. A DNO fault declared in the cell gives P ≈ 1.0. Otherwise the prior is
  multiplied by one likelihood ratio per source: the sensors, IODA and grid stress. A stale source counts as LR 1,
  and so does silence. Only a last gasp is positive evidence, and sensors still reporting power count against.

The brief's LR table from Nate doesn't exist, so the ratios below are hand-set orders of magnitude, each with its
reason. They are the first thing to replace with measured values.
"""
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from .cells import parent

QUORUM = 0.6
WINDOW = timedelta(minutes=5)
MIN_ANCHORS = 2
REGION_CELLS = 3
SYSTEM_SHARE = 0.5
QUIET = frozenset({"last_gasp", "dropout", "down"})
DNO_DECLARED_P = 0.999
# a fault in one ~1 km² cell in a given hour: ENWL's 30-year record puts a fault in a district most days, spread
# over its ~100 cells and 24 hours
PRIOR = 1e-3
# most of a cell's reporting sensors gasping at once has almost no cause but a real loss of supply; set so a quorum
# alone carries the 1e-3 prior past even odds (P ≈ 0.83)
LR_QUORUM = 5_000.0
# a gasp or two below quorum: one home's breaker, or one phase of a partial fault
LR_SOME_GASPS = 20.0
# every reporting sensor still has power; not 0, because a sensor wrongly fitted behind a backup keeps reporting
LR_ALL_UP = 0.05
# internet dips follow power cuts, but also routing faults
LR_IODA = 3.0
LR_STRESS = {"EMERGENCY": 2.0, "STRESSED": 1.2}


@dataclass(frozen=True)
class Reading:
    type: str  # home | anchor | control (the sensor table)
    state: str  # the tracker's: up | dropout | last_gasp
    since: datetime


def quiet_together(readings: Iterable[Reading]) -> int:
    """The most sensors that went quiet within WINDOW of each other: spread-out dropouts are comms noise, a block of
    them at once is what an outage looks like."""
    times = sorted(r.since for r in readings if r.state in QUIET)
    best = start = 0
    for end, t in enumerate(times):
        while t - times[start] > WINDOW:
            start += 1
        best = max(best, end - start + 1)
    return best


def cell_scale(readings: list[Reading]) -> str:
    """street | home | unresolved | none, for one cell."""
    if not readings:
        return "unresolved"
    if quiet_together(readings) / len(readings) >= QUORUM:
        return "street"
    if not any(r.type == "home" and r.state in QUIET for r in readings):
        return "none"
    anchors_up = sum(r.type == "anchor" and r.state == "up" for r in readings)
    return "home" if anchors_up >= MIN_ANCHORS else "unresolved"


def scale(cells: dict[str, list[Reading]], ioda_dip: bool = False, shedding: bool = False,
          stress: str | None = None) -> dict[str, str]:
    """Per cell: home, street, area, region, system, unresolved or none."""
    out = {cell: cell_scale(readings) for cell, readings in cells.items()}
    streets = [c for c, s in out.items() if s == "street"]
    if stress == "EMERGENCY" and len(streets) >= SYSTEM_SHARE * len(cells):
        return {c: "system" if s == "street" else s for c, s in out.items()}
    if len(streets) >= REGION_CELLS and (ioda_dip or shedding):
        return {c: "region" if s == "street" else s for c, s in out.items()}
    per_parent = Counter(parent(c) for c in streets)
    return {c: "area" if s == "street" and per_parent[parent(c)] > 1 else s for c, s in out.items()}


def sensor_lr(readings: Iterable[Reading]) -> float:
    gasped = up = 0
    for r in readings:
        gasped += r.state == "last_gasp"
        up += r.state == "up"
    if gasped + up == 0:
        return 1.0  # every sensor silent: silence alone never says outage
    if gasped / (gasped + up) >= QUORUM:
        return LR_QUORUM
    return LR_SOME_GASPS if gasped else LR_ALL_UP


def p_outage(readings: Iterable[Reading], dno_declared: bool = False, stale: frozenset[str] = frozenset(),
             ioda_dip: bool = False, stress: str | None = None, prior: float = PRIOR) -> float:
    """P(outage in the cell). `stale` names the sources whose evidence counts as LR 1: sensors, ioda, elexon."""
    if dno_declared:
        return DNO_DECLARED_P
    odds = prior / (1 - prior)
    if "sensors" not in stale:
        odds *= sensor_lr(readings)
    if ioda_dip and "ioda" not in stale:
        odds *= LR_IODA
    if "elexon" not in stale:
        odds *= LR_STRESS.get(stress, 1.0)
    return odds / (1 + odds)
