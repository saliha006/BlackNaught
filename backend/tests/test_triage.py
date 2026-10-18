import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app import harm, survival
from app.crypto import blind_index
from app.ingest import feeds, store
from app.main import app
from app.seed import keys, patient_row
from app.triage import GRADE_EVERY, Scorer

MODEL = survival.load(Path("/srv/models/km_enwl.json"))
NOW = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)


# --- survival ------------------------------------------------------------------------------------

def test_fit_is_empirical_survival():
    curve = survival.fit([0.5, 1.5, 2.5, 3.5])
    assert curve[:5] == [1.0, 0.75, 0.5, 0.25, 0.0]


def test_conditional_survival_properties():
    for elapsed in (0, 1, 4, 12, 200):
        surv = MODEL.predict(elapsed)["surv"]
        assert all(0 <= s <= 1 for s in surv)
        assert all(a >= b for a, b in zip(surv, surv[1:]))  # never increases with horizon
    assert MODEL.conditional(0, 0) == 1.0


def test_older_outages_last_longer():
    q = [MODEL.predict(e)["quantiles"] for e in (0, 4, 12)]
    assert q[0]["q50"] < q[1]["q50"] < q[2]["q50"]
    assert all(x["q50"] <= x["q75"] <= x["q90"] for x in q)


def test_quantile_inverts_conditional():
    for elapsed in (0, 3):
        for qn, key in ((0.5, "q50"), (0.9, "q90")):
            t = MODEL.predict(elapsed)["quantiles"][key]
            assert abs(MODEL.conditional(elapsed, t) - (1 - qn)) < 0.01


def test_geometric_tail_beyond_grid():
    assert 0 < MODEL.conditional(0, 400) < MODEL.conditional(0, 168)


def test_load_hashes_the_artifact():
    raw = Path("/srv/models/km_enwl.json").read_bytes()
    assert MODEL.sha256 == hashlib.sha256(raw).hexdigest() and MODEL.model_id == "m1-km-enwl"


# --- harm ------------------------------------------------------------------------------------------

def test_expected_excess_simple_cases():
    always_off = [1.0] * 24
    assert harm.expected_excess(always_off, 0) == harm.TAIL_CAP_H  # never restores → capped
    restored = [0.0] * 24
    assert harm.expected_excess(restored, 0) == pytest.approx(0.5)  # linear from 1 → 0 in the first hour
    assert harm.expected_excess(restored, 3) == 0.0
    halving = [0.5 ** h for h in range(1, 25)]
    assert harm.expected_excess(halving, 0) > harm.expected_excess(halving, 2) > harm.expected_excess(halving, 30) > 0


def test_two_houses_one_hour_into_a_real_fault():
    pred = MODEL.predict(1.0)
    house_a = harm.assess(pred["quantiles"], pred["surv"], reserve_left_h=3.0, severity=5, other_backup=False)
    house_b = harm.assess(pred["quantiles"], pred["surv"], reserve_left_h=14.0, severity=5, other_backup=False)
    assert house_a.escalate and house_a.q_used == "q75"
    assert not house_b.escalate and house_b.q_used == "q50"
    assert house_a.harm > house_b.harm


def test_nearly_empty_with_no_backup_uses_q90():
    pred = MODEL.predict(1.0)
    a = harm.assess(pred["quantiles"], pred["surv"], reserve_left_h=0.5, severity=5, other_backup=False)
    assert a.q_used == "q90" and a.escalate


def test_sms_never_stands_down_a_no_backup_patient():
    pred = MODEL.predict(1.0)
    a = harm.assess(pred["quantiles"], pred["surv"], 0.5, 5, other_backup=False, sms_power_back=True)
    assert a.escalate and "ignored" in a.why[-1]
    b = harm.assess(pred["quantiles"], pred["surv"], 0.5, 5, other_backup=True, sms_power_back=True)
    assert not b.escalate and "stood down" in b.why[-1]


def test_other_backup_reduces_harm():
    pred = MODEL.predict(1.0)
    alone = harm.assess(pred["quantiles"], pred["surv"], 1.0, 4, other_backup=False).harm
    backed = harm.assess(pred["quantiles"], pred["surv"], 1.0, 4, other_backup=True).harm
    assert backed == pytest.approx(alone * harm.OTHER_BACKUP_FACTOR, rel=1e-3)


# --- scorer against the test DB ----------------------------------------------------------------------

