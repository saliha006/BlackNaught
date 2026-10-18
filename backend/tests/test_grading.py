from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.grading import GIVE_UP, Grader, judge, summarise
from app.ingest import feeds, store
from app.main import app

T0 = datetime(2026, 10, 17, 20, 0, tzinfo=UTC)
H2 = T0 + timedelta(hours=2)


def pred(source="ukpn", status="active", restored_at=None, explicit=False, last_seen=H2 + timedelta(minutes=2)):
    return {"made_at": T0, "horizon_h": 2, "source": source, "status": status, "restored_at": restored_at,
            "restored_explicit": explicit, "last_seen": last_seen}


@pytest.mark.parametrize("p,expected", [
    (pred(status="restored", restored_at=T0 + timedelta(hours=1), explicit=True), (0, "restored_before_horizon")),
    (pred(status="restored", restored_at=T0 + timedelta(hours=3), explicit=True), (1, "restored_after_horizon")),
    (pred(), (1, "still_off_at_horizon")),
    (pred(status="vanished", last_seen=H2 + timedelta(minutes=10)), (1, "still_off_at_horizon")),
    (pred(status="vanished", last_seen=T0 + timedelta(hours=1)), (None, "vanished_before_horizon")),
    (pred(source="ssen", status="restored", restored_at=T0 + timedelta(hours=1)), (None, "approximate_restore_time")),
    (pred(source="ssen", status="restored", restored_at=T0 + timedelta(hours=5)), (None, "approximate_restore_time")),
    (pred(source="ssen"), (1, "still_off_at_horizon")),
    (pred(source="npg"), (None, "npg_no_restore_signal")),
])
def test_outcome_table(p, expected):
    outcome = judge(p, H2 + timedelta(minutes=5))
    assert (outcome.y, outcome.reason) == expected


def test_silent_feed_waits_then_censors():
    p = pred(last_seen=T0 + timedelta(hours=1, minutes=50))
    assert judge(p, H2 + timedelta(minutes=10)) is None  # not decidable yet
    assert judge(p, H2 + GIVE_UP + timedelta(seconds=1)).reason == "source_down_across_horizon"


def test_summary_bounds_and_trend():
    at = datetime(2026, 10, 17, 23, 5, tzinfo=UTC)
    rows = [{"horizon_h": 2, "model_id": "m", "source": "ukpn", "brier": 0.04, "censored": False, "p_still_off": 0.8,
             "graded_at": at},
            {"horizon_h": 2, "model_id": "m", "source": "ukpn", "brier": 0.36, "censored": False, "p_still_off": 0.6,
             "graded_at": at},
            {"horizon_h": 2, "model_id": "m", "source": "ukpn", "brier": None, "censored": True, "p_still_off": 0.5,
             "graded_at": at}]
    s = summarise(rows)
    g = s["by_horizon"][0]
    assert (g["n"], g["n_censored"], g["brier"]) == (2, 1, 0.2)
    assert g["bound"] == (round((0.4 + 0.25) / 3, 4), round((0.4 + 0.25) / 3, 4))  # p=0.5 scores the same either way
    assert s["trend"] == [{"at": "2026-10-17T23:00:00+00:00", "brier": 0.2, "n": 2.0}]
    assert summarise([]) == {"by_horizon": [], "trend": []}


@pytest.fixture
async def graded_world(db_factory, superuser):
    superuser.run("TRUNCATE outage, outage_version, prediction, grade RESTART IDENTITY CASCADE")
    ingest = db_factory("bn_ingest")
    early = feeds.Outage("ukpn", "R", "restored", T0 - timedelta(hours=1), restored_at=T0 + timedelta(hours=1),
                         restored_explicit=True, postcodes=["N1 3LD"])
    late = feeds.Outage("ukpn", "A", "active", T0 - timedelta(hours=1), postcodes=["N1 3LE"])
    npg = feeds.Outage("npg", "N", "active", T0 - timedelta(hours=1), postcodes=["TS21 1NH"])
    await store.sync(ingest, "ukpn", [early, late], H2 + timedelta(minutes=3))
    await store.sync(ingest, "npg", [npg], H2 + timedelta(minutes=3))
    for outage_id, p in ((1, 0.3), (2, 0.9), (3, 0.5)):
        superuser.run("INSERT INTO prediction (outage_id, made_at, elapsed_h, model_id, model_sha256, horizon_h,"
                      " p_still_off, quantiles) VALUES (:o, :t, 1, 'm1-km-enwl', 'x', 2, :p, '{}')", o=outage_id, t=T0, p=p)
    return Grader(db_factory("bn_agent"))


@pytest.mark.anyio
async def test_grader_scores_real_outcomes_once(graded_world, superuser):
    assert await graded_world.tick(H2 + timedelta(minutes=1)) == 0  # inside the grace window
    assert await graded_world.tick(H2 + timedelta(minutes=5)) == 3
    assert await graded_world.tick(H2 + timedelta(minutes=6)) == 0  # never graded twice
    rows = superuser.run("SELECT pred_id, outcome, censored, reason, round(brier::numeric, 2)::float8 FROM grade ORDER BY pred_id")
    assert rows == [[1, 0, False, "restored_before_horizon", 0.09],
                    [2, 1, False, "still_off_at_horizon", 0.01],
                    [3, None, True, "npg_no_restore_signal", None]]


@pytest.mark.anyio
async def test_grades_api(graded_world):
    await graded_world.tick(H2 + timedelta(minutes=5))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            body = (await c.get("/api/agent/grades")).json()
    by = {(g["source"], g["h"]): g for g in body["by_horizon"]}
    assert by[("ukpn", 2)]["n"] == 2 and by[("ukpn", 2)]["brier"] == pytest.approx(0.05, abs=1e-3)
    assert by[("npg", 2)]["n"] == 0 and by[("npg", 2)]["n_censored"] == 1
