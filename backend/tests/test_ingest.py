import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app import cells, stress
from app.geocode import Geocoder, normalise
from app.health import SourceHealth
from app.ingest import feeds, store
from app.ingest.poller import Poller, get_json, get_paged
from app.ingest.sources import dno_poll, elexon_poll, split_valid
from app.writer import Writer

FEEDS = Path("/fixtures/feeds")
NOW = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)


def load(name):
    return json.loads((FEEDS / name).read_text())


async def no_sleep(_):
    return None


# --- parsers on real recorded responses --------------------------------------------------------

def test_ukpn_parse_real_feed():
    outages = feeds.parse_ukpn(load("ukpn_live.json")["results"])
    assert outages and {o.status for o in outages} <= {"active", "restored", "planned"}
    restored = [o for o in outages if o.status == "restored"]
    assert restored and all(o.restored_explicit and o.restored_at.tzinfo == UTC for o in restored)
    for o in outages:
        assert o.started_at.tzinfo == UTC
        assert all(normalise(p) == p for p in o.postcodes)
        assert o.cell_l1 is None or o.cell_l1.startswith("L1:")


def test_ukpn_status_mapping():
    base = {"incidentreference": "I", "creationdatetime": "2026-10-17T10:00:00", "fullpostcodedata": "N13LD;N13LE"}
    rows = [{**base, "statusid": 5, "powercuttype": "Restored", "restoreddatetime": "2026-10-17T12:00:00"},
            {**base, "statusid": 1, "powercuttype": "Planned"},
            {**base, "statusid": 2, "powercuttype": "Unplanned"}]
    got = feeds.parse_ukpn(rows)
    assert [o.status for o in got] == ["restored", "planned", "active"]
    assert got[0].restored_at == datetime(2026, 10, 17, 11, 0, tzinfo=UTC)  # BST
    assert got[2].postcodes == ["N1 3LD", "N1 3LE"]


def test_npg_merges_rows_by_reference():
    records = load("npg_live.json")["results"]
    outages = feeds.parse_npg(records)
    assert len(outages) == len({r["reference"] for r in records}) < len(records)
    for o in outages:
        rows = o.raw["rows"]
        assert o.customers == sum(r.get("totalconfirmedpowercut") or 0 for r in rows)
        assert o.started_at == min(feeds.timeparse.iso(r["loggedtime"]) for r in rows)
        assert not o.restored_explicit and o.status in ("active", "planned")


def test_ssen_resolved_is_approximate():
    doc = load("ssen_live.json")
    outages = feeds.parse_ssen(doc)
    assert len(outages) == len(doc["Faults"])
    assert all(not o.restored_explicit for o in outages)
    assert all(set(o.feeder) >= {"primaryNrn", "hvFeederNrn", "lvFeederNrn", "txNrn"} for o in outages)
    resolved = feeds.parse_ssen({"Faults": [{**doc["Faults"][0], "resolved": True}]})[0]
    assert resolved.status == "restored" and resolved.restored_at is not None and not resolved.restored_explicit


def test_elexon_parse():
    readings = feeds.parse_elexon(load("elexon.json"))
    assert readings and all(t.tzinfo == UTC and 45 < hz < 55 for t, hz in readings)


def test_content_hash_tracks_meaningful_changes():
    o = feeds.Outage("ukpn", "I", "active", NOW, postcodes=["N1 3LD"], customers=4)
    same = feeds.Outage("ukpn", "I", "active", NOW, postcodes=["N1 3LD"], customers=4, lat=1.0)
    assert o.content_hash == same.content_hash
    assert o.content_hash != feeds.Outage("ukpn", "I", "restored", NOW, postcodes=["N1 3LD"], customers=4).content_hash


def test_split_valid_isolates_bad_records():
    good = load("ukpn_live.json")["results"][0]
    valid, rejected = split_valid([good, {"incidentreference": "BAD"}], feeds.parse_ukpn)
    assert valid == [good] and rejected[0][1].startswith("KeyError")


