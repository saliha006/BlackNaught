import random
import sys
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app import auth, home
from app.config import read_secret
from app.ingest import feeds, store
from app.main import app
from app.seed import households, keys, patient_row
from app.seed import main as seed_main
from conftest import TEST_DB, reset_schema


@pytest.fixture
async def homes(superuser, db_factory, tmp_path):
    reset_schema()
    now = datetime.now(UTC)
    dek, bidx = keys()
    rng = random.Random(9)
    inside = patient_row(rng, "N1 3LD", 51.545, -0.089, dek, bidx, "o2_concentrator", 3.0, False)
    outside = patient_row(rng, "SW1A 1AA", 51.501, -0.141, dek, bidx, "ventilator", 15.0, False)
    for row in (inside, outside):
        superuser.run("INSERT INTO patient (patient_id, household_id, cell_l1, postcode_bidx, contact_ct, device,"
                      " reserve_h, other_backup, severity) VALUES (CAST(:id AS uuid), CAST(:household AS uuid), :cell,"
                      " :bidx, :contact, :device, :reserve, :backup, :severity)", **row)
    for login, row in (("home-a", inside), ("home-b", outside)):
        superuser.run("INSERT INTO principal (login, role, household_id, pw_hash) VALUES (:l, 'household',"
                      " CAST(:h AS uuid), :p)", l=login, h=row["household"], p=auth._hasher.hash(f"{login}-pass-1234"))
    await store.sync(db_factory("bn_ingest"), "ukpn", [feeds.Outage(
        "ukpn", "INCD-1", "active", now - timedelta(hours=1), postcodes=["N1 3LD"], lat=51.545, lon=-0.089)], now)
    superuser.run("INSERT INTO freq_reading VALUES ('gb', now(), 50.01)")
    return bidx


@pytest.mark.anyio
async def test_household_in_a_fault_gets_actions_and_a_reserve_clock(homes, db_factory):
    body = await home.view(db_factory("bn_api"), "home-a", homes)
    assert body["power"] == "off" and body["reserve"]["device"] == "o2_concentrator"
    assert body["reserve"]["hours_left"] == pytest.approx(2.0, abs=0.05)
    assert "cylinder" in body["next_action"] and body["grid_context"]["hz"] == 50.01
    assert "eta" not in str(body).lower()


@pytest.mark.anyio
async def test_household_outside_any_fault_has_power(homes, db_factory):
    body = await home.view(db_factory("bn_api"), "home-b", homes)
    assert body["power"] == "on" and body["reserve"]["ends_at"] is None


@pytest.mark.anyio
async def test_operator_and_unknown_logins_see_nothing(homes, db_factory):
    api = db_factory("bn_api")
    assert await home.view(api, "operator", homes) is None
    assert await home.view(api, "nobody", homes) is None


@pytest.mark.anyio
async def test_endpoint_is_household_only_and_ignores_ids(homes):
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            assert (await c.get("/api/me/home")).status_code == 401
            await c.post("/api/auth/login", json={"login": "home-b", "passphrase": "home-b-pass-1234"})
            mine = (await c.get("/api/me/home?household=home-a&login=home-a")).json()
            assert mine["household"] == "home-b" and mine["power"] == "on"  # query params can't switch household
        auth.bootstrap(TEST_DB)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            await c.post("/api/auth/login", json={"login": "operator", "passphrase": read_secret("operator_pw")})
            assert (await c.get("/api/me/home")).status_code == 403


@pytest.mark.anyio
async def test_seed_creates_household_logins(homes, superuser, tmp_path, monkeypatch, capsys):
    out = tmp_path / "secrets" / "households.txt"
    assert households(superuser, 2, out) == 2
    lines = out.read_text().split()
    assert lines[0] == "home-1" and len(lines) == 4
    assert oct(out.stat().st_mode)[-3:] == "600"
    monkeypatch.setattr(sys, "argv", ["seed", "--per-outage", "0", "--households", "1", "--households-out",
                                      str(tmp_path / "h.txt"), "--database", TEST_DB])
    seed_main()
    assert "household logins: 1" in capsys.readouterr().out
