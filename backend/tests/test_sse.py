import asyncio
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sse_starlette.sse import ServerSentEvent
from starlette.requests import Request

from app import sse
from app.health import SourceHealth
from app.ingest.poller import Poller
from app.main import app, stream
from test_runtime import quiet  # noqa: F401 (fixture)


async def take(gen, n):
    return [await asyncio.wait_for(gen.__anext__(), 1) for _ in range(n)]


@pytest.mark.anyio
async def test_live_messages_reach_subscribers():
    b = sse.Broadcaster()
    client, backlog = b.subscribe(None)
    assert backlog == []
    gen = b.stream(client, backlog)
    b.publish("outage", {"id": 1})
    b.publish("triage", {"ranked": 3})
    got = await take(gen, 2)
    assert [(m["id"], m["event"]) for m in got] == [("1", "outage"), ("2", "triage")]
    # every message must survive sse-starlette's own encoder (it rejects non-string ids)
    assert ServerSentEvent(**got[0]).encode().startswith(b"id: 1")
    await gen.aclose()
    assert not b.clients


@pytest.mark.anyio
async def test_reconnect_replays_from_last_event_id():
    b = sse.Broadcaster()
    for i in range(5):
        b.publish("outage", {"i": i})
    client, backlog = b.subscribe(3)
    assert [m[0] for m in backlog] == [4, 5]
    got = await take(b.stream(client, backlog), 2)
    assert got[0]["retry"] == 3000
    assert all(ServerSentEvent(**m).encode() for m in got)


def test_gap_older_than_ring_asks_for_resync():
    b = sse.Broadcaster()
    for i in range(sse.RING + 10):
        b.publish("stats", {"i": i})
    _, backlog = b.subscribe(1)
    assert backlog == [(sse.RING + 10, sse.RESYNC, "{}")]


@pytest.mark.anyio
async def test_slow_client_drops_its_own_oldest_and_resyncs():
    b = sse.Broadcaster()
    slow, _ = b.subscribe(None)
    fast, _ = b.subscribe(None)
    for i in range(sse.PER_CLIENT + 3):
        b.publish("stats", {"i": i})
    assert slow.queue.qsize() == sse.PER_CLIENT and slow.behind
    first = await take(b.stream(slow, []), 2)
    assert first[0]["event"] == sse.RESYNC and first[1]["id"] == "4"  # 1..3 were dropped for this client only
    assert fast.queue.qsize() == sse.PER_CLIENT


def test_client_cap():
    b = sse.Broadcaster()
    for _ in range(sse.MAX_CLIENTS):
        b.subscribe(None)
    with pytest.raises(sse.TooManyClients):
        b.subscribe(None)


@pytest.mark.anyio
async def test_poller_reports_only_status_changes():
    seen = []
    h = SourceHealth("ukpn", 120)

    async def ok():
        return 1, False

    p = Poller(h, ok, on_status=lambda health: seen.append(health.status(datetime.now(UTC))))
    await p.poll_once()
    await p.poll_once()
    assert seen == ["ok"]


@pytest.mark.anyio
async def test_stream_endpoint_needs_workers_and_respects_cap(quiet, monkeypatch):  # noqa: F811
    async with app.router.lifespan_context(app):
        request = Request({"type": "http", "app": app, "headers": [], "method": "GET", "path": "/stream"})
        with pytest.raises(HTTPException) as no_workers:
            await stream(request, None)
        assert no_workers.value.status_code == 503
    monkeypatch.setenv("BN_WORKERS", "1")
    async with app.router.lifespan_context(app):
        rt = app.state.runtime
        response = await stream(request, None)
        assert response.headers["x-accel-buffering"] == "no"
        for _ in range(sse.MAX_CLIENTS - 1):
            rt.broadcaster.subscribe(None)
        with pytest.raises(HTTPException) as full:
            await stream(request, None)
        assert full.value.status_code == 503