# --- postcodes, cells, stress -------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [("n13ld", "N1 3LD"), ("PO2 0DU", "PO2 0DU"), (" ts21 1nh ", "TS21 1NH"),
                                          ("EC1A1BB", "EC1A 1BB"), ("N1 3", None), ("", None), ("12345", None)])
def test_normalise(raw, expected):
    assert normalise(raw) == expected


def test_cells_are_nested_and_closed():
    c = cells.cell_id(51.5414, -0.0887)
    assert cells.parent(c) == cells.cell_id(51.5414, -0.0887, 2)
    assert cells.parent(cells.parent(c)) == cells.cell_id(51.5414, -0.0887, 3)
    ring = cells.bounds(c)
    assert ring[0] == ring[-1] and ring[0][0] <= 51.5414 < ring[1][0] and ring[0][1] <= -0.0887 < ring[2][1]
    assert cells.cell_id(0.009999, 0) == "L1:0:0" and cells.cell_id(0.01, 0) == "L1:1:0"


@pytest.mark.parametrize("hz,state", [(None, "UNKNOWN"), (50.0, "NORMAL"), (49.8, "NORMAL"), (49.7, "STRESSED"),
                                      (50.45, "STRESSED"), (49.2, "EMERGENCY"), (51.0, "EMERGENCY")])
def test_stress_bands(hz, state):
    assert stress.state(hz) == state


# --- health -------------------------------------------------------------------------------------

def test_source_health_states():
    h = SourceHealth("ukpn", 120)
    assert h.status(NOW) == "stale"
    h.success(NOW, 10, degraded=False)
    assert h.status(NOW + timedelta(seconds=100)) == "ok"
    assert h.status(NOW + timedelta(seconds=361)) == "stale"
    assert h.status(NOW + timedelta(seconds=721)) == "down"
    h.success(NOW, 10, degraded=True)
    assert h.status(NOW) == "degraded"
    for _ in range(5):
        h.failure(NOW, "x" * 1000)
    assert h.status(NOW) == "down" and len(h.last_error) == 300
    assert h.as_dict(NOW)["consecutive_failures"] == 5


# --- HTTP retry behaviour ------------------------------------------------------------------------

def mock_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.anyio
async def test_retries_5xx_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503) if len(calls) < 3 else httpx.Response(200, json={"ok": 1})

    async with mock_client(handler) as c:
        assert await get_json(c, "https://x/", sleep=no_sleep) == {"ok": 1}
    assert len(calls) == 3


@pytest.mark.anyio
async def test_honours_retry_after_on_429():
    waits, calls = [], []

    async def record(seconds):
        waits.append(seconds)

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "7"}) if len(calls) == 1 else httpx.Response(200, json=[])

    async with mock_client(handler) as c:
        assert await get_json(c, "https://x/", sleep=record) == []
    assert waits == [7.0]


@pytest.mark.anyio
async def test_4xx_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(404)

    async with mock_client(handler) as c:
        with pytest.raises(httpx.HTTPStatusError):
            await get_json(c, "https://x/", sleep=no_sleep)
    assert len(calls) == 1


@pytest.mark.anyio
async def test_transport_errors_retry_then_raise():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ConnectError("down")

    async with mock_client(handler) as c:
        with pytest.raises(httpx.ConnectError):
            await get_json(c, "https://x/", sleep=no_sleep)
    assert len(calls) == 3


@pytest.mark.anyio
async def test_paging_follows_total_count():
    rows = [{"i": i} for i in range(230)]

    def handler(request):
        offset, limit = int(request.url.params["offset"]), int(request.url.params["limit"])
        return httpx.Response(200, json={"total_count": len(rows), "results": rows[offset:offset + limit]})

    async with mock_client(handler) as c:
        assert await get_paged(c, "https://x/", sleep=no_sleep) == rows


