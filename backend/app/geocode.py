"""UK postcode normalisation and a Postgres-backed postcodes.io cache."""
import asyncio
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from .db import Db

BULK_URL = "https://api.postcodes.io/postcodes"
BULK_MAX = 100  # postcodes.io limit per bulk call
VALID_TTL = timedelta(days=30)
INVALID_TTL = timedelta(days=1)
_PATTERN = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}$")


class GeocodeError(RuntimeError):
    """postcodes.io answered with something other than its documented bulk shape."""


def normalise(value: str) -> str | None:
    """'n13ld' -> 'N1 3LD'; anything that isn't a full unit postcode -> None."""
    compact = re.sub(r"\s+", "", value or "").upper()
    if len(compact) < 5:
        return None
    candidate = f"{compact[:-3]} {compact[-3:]}"
    return candidate if _PATTERN.match(candidate) else None


class Geocoder:
    def __init__(self, db: Db, client: httpx.AsyncClient):
        self.db = db
        self.client = client
        self._limit = asyncio.Semaphore(2)

    async def _cached(self, postcodes: list[str], now: datetime) -> dict[str, dict[str, Any]]:
        rows = await self.db.rows(
            "SELECT postcode, lat, lon, lsoa, admin_district, valid, fetched_at FROM postcode_geo"
            " WHERE postcode = ANY(:pcs)",
            pcs=postcodes,
        )
        fresh = {}
        for r in rows:
            ttl = VALID_TTL if r["valid"] else INVALID_TTL
            if now - r["fetched_at"] < ttl:
                fresh[r["postcode"]] = r
        return fresh

    async def _fetch(self, chunk: list[str]) -> list[dict[str, Any]]:
        async with self._limit:
            resp = await self.client.post(BULK_URL, json={"postcodes": chunk})
        resp.raise_for_status()
        body = resp.json()
        if not isinstance(body, dict) or not isinstance(body.get("result"), list):
            raise GeocodeError(f"unexpected bulk response: {str(body)[:200]}")
        out = []
        for item in body["result"]:
            hit = item["result"]
            out.append({
                "postcode": item["query"],
                "lat": hit["latitude"] if hit else None,
                "lon": hit["longitude"] if hit else None,
                "lsoa": hit.get("lsoa") if hit else None,
                "admin_district": hit.get("admin_district") if hit else None,
                "valid": hit is not None,
            })
        return out

    async def lookup(self, postcodes: list[str]) -> dict[str, dict[str, Any]]:
        """Cache first; misses fetched in bulk and stored. Invalid postcodes come back with valid=False."""
        wanted = sorted(set(postcodes))
        now = datetime.now(UTC)
        found = await self._cached(wanted, now)
        missing = [p for p in wanted if p not in found]
        chunks = [missing[i:i + BULK_MAX] for i in range(0, len(missing), BULK_MAX)]
        for rows in await asyncio.gather(*(self._fetch(c) for c in chunks)):
            if not rows:
                continue
            await self.db.run(
                "INSERT INTO postcode_geo (postcode, lat, lon, lsoa, admin_district, valid, fetched_at)"
                " SELECT * FROM unnest(:pc::text[], :lat::float8[], :lon::float8[], :lsoa::text[], :ad::text[],"
                " :valid::bool[], :at::timestamptz[])"
                " ON CONFLICT (postcode) DO UPDATE SET lat = EXCLUDED.lat, lon = EXCLUDED.lon, lsoa = EXCLUDED.lsoa,"
                " admin_district = EXCLUDED.admin_district, valid = EXCLUDED.valid, fetched_at = EXCLUDED.fetched_at",
                pc=[r["postcode"] for r in rows],
                lat=[r["lat"] for r in rows],
                lon=[r["lon"] for r in rows],
                lsoa=[r["lsoa"] for r in rows],
                ad=[r["admin_district"] for r in rows],
                valid=[r["valid"] for r in rows],
                at=[now] * len(rows),
            )
            found.update({r["postcode"]: r for r in rows})
        return found
