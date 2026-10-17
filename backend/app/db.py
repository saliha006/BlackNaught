"""pg8000 bridged into asyncio.

pg8000 allows one thread per connection, so every connection owns a single-thread executor and all
calls on it run there. asyncio.to_thread is deliberately not used: its shared pool could put one
connection on two threads.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pg8000.native
from pg8000.exceptions import DatabaseError, InterfaceError

from .config import read_secret, settings

log = logging.getLogger(__name__)

ROLE_SECRETS = {
    "bn_migrator": "db_migrator_pw",
    "bn_ingest": "db_ingest_pw",
    "bn_api": "db_api_pw",
    "bn_agent": "db_agent_pw",
    "postgres": "pg_super_pw",
}
STATEMENT_TIMEOUT = {"bn_agent": "30s", "bn_migrator": "0"}
# SQLSTATE class 08 = connection exception
_CONNECTION_CLASS = "08"


def connect(role: str, database: str | None = None) -> pg8000.native.Connection:
    cfg = settings()
    conn = pg8000.native.Connection(
        user=role,
        password=read_secret(ROLE_SECRETS[role]),
        host=cfg.db_host,
        port=cfg.db_port,
        database=database or cfg.db_name,
        timeout=10,
        application_name=f"blacknaught:{role}",
    )
    conn.run("SET TimeZone = 'UTC'")
    conn.run(f"SET statement_timeout = '{STATEMENT_TIMEOUT.get(role, '5s')}'")
    if role != "postgres":
        conn.run("SET search_path = bn, pg_temp")
    return conn


def _is_connection_error(exc: Exception) -> bool:
    # a killed backend surfaces as a raw socket error (ConnectionResetError), not InterfaceError
    if isinstance(exc, (InterfaceError, OSError)):
        return True
    code = exc.args[0].get("C", "") if exc.args and isinstance(exc.args[0], dict) else ""
    return code.startswith(_CONNECTION_CLASS)


class Db:
    """One pg8000 connection, used only from its own thread."""

    def __init__(self, role: str, database: str | None = None):
        self.role = role
        self.database = database
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"db-{role}")
        self._conn: pg8000.native.Connection | None = None

    def _run_sync(self, sql: str, params: dict[str, Any], retry: bool) -> list[list[Any]]:
        if self._conn is None:
            self._conn = connect(self.role, self.database)
        try:
            return self._conn.run(sql, **params) or []
        except (InterfaceError, DatabaseError, OSError) as exc:
            if not _is_connection_error(exc):
                raise
            log.warning("db %s connection lost, reconnecting", self.role)
            self._conn = None
            if not retry:
                raise
            return self._run_sync(sql, params, retry=False)

    async def run(self, sql: str, idempotent: bool = True, **params: Any) -> list[list[Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._run_sync, sql, params, idempotent)

    async def rows(self, sql: str, **params: Any) -> list[dict[str, Any]]:
        """Rows as dicts keyed by column name."""
        loop = asyncio.get_running_loop()

        def fetch() -> list[dict[str, Any]]:
            data = self._run_sync(sql, params, retry=True)
            cols = [c["name"] for c in self._conn.columns or []]
            return [dict(zip(cols, r)) for r in data]

        return await loop.run_in_executor(self._executor, fetch)

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._executor.submit(self._conn.close).result()
            except (InterfaceError, OSError):
                pass  # socket already gone; nothing left to release
            self._conn = None
        self._executor.shutdown(wait=True)
