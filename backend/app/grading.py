"""Horizon grading: was the outage still off at t0 + h? Scored against the operators' real restorations.

"Still off" needs evidence: the fault was still listed, unrestored, by a poll after the horizon (an active
record's last_seen only advances on a successful poll that still contains it). Anything we can't know
honestly is censored, counted and bounded, never guessed: a vanished record, an approximate (SSEN) restore
time, NPg (no restore signal at all), or a feed that stayed dead across the horizon.
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .db import Db

log = logging.getLogger(__name__)

TICK_S = 60
GRACE = timedelta(minutes=4)            # two DNO polls after the horizon before grading
GIVE_UP = timedelta(hours=1)            # source still silent this long after the horizon → censor
UNGRADED_SOURCES = {"npg": "npg_no_restore_signal"}


@dataclass(frozen=True)
class Outcome:
    y: int | None
    reason: str


def judge(p: dict[str, Any], now: datetime) -> Outcome | None:
    """None means not decidable yet; try again next tick."""
    horizon_at = p["made_at"] + timedelta(hours=p["horizon_h"])
    if p["source"] in UNGRADED_SOURCES:
        return Outcome(None, UNGRADED_SOURCES[p["source"]])
    if p["restored_at"] is not None:
        if not p["restored_explicit"]:
            # SSEN keeps resolved faults listed and only gives an 'updated' time, so neither side is provable
            return Outcome(None, "approximate_restore_time")
        if p["restored_at"] <= horizon_at:
            return Outcome(0, "restored_before_horizon")
        return Outcome(1, "restored_after_horizon")
    if p["last_seen"] >= horizon_at:
        return Outcome(1, "still_off_at_horizon")
    if p["status"] == "vanished":
        return Outcome(None, "vanished_before_horizon")
    if now - horizon_at > GIVE_UP:
        return Outcome(None, "source_down_across_horizon")
    return None


class Grader:
    def __init__(self, db: Db):
        self.db = db

    async def tick(self, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        due = await self.db.rows(
            "SELECT p.pred_id, p.made_at, p.horizon_h, p.p_still_off, o.source, o.status, o.restored_at,"
            " o.restored_explicit, o.last_seen FROM prediction p JOIN outage o USING (outage_id)"
            " LEFT JOIN grade g USING (pred_id)"
            " WHERE g.pred_id IS NULL AND o.status <> 'planned'"
            " AND p.made_at + make_interval(hours => p.horizon_h) + CAST(:grace AS interval) <= :now",
            grace=f"{int(GRACE.total_seconds())} seconds", now=now,
        )
        if not due:
            return 0
        graded = []
        for p in due:
            outcome = judge(p, now)
            if outcome is None:
                continue
            brier = None if outcome.y is None else (p["p_still_off"] - outcome.y) ** 2
            graded.append((p["pred_id"], outcome, brier))
        if graded:
            await self.db.run(
                "INSERT INTO grade (pred_id, graded_at, outcome, censored, reason, brier)"
                " SELECT id, CAST(:at AS timestamptz), y, y IS NULL, r, b FROM unnest(:id::int8[], :y::int2[],"
                " :r::text[], :b::real[]) AS t(id, y, r, b) ON CONFLICT DO NOTHING",
                at=now, id=[g[0] for g in graded], y=[g[1].y for g in graded],
                r=[g[1].reason for g in graded], b=[g[2] for g in graded],
            )
        return len(graded)

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:
                # grading must survive a bad tick overnight; the error is logged and the next tick retries
                log.exception("grading tick failed")
            await asyncio.sleep(TICK_S)


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Brier per (horizon, model, source), plus the censoring bound: every censored row scored as 0, then as 1."""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["horizon_h"], r["model_id"], r["source"]), []).append(r)
    by_horizon = []
    for (h, model_id, source), rs in sorted(groups.items()):
        known = [r["brier"] for r in rs if not r["censored"]]
        censored = [r["p_still_off"] for r in rs if r["censored"]]
        bound = None
        if known or censored:
            low = (sum(known) + sum(p ** 2 for p in censored)) / (len(known) + len(censored))
            high = (sum(known) + sum((p - 1) ** 2 for p in censored)) / (len(known) + len(censored))
            bound = (round(min(low, high), 4), round(max(low, high), 4))
        by_horizon.append({
            "h": h, "model_id": model_id, "source": source,
            "brier": round(sum(known) / len(known), 4) if known else None,
            "n": len(known), "n_censored": len(censored), "bound": bound,
        })
    hourly: dict[str, list[float]] = {}
    for r in rows:
        if not r["censored"]:
            hourly.setdefault(r["graded_at"].strftime("%Y-%m-%dT%H:00:00+00:00"), []).append(r["brier"])
    trend = [{"at": at, "brier": round(sum(v) / len(v), 4), "n": float(len(v))} for at, v in sorted(hourly.items())]
    return {"by_horizon": by_horizon, "trend": trend}
