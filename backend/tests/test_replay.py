import gzip
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.replay import ACCRA_CELL, SPEED, Replay, build

DAY = datetime(2021, 6, 1, tzinfo=UTC)
T0 = datetime(2026, 10, 18, 0, 0, tzinfo=UTC)  # midnight, so the replay starts at the week's minute 0
HEADER = "time,site_id,voltage,frequency,district,is_powered,was_moved\n"


def reading(minute: int, site: int, powered: bool, moved: bool = False, second: int = 10) -> str:
    at = DAY + timedelta(minutes=minute, seconds=second)
    return (f"{at:%Y-%m-%dT%H:%M:%S}.000Z,{site},{230.0 if powered else 0.0},50.0,Kwabenya,"
            f"{str(powered).lower()},{str(moved).lower()}\n")


@pytest.fixture
def accra(tmp_path) -> Path:
    """The real file format, 20 minutes of it: site 1 always on, site 2 off from minute 6 to 12, site 3 moved (the
    probe drops it), site 4 one flicker inside an otherwise powered bin."""
    rows = []
    for m in range(0, 20, 2):
        rows += [reading(m, 1, True), reading(m, 2, not 6 <= m < 12), reading(m, 3, True, moved=True),
                 reading(m, 4, True)]
    rows.append(reading(4, 4, False, second=40))
    with gzip.open(tmp_path / "accra_2021-06-01.csv.gz", "wt") as f:
        f.write(HEADER + "".join(rows))
    return tmp_path


class Bus:
    def __init__(self):
        self.events: list[dict] = []

    async def publish(self, event: dict) -> None:
        self.events.append(event)


def started(folder: Path, now: datetime = T0) -> tuple[Replay, Bus]:
    bus = Bus()
    replay = Replay(None, bus, folder)
    replay.begin(build(folder), now)
    return replay, bus


def test_the_week_is_read_with_the_probe_loader_into_two_minute_bins(accra):
    week = build(accra)
    assert week.sites == ["acc-1", "acc-2", "acc-4"] and week.length_min == 24 * 60
    assert list(week.minute) == sorted(week.minute) and set(week.minute) == set(range(0, 20, 2))
    off = {(m, week.sites[s]) for m, s, p in zip(week.minute, week.site, week.powered) if not p}
    assert off == {(6, "acc-2"), (8, "acc-2"), (10, "acc-2"), (4, "acc-4")}  # one unpowered reading turns a bin off


@pytest.mark.anyio
async def test_bins_play_in_order_ten_times_faster_with_a_gasp_then_silence_for_an_outage(accra):
    replay, bus = started(accra)
    played: dict[str, list[tuple[int, str]]] = {}
    for minute in range(20):
        now = T0 + timedelta(seconds=minute * 60 / SPEED)
        bus.events.clear()
        await replay.tick(now)
        for e in bus.events:
            assert e["observed_at"] == now and e["label"] == "REPLAY" and e["source"] == "accra_replay"
            assert e["payload"]["cell_l1"] == ACCRA_CELL
            played.setdefault(e["payload"]["sensor_id"], []).append((minute, e["payload"]["kind"]))
    assert played["acc-2"] == [(0, "heartbeat"), (2, "heartbeat"), (4, "heartbeat"), (6, "last_gasp"),
                               (12, "heartbeat"), (14, "heartbeat"), (16, "heartbeat"), (18, "heartbeat")]
    assert [k for _, k in played["acc-4"]] == ["heartbeat", "heartbeat", "last_gasp"] + ["heartbeat"] * 7
    assert played["acc-1"] == [(m, "heartbeat") for m in range(0, 20, 2)]


@pytest.mark.anyio
async def test_a_stalled_loop_catching_up_sends_one_event_per_sensor(accra):
    replay, bus = started(accra)
    assert await replay.tick(T0 + timedelta(hours=3)) == 3
    assert await replay.tick(T0 + timedelta(hours=3)) == 0  # nothing new is due


@pytest.mark.anyio
async def test_the_week_wraps_around_to_its_first_bins(accra):
    replay, bus = started(accra, T0 - timedelta(minutes=1))  # 23:59: the replay starts at the day's last minute
    await replay.tick(T0 - timedelta(minutes=1) + timedelta(seconds=60 / SPEED))
    assert {e["payload"]["sensor_id"] for e in bus.events} == {"acc-1", "acc-2", "acc-4"}


@pytest.mark.anyio
async def test_sensors_are_registered_once_as_anchors_in_the_accra_cell(accra, db_factory, superuser):
    superuser.run("TRUNCATE sensor")
    replay = Replay(db_factory("bn_ingest"), Bus(), accra)
    replay.begin(build(accra), T0)
    await replay.register()
    await replay.register()
    rows = superuser.run("SELECT sensor_id, type, household_id, cell_l1 FROM sensor ORDER BY sensor_id")
    assert rows == [[s, "anchor", None, ACCRA_CELL] for s in ("acc-1", "acc-2", "acc-4")]


@pytest.mark.anyio
async def test_without_the_data_the_replay_stays_off(tmp_path, monkeypatch):
    monkeypatch.setattr("app.replay.HEARTBEAT_S", 0)
    replay = Replay(None, Bus(), tmp_path)
    await replay.run()
    assert replay.week is None
