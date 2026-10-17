from datetime import UTC, datetime

import httpx
import pytest
from pydantic import ValidationError

from app.contracts import export
from app.events import Event, event_id
from app.main import app

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
    "/api/me/home",
    "/api/audit/verify",
]


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.anyio
@pytest.mark.parametrize("path", GETS)
async def test_every_get_endpoint_serves_its_contract(client, path):
    r = await client.get(path)
    assert r.status_code == 200, r.text


@pytest.mark.anyio
async def test_status_filter(client):
    r = await client.get("/api/outages?status=restored")
    assert {o["status"] for o in r.json()} == {"restored"}
    assert (await client.get("/api/outages?status=bogus")).status_code == 422


@pytest.mark.anyio
async def test_triage_two_houses_story(client):
    items = (await client.get("/api/triage")).json()["items"]
    concentrator, ventilator = items[0], items[1]
    assert concentrator["escalate"] and concentrator["q_used"] == "q90"
    assert not ventilator["escalate"]
    assert concentrator["outage_id"] == ventilator["outage_id"]


@pytest.mark.anyio
async def test_patient_never_gets_eta(client):
    body = (await client.get("/api/me/home")).json()
    assert "eta" not in str(body).lower()


@pytest.mark.anyio
async def test_unknown_grid_404(client):
    assert (await client.get("/api/grids/xx/stress")).status_code == 404


@pytest.mark.anyio
async def test_limits_validated(client):
    assert (await client.get("/api/triage?limit=0")).status_code == 422
    assert (await client.get("/api/cells?level=4")).status_code == 422


@pytest.mark.anyio
async def test_approve_and_reject(client):
    r = await client.post("/api/decisions/abc/approve", json={"approve": False})
    assert r.json()["state"] == "rejected"
    r = await client.post("/api/decisions/abc/approve", json={"approve": True, "note": "ok"})
    assert r.json() == {"decision_id": "abc", "state": "approved", "audit_seq": 42}


@pytest.mark.anyio
async def test_login_rejects_until_auth_ships(client):
    assert (await client.post("/api/auth/login", json={"login": "x", "passphrase": "y"})).status_code == 401
    assert (await client.post("/api/auth/logout")).status_code == 204
    assert (await client.get("/api/alerts/cap/abc")).status_code == 404


def test_event_envelope_validates_and_rejects():
    now = datetime.now(UTC).isoformat()
    ok = {
        "event_id": event_id("ukpn", "INC1", "h"),
        "source": "ukpn",
        "observed_at": now,
        "received_at": now,
        "label": "LIVE",
        "payload": {"kind": "dno_fault", "source_ref": "INC1", "status": "active", "postcodes": ["N1 3LD"]},
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
