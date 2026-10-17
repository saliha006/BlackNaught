"""Every source's timestamp format, parsed to aware UTC in one place."""
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")


def uk_local(value: str) -> datetime:
    """UKPN sends naive Europe/London wall-clock strings, e.g. '2026-10-15T00:49:22'."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC)
    return parsed.replace(tzinfo=LONDON, fold=0).astimezone(UTC)


def uk_wall_clock(value: str) -> datetime:
    """NPg labels UK local times as +00:00 (an updatedate of 22:05+00:00 arrived at 21:09 UTC in BST),
    so the offset is discarded and the wall-clock time read as Europe/London."""
    return uk_local(datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None).isoformat())


def iso(value: str) -> datetime:
    """ISO-8601 with an offset: '+00:00', '+0000' or 'Z'."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp without offset: {value!r}")
    return parsed.astimezone(UTC)


def epoch(value: float) -> datetime:
    return datetime.fromtimestamp(value, UTC)


def cap(value: datetime) -> str:
    """CAP 1.2 forbids 'Z'; UTC is written -00:00."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S") + "-00:00"
