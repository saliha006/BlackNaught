"""In-process event bus: `critical` never drops (real backpressure), `bulk` drops its oldest item.

The consumer always drains critical first, then up to BULK_PER_TURN bulk events.
"""
import asyncio
from collections import Counter
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

CRITICAL_MAX = 50_000
BULK_MAX = 10_000
BULK_PER_TURN = 500
CRITICAL_KINDS = frozenset({"last_gasp", "dno_fault", "sms_reply", "source_state"})

Handler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self.critical: asyncio.Queue[dict[str, Any]] = asyncio.Queue(CRITICAL_MAX)
        self.bulk: asyncio.Queue[dict[str, Any]] = asyncio.Queue(BULK_MAX)
        self.seen: Counter[str] = Counter()
        self.dropped: Counter[str] = Counter()
        self._wake = asyncio.Event()

    async def publish(self, event: dict[str, Any]) -> None:
        kind = event["payload"]["kind"]
        if kind in CRITICAL_KINDS:
            await self.critical.put(event)
        else:
            if self.bulk.full():
                oldest = self.bulk.get_nowait()
                self.dropped[oldest["payload"]["kind"]] += 1
            self.bulk.put_nowait(event)
        self._wake.set()

    def take_counts(self) -> tuple[Counter[str], Counter[str]]:
        """Counts since the last call (for the per-minute event_counts row)."""
        seen, dropped = self.seen, self.dropped
        self.seen, self.dropped = Counter(), Counter()
        return seen, dropped

    async def consume(self, handle: Handler) -> None:
        while True:
            if self.critical.empty() and self.bulk.empty():
                self._wake.clear()
                await self._wake.wait()
            while not self.critical.empty():
                await self._dispatch(self.critical.get_nowait(), handle)
            for _ in range(min(BULK_PER_TURN, self.bulk.qsize())):
                await self._dispatch(self.bulk.get_nowait(), handle)

    async def _dispatch(self, event: dict[str, Any], handle: Handler) -> None:
        self.seen[event["payload"]["kind"]] += 1
        await handle(event)


def minute_of(at: datetime) -> datetime:
    return at.astimezone(UTC).replace(second=0, microsecond=0)
