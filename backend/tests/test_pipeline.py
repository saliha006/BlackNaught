import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app import timeparse
from app.bus import BULK_MAX, EventBus, minute_of
from app.sensors import DROPOUT_AFTER, RESTART_GRACE, SensorTracker
from app.writer import TABLES, Writer

T0 = datetime(2026, 10, 17, 21, 0, tzinfo=UTC)


# --- time parsing ---------------------------------------------------------------------------

def test_ukpn_local_time_in_bst_converts_to_utc():
    assert timeparse.uk_local("2026-10-15T00:49:22") == datetime(2026, 10, 14, 23, 49, 22, tzinfo=UTC)


def test_ukpn_local_time_in_gmt_is_unchanged():
    assert timeparse.uk_local("2026-01-15T09:00:00") == datetime(2026, 1, 15, 9, 0, tzinfo=UTC)


def test_ukpn_value_with_offset_is_respected():
    assert timeparse.uk_local("2026-10-15T00:49:22+00:00") == datetime(2026, 10, 15, 0, 49, 22, tzinfo=UTC)


@pytest.mark.parametrize("raw", ["2026-10-17T21:40:00+00:00", "2026-10-17T21:40:00+0000", "2026-10-17T21:40:00Z",
                                 "2026-10-17T22:40:00+01:00"])
def test_iso_offsets(raw):
    assert timeparse.iso(raw) == datetime(2026, 10, 17, 21, 40, tzinfo=UTC)


def test_iso_rejects_naive():
    with pytest.raises(ValueError, match="without offset"):
        timeparse.iso("2026-10-17T21:40:00")


def test_epoch_and_cap_format():
    assert timeparse.epoch(0) == datetime(1970, 1, 1, tzinfo=UTC)
    stamp = timeparse.cap(datetime(2026, 10, 18, 3, 10, tzinfo=UTC))
    assert stamp == "2026-10-18T03:10:00-00:00" and "Z" not in stamp


# --- writer -----------------------------------------------------------------------------------

@pytest.fixture
def writer_db(db_factory, superuser):
    superuser.run("TRUNCATE freq_reading, sensor_transition, event_counts, source_poll")
    return db_factory("bn_ingest")


@pytest.mark.anyio
async def test_writer_batches_and_dedupes(writer_db, superuser):
    w = Writer(writer_db)
    rows = [("gb", T0 + timedelta(seconds=i), 50.0 + i / 1000) for i in range(1200)]
    await w.flush([("freq_reading", r) for r in rows + rows[:10]])
    assert superuser.run("SELECT count(*) FROM freq_reading")[0][0] == 1200


@pytest.mark.anyio
async def test_event_counts_accumulate(writer_db, superuser):
    w = Writer(writer_db)
    await w.flush([("event_counts", (T0, "heartbeat", 5, 1)), ("event_counts", (T0, "heartbeat", 7, 0))])
    await w.flush([("event_counts", (T0, "heartbeat", 3, 2))])
    assert superuser.run("SELECT n, dropped FROM event_counts")[0] == [15, 3]


@pytest.mark.anyio
async def test_bad_row_is_isolated_not_the_batch(writer_db, superuser):
    w = Writer(writer_db)
    good = [("sensor_transition", (f"s{i}", T0, "up", "L1:0:0", "SIMULATED")) for i in range(9)]
    bad = ("sensor_transition", ("s-bad", T0, "exploded", "L1:0:0", "SIMULATED"))  # violates CHECK
    await w.flush(good[:4] + [bad] + good[4:])
    assert superuser.run("SELECT count(*) FROM sensor_transition")[0][0] == 9
    assert w.rejected == 1


@pytest.mark.anyio
async def test_run_flushes_on_timer_and_stops_on_sentinel(writer_db, superuser):
    w = Writer(writer_db)
    task = asyncio.create_task(w.run())
    w.put("source_poll", ("ukpn", T0, True, 200, 62, 120, None))
    await asyncio.sleep(0.6)
    assert superuser.run("SELECT count(*) FROM source_poll")[0][0] == 1
    w.put("source_poll", ("npg", T0, False, 503, 0, 900, "upstream"))
    w.stop()
    await asyncio.wait_for(task, 5)
    assert superuser.run("SELECT count(*) FROM source_poll")[0][0] == 2


