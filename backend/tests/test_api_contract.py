from datetime import UTC, datetime

import httpx
import pytest
from pydantic import ValidationError

from app.contracts import export
from app.events import Event, event_id
from app.ingest import feeds, store
from app.main import app, footprint_scale

GETS = [
    "/api/health",
    "/api/sources/health",
    "/api/outages",
    "/api/outages?status=active",
    "/api/grids/gb/stress",
    "/api/cells?level=1",
    "/api/areas/risk",
    "/api/triage?limit=1",
    "/api/agent/decisions",
    "/api/agent/grades",
    "/api/audit/verify",
    "/api/audit/checkpoints",
]


@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest.mark.anyio
@pytest.mark.parametrize("path", GETS)
async def test_every_get_endpoint_serves_its_contract(client, path):
    r = await client.get(path)
    assert r.status_code == 200, r.text


@pytest.fixture
async def seeded(db_factory, superuser):
    superuser.run("TRUNCATE outage, outage_version, freq_reading RESTART IDENTITY CASCADE")
    now = datetime.now(UTC)
    rows = [feeds.Outage("ukpn", "A", "active", now, customers=40, postcodes=["N1 3LD", "N1 3LE"], lat=51.54, lon=-0.09),
            feeds.Outage("ssen", "B", "restored", now, restored_at=now, customers=5000)]
    db = db_factory("bn_ingest")
    await store.sync(db, "ukpn", rows[:1], now)
    await store.sync(db, "ssen", rows[1:], now)
    superuser.run("INSERT INTO freq_reading VALUES ('gb', now() - interval '1 min', 49.95), ('gb', now(), 49.70)")


@pytest.mark.anyio
async def test_outages_come_from_the_database(client, seeded):
    body = (await client.get("/api/outages")).json()
    assert {o["source"] for o in body} == {"ukpn", "ssen"}
    active = (await client.get("/api/outages?status=active")).json()
    assert len(active) == 1 and active[0]["postcode_count"] == 2 and active[0]["scale"] == "street"
    assert active[0]["centroid"] == [51.54, -0.09] and active[0]["cell_l1"].startswith("L1:")
    assert (await client.get("/api/outages?status=bogus")).status_code == 422


@pytest.mark.anyio
async def test_stress_uses_latest_reading(client, seeded):
    body = (await client.get("/api/grids/gb/stress")).json()
    assert body["hz"] == 49.7 and body["state"] == "STRESSED" and body["label"] == "LIVE"


@pytest.mark.anyio
async def test_health_without_workers(client):
    assert (await client.get("/api/health")).json()["db"] is True
    assert (await client.get("/api/sources/health")).json()["sources"] == []


def test_footprint_scale():
    assert [footprint_scale(c) for c in (None, 1, 100, 101, 2000, 2001)] ==         ["unresolved", "street", "street", "area", "area", "region"]


@pytest.mark.anyio
async def test_unknown_grid_404(client):
    assert (await client.get("/api/grids/xx/stress")).status_code == 404


@pytest.mark.anyio
async def test_limits_validated(client):
    assert (await client.get("/api/triage?limit=0")).status_code == 422
    assert (await client.get("/api/cells?level=4")).status_code == 422


@pytest.mark.anyio
async def test_cap_alert_404_until_approved(client):
    assert (await client.get("/api/alerts/cap/00000000-0000-4000-8000-000000000000")).status_code == 404
    assert (await client.get("/api/alerts/cap/abc")).status_code == 422


def test_event_envelope_validates_and_rejects():
    now = datetime.now(UTC).isoformat()
    ok = {
        "event_id": event_id("ukpn", "INC1", "h"),
        "source": "ukpn",
        "observed_at": now,
        "received_at": now,
        "label": "LIVE",
        "payload": {"kind": "dno_fault", "outage_id": 1, "source_ref": "INC1", "status": "active", "postcodes": ["N1 3LD"]},
    }
    assert Event.model_validate(ok).payload.kind == "dno_fault"
    with pytest.raises(ValidationError):
        Event.model_validate({**ok, "payload": {"kind": "sms_reply", "patient_ref": "P-1", "code": "3"}})
    with pytest.raises(ValidationError):
        Event.model_validate({**ok, "event_id": "not-hex"})


def test_event_id_is_deterministic():
    assert event_id("a", "b") == event_id("a", "b") != event_id("a", "c")
    assert len(event_id("x")) == 32


def test_contract_export(tmp_path):
    export(tmp_path)
    openapi = (tmp_path / "openapi.yaml").read_text()
    assert "/api/triage" in openapi and "/api/me/home" in openapi
    assert '"discriminator"' in (tmp_path / "events.schema.json").read_text()
