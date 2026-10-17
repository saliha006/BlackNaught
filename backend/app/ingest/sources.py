"""One poll function per source: fetch → validate per record → store → notify."""
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ..db import Db
from ..geocode import GeocodeError, Geocoder
from ..writer import Writer
from . import feeds, store
from .poller import get_json, get_paged

log = logging.getLogger(__name__)

DEGRADED_SHARE = 0.5
ELEXON_OVERLAP = timedelta(seconds=60)
ELEXON_FIRST_WINDOW = timedelta(minutes=10)

OnChanged = Callable[[str, list[tuple[int, feeds.Outage]]], Awaitable[None]]


def split_valid(records: list[Any], parse: Callable[[list[Any]], list[feeds.Outage]]) -> tuple[list[Any], list[tuple[Any, str]]]:
    """Per-record validation, so one malformed record is rejected instead of failing the poll."""
    valid, rejected = [], []
    for record in records:
        try:
            parse([record])
        except (KeyError, ValueError, TypeError) as exc:
            rejected.append((record, f"{type(exc).__name__}: {exc}"))
        else:
            valid.append(record)
    return valid, rejected


DNO = {
    "ukpn": (feeds.UKPN_URL, True, feeds.parse_ukpn, "incidentreference"),
    "npg": (feeds.NPG_URL, True, feeds.parse_npg, "reference"),
    "ssen": (feeds.SSEN_URL, False, lambda rs: feeds.parse_ssen({"Faults": rs}), "reference"),
}


def dno_poll(source: str, client: httpx.AsyncClient, db: Db, geocoder: Geocoder,
             on_changed: OnChanged) -> Callable[[], Awaitable[tuple[int, bool]]]:
    url, paged, parse, ref_key = DNO[source]

    async def poll() -> tuple[int, bool]:
        if paged:
            records = await get_paged(client, url)
        else:
            records = (await get_json(client, url)).get("Faults", [])
        valid, rejected = split_valid(records, parse)
        for record, error in rejected:
            await store.reject(db, source, record.get(ref_key) if isinstance(record, dict) else None, error, record)
        outages = parse(valid)
        postcodes = [p for o in outages if o.status == "active" for p in o.postcodes]
        if postcodes:
            try:
                await geocoder.lookup(postcodes)
            except (httpx.HTTPError, GeocodeError) as exc:
                # cells and CAP polygons fall back to the feed's own coordinates
                log.warning("geocoding failed for %s: %s", source, exc)
        changed = await store.sync(db, source, outages, datetime.now(UTC))
        if changed:
            await on_changed(source, changed)
        return len(records), bool(records) and len(rejected) / len(records) > DEGRADED_SHARE

    return poll


def elexon_poll(client: httpx.AsyncClient, writer: Writer) -> Callable[[], Awaitable[tuple[int, bool]]]:
    last_seen: list[datetime] = []

    async def poll() -> tuple[int, bool]:
        now = datetime.now(UTC)
        start = last_seen[0] - ELEXON_OVERLAP if last_seen else now - ELEXON_FIRST_WINDOW
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        # without from/to Elexon returns a whole day
        document = await get_json(client, feeds.ELEXON_URL,
                                  {"from": start.strftime(fmt), "to": now.strftime(fmt), "format": "json"})
        readings = feeds.parse_elexon(document)
        for measured_at, hz in readings:
            writer.put("freq_reading", ("gb", measured_at, hz))
        if readings:
            last_seen[:] = [max(m for m, _ in readings)]
        return len(readings), False

    return poll
