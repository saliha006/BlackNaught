import base64
import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app import audit, survival
from app.agent import Agent, Patient, plan, widen
from app.ingest import feeds, store
from app.seed import INSERT, keys, patient_row
from app.triage import Scorer

MODEL = survival.load(Path("/srv/models/km_enwl.json"))
NOW = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)


def patient(ref: str, harm: float, other_backup: bool = False, escalate: bool = False, reserve: float = 6.0,
            q90: float = 3.0, source: str = "ukpn") -> Patient:
    return Patient(ref, 1, source, "o2_concentrator", other_backup, harm, escalate, reserve, q90, [])


def refs(stops):
    return [p.ref for p, _ in stops]


# --- planning (no database) ----------------------------------------------------------------------

def test_five_responders_twelve_patients_the_least_harm_per_minute_waits():
    p = plan([patient(f"P-{i:02}", harm=float(i)) for i in range(1, 13)], workers=5, shift_min=120)
    assert sum(len(stops) for stops in p.visits.values()) == 10  # two 45 min visits fit in 120 min, a third doesn't
    assert [w.ref for w in p.waiting] == ["P-02", "P-01"]
    assert refs(p.visits["W1"]) == ["P-12", "P-07"] and [at for _, at in p.visits["W1"]] == [0, 45]


def test_a_short_check_in_still_fills_the_gap_left_by_long_visits():
    patients = [patient(f"N{i}", harm=10.0) for i in range(10)] + [patient("B1", harm=0.1, other_backup=True)]
    p = plan(patients, workers=5, shift_min=120)
    assert not p.waiting  # 2 × 45 + 20 = 110 min


def test_whoever_runs_out_first_is_visited_first_despite_less_harm_per_minute():
    patients = [patient(f"H{i}", harm=50.0) for i in range(10)] + [patient("E1", harm=1.0, escalate=True)]
    p = plan(patients, workers=5, shift_min=120)
    assert refs(p.visits["W1"])[0] == "E1"
    assert "E1" not in [w.ref for w in p.waiting]


def test_a_stale_feed_widens_to_q90_and_only_its_patients_cross():
    on_stale = patient("P-A", 5.0, reserve=4.0, q90=6.0, source="npg")
    on_fresh = patient("P-B", 5.0, reserve=4.0, q90=6.0, source="ukpn")
    covered = patient("P-C", 5.0, reserve=8.0, q90=6.0, source="npg")
    assert widen([on_stale, on_fresh, covered], {"npg"}) == [on_stale]
    assert on_stale.escalate and not on_fresh.escalate and not covered.escalate
    assert on_stale.why == ["npg feed stale → q90 6.0 h > reserve 4.0 h"]


# --- the loop against the database ---------------------------------------------------------------

class FakeSigner:
    def __init__(self):
        self.calls = 0
        self.down = False

    async def sign(self, payload: bytes, purpose: str) -> dict[str, str]:
        if self.down:
            raise httpx.ConnectError("signer unreachable")
        assert purpose == "agent_tool_call"
        self.calls += 1
        return {"alg": "ML-DSA-65", "key_id": "test", "sig_b64": base64.b64encode(hashlib.sha256(payload).digest()).decode()}


@pytest.fixture
async def agent_db(db_factory, superuser):
    superuser.run("TRUNCATE outage, outage_version, patient, prediction, grade, triage_snapshot, decision, agent_memory,"
                  " source_poll RESTART IDENTITY CASCADE")
    fault = feeds.Outage("ukpn", "INCD-A", "active", NOW - timedelta(hours=1), postcodes=["N1 3LD"], lat=51.54, lon=-0.09)
    await store.sync(db_factory("bn_ingest"), "ukpn", [fault], NOW)
    dek, bidx = keys()
    rng = random.Random(1)
    for device, reserve, backup in (("o2_concentrator", 0.5, False), ("ventilator", 12.0, False),
                                    ("ventilator", 12.0, False), ("suction", 3.0, True)):
        superuser.run(INSERT, **patient_row(rng, "N1 3LD", 51.54, -0.09, dek, bidx, device, reserve, backup))
    db = db_factory("bn_agent")
    assert await Scorer(db, MODEL, bidx).tick(NOW) == 4
    return db


