"""Tamper-evident audit chain: append, checkpoint, verify.

The chain itself is computed inside Postgres (audit_append, SECURITY DEFINER, advisory lock), so a second writer
can't fork it. Bodies are canonical JSON stored as text, so verification re-hashes the exact bytes. Checkpoints
(every 500 rows or 5 min) are signed by Ahmed's ML-DSA signer when it's configured; the signing key never lives
in this process. Until then a checkpoint is stored unsigned and verify reports sig_ok = null instead of guessing.
"""
import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from .db import Db

CHECKPOINT_ROWS = 500
CHECKPOINT_EVERY = timedelta(minutes=5)
VERIFY_PAGE = 5000
GENESIS = bytes(32)


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str)


async def append(db: Db, kind: str, actor: str, ref: str | None, data: dict[str, Any],
                 at: datetime | None = None) -> int:
    body = canonical({"at": (at or datetime.now(UTC)).isoformat(), "actor": actor, "kind": kind, "ref": ref,
                      "data": data})
    return (await db.run("SELECT audit_append(:body)", body=body))[0][0]


class HttpSigner:
    """Client for Ahmed's signer container (contract: BLACKNAUGHT.md §B12)."""

    def __init__(self, client: httpx.AsyncClient, url: str):
        self.client = client
        self.url = url.rstrip("/")

    async def sign(self, payload: bytes) -> dict[str, str]:
        resp = await self.client.post(f"{self.url}/sign", json={
            "purpose": "audit_checkpoint", "payload_b64": base64.b64encode(payload).decode()})
        resp.raise_for_status()
        return resp.json()

    async def verify(self, payload: bytes, sig_b64: str) -> bool:
        resp = await self.client.post(f"{self.url}/verify", json={
            "payload_b64": base64.b64encode(payload).decode(), "sig_b64": sig_b64})
        resp.raise_for_status()
        return bool(resp.json()["ok"])


def checkpoint_payload(seq: int, head: bytes, at: datetime) -> bytes:
    return canonical({"seq": seq, "head": head.hex(), "at": at.isoformat()}).encode()


class Checkpointer:
    def __init__(self, db: Db, signer: HttpSigner | None):
        self.db = db
        self.signer = signer

    async def maybe_checkpoint(self, now: datetime | None = None) -> int | None:
        now = now or datetime.now(UTC)
        head = await self.db.rows("SELECT seq, hash FROM audit_log ORDER BY seq DESC LIMIT 1")
        if not head:
            return None
        last = await self.db.rows("SELECT seq, at FROM audit_checkpoint ORDER BY seq DESC LIMIT 1")
        seq, digest = head[0]["seq"], bytes(head[0]["hash"])
        if last and (last[0]["seq"] == seq or (seq - last[0]["seq"] < CHECKPOINT_ROWS
                                              and now - last[0]["at"] < CHECKPOINT_EVERY)):
            return None
        signed: dict[str, str] = {}
        if self.signer is not None:
            signed = await self.signer.sign(checkpoint_payload(seq, digest, now))
        await self.db.run(
            "INSERT INTO audit_checkpoint (seq, head, at, alg, key_id, sig_b64) VALUES (:s, :h, :at, :alg, :k, :sig)",
            s=seq, h=digest, at=now, alg=signed.get("alg"), k=signed.get("key_id"), sig=signed.get("sig_b64"),
        )
        await append(self.db, "audit_checkpoint", "system", str(seq),
                     {"head": digest.hex(), "signed": bool(signed)}, now)
        return seq


async def verify(db: Db, signer: HttpSigner | None) -> dict[str, Any]:
    started = datetime.now(UTC)
    prev, expected_seq, rows, hashes = GENESIS, 1, 0, {}
    checkpoint = await db.rows("SELECT seq, head, at, sig_b64 FROM v_audit_checkpoint ORDER BY seq DESC LIMIT 1")
    want = checkpoint[0]["seq"] if checkpoint else None
    first_bad, reason = None, None
    while first_bad is None:
        page = await db.rows("SELECT seq, body, prev_hash, hash FROM v_audit WHERE seq >= :s ORDER BY seq LIMIT :n",
                             s=expected_seq, n=VERIFY_PAGE)
        if not page:
            break
        for r in page:
            rows += 1
            recomputed = hashlib.sha256(prev + r["body"].encode()).digest()
            if r["seq"] != expected_seq:
                first_bad, reason = expected_seq, "missing_seq"
            elif bytes(r["prev_hash"]) != prev:
                first_bad, reason = r["seq"], "broken_link"
            elif bytes(r["hash"]) != recomputed:
                first_bad, reason = r["seq"], "hash_mismatch"
            if first_bad is not None:
                break
            if r["seq"] == want:
                hashes[want] = recomputed
            prev, expected_seq = recomputed, expected_seq + 1
    last_checkpoint = None
    if checkpoint:
        c = checkpoint[0]
        head = bytes(c["head"])
        sig_ok = None
        if signer is not None and c["sig_b64"]:
            sig_ok = await signer.verify(checkpoint_payload(c["seq"], head, c["at"]), c["sig_b64"])
        last_checkpoint = {"seq": c["seq"], "sig_ok": sig_ok, "head_matches": hashes.get(c["seq"]) == head}
        if first_bad is None and not last_checkpoint["head_matches"]:
            first_bad, reason = c["seq"], "checkpoint_head_mismatch"
    return {
        "ok": first_bad is None and (last_checkpoint is None or last_checkpoint["sig_ok"] is not False),
        "rows": rows,
        "first_bad_seq": first_bad,
        "reason": reason,
        "last_checkpoint": last_checkpoint,
        "took_ms": int((datetime.now(UTC) - started).total_seconds() * 1000),
    }
