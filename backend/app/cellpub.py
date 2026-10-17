"""Publishes the suppressed patient map every 15 minutes."""
import asyncio
import logging
from datetime import UTC, datetime, timedelta

from .db import Db
from .suppression import publish

log = logging.getLogger(__name__)

EVERY = timedelta(minutes=15)
KEEP = timedelta(hours=2)


async def publish_once(db: Db, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    rows = await db.run("SELECT cell_l1, count(*) FROM patient GROUP BY cell_l1")
    published = publish({cell: n for cell, n in rows})
    if published:
        await db.run(
            "INSERT INTO cell_snapshot (published_at, cell_id, level, patients)"
            " SELECT CAST(:at AS timestamptz), * FROM unnest(:c::text[], :l::int2[], :p::int[])",
            at=now, c=list(published), l=[int(c[1]) for c in published], p=list(published.values()),
        )
    await db.run("DELETE FROM cell_snapshot WHERE published_at < :cut", cut=now - KEEP)
    return len(published)


async def run(db: Db) -> None:
    while True:
        try:
            await publish_once(db)
        except Exception:
            # a failed publish keeps the previous map, which is safe: it was already suppressed
            log.exception("cell publish failed")
        await asyncio.sleep(EVERY.total_seconds())
