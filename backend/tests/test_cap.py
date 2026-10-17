from datetime import UTC, datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx
import pytest
import xmlschema

from app import auth, cap, decisions
from app.ingest import feeds, store
from app.config import read_secret
from app.main import app
from conftest import TEST_DB, reset_schema

SCHEMA = xmlschema.XMLSchema(str(Path(__file__).parent / "data" / "CAP-v1.2.xsd"))
NS = {"c": cap.NS}
SENT = datetime(2026, 10, 18, 2, 10, tzinfo=UTC)
POSTCODE_POINTS = [(51.5456, -0.0890), (51.5445, -0.0891), (51.5430, -0.0870), (51.5460, -0.0860)]


def build(points=POSTCODE_POINTS, **kw):
    return cap.build("d-1", "exercise@blacknaught.invalid", "operator", points, "N1", severe=True, confirmed=True,
                     sent=SENT, **kw)


def test_alert_validates_against_the_oasis_schema():
    xml = build()
    SCHEMA.validate(xml)
    root = ET.fromstring(xml)
    assert root.find("c:status", NS).text == "Exercise"
    assert root.find("c:info/c:severity", NS).text == "Severe"
    assert root.find("c:info/c:certainty", NS).text == "Observed"


def test_times_never_use_z():
    root = ET.fromstring(build())
    assert root.find("c:sent", NS).text == "2026-10-18T02:10:00-00:00"
    assert root.find("c:info/c:expires", NS).text == "2026-10-18T08:10:00-00:00"


def test_polygon_is_a_closed_hull():
    ring = ET.fromstring(build()).find("c:info/c:area/c:polygon", NS).text.split()
    assert ring[0] == ring[-1] and len(ring) >= 4
    hull = cap.convex_hull(POSTCODE_POINTS + [(51.5450, -0.0880)])  # an interior point never makes the hull
    assert (51.5450, -0.0880) not in hull


def test_one_or_two_points_fall_back_to_a_circle():
    xml = build(points=[(51.5, -0.1), (51.5, -0.1)])
    SCHEMA.validate(xml)
    assert ET.fromstring(xml).find("c:info/c:area/c:circle", NS).text == "51.50000,-0.10000 1.0"
    with pytest.raises(ValueError):
        build(points=[])


def test_headline_is_capped_and_area_is_outward_codes_only():
    root = ET.fromstring(build(headline="x" * 300))
    assert len(root.find("c:info/c:headline", NS).text) == 140
    assert cap.area_desc(["N1 3LD", "N1 3LE", "E1 6AN"]) == "E1, N1"
    assert cap.area_desc([]) == "the affected area"


@pytest.fixture
async def world(superuser, db_factory):
    reset_schema()
    auth.bootstrap(TEST_DB)
    now = datetime.now(UTC)
    superuser.run("INSERT INTO postcode_geo VALUES ('N1 3LD', 51.5456, -0.0890, 'E', 'Islington', true, now()),"
                  " ('N1 3LE', 51.5445, -0.0891, 'E', 'Islington', true, now()),"
                  " ('N1 3NW', 51.5430, -0.0870, 'E', 'Islington', true, now())")
    await store.sync(db_factory("bn_ingest"), "ukpn", [feeds.Outage(
        "ukpn", "INCD-1", "active", now - timedelta(hours=1), postcodes=["N1 3LD", "N1 3LE", "N1 3NW"],
        lat=51.545, lon=-0.089)], now)
    agent = db_factory("bn_agent")
    cap_id, _ = await decisions.create(agent, "draft_cap_alert", {"outage_id": 1, "headline": "Power cut in N1"},
                                       ["2 no-backup patients inside"])
    other_id, _ = await decisions.create(agent, "escalate", {"patient_ref": "P-1"}, ["q75 > reserve"])
    return cap_id, other_id


@pytest.mark.anyio
async def test_cap_exported_once_on_approval(world, superuser):
    cap_id, other_id = world
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            assert (await c.get(f"/api/alerts/cap/{cap_id}")).status_code == 403  # drafted, not approved
            assert (await c.get(f"/api/alerts/cap/{other_id}")).status_code == 404  # not a CAP decision
            await c.post("/api/auth/login", json={"login": "operator", "passphrase": read_secret("operator_pw")})
            assert (await c.post(f"/api/decisions/{cap_id}/approve", json={"approve": True})).status_code == 200
            r = await c.get(f"/api/alerts/cap/{cap_id}")
            assert r.status_code == 200 and r.headers["content-type"].startswith("application/cap+xml")
            SCHEMA.validate(r.text)
            root = ET.fromstring(r.text)
            assert root.find("c:info/c:headline", NS).text == "Power cut in N1"
            assert root.find("c:info/c:area/c:areaDesc", NS).text == "N1"
            assert "SIMULATED" in root.find("c:note", NS).text
            await c.post(f"/api/decisions/{other_id}/approve", json={"approve": True})
            assert (await c.get(f"/api/alerts/cap/{other_id}")).status_code == 404
    assert superuser.run("SELECT count(*) FROM cap_alert")[0][0] == 1
    assert superuser.run("SELECT count(*) FROM audit_log WHERE kind = 'cap_export'")[0][0] == 1


@pytest.mark.anyio
async def test_cap_store_refuses_unapproved(world, db_factory):
    cap_id, _ = world
    api = db_factory("bn_api")
    stored = await api.run("SELECT cap_store(CAST(:id AS uuid), 'x', '<a/>', NULL)", id=cap_id)
    assert stored == [[None]]
    assert await decisions.export_cap(api, cap_id, "operator", None) is None
