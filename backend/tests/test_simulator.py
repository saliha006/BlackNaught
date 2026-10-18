import random
from datetime import UTC, datetime, timedelta

import pytest

from app import simulator
from app.ingest import feeds, store
from app.simulator import Simulator

NOW = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)
STARTED = NOW - timedelta(hours=1)


class Bus:
    def __init__(self):
        self.events: list[dict] = []

    async def publish(self, event: dict) -> None:
        self.events.append(event)

    def take(self) -> list[dict]:
        out, self.events = self.events, []
        return out


def fault(status: str = "active", restored_at: datetime | None = None) -> feeds.Outage:
    # N1 9ZZ isn't geocoded, so it gets no sensors
    return feeds.Outage("ukpn", "INCD-S", status, STARTED, restored_at=restored_at,
                        postcodes=["N1 3LD", "N1 3LE", "N1 9ZZ"], lat=51.545, lon=-0.089)


@pytest.fixture
async def ingest(db_factory, superuser):
    superuser.run("TRUNCATE outage, outage_version, sensor RESTART IDENTITY CASCADE")
    superuser.run("INSERT INTO postcode_geo VALUES ('N1 3LD', 51.5456, -0.0890, 'E', 'Islington', true, now()),"
                  " ('N1 3LE', 51.5445, -0.0891, 'E', 'Islington', true, now()) ON CONFLICT DO NOTHING")
    db = db_factory("bn_ingest")
    await store.sync(db, "ukpn", [fault()], NOW)
    return db


@pytest.mark.anyio
async def test_sensors_sit_on_the_fault_footprint(ingest, superuser):
    await Simulator(ingest, Bus(), random.Random(1)).tick(NOW)
    rows = superuser.run("SELECT type, household_id IS NOT NULL, cell_l1 FROM sensor")
    assert sorted((t, h) for t, h, _ in rows) == [("anchor", False)] * 4 + [("control", False)] * 2 + [("home", True)] * 6
    home_cells = {c for t, _, c in rows if t != "control"}
    assert {c for t, _, c in rows if t == "control"}.isdisjoint(home_cells)  # controls watch the next cell over


@pytest.mark.anyio
async def test_an_affected_sensor_gasps_once_at_the_real_start_then_stays_silent(ingest):
    bus = Bus()
    sim = Simulator(ingest, bus, random.Random(1))
    await sim.tick(NOW)
    down = {s.sensor_id for s in sim.sensors.values() if s.affected and not s.behind_backup}
    first = bus.take()
    gasps = [e for e in first if e["payload"]["kind"] == "last_gasp"]
    assert {e["payload"]["sensor_id"] for e in gasps} == down and down
    assert all(e["observed_at"] == STARTED and e["label"] == "SIMULATED" and e["source"] == "sim" for e in gasps)
    assert {e["payload"]["sensor_id"] for e in first if e["payload"]["kind"] == "heartbeat"}.isdisjoint(down)
    await sim.tick(NOW + timedelta(minutes=1))
    assert not {e["payload"]["sensor_id"] for e in bus.take()} & down


@pytest.mark.anyio
async def test_power_comes_back_with_the_real_restoration(ingest, monkeypatch):
    bus = Bus()
    sim = Simulator(ingest, bus, random.Random(1))
    await sim.tick(NOW)
    down = {s.sensor_id for s in sim.sensors.values() if s.affected and not s.behind_backup}
    restored = NOW + timedelta(minutes=30)
    await store.sync(ingest, "ukpn", [fault("restored", restored)], restored)
    bus.take()
    for s in sim.sensors.values():
        s.online = True
    monkeypatch.setattr("app.simulator.DROP_P", 0.0)  # no comms gaps, so every powered sensor must report
    await sim.tick(restored + timedelta(minutes=1))
    assert down <= {e["payload"]["sensor_id"] for e in bus.take() if e["payload"]["kind"] == "heartbeat"}
    await sim.tick(restored + simulator.RESTORED_KEEP + timedelta(minutes=1))
    assert not sim.sensors  # retired once the restoration has been seen for long enough


@pytest.mark.anyio
async def test_comms_noise_keeps_about_three_quarters_of_heartbeats(ingest):
    bus = Bus()
    sim = Simulator(ingest, bus, random.Random(7))
    await sim.tick(NOW)
    reporting = [s.sensor_id for s in sim.sensors.values() if not s.affected or s.behind_backup]
    bus.take()
    rounds = 300
    for m in range(1, rounds + 1):
        await sim.tick(NOW + timedelta(minutes=m))
    beats = sum(e["payload"]["kind"] == "heartbeat" for e in bus.take())
    assert 0.65 < beats / (rounds * len(reporting)) < 0.85


@pytest.mark.anyio
async def test_a_partial_fault_takes_one_home_in_three_and_the_fleet_is_capped(ingest, superuser, monkeypatch):
    monkeypatch.setattr("app.simulator.PARTIAL_FAULT_P", 1.0)
    sim = Simulator(ingest, Bus(), random.Random(1))
    await sim.tick(NOW)
    homes = [s for s in sim.sensors.values() if s.type == "home"]
    assert sum(s.affected for s in homes) == len(homes) // 3
    superuser.run("TRUNCATE sensor")
    monkeypatch.setattr("app.simulator.MAX_SENSORS", 5)
    capped = Simulator(ingest, Bus(), random.Random(1))
    await capped.tick(NOW)
    assert len(capped.sensors) == 5 and superuser.run("SELECT count(*) FROM sensor")[0][0] == 5