async def started(db, signer, workers: int = 1, granite=None) -> Agent:
    agent = Agent(db, signer, workers, granite)
    await agent.load_memory()
    return agent


def decisions(superuser) -> dict[str, list]:
    out: dict[str, list] = {}
    for tool, state, args in superuser.run("SELECT tool, state, args FROM decision ORDER BY created_at"):
        out.setdefault(tool, []).append((state, args))
    return out


@pytest.mark.anyio
async def test_one_tick_plans_acts_and_leaves_reach_to_people_for_a_human(agent_db, superuser):
    signer = FakeSigner()
    agent = await started(agent_db, signer)
    assert await agent.tick(NOW) == 6
    made = decisions(superuser)
    assert set(made) == {"assign_visit", "escalate", "notify_carer", "draft_cap_alert", "write_sitrep", "field_briefing"}
    # one responder, 120 min: the empty concentrator first, then two more visits; one ventilator patient waits
    assert len(made["assign_visit"][0][1]["patients"]) == 3
    assert made["escalate"][0][0] == made["draft_cap_alert"][0][0] == "awaiting_approval"
    assert made["assign_visit"][0][0] == made["notify_carer"][0][0] == made["write_sitrep"][0][0] == "auto_done"
    assert made["escalate"][0][1]["service"] == "ambulance"
    cap_args = made["draft_cap_alert"][0][1]
    assert cap_args["outage_id"] == 1 and cap_args["area"] == "N1" and cap_args["writer"] == "template"
    assert cap_args["description"].startswith("There is a power cut in N1. It started at 21:00 UTC")
    assert "Waiting: 1. Awaiting an operator: 2." in made["write_sitrep"][0][1]["text"]
    assert made["field_briefing"][0][1]["text"].startswith("Responder W1. Stop 1: P-")
    assert signer.calls == 6


@pytest.mark.anyio
async def test_every_tool_call_carries_a_signature_over_what_was_decided(agent_db, superuser):
    await (await started(agent_db, FakeSigner())).tick(NOW)
    rows = superuser.run("SELECT decision_id::text, tool, args, rationale FROM decision")
    signatures = {json.loads(b)["ref"]: json.loads(b)["data"]
                  for (b,) in superuser.run("SELECT body FROM audit_log WHERE kind = 'tool_call_signature'")}
    assert {r[0] for r in rows} <= set(signatures)  # the audit chain is never truncated, so earlier tests' are there too
    for decision_id, tool, args, rationale in rows:
        body = audit.canonical({"tool": tool, "args": args, "rationale": rationale}).encode()
        assert signatures[decision_id]["sha256"] == hashlib.sha256(body).hexdigest()
        assert signatures[decision_id]["alg"] == "ML-DSA-65"


@pytest.mark.anyio
async def test_memory_survives_a_restart_so_nothing_is_repeated(agent_db, superuser):
    await (await started(agent_db, FakeSigner())).tick(NOW)
    before = superuser.run("SELECT count(*) FROM decision")[0][0]
    restarted = await started(agent_db, FakeSigner())  # a fresh process: nothing carried over in RAM
    assert await restarted.tick(NOW + timedelta(minutes=1)) == 0
    assert superuser.run("SELECT count(*) FROM decision")[0][0] == before
    assert restarted.memory["loop"]["ticks"] == 2


@pytest.mark.anyio
async def test_no_signature_means_no_action_and_the_retry_does_not_double_up(agent_db, superuser):
    signer = FakeSigner()
    signer.down = True
    agent = await started(agent_db, signer)
    with pytest.raises(httpx.ConnectError):
        await agent.tick(NOW)
    assert superuser.run("SELECT count(*) FROM decision")[0][0] == 0
    signer.down = False
    assert await agent.tick(NOW) == 6
    assert await agent.tick(NOW + timedelta(minutes=1)) == 0


