"""Polling loop with bounded retries, Retry-After, failure backoff and per-source health."""
import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import httpx

from ..health import DOWN_AFTER_FAILURES, SourceHealth

log = logging.getLogger(__name__)

ATTEMPTS = 3
RETRY_CAP_S = 30
RETRY_AFTER_CAP_S = 300
MAX_INTERVAL_S = 600
POLL_TIMEOUT_S = 45
TIMEOUT = httpx.Timeout(connect=5, read=15, write=5, pool=5)

Sleep = Callable[[float], Awaitable[None]]


def new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=TIMEOUT,
        headers={"User-Agent": "blacknaught-datathon/0.1"},
        limits=httpx.Limits(max_connections=10),
    )


async def get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None,
                   sleep: Sleep = asyncio.sleep) -> Any:
    """GET with up to 3 attempts on timeouts, connect errors and 5xx (full jitter); 429 honours Retry-After."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            resp = await client.get(url, params=params)
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt == ATTEMPTS:
                raise
            await sleep(random.uniform(0.5, 1.0) * min(RETRY_CAP_S, 2**attempt))
            continue
        if resp.status_code == 429 and attempt < ATTEMPTS:
            await sleep(min(RETRY_AFTER_CAP_S, float(resp.headers.get("Retry-After", 2**attempt))))
            continue
        if resp.status_code >= 500 and attempt < ATTEMPTS:
            await sleep(random.uniform(0.5, 1.0) * min(RETRY_CAP_S, 2**attempt))
            continue
        resp.raise_for_status()
        return resp.json()
    raise AssertionError("unreachable")


async def get_paged(client: httpx.AsyncClient, url: str, sleep: Sleep = asyncio.sleep) -> list[dict[str, Any]]:
    """OpenDataSoft v2.1 records: limit is capped at 100, so page by offset until total_count."""
    records: list[dict[str, Any]] = []
    while True:
        page = await get_json(client, url, {"limit": 100, "offset": len(records)}, sleep)
        records.extend(page["results"])
        if not page["results"] or len(records) >= page["total_count"]:
            return records


class Poller:
    """Runs `poll()` every interval; `poll` returns (records, degraded)."""

    def __init__(self, health: SourceHealth, poll: Callable[[], Awaitable[tuple[int, bool]]],
                 sleep: Sleep = asyncio.sleep, on_status: Callable[[SourceHealth], None] | None = None):
        self.health = health
        self.poll = poll
        self.sleep = sleep
        self.on_status = on_status
        self._last_status: str | None = None

    async def poll_once(self) -> bool:
        now = datetime.now(UTC)
        try:
            async with asyncio.timeout(POLL_TIMEOUT_S):
                records, degraded = await self.poll()
        except (httpx.HTTPError, TimeoutError, KeyError, ValueError) as exc:
            self.health.failure(now, f"{type(exc).__name__}: {exc}")
            log.warning("%s poll failed: %s", self.health.source, exc)
            self._report(now)
            return False
        self.health.success(now, records, degraded)
        self._report(now)
        return True

    def _report(self, now: datetime) -> None:
        status = self.health.status(now)
        if self.on_status is not None and status != self._last_status:
            self.on_status(self.health)
        self._last_status = status

    def next_interval(self) -> float:
        base = self.health.interval_s
        if self.health.consecutive_failures >= DOWN_AFTER_FAILURES:
            base = min(MAX_INTERVAL_S, base * 2 ** (self.health.consecutive_failures - DOWN_AFTER_FAILURES + 1))
        return base * random.uniform(0.9, 1.1)

    async def run(self) -> None:
        while True:
            await self.poll_once()
            await self.sleep(self.next_interval())
