"""Country-level internet-outage signal from IODA, as wide-area evidence that a grid-scale event is under way.

Our own detector runs on IODA's raw ping-slash24 signal (its curated event list missed Sri Lanka's 2025 collapse):
- a dip is the latest value below 0.9 × the median of the previous 12 windows (2 h at IODA's 10-min step),
  held for 2 windows in a row. Sri Lanka's 9 Feb 2025 blackout dipped to 0.858 at 06:20 UTC (measured);
- a dip seen in 3 or more countries at once is IODA's own measurement failing, not a blackout (PRD §5.5), so
  control countries are watched only to catch that.
"""
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from .poller import get_json

RAW_URL = "https://api.ioda.inetintel.cc.gatech.edu/v2/signals/raw/country/{country}"
DATASOURCE = "ping-slash24"
TARGETS = ("GB", "GH", "LK")
CONTROLS = ("FR", "DE", "US")
DIP_RATIO = 0.9
BASELINE_WINDOWS = 12
PERSIST = 2
ARTIFACT_COUNTRIES = 3
LOOKBACK = timedelta(hours=3)


@dataclass(frozen=True)
class Reading:
    country: str
    at: datetime
    ratio: float | None


def latest_ratios(values: list[float | None]) -> list[float | None]:
    """Ratio of each of the last PERSIST windows to the median of the BASELINE_WINDOWS before it."""
    if len(values) < BASELINE_WINDOWS + PERSIST:
        return []
    out: list[float | None] = []
    for i in range(len(values) - PERSIST, len(values)):
        base = [v for v in values[i - BASELINE_WINDOWS:i] if v]
        out.append(values[i] / statistics.median(base) if base and values[i] is not None else None)
    return out


def is_dip(ratios: list[float | None]) -> bool:
    return len(ratios) == PERSIST and all(r is not None and r < DIP_RATIO for r in ratios)


async def fetch(client: httpx.AsyncClient, country: str, now: datetime) -> Reading:
    start = int((now - LOOKBACK).timestamp())
    doc = await get_json(client, RAW_URL.format(country=country),
                         {"from": start, "until": int(now.timestamp()), "datasource": DATASOURCE})
    series = next((s for s in doc["data"][0] if s["datasource"] == DATASOURCE), None)
    if series is None or not series["values"]:
        return Reading(country, now, None)
    ratios = latest_ratios(series["values"])
    at = datetime.fromtimestamp(series["from"] + (len(series["values"]) - 1) * series["step"], UTC)
    return Reading(country, at, ratios[-1] if is_dip(ratios) else None)


def confirmed_dips(readings: list[Reading]) -> list[Reading]:
    """Target countries with a dip, unless enough countries dipped together to blame the measurement."""
    dipping = [r for r in readings if r.ratio is not None]
    if len(dipping) >= ARTIFACT_COUNTRIES:
        return []
    return [r for r in dipping if r.country in TARGETS]
