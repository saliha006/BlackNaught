"""F6 agent loop v1 (Ahmed): perceive → assess → plan → act → observe, every 60 s.

It reads the latest triage and feed health, plans the responders' visits, and acts only through decisions.create(),
so every action lands in the hash-chained audit log. Each tool call is signed with the agent's own signer token
before it is made, and the signature is appended to the audit chain against the decision. Escalations and CAP
drafts wait for an operator (decisions.NEEDS_APPROVAL). Memory is the agent_memory table, so a restarted agent
carries on without repeating itself.

Runs as its own process, `python -m app.agent` (the `agent` service in infra/agent.yml), as role bn_agent.
"""
import asyncio
import hashlib
import json
import logging
import os
from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from . import audit, decisions
from .cap import area_desc
from .config import read_secret, settings
from .db import Db
from .granite import Granite
from .runtime import INTERVALS

log = logging.getLogger("agent")

TICK_S = 60
WORKERS = 5
SHIFT_MIN = 120                    # each responder's time in one planning round
VISIT_MIN = {False: 45, True: 20}  # by other_backup: without a second source the visit brings and sets up a supply
STALE_AFTER = 3                    # missed poll intervals before a feed counts as stale
TRIAGE_MAX_AGE = timedelta(minutes=5)
CAP_MIN_PATIENTS = 3               # at-risk patients on one outage before a public alert is drafted
BULK_SMS_OVER = 10                 # carers texted in one round above this go to an operator as one bulk_sms
SITREP_EVERY = timedelta(minutes=15)
RECALIBRATE_EVERY = timedelta(hours=1)
MIN_GRADES = 60    # graded predictions per horizon and model before a correction is fitted
FIT_SHARE = 2 / 3  # the older grades fit the correction and the newer ones judge it, so it's scored on unseen data
MIN_GAIN = 0.005   # Brier a correction must save on the newer grades to count as drift
SITREP_MAX_WAITING = 20            # rationale lines naming who waits; the rest are counted
SUPPLY = {"o2_concentrator": "oxygen cylinder", "o2_cylinder": "oxygen cylinder"}  # anything else: a backup battery
# a fresh Granite text takes ~80 s on the VM's CPU, so one a tick keeps the loop's next look at triage close;
# anything past that keeps its template (repeats come from Granite's cache)
GRANITE_PER_TICK = 1
SITREP_STYLE = ("Rewrite this situation report for a control-room operator in two or three short sentences of plain "
                "English. Keep every number exactly as given and add no new facts or numbers.")
BRIEFING_STYLE = ("Write a short field briefing for a community responder from this task list: one line per stop, in "
                  "order, saying who, when and why it matters. Keep every number exactly as given and add no new facts.")
CAP_STYLE = ("Write the description of a public emergency alert about this power cut in one or two calm sentences for "
             "the public. Use only these facts: add no numbers, times, causes or promises, and never mention patients.")

# the same pseudonym as v_triage_latest, so the control room and the decision log name a patient the same way
TRIAGE = """
SELECT t.tick_at, 'P-' || upper(substr(md5(t.patient_id::text), 1, 6)) AS ref, t.outage_id, o.source, p.device,
       p.other_backup, t.harm, t.escalate, t.why
FROM triage_snapshot t JOIN patient p USING (patient_id) JOIN outage o USING (outage_id)
WHERE t.tick_at = (SELECT max(tick_at) FROM triage_snapshot)
ORDER BY t.rank
"""
# GB only: the brief keeps the correction to grids whose feeds give explicit restorations; censored rows can't be scored
GRADES = """
SELECT p.horizon_h, p.model_id, p.p_still_off, g.outcome FROM grade g
JOIN prediction p USING (pred_id) JOIN outage o USING (outage_id)
WHERE NOT g.censored AND o.source IN ('ukpn', 'npg', 'ssen')
ORDER BY g.graded_at
"""


@dataclass
class Patient:
    ref: str
    outage_id: int
    source: str
    device: str
    other_backup: bool
    harm: float
    escalate: bool
    reserve_left_h: float
    q90_h: float
    why: list[str]

    @property
    def visit_min(self) -> int:
        return VISIT_MIN[self.other_backup]

    @property
    def key(self) -> str:
        return f"{self.ref}:{self.outage_id}"