@pytest.mark.anyio
async def test_poller_records_health_and_backs_off():
    h = SourceHealth("ukpn", 120)

    async def ok():
        return 7, False

    async def broken():
        raise httpx.ConnectError("down")

    assert await Poller(h, ok).poll_once() and h.records_last == 7
    failing = Poller(h, broken)
    for _ in range(6):
        assert not await failing.poll_once()
    assert h.consecutive_failures == 6 and "ConnectError" in h.last_error
    assert 120 * 4 * 0.9 <= failing.next_interval() <= 120 * 4 * 1.1


# --- store + end-to-end polls against the test DB ---------------------------------------------------

@pytest.fixture
def ingest_db(db_factory, superuser):
    superuser.run("TRUNCATE outage, outage_version, ingest_reject, postcode_geo, freq_reading RESTART IDENTITY CASCADE")
    return db_factory("bn_ingest")


def _o(ref, status="active", customers=4):
    return feeds.Outage("ukpn", ref, status, NOW - timedelta(hours=1), customers=customers,
                        postcodes=["N1 3LD"], lat=51.54, lon=-0.09, raw={"ref": ref})


@pytest.mark.anyio
async def test_sync_versions_and_vanishes(ingest_db, superuser):
    assert [i for i, _ in await store.sync(ingest_db, "ukpn", [_o("A"), _o("B")], NOW)] == [1, 2]
    assert await store.sync(ingest_db, "ukpn", [_o("A"), _o("B")], NOW) == []
    changed = await store.sync(ingest_db, "ukpn", [_o("A", "restored"), _o("B")], NOW)
    assert [i for i, _ in changed] == [1]
    assert superuser.run("SELECT version, status FROM outage WHERE outage_id = 1")[0] == [2, "restored"]
    assert superuser.run("SELECT count(*) FROM outage_version WHERE outage_id = 1")[0][0] == 2
    await store.sync(ingest_db, "ukpn", [_o("A", "restored")], NOW)  # B missed once
    assert superuser.run("SELECT status, missed_polls FROM outage WHERE source_ref = 'B'")[0] == ["active", 1]
    await store.sync(ingest_db, "ukpn", [_o("A", "restored")], NOW)  # B missed twice
    assert superuser.run("SELECT status FROM outage WHERE source_ref = 'B'")[0][0] == "vanished"
    await store.sync(ingest_db, "ukpn", [_o("A", "restored")], NOW)  # restored rows never vanish
    assert superuser.run("SELECT status FROM outage WHERE source_ref = 'A'")[0][0] == "restored"
    back = await store.sync(ingest_db, "ukpn", [_o("A", "restored"), _o("B")], NOW)  # reappears
    assert [i for i, _ in back] == [2]
    assert superuser.run("SELECT status, missed_polls FROM outage WHERE source_ref = 'B'")[0] == ["active", 0]


@pytest.mark.anyio
async def test_reject_logged(ingest_db, superuser):
    await store.reject(ingest_db, "ukpn", "X", "KeyError: 'statusid'", {"incidentreference": "X"})
    assert superuser.run("SELECT source_ref, error FROM ingest_reject")[0] == ["X", "KeyError: 'statusid'"]


def postcodes_handler(calls):
    recorded = {r["query"]: r for r in load("postcodes_bulk.json")["result"]}

    def handler(request):
        calls.append(json.loads(request.content)["postcodes"])
        wanted = calls[-1]
        return httpx.Response(200, json={"status": 200, "result": [recorded.get(p, {"query": p, "result": None})
                                                                    for p in wanted]})
    return handler


@pytest.mark.anyio
async def test_geocoder_caches_hits_and_misses(ingest_db, superuser):
    calls = []
    async with mock_client(postcodes_handler(calls)) as c:
        geo = Geocoder(ingest_db, c)
        got = await geo.lookup(["N1 3LD", "PO2 0DU", "ZZ9 9ZZ", "N1 3LD"])
        assert got["N1 3LD"]["valid"] and round(got["N1 3LD"]["lat"], 2) == 51.55
        assert got["ZZ9 9ZZ"]["valid"] is False
        again = await geo.lookup(["N1 3LD", "ZZ9 9ZZ"])
    assert len(calls) == 1 and sorted(calls[0]) == ["N1 3LD", "PO2 0DU", "ZZ9 9ZZ"]
    assert again["N1 3LD"]["admin_district"] == "Islington"
    assert superuser.run("SELECT count(*) FROM postcode_geo")[0][0] == 3


