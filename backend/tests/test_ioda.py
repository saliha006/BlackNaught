import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.events import Event
from app.ingest import ioda
from app.ingest.sources import ioda_poll
from app.runtime import Runtime
from test_runtime import quiet  # noqa: F401 (fixture)

LK_BLACKOUT = json.loads(Path("/fixtures/feeds/ioda_lk_blackout.json").read_text())
NOW = datetime(2025, 2, 9, 6, 15, tzinfo=UTC)


def flat_series(country, value=1000.0, n=14):
    return {"data": [[{"datasource": ioda.DATASOURCE, "entityCode": country, "from": 1739073600, "step": 600,
                       "values": [value] * n}]]}


def dipped_series(country):
    doc = flat_series(country)
    doc["data"][0][0]["values"][-2:] = [500.0, 480.0]
    return doc


def client_for(responses):
    def handler(request):
        country = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json=responses.get(country, flat_series(country)))
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_ratios_need_a_full_baseline():
    assert ioda.latest_ratios([1.0] * 5) == []
    ratios = ioda.latest_ratios([100.0] * 12 + [85.0, 80.0])
    assert ratios == pytest.approx([0.85, 0.8])
    assert ioda.is_dip(ratios) and not ioda.is_dip([0.85, 0.95]) and not ioda.is_dip([0.85, None])


@pytest.mark.anyio
async def test_detects_the_real_sri_lanka_2025_blackout():
    async with client_for({"LK": LK_BLACKOUT}) as c:
        reading = await ioda.fetch(c, "LK", NOW)
    assert reading.ratio is not None and reading.ratio < ioda.DIP_RATIO
    assert reading.at == datetime(2025, 2, 9, 6, 10, tzinfo=UTC)


@pytest.mark.anyio
async def test_steady_signal_is_not_a_dip():
    async with client_for({}) as c:
        assert (await ioda.fetch(c, "GB", NOW)).ratio is None


def test_dips_in_many_countries_are_blamed_on_the_measurement():
    lone = [ioda.Reading("LK", NOW, 0.88), ioda.Reading("GB", NOW, None), ioda.Reading("FR", NOW, None)]
    assert [r.country for r in ioda.confirmed_dips(lone)] == ["LK"]
    everywhere = [ioda.Reading(c, NOW, 0.05) for c in ("LK", "GB", "FR")]
    assert ioda.confirmed_dips(everywhere) == []
    control_only = [ioda.Reading("US", NOW, 0.5)]
    assert ioda.confirmed_dips(control_only) == []


@pytest.mark.anyio
async def test_poll_reports_target_dips_only():
    got = []

    async def on_dips(dips):
        got.extend(d.country for d in dips)

    async with client_for({"LK": dipped_series("LK")}) as c:
        n, degraded = await ioda_poll(c, on_dips)()
    assert (n, degraded, got) == (len(ioda.TARGETS + ioda.CONTROLS), False, ["LK"])
    got.clear()
    async with client_for({c: dipped_series(c) for c in ("LK", "GB", "US")}) as c:
        await ioda_poll(c, on_dips)()
    assert got == []


@pytest.mark.anyio
async def test_runtime_turns_dips_into_contract_events(quiet):  # noqa: F811
    rt = Runtime()
    try:
        await rt.internet_dips([ioda.Reading("LK", NOW, 0.881)])
        event = rt.bus.bulk.get_nowait()
        assert Event.model_validate(event).payload.region == "LK"
        assert rt.broadcaster.ring[-1][1] == "ioda"
    finally:
        await rt.client.aclose()
        rt.ingest_db.close()
        rt.writer.db.close()
