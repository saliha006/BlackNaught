import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app import audit
from app.main import app
from conftest import reset_schema

T0 = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)


@pytest.fixture
def fresh(superuser):
    """The append-only trigger blocks cleanup by design, so each audit test gets a rebuilt schema."""
    reset_schema()
    yield


class FakeSigner(audit.HttpSigner):
    def __init__(self):
        self.signed = []

    async def sign(self, payload, purpose="audit_checkpoint"):
        self.signed.append(payload)
        digest = hashlib.sha256(payload).digest()
        return {"alg": "ML-DSA-65", "key_id": "k1", "sig_b64": base64.b64encode(digest).decode()}

    async def verify(self, payload, sig_b64):
        return base64.b64decode(sig_b64) == hashlib.sha256(payload).digest()


def test_canonical_is_stable():
    assert audit.canonical({"b": 1, "a": "é"}) == '{"a":"é","b":1}'
    with pytest.raises(ValueError):
        audit.canonical({"x": float("nan")})


@pytest.mark.anyio
async def test_chain_of_1000_verifies(fresh, db_factory):
    agent = db_factory("bn_agent")
    for i in range(1000):
        await audit.append(agent, "tool_call", "agent", f"d{i}", {"i": i}, T0)
    result = await audit.verify(db_factory("bn_api"), None)
    assert result["ok"] and result["rows"] == 1000 and result["first_bad_seq"] is None


@pytest.mark.anyio
async def test_tampered_row_is_located(fresh, db_factory, superuser):
    agent = db_factory("bn_agent")
    for i in range(20):
        await audit.append(agent, "approval", "operator", f"d{i}", {"approve": True}, T0)
    superuser.run("ALTER TABLE audit_log DISABLE TRIGGER audit_no_upd_del")
    superuser.run("UPDATE audit_log SET body = replace(body, 'true', 'false') WHERE seq = 7")
    superuser.run("ALTER TABLE audit_log ENABLE TRIGGER audit_no_upd_del")
    result = await audit.verify(db_factory("bn_api"), None)
    assert not result["ok"] and (result["first_bad_seq"], result["reason"]) == (7, "hash_mismatch")


@pytest.mark.anyio
async def test_full_chain_rewrite_caught_by_signed_checkpoint(fresh, db_factory, superuser):
    agent = db_factory("bn_agent")
    signer = FakeSigner()
    for i in range(10):
        await audit.append(agent, "approval", "operator", f"d{i}", {"approve": True}, T0)
    assert await audit.Checkpointer(agent, signer).maybe_checkpoint(T0) == 10
    # a superuser rewrites row 3 and recomputes every later hash, so the chain on its own still looks valid
    superuser.run("ALTER TABLE audit_log DISABLE TRIGGER audit_no_upd_del")
    rows = superuser.run("SELECT seq, body FROM audit_log ORDER BY seq")
    prev = bytes(32)
    for seq, body in rows:
        if seq == 3:
            body = body.replace("true", "false")
        digest = hashlib.sha256(prev + body.encode()).digest()
        superuser.run("UPDATE audit_log SET body = :b, prev_hash = :p, hash = :h WHERE seq = :s",
                      b=body, p=prev, h=digest, s=seq)
        prev = digest
    superuser.run("ALTER TABLE audit_log ENABLE TRIGGER audit_no_upd_del")
    result = await audit.verify(db_factory("bn_api"), signer)
    assert not result["ok"] and result["reason"] == "checkpoint_head_mismatch"
    assert result["last_checkpoint"]["sig_ok"] is True and not result["last_checkpoint"]["head_matches"]


@pytest.mark.anyio
async def test_checkpoint_cadence(fresh, db_factory):
    agent = db_factory("bn_agent")
    cp = audit.Checkpointer(agent, None)
    assert await cp.maybe_checkpoint(T0) is None  # empty chain
    await audit.append(agent, "x", "a", None, {}, T0)
    assert await cp.maybe_checkpoint(T0) == 1
    await audit.append(agent, "x", "a", None, {}, T0)
    assert await cp.maybe_checkpoint(T0 + timedelta(minutes=1)) is None  # too soon and too few rows
    assert await cp.maybe_checkpoint(T0 + audit.CHECKPOINT_EVERY + timedelta(minutes=1)) is not None
    unsigned = (await agent.rows("SELECT alg, sig_b64 FROM audit_checkpoint ORDER BY seq LIMIT 1"))[0]
    assert unsigned == {"alg": None, "sig_b64": None}
    result = await audit.verify(db_factory("bn_api"), None)
    assert result["ok"] and result["last_checkpoint"]["sig_ok"] is None


@pytest.mark.anyio
async def test_http_signer_contract():
    seen = []

    def handler(request):
        seen.append((request.url.path, request.headers.get("authorization"), json.loads(request.content)))
        if request.url.path == "/sign":
            return httpx.Response(200, json={"alg": "ML-DSA-65", "key_id": "k", "sig_b64": "c2ln"})
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        signer = audit.HttpSigner(c, "http://signer:8100/", "tok")
        assert (await signer.sign(b"abc"))["alg"] == "ML-DSA-65"
        await signer.sign(b"abc", "cap_alert")
        assert await signer.verify(b"abc", "c2ln")
    assert seen[0] == ("/sign", "Bearer tok", {"purpose": "audit_checkpoint", "payload_b64": "YWJj"})
    assert seen[1][2]["purpose"] == "cap_alert"
    assert seen[2][:2] == ("/verify", None)


@pytest.mark.anyio
async def test_checkpoints_api_gives_the_signed_bytes_and_leaves_unsigned_ones_out(fresh, db_factory):
    agent = db_factory("bn_agent")
    await audit.append(agent, "x", "a", None, {}, T0)
    assert await audit.Checkpointer(agent, None).maybe_checkpoint(T0) is not None  # unsigned
    signer = FakeSigner()
    for minutes in (10, 20, 30):
        await audit.append(agent, "x", "a", None, {}, T0)
        assert await audit.Checkpointer(agent, signer).maybe_checkpoint(T0 + timedelta(minutes=minutes)) is not None
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            signed = (await c.get("/api/audit/checkpoints")).json()
            page = (await c.get("/api/audit/checkpoints", params={"after": signed[0]["seq"], "limit": 1})).json()
            assert (await c.get("/api/audit/checkpoints", params={"limit": 501})).status_code == 422
    assert len(signed) == 3 and all(c["alg"] == "ML-DSA-65" and c["key_id"] == "k1" for c in signed)
    for c in signed:
        assert c["payload"].encode() in signer.signed  # byte for byte what the signer was given
        assert await signer.verify(c["payload"].encode(), c["sig_b64"])
        fields = json.loads(c["payload"])
        assert (fields["seq"], fields["head"]) == (c["seq"], c["head"])
        assert datetime.fromisoformat(fields["at"]) == datetime.fromisoformat(c["at"])
    assert [c["seq"] for c in page] == [signed[1]["seq"]]


@pytest.mark.anyio
async def test_verify_api(fresh, db_factory):
    await audit.append(db_factory("bn_agent"), "x", "a", None, {}, T0)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            body = (await c.get("/api/audit/verify")).json()
    assert body["ok"] and body["rows"] == 1
