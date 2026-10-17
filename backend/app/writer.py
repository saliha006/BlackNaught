"""Batching writer: one round trip per table per batch instead of one per row.

Rows are queued as (table, tuple). Every 250 ms or 500 rows the writer flushes each table with
INSERT ... SELECT FROM unnest(...) ON CONFLICT. A failing batch is split in half until the bad
row is isolated, so one bad row can't sink the rest.
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from pg8000.exceptions import DatabaseError

from .db import Db

log = logging.getLogger(__name__)

FLUSH_SECONDS = 0.25
FLUSH_ROWS = 500
LAG_WARN = 20_000


@dataclass(frozen=True)
class TableSpec:
    columns: tuple[str, ...]
    types: tuple[str, ...]
    conflict: str

    def sql(self, table: str) -> str:
        args = ", ".join(f":c{i}::{t}[]" for i, t in enumerate(self.types))
        return f"INSERT INTO {table} ({', '.join(self.columns)}) SELECT * FROM unnest({args}) {self.conflict}"


TABLES: dict[str, TableSpec] = {
    "freq_reading": TableSpec(("grid", "measured_at", "hz"), ("text", "timestamptz", "numeric"), "ON CONFLICT DO NOTHING"),
    "sensor_transition": TableSpec(
        ("sensor_id", "at", "state", "cell_l1", "label"),
        ("text", "timestamptz", "text", "text", "text"),
        "ON CONFLICT DO NOTHING",
    ),
    "event_counts": TableSpec(
        ("minute", "kind", "n", "dropped"),
        ("timestamptz", "text", "int", "int"),
        "ON CONFLICT (minute, kind) DO UPDATE SET n = event_counts.n + EXCLUDED.n,"
        " dropped = event_counts.dropped + EXCLUDED.dropped",
    ),
    "source_poll": TableSpec(
        ("source", "polled_at", "ok", "http_status", "n_records", "latency_ms", "error"),
        ("text", "timestamptz", "boolean", "int", "int", "int", "text"),
        "ON CONFLICT DO NOTHING",
    ),
}


class Writer:
    def __init__(self, db: Db):
        self.db = db
        self.queue: asyncio.Queue[tuple[str, tuple[Any, ...]] | None] = asyncio.Queue()
        self.rejected = 0

    def put(self, table: str, row: tuple[Any, ...]) -> None:
        if table not in TABLES:
            raise KeyError(table)
        self.queue.put_nowait((table, row))

    @property
    def lag(self) -> int:
        return self.queue.qsize()

    async def _write(self, table: str, rows: list[tuple[Any, ...]]) -> None:
        spec = TABLES[table]
        params = {f"c{i}": list(col) for i, col in enumerate(zip(*rows))}
        try:
            await self.db.run(spec.sql(table), **params)
        except DatabaseError:
            if len(rows) == 1:
                self.rejected += 1
                log.exception("writer rejected one %s row: %r", table, rows[0])
                return
            mid = len(rows) // 2
            await self._write(table, rows[:mid])
            await self._write(table, rows[mid:])

    async def flush(self, batch: list[tuple[str, tuple[Any, ...]]]) -> None:
        by_table: dict[str, list[tuple[Any, ...]]] = {}
        for table, row in batch:
            by_table.setdefault(table, []).append(row)
        for table, rows in by_table.items():
            await self._write(table, rows)

    async def run(self) -> None:
        """Drain until a None sentinel arrives (Queue.shutdown needs 3.13; the image is 3.12)."""
        loop = asyncio.get_running_loop()
        while True:
            first = await self.queue.get()
            if first is None:
                return
            batch = [first]
            deadline = loop.time() + FLUSH_SECONDS
            stop = False
            while len(batch) < FLUSH_ROWS:
                timeout = deadline - loop.time()
                if timeout <= 0:
                    break
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout)
                except TimeoutError:
                    break
                if item is None:
                    stop = True
                    break
                batch.append(item)
            await self.flush(batch)
            if self.lag > LAG_WARN:
                log.warning("writer lagging: %d rows queued", self.lag)
            if stop:
                return

    def stop(self) -> None:
        self.queue.put_nowait(None)