def welfare_script(p: Patient) -> str:
    """What the volunteer says on the welfare call: only what the record holds, and never a restoration time."""
    return (f"Hello, this is the Blacknaught welfare line about {p.ref}. There's a power cut in your area and no "
            f"responder can reach you this round. Is the {p.device.replace('_', ' ')} running on its backup? The "
            f"record shows about {p.reserve_left_h:.1f} h of reserve left. If breathing gets worse, call 999 now.")


def from_row(r: dict[str, Any]) -> Patient:
    why = r["why"]
    return Patient(r["ref"], r["outage_id"], r["source"], r["device"], r["other_backup"], r["harm"], r["escalate"],
                   float(why["reserve_left_h"]), float(why["remaining_h"]["q90"]), why["reasons"])


def widen(patients: list[Patient], stale: set[str]) -> list[Patient]:
    """A stale feed can't confirm when power returns, so its patients are judged on q90 instead of the quantile
    triage chose. Returns the patients that newly cross their reserve; they escalate and move up the plan."""
    crossed = []
    for p in patients:
        if p.source in stale and not p.escalate and p.q90_h > p.reserve_left_h:
            p.escalate = True
            p.why.append(f"{p.source} feed stale → q90 {p.q90_h:.1f} h > reserve {p.reserve_left_h:.1f} h")
            crossed.append(p)
    return crossed


def brier(p: list[float], y: list[int]) -> float:
    return sum((a - b) ** 2 for a, b in zip(p, y)) / len(y)


def isotonic(p: list[float], y: list[int]) -> tuple[list[float], list[float]]:
    """Pool-adjacent-violators: the least-squares non-decreasing fit of outcome on probability, as a step function
    (each step's upper probability, its corrected value)."""
    seen: dict[float, list[float]] = {}
    for pi, yi in zip(p, y):
        total = seen.setdefault(pi, [0.0, 0])
        total[0] += yi
        total[1] += 1
    blocks: list[list[float]] = []  # [sum of outcomes, count, upper probability]
    for pi in sorted(seen):
        blocks.append([*seen[pi], pi])
        while len(blocks) > 1 and blocks[-2][0] * blocks[-1][1] > blocks[-1][0] * blocks[-2][1]:
            total, count, upper = blocks.pop()
            blocks[-1][0] += total
            blocks[-1][1] += count
            blocks[-1][2] = upper
    return [b[2] for b in blocks], [b[0] / b[1] for b in blocks]


def corrected(steps: tuple[list[float], list[float]], p: float) -> float:
    uppers, values = steps
    return values[min(bisect_left(uppers, p), len(values) - 1)]


@dataclass
class Plan:
    visits: dict[str, list[tuple[Patient, int]]]  # responder → [(patient, minutes until arrival)]
    waiting: list[Patient]


def plan(patients: list[Patient], workers: int = WORKERS, shift_min: int = SHIFT_MIN) -> Plan:
    """Greedy knapsack on harm-hours avoided per responder minute. Patients whose reserve runs out before power is
    likely back go first, then the most harm per minute. Each goes to the responder with the most time left, so a
    patient who doesn't fit there fits nowhere and waits; a shorter visit later in the order can still fill a gap."""
    load = {f"W{i}": 0 for i in range(1, workers + 1)}
    visits: dict[str, list[tuple[Patient, int]]] = {w: [] for w in load}
    waiting = []
    for p in sorted(patients, key=lambda p: (not p.escalate, -p.harm / p.visit_min, p.ref)):
        worker = min(load, key=lambda w: (load[w], w))
        if load[worker] + p.visit_min > shift_min:
            waiting.append(p)
            continue
        visits[worker].append((p, load[worker]))
        load[worker] += p.visit_min
    return Plan(visits, waiting)


