import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.combiner import (DNO_DECLARED_P, LR_IODA, LR_STRESS, PRIOR, Reading, cell_scale, p_outage, quiet_together,
                          scale)
from app.ingest import feeds, store
from app.localiser import evaluate

T0 = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)
# two L1 cells under one L2 parent, and one far away
NEAR_A, NEAR_B, FAR = "L1:5150:-6", "L1:5151:-6", "L1:5300:-90"


def street_out(at: datetime = T0) -> list[Reading]:
    """Five sensors on a street: three gasp together, two anchors keep reporting."""
    return [Reading("home", "last_gasp", at), Reading("home", "last_gasp", at + timedelta(seconds=40)),
            Reading("home", "last_gasp", at + timedelta(minutes=2)), Reading("anchor", "up", at),
            Reading("anchor", "up", at)]


def quiet_street(at: datetime = T0) -> list[Reading]:
    return [Reading("home", "up", at), Reading("home", "up", at), Reading("anchor", "up", at), Reading("anchor", "up", at)]


def odds(p: float) -> float:
    return p / (1 - p)


def test_a_quorum_of_sensors_quiet_together_is_a_street_event():
    assert cell_scale(street_out()) == "street"
    assert p_outage(street_out()) > 0.5


def test_dropouts_spread_over_hours_are_comms_noise_not_a_quorum():
    spread = [Reading("home", "dropout", T0 + timedelta(hours=h)) for h in range(3)]
    spread += [Reading("anchor", "up", T0), Reading("anchor", "up", T0)]
    assert quiet_together(spread) == 1
    assert cell_scale(spread) == "home"  # each quiet home, with its anchors up, is a home-only case


def test_one_home_down_while_its_anchors_report_is_that_home_only():
    readings = [Reading("home", "last_gasp", T0)] + quiet_street()
    assert cell_scale(readings) == "home"
    assert p_outage(readings) < 0.5  # the street isn't out; the patient's own priority is the agent's to keep


def test_too_few_anchors_reporting_leaves_the_scale_unresolved():
    readings = [Reading("home", "last_gasp", T0), Reading("home", "up", T0), Reading("home", "up", T0),
                Reading("anchor", "up", T0), Reading("anchor", "dropout", T0)]
    assert cell_scale(readings) == "unresolved"
    assert cell_scale([]) == "unresolved"


def test_quorum_cells_widen_to_area_region_and_system():
    two_near = {NEAR_A: street_out(), NEAR_B: street_out(), FAR: quiet_street()}
    assert scale(two_near) == {NEAR_A: "area", NEAR_B: "area", FAR: "none"}
    three = {NEAR_A: street_out(), NEAR_B: street_out(), FAR: street_out(), "L1:1:1": quiet_street()}
    assert scale(three)[FAR] == "street"  # far away, and no IODA dip or shedding to tie it together
    assert set(scale(three, ioda_dip=True).values()) == {"region", "none"}
    assert set(scale(three, shedding=True).values()) == {"region", "none"}
    assert scale(three, stress="EMERGENCY")[NEAR_A] == "system"  # 3 of 4 sensed cells quiet in an emergency
    assert scale({NEAR_A: street_out(), FAR: quiet_street(), "L1:1:1": quiet_street()}, stress="EMERGENCY")[NEAR_A] == "street"


def test_a_dno_declared_fault_is_near_certain_whatever_the_sensors_say():
    assert p_outage(quiet_street(), dno_declared=True) == DNO_DECLARED_P


def test_a_stale_source_counts_as_no_evidence():
    assert p_outage(street_out(), stale=frozenset({"sensors"})) == pytest.approx(PRIOR)
    assert p_outage([], ioda_dip=True, stale=frozenset({"ioda"})) == pytest.approx(PRIOR)
    assert p_outage([], stress="EMERGENCY", stale=frozenset({"elexon"})) == pytest.approx(PRIOR)
    assert abs(odds(p_outage([], ioda_dip=True)) / odds(PRIOR) - LR_IODA) < 1e-9
    assert abs(odds(p_outage([], stress="EMERGENCY")) / odds(PRIOR) - LR_STRESS["EMERGENCY"]) < 1e-9


def test_silence_is_not_evidence_of_an_outage_and_power_reports_count_against():
    silent = [Reading("home", "dropout", T0), Reading("anchor", "dropout", T0)]
    assert p_outage(silent) == pytest.approx(PRIOR)
    assert p_outage(quiet_street()) < PRIOR


@pytest.mark.anyio
async def test_the_localiser_scores_only_the_live_fleet_against_the_footprint(db_factory, superuser):
    superuser.run("TRUNCATE outage, outage_version, sensor, sensor_transition RESTART IDENTITY CASCADE")
    superuser.run("INSERT INTO postcode_geo VALUES ('N1 3LD', 51.5456, -0.0890, 'E', 'Islington', true, now())"
                  " ON CONFLICT DO NOTHING")
    ingest = db_factory("bn_ingest")
    now = datetime.now(UTC)
    await store.sync(ingest, "ukpn", [feeds.Outage("ukpn", "INCD-L", "active", now - timedelta(hours=1),
                                                   postcodes=["N1 3LD"], lat=51.5456, lon=-0.089)], now)
    out, control, gone = "L1:5154:-6", "L1:5156:-6", "L1:5300:-90"  # gone: a fault the simulator retired (id 99)
    rows = [("h-1-N13LD-0", "home", out, "last_gasp"), ("h-1-N13LD-1", "home", out, "last_gasp"),
            ("a-1-N13LD-0", "anchor", out, "last_gasp"), ("a-1-N13LD-1", "anchor", out, "up"),
            ("c-1-0", "control", control, "up"), ("c-1-1", "control", control, "up"),
            ("h-99-X-0", "home", gone, "last_gasp")]
    for sensor_id, kind, cell, state in rows:
        superuser.run("INSERT INTO sensor VALUES (:id, :type, CAST(:household AS uuid), :cell)", id=sensor_id, type=kind,
                      household=str(uuid.uuid4()) if kind == "home" else None, cell=cell)
        superuser.run("INSERT INTO sensor_transition VALUES (:id, :at, :state, :cell, 'SIMULATED')", id=sensor_id,
                      at=now - timedelta(hours=1), state=state, cell=cell)
    result = (await evaluate(ingest))["gb_simulated"]
    assert result["sensed_cells"] == 2 and result["footprint_cells"] == 1  # the retired fault's cell isn't scored
    assert (result["precision"], result["recall"], result["postcode_recall"]) == (1.0, 1.0, 1.0)
