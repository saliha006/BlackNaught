"""Per-source freshness: ok → stale (>3× interval) → down (>6×, or 5 failures in a row); degraded on schema drift."""
from dataclasses import dataclass
from datetime import datetime

DOWN_AFTER_FAILURES = 5


@dataclass
class SourceHealth:
    source: str
    interval_s: int
    label: str = "LIVE"
    last_attempt: datetime | None = None
    last_success: datetime | None = None
    consecutive_failures: int = 0
    last_error: str | None = None
    records_last: int | None = None
    degraded: bool = False

    def staleness_s(self, now: datetime) -> int | None:
        return None if self.last_success is None else int((now - self.last_success).total_seconds())

    def status(self, now: datetime) -> str:
        staleness = self.staleness_s(now)
        if self.consecutive_failures >= DOWN_AFTER_FAILURES or (staleness or 0) > 6 * self.interval_s:
            return "down"
        if self.degraded:
            return "degraded"
        if staleness is None or staleness > 3 * self.interval_s:
            return "stale"
        return "ok"

    def success(self, now: datetime, records: int, degraded: bool) -> None:
        self.last_attempt = self.last_success = now
        self.consecutive_failures = 0
        self.last_error = None
        self.records_last = records
        self.degraded = degraded

    def failure(self, now: datetime, error: str) -> None:
        self.last_attempt = now
        self.consecutive_failures += 1
        self.last_error = error[:300]

    def as_dict(self, now: datetime) -> dict:
        return {
            "source": self.source,
            "status": self.status(now),
            "interval_s": self.interval_s,
            "staleness_s": self.staleness_s(now),
            "records_last": self.records_last,
            "consecutive_failures": self.consecutive_failures,
            "label": self.label,
        }
