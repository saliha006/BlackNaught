"""Server-side sessions for the operator (and later households).

Opaque 256-bit tokens; only their SHA-256 is stored, so a database leak can't be replayed as a login. Cookie is
HttpOnly + SameSite=Strict, scoped to /api, Secure behind TLS. Passwords are argon2id (argon2-cffi is in the image).
Bootstrap the operator: python -m app.auth bootstrap   (reads the operator_pw compose secret)
"""
import hashlib
import secrets
import sys
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from .config import read_secret
from .db import Db, connect

COOKIE = "bn_session"
MIN_OPERATOR_PW = 16
LOGIN_ATTEMPTS_PER_MINUTE = 10
_hasher = PasswordHasher()


@dataclass(frozen=True)
class Principal:
    login: str
    role: str


def token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


class RateLimiter:
    """Per-IP sliding window, so one client can't hammer the login endpoint across many accounts."""

    def __init__(self, limit: int = LOGIN_ATTEMPTS_PER_MINUTE, window_s: float = 60):
        self.limit, self.window_s = limit, window_s
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        hits = self.hits[key]
        while hits and now - hits[0] > self.window_s:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


async def login(db: Db, name: str, passphrase: str) -> tuple[Principal, str] | None:
    rows = await db.rows("SELECT role, pw_hash, locked_until FROM auth_principal(:l)", l=name)
    if not rows:
        _hasher.hash(passphrase)  # spend the same time as a real check, so unknown logins aren't distinguishable
        return None
    row = rows[0]
    locked = row["locked_until"] is not None and row["locked_until"] > datetime.now(UTC)
    try:
        ok = not locked and _hasher.verify(row["pw_hash"], passphrase)
    except (VerifyMismatchError, VerificationError):
        ok = False
    await db.run("SELECT auth_result(:l, :ok)", l=name, ok=ok)
    if not ok:
        return None
    token = secrets.token_urlsafe(32)
    await db.run("SELECT session_create(:t, :l)", t=token_hash(token), l=name)
    return Principal(name, row["role"]), token


async def resolve(db: Db, token: str | None) -> Principal | None:
    if not token:
        return None
    rows = await db.rows("SELECT login, role FROM session_get(:t)", t=token_hash(token))
    return Principal(rows[0]["login"], rows[0]["role"]) if rows else None


async def logout(db: Db, token: str | None) -> None:
    if token:
        await db.run("SELECT session_delete(:t)", t=token_hash(token))


def bootstrap(database: str | None = None) -> None:
    password = read_secret("operator_pw")
    if len(password) < MIN_OPERATOR_PW:
        raise SystemExit(f"operator_pw must be at least {MIN_OPERATOR_PW} characters")
    conn = connect("bn_migrator", database)
    try:
        conn.run("SET ROLE bn_owner")
        conn.run("INSERT INTO bn.principal (login, role, pw_hash) VALUES ('operator', 'operator', :h)"
                 " ON CONFLICT (login) DO UPDATE SET pw_hash = EXCLUDED.pw_hash, failed = 0, locked_until = NULL",
                 h=_hasher.hash(password))
    finally:
        conn.close()


if __name__ == "__main__" and sys.argv[1:2] == ["bootstrap"]:
    bootstrap(sys.argv[2] if len(sys.argv) > 2 else None)
    print("operator login ready")