class Agent:
    def __init__(self, db: Db, signer: audit.HttpSigner | None, workers: int = WORKERS, granite: Granite | None = None):
        self.db = db
        self.signer = signer
        self.workers = workers
        self.granite = granite
        self.granite_left = GRANITE_PER_TICK
        self.memory: dict[str, Any] = {}

    async def load_memory(self) -> None:
        self.memory = {r["key"]: r["value"] for r in await self.db.rows("SELECT key, value FROM agent_memory")}

    async def remember(self, keys: list[str], value: Any, now: datetime) -> None:
        await self.db.run(
            "INSERT INTO agent_memory (key, value, updated_at) SELECT k, CAST(:v AS jsonb), :at FROM unnest(:keys::text[]) AS k"
            " ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at",
            keys=keys, v=json.dumps(value), at=now)
        self.memory.update(dict.fromkeys(keys, value))

    async def call(self, tool: str, args: dict[str, Any], rationale: list[str], now: datetime,
                   memo: str | None = None) -> str:
        """One tool call. It is signed before it is made, so a signer failure means no action (retried next tick)."""
        body = audit.canonical({"tool": tool, "args": args, "rationale": rationale}).encode()
        signed = await self.signer.sign(body, "agent_tool_call") if self.signer is not None else None
        decision_id, state = await decisions.create(self.db, tool, args, rationale)
        if memo is not None:
            await self.remember([memo], decision_id, now)
        if signed is not None:
            await audit.append(self.db, "tool_call_signature", "agent", decision_id, {
                "alg": signed["alg"], "key_id": signed["key_id"], "sha256": hashlib.sha256(body).hexdigest(),
                "sig_b64": signed["sig_b64"]})
        log.info("%s → %s (%s)", tool, state, decision_id)
        return decision_id

    async def words(self, style: str, facts: str) -> tuple[str, str]:
        """(text, writer): Granite's wording when it's up and its numbers check out, otherwise the facts as written."""
        text = None
        if self.granite is not None and self.granite_left > 0:
            self.granite_left -= 1
            text = await self.granite.write(style, facts)
        return (text, "granite") if text else (facts, "template")

    async def call_once(self, memo: str, tool: str, args: dict[str, Any], rationale: list[str], now: datetime) -> int:
        if memo in self.memory:
            return 0
        await self.call(tool, args, rationale, now, memo)
        return 1

    async def stale_sources(self, now: datetime) -> dict[str, float]:
        """Feeds silent for more than STALE_AFTER poll intervals → seconds since their last good poll (or since their
        first poll, if none was ever good). A feed that has never polled isn't judged."""
        rows = await self.db.rows("SELECT source, coalesce(max(polled_at) FILTER (WHERE ok), min(polled_at)) AS since"
                                  " FROM source_poll WHERE source = ANY(:sources) GROUP BY source", sources=list(INTERVALS))
        silent = {r["source"]: (now - r["since"]).total_seconds() for r in rows}
        return {s: t for s, t in silent.items() if t > STALE_AFTER * INTERVALS[s]}

    async def mark_stale(self, now: datetime, stale: dict[str, float], crossed: list[Patient]) -> int:
        calls = 0
        for source, interval in INTERVALS.items():
            if (source in stale) == self.memory.get(f"stale:{source}", False):
                continue
            if source in stale:
                refs = [p.ref for p in crossed if p.source == source]
                await self.call("mark_source_stale", {"source": source}, [
                    f"no good poll for {stale[source]:.0f} s (> {STALE_AFTER} × {interval} s)",
                    "its outages are judged on q90 and the plan is re-ranked"
                    + (f"; {', '.join(refs)} now cross their reserve" if refs else ""),
                ], now)
                calls += 1
            await self.remember([f"stale:{source}"], source in stale, now)
        return calls

    async def assign(self, now: datetime, schedule: Plan) -> list[str]:
        """Returns the responders who got a new task list."""
        changed = []
        for worker, stops in schedule.visits.items():
            refs = [p.ref for p, _ in stops]
            if sorted(refs) == sorted(self.memory.get(f"visits:{worker}", [])):
                continue  # a re-order alone isn't a new task list
            if refs:
                await self.call("assign_visit", {"worker": worker, "patients": refs}, [
                    f"{p.ref} at +{at} min: harm {p.harm:.1f} over a {p.visit_min} min visit"
                    + ("; reserve runs out before power is likely back" if p.escalate else "") for p, at in stops
                ], now)
                changed.append(worker)
            await self.remember([f"visits:{worker}"], refs, now)
        return changed

    async def brief(self, now: datetime, schedule: Plan, workers: list[str]) -> int:
        for worker in workers:
            facts = f"Responder {worker}. " + " ".join(
                f"Stop {n}: {p.ref} at +{at} min, {p.device.replace('_', ' ')}, "
                f"{'has a backup' if p.other_backup else 'no backup'}, reserve {p.reserve_left_h:.1f} h"
                + ("; it runs out before power is likely back." if p.escalate else ".")
                for n, (p, at) in enumerate(schedule.visits[worker], 1))
            text, writer = await self.words(BRIEFING_STYLE, facts)
            await self.call("field_briefing", {"worker": worker, "text": text, "writer": writer},
                            [f"the task list of {worker} changed"], now)
        return len(workers)

    async def help_unreached(self, now: datetime, schedule: Plan) -> int:
        """Whoever waits gets their carer told (one bulk_sms for an operator past BULK_SMS_OVER carers); a supply is
        sent if the reserve ends this round; a no-backup patient who escalates and can't be reached before the
        reserve runs out goes to the ambulance service (approval)."""
        waits = [(p, f"waits: the {self.workers} responders' {SHIFT_MIN} min go to more harm per minute")
                 for p in schedule.waiting]
        late = [(p, f"{worker} arrives at +{at} min, when the {p.reserve_left_h:.1f} h reserve is gone")
                for worker, stops in schedule.visits.items() for p, at in stops if at / 60 >= p.reserve_left_h]
        untold = [(p, why) for p, why in waits if f"notify_carer:{p.key}" not in self.memory]
        calls = 0
        if len(untold) > BULK_SMS_OVER:
            decision_id = await self.call("bulk_sms", {"template": "power_cut_waiting",
                                                       "patients": [p.ref for p, _ in untold]},
                                          [f"{len(untold)} carers to text in one round (> {BULK_SMS_OVER})"], now)
            await self.remember([f"notify_carer:{p.key}" for p, _ in untold], decision_id, now)
            calls += 1
        else:
            for p, why in untold:
                calls += await self.call_once(f"notify_carer:{p.key}", "notify_carer",
                                              {"patient": p.ref, "outage_id": p.outage_id,
                                               "template": "power_cut_waiting", "script": welfare_script(p)},
                                              [why], now)
        for p, why in waits:
            if p.reserve_left_h * 60 < SHIFT_MIN:
                calls += await self.call_once(f"request_supplier:{p.key}", "request_supplier",
                                              {"patient": p.ref, "item": SUPPLY.get(p.device, "backup battery")},
                                              [why, f"reserve {p.reserve_left_h:.1f} h ends inside this round"], now)
        for p, why in waits + late:
            if p.escalate and not p.other_backup:
                calls += await self.call_once(f"escalate:{p.key}", "escalate",
                                              {"patient": p.ref, "outage_id": p.outage_id, "service": "ambulance"},
                                              p.why + [why], now)
        return calls

    async def draft_alerts(self, now: datetime, pairs: list[Patient]) -> int:
        per_outage = Counter(p.outage_id for p in pairs)
        due = [o for o, n in per_outage.items() if n >= CAP_MIN_PATIENTS and f"draft_cap_alert:{o}" not in self.memory]
        if not due:
            return 0
        rows = await self.db.rows("SELECT outage_id, postcodes, started_at, customers FROM outage"
                                  " WHERE outage_id = ANY(:ids)", ids=due)
        for r in rows:
            o, area = r["outage_id"], area_desc(r["postcodes"])
            # public text: only what the DNO itself publishes, never anything about the patients behind the draft
            facts = (f"There is a power cut in {area}. It started at {r['started_at']:%H:%M} UTC"
                     + (f" and affects {r['customers']} customers." if r["customers"] else "."))
            description, writer = await self.words(CAP_STYLE, facts)
            await self.call("draft_cap_alert", {"outage_id": o, "area": area, "description": description,
                                                "writer": writer},
                            [f"{per_outage[o]} electricity-dependent patients in this outage (≥ {CAP_MIN_PATIENTS})"],
                            now, f"draft_cap_alert:{o}")
        return len(rows)

    async def sitrep(self, now: datetime, patients: list[Patient], schedule: Plan, stale: dict[str, float],
                     replanned: bool) -> int:
        last = self.memory.get("sitrep_at")
        if not replanned and last and now - datetime.fromisoformat(last) < SITREP_EVERY:
            return 0
        awaiting = (await self.db.run("SELECT count(*) FROM decision WHERE state = 'awaiting_approval'"))[0][0]
        waiting = schedule.waiting
        text = (f"Patients in active outages: {len(patients)}. Visits planned: "
                f"{sum(len(stops) for stops in schedule.visits.values())} (responders: {self.workers})."
                f" Waiting: {len(waiting)}. Decisions awaiting an operator: {awaiting}."
                + (f" Stale feeds: {', '.join(sorted(stale))}." if stale else ""))
        rationale = [f"{p.ref} waits: harm {p.harm:.1f} over {p.visit_min} min" for p in waiting[:SITREP_MAX_WAITING]]
        if len(waiting) > SITREP_MAX_WAITING:
            rationale.append(f"and {len(waiting) - SITREP_MAX_WAITING} more with less harm per minute")
        text, writer = await self.words(SITREP_STYLE, text)
        await self.call("write_sitrep", {"text": text, "writer": writer}, rationale, now)
        await self.remember(["sitrep_at"], now.isoformat(), now)
        return 1

    async def self_correct(self, now: datetime) -> int:
        """recalibrate(horizon): a monotone correction per horizon and model, fitted on the older GB grades and kept
        only if it lowers the Brier on the newer ones, which is what drift looks like for a probability. Each check is
        a decision either way, so declining to correct is on the record too."""
        last = self.memory.get("recalibrate_at")
        if last and now - datetime.fromisoformat(last) < RECALIBRATE_EVERY:
            return 0
        groups: dict[tuple[int, str], tuple[list[float], list[int]]] = {}
        for r in await self.db.rows(GRADES):
            p, y = groups.setdefault((r["horizon_h"], r["model_id"]), ([], []))
            p.append(float(r["p_still_off"]))
            y.append(r["outcome"])
        calls = 0
        for (h, model_id), (p, y) in sorted(groups.items()):
            if len(y) < MIN_GRADES:
                continue
            cut = int(len(y) * FIT_SHARE)
            steps = isotonic(p[:cut], y[:cut])
            before, after = brier(p[cut:], y[cut:]), brier([corrected(steps, q) for q in p[cut:]], y[cut:])
            applied = before - after >= MIN_GAIN
            fitted = {"p": [round(v, 3) for v in steps[0]], "corrected": [round(v, 3) for v in steps[1]]}
            await self.call("recalibrate", {"horizon_h": h, "model_id": model_id, "applied": applied,
                                            "brier_before": round(before, 4), "brier_after": round(after, 4),
                                            "n_fit": cut, "n_test": len(y) - cut, "steps": fitted if applied else None}, [
                f"GB grades at +{h} h: a correction fitted on the older {cut} takes the Brier on the newer "
                f"{len(y) - cut} from {before:.4f} to {after:.4f}",
                "kept in agent memory; the triage scorer doesn't apply it yet" if applied
                else f"not a gain of {MIN_GAIN}, so the model is left as it is",
            ], now)
            if applied:
                await self.remember([f"calibration:{model_id}:{h}"], fitted, now)
            calls += 1
        await self.remember(["recalibrate_at"], now.isoformat(), now)
        return calls

    async def tick(self, now: datetime) -> int:
        """One pass of the loop; returns the number of tool calls made."""
        rows = await self.db.rows(TRIAGE)
        stale = await self.stale_sources(now)
        self.granite_left = GRANITE_PER_TICK
        if rows and now - rows[0]["tick_at"] > TRIAGE_MAX_AGE:
            log.warning("triage is from %s; not planning on it", rows[0]["tick_at"])
            rows = []
        pairs = [from_row(r) for r in rows]
        by_ref: dict[str, Patient] = {}
        for p in pairs:  # ranked by harm, so a patient in two outages keeps the worse one
            by_ref.setdefault(p.ref, p)
        patients = list(by_ref.values())
        calls = await self.mark_stale(now, stale, widen(patients, set(stale)))
        if rows:
            # every decision first; Granite's wording (briefings last) can be slow and must never hold one up
            schedule = plan(patients, self.workers)
            changed = await self.assign(now, schedule)
            calls += len(changed) + await self.help_unreached(now, schedule) + await self.draft_alerts(now, pairs)
            calls += await self.sitrep(now, patients, schedule, stale, replanned=bool(changed))
            calls += await self.brief(now, schedule, changed)
        calls += await self.self_correct(now)
        ticks = self.memory.get("loop", {}).get("ticks", 0) + 1
        await self.remember(["loop"], {"ticks": ticks, "last_tick": now.isoformat()}, now)
        return calls

    async def run(self) -> None:
        await self.load_memory()
        log.info("memory: %d keys; resuming after tick %d", len(self.memory), self.memory.get("loop", {}).get("ticks", 0))
        while True:
            try:
                await self.tick(datetime.now(UTC))
            except Exception:
                # one bad tick must not stop the agent; an action that failed was never remembered, so it is retried
                log.exception("agent tick failed")
            await asyncio.sleep(TICK_S)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    url, granite_url = settings().signer_url, os.environ.get("BN_GRANITE_URL")
    async with httpx.AsyncClient(timeout=10) as client:
        signer = audit.HttpSigner(client, url, read_secret("signer_token_agent")) if url else None
        await Agent(Db("bn_agent"), signer, granite=Granite(client, granite_url) if granite_url else None).run()


if __name__ == "__main__":
    asyncio.run(main())
