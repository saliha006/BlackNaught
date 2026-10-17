import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from app import runtime as runtime_mod
from app.events import Event
from app.ingest.feeds import Outage
from app.main import app


@pytest.fixture
def quiet(monkeypatch):
    """No live network in tests: the runtime starts with no pollers and fast housekeeping."""
    monkeypatch.setattr(runtime_mod.Runtime, "pollers", lambda self: [])
    monkeypatch.setattr(runtime_mod, "SWEEP_S", 0.01)
    monkeypatch.setattr(runtime_mod, "COUNT_FLUSH_S", 0.01)


def _sensor_event(kind, sensor="s1", at=None):
    at = at or datetime.now(UTC)
    return {"event_id": "0" * 32, "source": "sim", "observed_at": at, "received_at": at, "label": "SIMULATED",
            "payload": {"kind": kind, "sensor_id": sensor, "cell_l1": "L1:5154:-6"}}


@pytest.mark.anyio
async def test_sensor_events_become_transitions(quiet):
    rt = runtime_mod.Runtime()
    try:
        await rt.handle(_sensor_event("heartbeat"))
        await rt.handle(_sensor_event("heartbeat"))
        await rt.handle(_sensor_event("last_gasp"))
        await rt.handle({**_sensor_event("heartbeat"), "payload": {"kind": "freq_reading", "hz": 50.0}})
        queued = [rt.writer.queue.get_nowait() for _ in range(rt.writer.queue.qsize())]
        assert [row[2] for table, row in queued] == ["up", "last_gasp"]
    finally:
        await rt.client.aclose()
        rt.ingest_db.close()
        rt.writer.db.close()


@pytest.mark.anyio
async def test_changed_outages_publish_contract_events(quiet):
    rt = runtime_mod.Runtime()
    try:
        o = Outage("ukpn", "INCD-1", "active", datetime.now(UTC), postcodes=["N1 3LD"])
        await rt.outages_changed("ukpn", [(7, o)])
        event = rt.bus.critical.get_nowait()
        parsed = Event.model_validate(event)
        assert parsed.payload.outage_id == 7 and parsed.payload.postcodes == ["N1 3LD"]
    finally:
        await rt.client.aclose()
        rt.ingest_db.close()
        rt.writer.db.close()


@pytest.mark.anyio
async def test_workers_start_and_stop_cleanly_through_lifespan(quiet, monkeypatch, superuser):
    superuser.run("TRUNCATE sensor_transition, event_counts")
    monkeypatch.setenv("BN_WORKERS", "1")
    async with app.router.lifespan_context(app):
        rt = app.state.runtime
        assert {t.get_name() for t in rt.tasks} == {"writer", "bus", "housekeeping"}
        await rt.bus.publish(_sensor_event("heartbeat", "s9"))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            sources = (await c.get("/api/sources/health")).json()["sources"]
            assert {s["source"] for s in sources} == {"ukpn", "npg", "ssen", "elexon"}
            assert all(s["status"] == "stale" for s in sources)  # nothing polled yet, never "ok"
        await asyncio.sleep(0.6)
    assert all(t.done() for t in rt.tasks)
    assert superuser.run("SELECT sensor_id, state FROM sensor_transition")[0] == ["s9", "up"]
    assert superuser.run("SELECT sum(n) FROM event_counts WHERE kind = 'heartbeat'")[0][0] == 1