class FakeGranite:
    def __init__(self):
        self.asked = 0

    async def write(self, style: str, facts: str) -> str:
        self.asked += 1
        return "In plain words: " + facts


def decided(superuser) -> list[tuple[str, dict]]:
    """Every decision without its wording, so runs with and without Granite can be compared."""
    wording = {"text", "description", "writer"}
    return sorted(((tool, {k: v for k, v in args.items() if k not in wording})
                   for tool, _, args in superuser.run("SELECT tool, state, args FROM decision")),
                  key=lambda d: (d[0], json.dumps(d[1], sort_keys=True)))


@pytest.mark.anyio
async def test_granite_only_changes_the_wording_never_the_decisions(agent_db, superuser):
    await (await started(agent_db, FakeSigner())).tick(NOW)
    without = decided(superuser)
    superuser.run("TRUNCATE decision, agent_memory CASCADE")
    granite = FakeGranite()
    await (await started(agent_db, FakeSigner(), granite=granite)).tick(NOW)
    assert decided(superuser) == without
    assert granite.asked == 3  # the CAP text, the sitrep and one briefing
    written = {tool: args for tool, _, args in superuser.run("SELECT tool, state, args FROM decision")
               if "writer" in args}
    assert {args["writer"] for args in written.values()} == {"granite"}
    assert written["write_sitrep"]["text"].startswith("In plain words: Patients in active outages: 4.")


@pytest.mark.anyio
async def test_texting_more_carers_than_the_limit_waits_for_an_operator(agent_db, superuser, monkeypatch):
    monkeypatch.setattr("app.agent.BULK_SMS_OVER", 0)
    agent = await started(agent_db, FakeSigner())
    await agent.tick(NOW)
    made = decisions(superuser)
    assert "notify_carer" not in made
    [(state, args)] = made["bulk_sms"]
    assert state == "awaiting_approval" and len(args["patients"]) == 1
    assert await agent.tick(NOW + timedelta(minutes=1)) == 0  # the carers it covers aren't texted again one by one


@pytest.mark.anyio
async def test_when_nobody_can_be_reached_whoever_runs_out_this_round_gets_a_supply(agent_db, superuser, monkeypatch):
    monkeypatch.setattr("app.agent.VISIT_MIN", {False: 200, True: 200})  # no visit fits a 120 min round
    monkeypatch.setattr("app.agent.SITREP_MAX_WAITING", 2)
    await (await started(agent_db, FakeSigner())).tick(NOW)
    made = decisions(superuser)
    assert "assign_visit" not in made and len(made["notify_carer"]) == 4
    [(state, args)] = made["request_supplier"]  # only the concentrator's reserve ends inside the round
    assert state == "auto_done" and args["item"] == "oxygen cylinder"
    rationale = superuser.run("SELECT rationale FROM decision WHERE tool = 'write_sitrep'")[0][0]
    assert len(rationale) == 3 and rationale[-1] == "and 2 more with less harm per minute"


@pytest.mark.anyio
async def test_a_stale_feed_is_marked_once_and_re_ranks_its_patients(agent_db, superuser):
    superuser.run("INSERT INTO source_poll (source, polled_at, ok) VALUES ('ukpn', :t, true), ('npg', :n, true)",
                  t=NOW - timedelta(minutes=30), n=NOW)
    agent = await started(agent_db, FakeSigner())
    await agent.tick(NOW)
    await agent.tick(NOW + timedelta(minutes=1))
    marked = decisions(superuser)["mark_source_stale"]
    assert [args["source"] for _, args in marked] == ["ukpn"]
    assert agent.memory["stale:ukpn"] is True and "stale:npg" not in agent.memory


@pytest.mark.anyio
async def test_an_old_triage_is_never_acted_on(agent_db, superuser):
    agent = await started(agent_db, FakeSigner())
    assert await agent.tick(NOW + timedelta(minutes=10)) == 0
    assert superuser.run("SELECT count(*) FROM decision")[0][0] == 0
