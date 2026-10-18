"""Triage scorer: every tick, one batch over all at-risk patients × active outages.

Scoring runs on a timer (and on new faults), not per HTTP request, so the ranking is consistent for every viewer
and model calls are batched. Patients are matched to outages through the postcode blind index, so the register
never needs decrypting to rank. Outage-level predictions are logged for horizon grading (one per outage per 15 min).
"""
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from .crypto import blind_index
from .db import Db
from .harm import assess
from .survival import KmModel

log = logging.getLogger(__name__)

TICK_S = 30
GRADE_EVERY = timedelta(minutes=15)
RETENTION = timedelta(hours=2)
HORIZONS_H = (2, 4)


class Scorer:
    def __init__(self, db: Db, model: KmModel, bidx_key: bytes):
        self.db = db
        self.model = model
        self.bidx_key = bidx_key
        self.wake = asyncio.Event()
        self.on_ranked: Callable[[dict], None] | None = None
        self.last_logged: dict[int, datetime] = {}
        # model calls block (TF graph mode once M2 lands), so they get their own thread off the event loop
        self._model_thread = ThreadPoolExecutor(max_workers=1, thread_name_prefix="scorer-model")

    async def _at_risk(self) -> tuple[list[dict], list[dict]]:
        outages = await self.db.rows(
            "SELECT outage_id, started_at, postcodes, customers, feeder FROM outage"
            " WHERE status = 'active' AND cardinality(postcodes) > 0"
        )
        index: dict[bytes, list[dict]] = {}
        for o in outages:
            for postcode in o["postcodes"]:
                index.setdefault(blind_index(self.bidx_key, postcode), []).append(o)
        if not index:
            return outages, []
        patients = await self.db.rows(
            "SELECT patient_id, postcode_bidx, reserve_h, other_backup, severity FROM patient"
            " WHERE postcode_bidx = ANY(:bidx)",
            bidx=list(index),
        )
        pairs = []
        for p in patients:
            for o in index[bytes(p["postcode_bidx"])]:
                pairs.append({"patient": p, "outage": o})
        return outages, pairs

    def _predict(self, elapsed: dict[int, float], features: dict[int, dict]) -> dict[int, dict]:
        return {outage_id: self.model.predict(features[outage_id], h) for outage_id, h in elapsed.items()}

    async def tick(self, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        outages, pairs = await self._at_risk()
        elapsed = {o["outage_id"]: max(0.0, (now - o["started_at"]).total_seconds() / 3600) for o in outages}
        loop = asyncio.get_running_loop()
        features = {o["outage_id"]: {"started_at": o["started_at"], "customers": o["customers"], "feeder": o["feeder"]}
                    for o in outages}
        predictions = await loop.run_in_executor(self._model_thread, self._predict, elapsed, features)

        scored = []
        for pair in pairs:
            p, o = pair["patient"], pair["outage"]
            pred = predictions[o["outage_id"]]
            reserve_left = max(0.0, float(p["reserve_h"]) - elapsed[o["outage_id"]])
            a = assess(pred["quantiles"], pred["surv"], reserve_left, p["severity"], p["other_backup"])
            scored.append((p, o, a, reserve_left, pred["quantiles"]))
        # deterministic order: harm, then whoever runs out first, then id
        scored.sort(key=lambda s: (-s[2].harm, s[3], str(s[0]["patient_id"])))

        if scored:
            await self.db.run(
                "INSERT INTO triage_snapshot (tick_at, patient_id, outage_id, rank, harm, q_used, q_hours, escalate,"
                " why, model_id) SELECT CAST(:at AS timestamptz), * FROM unnest(:pid::uuid[], :oid::int8[], :rank::int[], :harm::real[],"
                " :q::text[], :qh::real[], :esc::bool[], :why::jsonb[], :model::text[])",
                at=now,
                pid=[str(s[0]["patient_id"]) for s in scored],
                oid=[s[1]["outage_id"] for s in scored],
                rank=list(range(1, len(scored) + 1)),
                harm=[s[2].harm for s in scored],
                q=[s[2].q_used for s in scored],
                qh=[s[2].q_hours for s in scored],
                esc=[s[2].escalate for s in scored],
                why=[json.dumps({"reasons": s[2].why, "remaining_h": s[4], "reserve_left_h": round(s[3], 2)})
                     for s in scored],
                model=[self.model.model_id] * len(scored),
            )
        if self.on_ranked is not None:
            self.on_ranked({"tick_at": now, "ranked": len(scored), "escalate": sum(s[2].escalate for s in scored),
                            "model": self.model.model_id})
        await self._log_predictions(now, elapsed, predictions)
        await self.db.run("DELETE FROM triage_snapshot WHERE tick_at < :cut", cut=now - RETENTION)
        return len(scored)

    async def _log_predictions(self, now: datetime, elapsed: dict[int, float], predictions: dict[int, dict]) -> None:
        due = [i for i in elapsed if now - self.last_logged.get(i, datetime.min.replace(tzinfo=UTC)) >= GRADE_EVERY]
        if not due:
            return
        rows = [(i, h, predictions[i]["surv"][h - 1], json.dumps(predictions[i]["quantiles"]))
                for i in due for h in HORIZONS_H]
        await self.db.run(
            "INSERT INTO prediction (outage_id, made_at, elapsed_h, model_id, model_sha256, horizon_h, p_still_off,"
            " quantiles) SELECT o, CAST(:at AS timestamptz), e, :mid, :sha, h, p, q FROM unnest(:o::int8[], :e::real[], :h::int2[],"
            " :p::real[], :q::jsonb[]) AS t(o, e, h, p, q) ON CONFLICT DO NOTHING",
            at=now, mid=self.model.model_id, sha=self.model.sha256,
            o=[r[0] for r in rows], e=[elapsed[r[0]] for r in rows], h=[r[1] for r in rows],
            p=[r[2] for r in rows], q=[r[3] for r in rows],
        )
        for i in due:
            self.last_logged[i] = now

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:
                # one bad tick must not stop triage; the last snapshot stays served and the error is visible
                log.exception("triage tick failed")
            self.wake.clear()
            try:
                await asyncio.wait_for(self.wake.wait(), TICK_S)
            except TimeoutError:
                pass