def test_writer_rejects_unknown_table(writer_db):
    with pytest.raises(KeyError):
        Writer(writer_db).put("patient", ())


def test_table_specs_are_aligned():
    for spec in TABLES.values():
        assert len(spec.columns) == len(spec.types)


# --- bus ----------------------------------------------------------------------------------------

def _ev(kind, i=0):
    return {"payload": {"kind": kind, "i": i}}


@pytest.mark.anyio
async def test_bulk_drops_oldest_critical_never_drops():
    bus = EventBus()
    for i in range(BULK_MAX + 5):
        await bus.publish(_ev("heartbeat", i))
    for i in range(3):
        await bus.publish(_ev("last_gasp", i))
    assert bus.bulk.qsize() == BULK_MAX and bus.dropped["heartbeat"] == 5
    assert bus.bulk.get_nowait()["payload"]["i"] == 5  # 0..4 were the oldest
    assert bus.critical.qsize() == 3


@pytest.mark.anyio
async def test_consumer_drains_critical_first_and_counts():
    bus = EventBus()
    order = []
    await bus.publish(_ev("heartbeat"))
    await bus.publish(_ev("dno_fault"))

    async def handle(event):
        order.append(event["payload"]["kind"])

    task = asyncio.create_task(bus.consume(handle))
    await asyncio.sleep(0.05)
    await bus.publish(_ev("freq_reading"))
    await asyncio.sleep(0.05)
    task.cancel()
    assert order == ["dno_fault", "heartbeat", "freq_reading"]
    seen, dropped = bus.take_counts()
    assert seen == {"dno_fault": 1, "heartbeat": 1, "freq_reading": 1} and not dropped
    assert bus.take_counts() == ({}, {})


def test_minute_of():
    assert minute_of(datetime(2026, 10, 17, 21, 5, 59, 9, tzinfo=UTC)) == datetime(2026, 10, 17, 21, 5, tzinfo=UTC)


# --- sensors --------------------------------------------------------------------------------------

def test_heartbeats_only_emit_on_change():
    t = SensorTracker(T0)
    assert t.heartbeat("a", "L1:1:1", "SIMULATED", T0) == ("a", T0, "up", "L1:1:1", "SIMULATED")
    assert t.heartbeat("a", "L1:1:1", "SIMULATED", T0 + timedelta(seconds=60)) is None
    assert t.last_gasp("a", "L1:1:1", "SIMULATED", T0 + timedelta(seconds=90))[2] == "last_gasp"
    assert t.heartbeat("a", "L1:1:1", "SIMULATED", T0 + timedelta(seconds=300))[2] == "up"


def test_silence_is_dropout_never_down_and_respects_grace():
    t = SensorTracker(T0)
    t.heartbeat("a", "L1:1:1", "SIMULATED", T0)
    t.heartbeat("b", "L1:1:1", "SIMULATED", T0 + RESTART_GRACE)
    assert t.sweep(T0 + timedelta(seconds=60)) == []  # inside restart grace
    later = T0 + DROPOUT_AFTER + timedelta(seconds=1)
    out = t.sweep(max(later, T0 + RESTART_GRACE))
    assert [(s, st) for s, _, st, _, _ in out] == [("a", "dropout")]
    assert t.sweep(later + timedelta(seconds=1)) == []  # already dropped out
    assert t.cell_counts() == {"L1:1:1": {"dropout": 1, "up": 1}}


def test_out_of_order_heartbeat_keeps_latest_last_seen():
    t = SensorTracker(T0)
    t.heartbeat("a", "c", "SIMULATED", T0 + timedelta(seconds=120))
    t.heartbeat("a", "c", "SIMULATED", T0)
    assert t.sensors["a"].last_seen == T0 + timedelta(seconds=120)
