"""Outage upserts with content-hash versioning. A record missing from 2 successful polls is 'vanished'."""
import json
from datetime import datetime
from typing import Any

from ..db import Db
from .feeds import Outage

VANISH_AFTER_MISSES = 2

_INSERT = """
INSERT INTO outage (source, source_ref, status, started_at, restored_at, restored_explicit, first_seen, last_seen,
  customers, priority_customers, postcodes, lat, lon, cell_l1, feeder, label, content_hash)
VALUES (:source, :ref, :status, :started, :restored, :explicit, :now, :now, :customers, :priority, :postcodes,
  :lat, :lon, :cell, CAST(:feeder AS jsonb), 'LIVE', :hash)
RETURNING outage_id
"""
_UPDATE = """
UPDATE outage SET status = :status, started_at = :started, restored_at = :restored, restored_explicit = :explicit,
  last_seen = :now, missed_polls = 0, customers = :customers, priority_customers = :priority,
  postcodes = :postcodes, lat = :lat, lon = :lon, cell_l1 = :cell, feeder = CAST(:feeder AS jsonb),
  content_hash = :hash, version = version + 1
WHERE outage_id = :id
RETURNING version
"""


def _params(o: Outage, now: datetime) -> dict[str, Any]:
    return {
        "status": o.status, "started": o.started_at, "restored": o.restored_at, "explicit": o.restored_explicit,
        "now": now, "customers": o.customers, "priority": o.priority_customers, "postcodes": o.postcodes,
        "lat": o.lat, "lon": o.lon, "cell": o.cell_l1, "feeder": json.dumps(o.feeder), "hash": o.content_hash,
    }


async def _version(db: Db, outage_id: int, version: int, now: datetime, raw: dict[str, Any]) -> None:
    await db.run(
        "INSERT INTO outage_version (outage_id, version, observed_at, raw) VALUES (:id, :v, :now, CAST(:raw AS jsonb))",
        id=outage_id, v=version, now=now, raw=json.dumps(raw, default=str),
    )


async def sync(db: Db, source: str, outages: list[Outage], now: datetime) -> list[tuple[int, Outage]]:
    """Apply one successful poll. Returns (outage_id, outage) for every new or changed outage."""
    existing = {
        r["source_ref"]: r
        for r in await db.rows(
            "SELECT outage_id, source_ref, status, content_hash, missed_polls FROM outage WHERE source = :s", s=source
        )
    }
    changed = []
    for o in outages:
        row = existing.get(o.source_ref)
        if row is None:
            outage_id = (await db.run(_INSERT, source=source, ref=o.source_ref, **_params(o, now)))[0][0]
            await _version(db, outage_id, 1, now, o.raw)
            changed.append((outage_id, o))
        elif bytes(row["content_hash"]) != o.content_hash or row["status"] == "vanished":
            version = (await db.run(_UPDATE, id=row["outage_id"], **_params(o, now)))[0][0]
            await _version(db, row["outage_id"], version, now, o.raw)
            changed.append((row["outage_id"], o))
        else:
            await db.run("UPDATE outage SET last_seen = :now, missed_polls = 0 WHERE outage_id = :id",
                         now=now, id=row["outage_id"])
    seen = {o.source_ref for o in outages}
    missing = [r["outage_id"] for ref, r in existing.items()
               if ref not in seen and r["status"] in ("active", "planned")]
    if missing:
        await db.run(
            "UPDATE outage SET missed_polls = missed_polls + 1,"
            " status = CASE WHEN missed_polls + 1 >= :n THEN 'vanished' ELSE status END"
            " WHERE outage_id = ANY(:ids)",
            n=VANISH_AFTER_MISSES, ids=missing,
        )
    return changed


async def reject(db: Db, source: str, source_ref: str | None, error: str, raw: dict[str, Any]) -> None:
    await db.run(
        "INSERT INTO ingest_reject (source, source_ref, error, raw) VALUES (:s, :r, :e, CAST(:raw AS jsonb))",
        s=source, r=source_ref, e=error[:500], raw=json.dumps(raw, default=str),
    )