@pytest.mark.anyio
async def test_geocoder_chunks_at_100(ingest_db):
    calls = []
    many = [f"{area}{d} {k}AA" for area in ("N", "E") for d in range(1, 10) for k in range(10)]
    async with mock_client(postcodes_handler(calls)) as c:
        await Geocoder(ingest_db, c).lookup(many)
    assert all(len(chunk) <= 100 for chunk in calls) and len(calls) >= 2


@pytest.mark.anyio
async def test_dno_poll_end_to_end_from_recorded_ukpn(ingest_db, superuser):
    page = load("ukpn_live.json")
    published = []

    def handler(request):
        if "postcodes.io" in str(request.url):
            return postcodes_handler([])(request)
        return httpx.Response(200, json={"total_count": len(page["results"]), "results": page["results"]})

    async def on_changed(source, changed):
        published.append((source, [i for i, _ in changed]))

    async with mock_client(handler) as c:
        poll = dno_poll("ukpn", c, ingest_db, Geocoder(ingest_db, c), on_changed)
        n, degraded = await poll()
        n2, _ = await poll()
    assert n == n2 == len(page["results"]) and not degraded
    stored = superuser.run("SELECT count(*) FROM outage WHERE source = 'ukpn'")[0][0]
    assert stored == len(page["results"]) and len(published) == 1  # second poll: nothing changed


@pytest.mark.anyio
async def test_dno_poll_flags_schema_drift(ingest_db, superuser):
    good = load("ukpn_live.json")["results"][0]
    bad = [{"incidentreference": f"B{i}"} for i in range(3)]

    def handler(request):
        if "postcodes.io" in str(request.url):
            return httpx.Response(200, json={"status": 500, "error": "shape changed"})  # malformed geocoder reply
        return httpx.Response(200, json={"total_count": 4, "results": [good] + bad})

    async def on_changed(source, changed):
        pass

    async with mock_client(handler) as c:
        n, degraded = await dno_poll("ukpn", c, ingest_db, Geocoder(ingest_db, c), on_changed)()
    assert n == 4 and degraded
    assert superuser.run("SELECT count(*) FROM outage")[0][0] == 1  # the good record still landed
    assert superuser.run("SELECT count(*) FROM ingest_reject")[0][0] == 3


@pytest.mark.anyio
async def test_dno_poll_survives_geocoder_outage(ingest_db, superuser):
    page = load("ssen_live.json")

    def handler(request):
        if "postcodes.io" in str(request.url):
            return httpx.Response(502)
        return httpx.Response(200, json=page)

    async def on_changed(source, changed):
        pass

    async with mock_client(handler) as c:
        n, _ = await dno_poll("ssen", c, ingest_db, Geocoder(ingest_db, c), on_changed)()
    assert superuser.run("SELECT count(*) FROM outage WHERE source = 'ssen'")[0][0] == len(page["Faults"]) == n


@pytest.mark.anyio
async def test_elexon_poll_writes_and_windows(ingest_db, superuser):
    seen_params = []

    def handler(request):
        seen_params.append(dict(request.url.params))
        return httpx.Response(200, json=load("elexon.json"))

    writer = Writer(ingest_db)
    async with mock_client(handler) as c:
        poll = elexon_poll(c, writer)
        n, _ = await poll()
        await poll()
    batch = []
    while not writer.queue.empty():
        batch.append(writer.queue.get_nowait())
    await writer.flush(batch)
    assert superuser.run("SELECT count(*) FROM freq_reading")[0][0] == n
    assert {"from", "to"} <= set(seen_params[0]) and seen_params[1]["from"] > seen_params[0]["from"]
