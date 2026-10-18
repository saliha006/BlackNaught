"""Sensor state from heartbeats. Heartbeats stay in memory; only state changes are stored.

Silence becomes 'dropout' (unknown), never 'down': silence alone never means an outage.
A last gasp is the only sensor signal that says power was lost.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

HEARTBEAT_S = 60
DROPOUT_AFTER = timedelta(seconds=3 * HEARTBEAT_S)
RESTART_GRACE = timedelta(minutes=2)


@dataclass(slots=True)
class SensorState:
    cell_l1: str
    label: str
    last_seen: datetime
    state: str


Transition = tuple[str, datetime, str, str, str]  # sensor_transition row


class SensorTracker:
    def __init__(self, started_at: datetime):
        self.sensors: dict[str, SensorState] = {}
        self.grace_until = started_at + RESTART_GRACE

    def _set(self, sensor_id: str, cell: str, label: str, at: datetime, state: str) -> Transition | None:
        current = self.sensors.get(sensor_id)
        if current is None:
            self.sensors[sensor_id] = SensorState(cell, label, at, state)
            return (sensor_id, at, state, cell, label)
        current.last_seen = max(current.last_seen, at)
        if current.state == state:
            return None
        current.state = state
        return (sensor_id, at, state, cell, label)

    def heartbeat(self, sensor_id: str, cell: str, label: str, at: datetime) -> Transition | None:
        return self._set(sensor_id, cell, label, at, "up")

    def last_gasp(self, sensor_id: str, cell: str, label: str, at: datetime) -> Transition | None:
        return self._set(sensor_id, cell, label, at, "last_gasp")

    def sweep(self, now: datetime) -> list[Transition]:
        """Mark sensors silent for 3 heartbeats as dropout (skipped during the restart grace window)."""
        if now < self.grace_until:
            return []
        out = []
        for sensor_id, s in self.sensors.items():
            if s.state == "up" and now - s.last_seen > DROPOUT_AFTER:
                s.state = "dropout"
                out.append((sensor_id, now, "dropout", s.cell_l1, s.label))
        return out

    def cell_counts(self) -> dict[str, dict[str, int]]:
        """Per cell: how many sensors are in each state (the combiner's quorum input)."""
        counts: dict[str, dict[str, int]] = {}
        for s in self.sensors.values():
            cell = counts.setdefault(s.cell_l1, {})
            cell[s.state] = cell.get(s.state, 0) + 1
        return counts
