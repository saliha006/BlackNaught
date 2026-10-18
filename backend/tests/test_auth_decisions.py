import httpx
import pytest

from app import auth, decisions
from app.main import app
from conftest import TEST_DB, reset_schema


@pytest.fixture
def fresh(superuser):
    reset_schema()
    auth.bootstrap(TEST_DB)
    yield


@pytest.fixture
async def client(fresh):
    async with app.router.lifespan_context(app):
        app.state.login_limiter = auth.RateLimiter(limit=1000)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            yield c


def operator_pw():
    from app.config import read_secret
    return read_secret("operator_pw")


async def log_in(c, pw=None):
    return await c.post("/api/auth/login", json={"login": "operator", "passphrase": pw or operator_pw()})


@pytest.mark.anyio
async def test_login_sets_a_hardened_cookie_and_logout_clears_it(client):
    r = await log_in(client)
    assert r.status_code == 200 and r.json() == {"role": "operator"}
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie
    assert (await client.post("/api/auth/logout")).status_code == 204
    assert (await client.post("/api/decisions/00000000-0000-4000-8000-000000000000/approve",
                              json={"approve": True})).status_code == 401


@pytest.mark.anyio
async def test_wrong_password_and_unknown_login_look_the_same(client):
    assert (await log_in(client, "nope")).status_code == 401
    r = await client.post("/api/auth/login", json={"login": "ghost", "passphrase": "x"})
    assert r.status_code == 401 and r.json() == {"detail": "invalid credentials"}


@pytest.mark.anyio
async def test_five_failures_lock_the_account(client, superuser):
    for _ in range(5):
        await log_in(client, "wrong")
    assert (await log_in(client)).status_code == 401  # right password, still locked
    superuser.run("UPDATE principal SET locked_until = now() - interval '1 second'")
    assert (await log_in(client)).status_code == 200


@pytest.mark.anyio
async def test_login_attempts_rate_limited_per_client(fresh):
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            codes = [(await log_in(c, "x")).status_code for _ in range(auth.LOGIN_ATTEMPTS_PER_MINUTE + 1)]
    assert codes[-1] == 429 and set(codes[:-1]) == {401}


def test_rate_limiter_window():
    rl = auth.RateLimiter(limit=2, window_s=60)
    assert rl.allow("a", 0) and rl.allow("a", 1) and not rl.allow("a", 2)
    assert rl.allow("b", 2) and rl.allow("a", 61.5)


@pytest.mark.anyio
async def test_idle_session_expires(client, superuser):
    await log_in(client)
    superuser.run("UPDATE session SET last_seen = now() - interval '31 minutes'")
    r = await client.post("/api/decisions/00000000-0000-4000-8000-000000000000/approve", json={"approve": True})
    assert r.status_code == 401


@pytest.mark.anyio
async def test_household_cannot_approve(client, superuser):
    superuser.run("INSERT INTO principal (login, role, pw_hash) VALUES ('home-ama', 'household', :h)",
                  h=auth._hasher.hash("household-pass-123"))
    await client.post("/api/auth/login", json={"login": "home-ama", "passphrase": "household-pass-123"})
    r = await client.post("/api/decisions/00000000-0000-4000-8000-000000000000/approve", json={"approve": True})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_escalation_waits_for_a_human_and_is_audited(client, db_factory):
    agent = db_factory("bn_agent")
    esc_id, esc_state = await decisions.create(agent, "escalate", {"patient_ref": "P-1"}, ["q75 8.3 h > 3.0 h"])
    visit_id, visit_state = await decisions.create(agent, "assign_visit", {"worker": "w1"}, ["knapsack"])
    assert (esc_state, visit_state) == ("awaiting_approval", "auto_done")
    await log_in(client)
    r = await client.post(f"/api/decisions/{esc_id}/approve", json={"approve": True, "note": "ambulance informed"})
    assert r.status_code == 200 and r.json()["state"] == "approved" and r.json()["audit_seq"] > 0
    again = await client.post(f"/api/decisions/{esc_id}/approve", json={"approve": False})
    assert again.status_code == 409
    auto = await client.post(f"/api/decisions/{visit_id}/approve", json={"approve": True})
    assert auto.status_code == 409  # auto-done decisions can't be re-approved
    feed = (await client.get("/api/agent/decisions")).json()
    assert {d["id"] for d in feed} == {esc_id, visit_id}
    assert next(d for d in feed if d["id"] == esc_id)["state"] == "approved"
    kinds = [k for (k,) in await agent.run("SELECT kind FROM audit_log ORDER BY seq")]
    assert kinds.count("decision") == 2 and kinds.count("approval") == 3 and "login" in kinds
    assert (await client.get("/api/audit/verify")).json()["ok"]


@pytest.mark.anyio
async def test_a_waiting_decision_stays_in_the_feed_however_many_come_after(client, db_factory):
    agent = db_factory("bn_agent")
    waiting, _ = await decisions.create(agent, "draft_cap_alert", {"outage_id": 1}, ["3 patients in this outage"])
    for i in range(3):
        await decisions.create(agent, "write_sitrep", {"text": f"round {i}"}, [])
    feed = (await client.get("/api/agent/decisions?limit=2")).json()
    assert feed[0]["id"] == waiting  # older than the sitreps, but an operator still has to see it
    assert feed[1]["tool"] == "write_sitrep"


@pytest.mark.anyio
async def test_approve_rejects_non_uuid(client):
    await log_in(client)
    assert (await client.post("/api/decisions/not-a-uuid/approve", json={"approve": True})).status_code == 422


def test_bootstrap_refuses_short_password(monkeypatch):
    monkeypatch.setattr(auth, "read_secret", lambda name: "short")
    with pytest.raises(SystemExit, match="at least"):
        auth.bootstrap(TEST_DB)