@pytest.fixture
async def world(db_factory, superuser):
    superuser.run("TRUNCATE outage, outage_version, patient, prediction, grade, triage_snapshot RESTART IDENTITY CASCADE")
    started = NOW - timedelta(hours=1)
    faults = [feeds.Outage("ukpn", "INCD-A", "active", started, postcodes=["N1 3LD", "N1 3LE"], lat=51.54, lon=-0.09),
              feeds.Outage("ukpn", "INCD-B", "active", started, postcodes=["E1 6AN"], lat=51.52, lon=-0.07),
              feeds.Outage("ukpn", "INCD-P", "planned", started, postcodes=["N1 3LD"], lat=51.54, lon=-0.09)]
    await store.sync(db_factory("bn_ingest"), "ukpn", faults, NOW)
    dek, bidx = keys()
    rng = random.Random(1)
    rows = [patient_row(rng, "N1 3LD", 51.54, -0.09, dek, bidx, "o2_concentrator", 4.0, False),
            patient_row(rng, "N1 3LD", 51.54, -0.09, dek, bidx, "ventilator", 15.0, False),
            patient_row(rng, "SW1A 1AA", 51.50, -0.14, dek, bidx, "ventilator", 2.0, False)]  # not in any fault
    for row in rows:
        superuser.run("INSERT INTO patient (patient_id, household_id, cell_l1, postcode_bidx, contact_ct, device,"
                      " reserve_h, other_backup, severity) VALUES (CAST(:id AS uuid), CAST(:household AS uuid), :cell,"
                      " :bidx, :contact, :device, :reserve, :backup, :severity)", **row)
    return Scorer(db_factory("bn_agent"), MODEL, bidx)


@pytest.mark.anyio
async def test_scorer_ranks_only_patients_inside_active_faults(world, superuser):
    assert await world.tick(NOW) == 2
    ranked = superuser.run("SELECT p.device, t.rank, t.escalate, t.why FROM triage_snapshot t JOIN patient p"
                           " USING (patient_id) ORDER BY t.rank")
    assert [(d, r, e) for d, r, e, _ in ranked] == [("o2_concentrator", 1, True), ("ventilator", 2, False)]
    why = ranked[0][3] if isinstance(ranked[0][3], dict) else json.loads(ranked[0][3])
    assert why["reserve_left_h"] == pytest.approx(3.0) and set(why["remaining_h"]) == {"q50", "q75", "q90"}


@pytest.mark.anyio
async def test_predictions_logged_for_grading_every_15_min(world, superuser):
    await world.tick(NOW)
    assert superuser.run("SELECT count(*) FROM prediction")[0][0] == 4  # 2 active outages × 2 horizons
    await world.tick(NOW + timedelta(minutes=5))
    assert superuser.run("SELECT count(*) FROM prediction")[0][0] == 4
    await world.tick(NOW + GRADE_EVERY)
    assert superuser.run("SELECT count(*) FROM prediction")[0][0] == 8
    p2, p4 = superuser.run("SELECT p_still_off FROM prediction WHERE outage_id = 1 AND made_at = :t ORDER BY horizon_h",
                           t=NOW)
    assert p2[0] > p4[0]


@pytest.mark.anyio
async def test_old_snapshots_pruned(world, superuser):
    await world.tick(NOW)
    await world.tick(NOW + timedelta(hours=3))
    assert superuser.run("SELECT count(DISTINCT tick_at) FROM triage_snapshot")[0][0] == 1


@pytest.mark.anyio
async def test_no_faults_means_empty_snapshot(db_factory, superuser):
    superuser.run("TRUNCATE outage, outage_version, patient, prediction, grade, triage_snapshot RESTART IDENTITY CASCADE")
    scorer = Scorer(db_factory("bn_agent"), MODEL, keys()[1])
    assert await scorer.tick(NOW) == 0


@pytest.mark.anyio
async def test_triage_api_serves_latest_snapshot(world):
    await world.tick(NOW)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            body = (await c.get("/api/triage?limit=1")).json()
            assert body["items"][0]["device"] == "o2_concentrator" and body["items"][0]["escalate"]
            assert body["next_cursor"] == 1 and body["items"][0]["scale"] in ("street", "unresolved")
            page2 = (await c.get("/api/triage?limit=1&cursor=1")).json()
            assert page2["items"][0]["rank"] == 2 and page2["next_cursor"] is None
            assert "eta" not in json.dumps(body).lower()


def test_blind_index_matches_seeded_patients():
    _, bidx = keys()
    assert blind_index(bidx, "N1 3LD") != blind_index(bidx, "N1 3LE")


def test_fit_from_enwl_csv(tmp_path):
    csv_path = tmp_path / "enwl.csv"
    csv_path.write_text("﻿incident_duration;district_name\n60;Manchester\n120;Bolton\n;Wigan\n240;Bury\n",
                        encoding="utf-8")
    doc = survival.fit_from_enwl(csv_path)
    assert doc["n"] == 3 and doc["curve"][0] == 1.0 and doc["curve"][2] == pytest.approx(1 / 3)
