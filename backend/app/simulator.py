"""F2 sensor simulator (Ahmed): fuse-box sensors on real fault footprints, every event labelled SIMULATED.

Each real DNO fault with geocoded postcodes gets fuse-box sensors at synthetic homes and anchors in each of its unit
postcodes, plus controls in a neighbouring cell. Sensors heartbeat every 60 s. An affected sensor sends a last gasp at
the fault's real start and stays silent until the real restoration. The noise follows the brief: about 74% uptime
(comms dropouts that last minutes), a few sensors wrongly fitted behind a backup supply, and partial faults where only
one home in three loses power. Events go on the app's bus as source "sim", the path a real sensor's would take.
"""
import asyncio
import logging
import random
import uuid
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .bus import EventBus
from .cells import cell_id
from .db import Db
from .events import event_id
from .sensors import HEARTBEAT_S

log = logging.getLogger(__name__)

MAX_SENSORS = 5000
HOMES_PER_POSTCODE = 3
ANCHORS_PER_POSTCODE = 2
CONTROLS_PER_FAULT = 2
CONTROL_OFFSET_DEG = 0.02  # about 2 km north, so the controls watch a neighbouring cell
# comms as a two-state chain per minute: online drops 5% of the time, offline recovers 15% → 75% uptime, ~7 min gaps
DROP_P, RECOVER_P = 0.05, 0.15
BEHIND_BACKUP_P = 0.08
PARTIAL_FAULT_P = 0.25
RESTORED_KEEP = timedelta(hours=2)  # a restored fault keeps its sensors this long, so the return is seen
# each sensor reports in its own 5 s slot of the minute, the way a real fleet's clocks drift apart, rather than the
# whole fleet in one burst (which also made the control room's 5 s events/s read 0 most of the time)
SLOTS = 12

FAULTS = """
SELECT outage_id, status, started_at, postcodes FROM outage
WHERE source IN ('ukpn', 'npg', 'ssen') AND cardinality(postcodes) > 0 AND (status = 'active' OR restored_at > :cut)
"""


@dataclass
class Sensor:
    sensor_id: str
    type: str
    household_id: str | None
    cell_l1: str
    outage_id: int
    affected: bool  # on the faulted supply: never for controls, one home in three in a partial fault
    behind_backup: bool
    online: bool = True
    gasped: bool = False

    @property
    def slot(self) -> int:
        return zlib.crc32(self.sensor_id.encode()) % SLOTS


def footprint(outage_id: int, spots: list[tuple[str, float, float]]) -> list[Sensor]:
    """The sensors for one fault. Seeded by the fault, so a restart rebuilds the same fleet with the same ids."""
    traits = random.Random(outage_id)
    partial = traits.random() < PARTIAL_FAULT_P
    out = []
    for postcode, lat, lon in spots:
        cell, tag = cell_id(lat, lon), f"{outage_id}-{postcode.replace(' ', '')}"
        out += [Sensor(f"h-{tag}-{i}", "home", str(uuid.UUID(int=traits.getrandbits(128))), cell, outage_id,
                       not partial or i == 0, traits.random() < BEHIND_BACKUP_P) for i in range(HOMES_PER_POSTCODE)]
        out += [Sensor(f"a-{tag}-{i}", "anchor", None, cell, outage_id, not partial or i == 0, False)
                for i in range(ANCHORS_PER_POSTCODE)]
    _, lat, lon = spots[0]
    control_cell = cell_id(lat + CONTROL_OFFSET_DEG, lon)
    out += [Sensor(f"c-{outage_id}-{i}", "control", None, control_cell, outage_id, False, False)
            for i in range(CONTROLS_PER_FAULT)]
    return out


class Simulator:
    def __init__(self, db: Db, bus: EventBus, rng: random.Random | None = None):
        self.db = db
        self.bus = bus
        self.rng = rng or random.Random()
        self.sensors: dict[str, Sensor] = {}
        self.placed: set[int] = set()

    async def place(self, faults: list[dict]) -> None:
        new = [f for f in faults if f["outage_id"] not in self.placed]
        if not new:
            return
        geo = {r["postcode"]: (r["lat"], r["lon"]) for r in await self.db.rows(
            "SELECT postcode, lat, lon FROM postcode_geo WHERE valid AND postcode = ANY(:p)",
            p=sorted({p for f in new for p in f["postcodes"]}))}
        fleet = []
        for f in new:
            self.placed.add(f["outage_id"])
            spots = [(p, *geo[p]) for p in f["postcodes"] if p in geo]
            if spots:
                fleet += footprint(f["outage_id"], spots)
        fleet = fleet[:max(0, MAX_SENSORS - len(self.sensors))]
        if not fleet:
            return
        await self.db.run(
            "INSERT INTO sensor (sensor_id, type, household_id, cell_l1) SELECT * FROM unnest(:id::text[],"
            " :type::text[], :household::uuid[], :cell::text[]) ON CONFLICT DO NOTHING",
            id=[s.sensor_id for s in fleet], type=[s.type for s in fleet],
            household=[s.household_id for s in fleet], cell=[s.cell_l1 for s in fleet])
        self.sensors.update((s.sensor_id, s) for s in fleet)

    async def emit(self, kind: str, s: Sensor, at: datetime, now: datetime) -> None:
        await self.bus.publish({
            "event_id": event_id("sim", s.sensor_id, kind, at.isoformat()), "source": "sim", "observed_at": at,
            "received_at": now, "label": "SIMULATED",
            "payload": {"kind": kind, "sensor_id": s.sensor_id, "cell_l1": s.cell_l1},
        })

    async def tick(self, now: datetime, slot: int | None = None) -> int:
        """One round for the sensors in this slot of the minute (every sensor when slot is None); returns the number of
        events sent."""
        faults = {f["outage_id"]: f for f in await self.db.rows(FAULTS, cut=now - RESTORED_KEEP)}
        await self.place(list(faults.values()))
        sent = 0
        for s in list(self.sensors.values()):
            if slot is not None and s.slot != slot:
                continue
            fault = faults.get(s.outage_id)
            if fault is None:  # restored long enough ago, or gone from the feed: the sensor is retired
                del self.sensors[s.sensor_id]
                continue
            if s.affected and not s.behind_backup and fault["status"] == "active":
                if not s.gasped:
                    await self.emit("last_gasp", s, fault["started_at"], now)
                    s.gasped = True
                    sent += 1
                continue
            s.gasped = False
            s.online = self.rng.random() >= DROP_P if s.online else self.rng.random() < RECOVER_P
            if s.online:
                await self.emit("heartbeat", s, now, now)
                sent += 1
        return sent

    async def run(self) -> None:
        slot = 0
        while True:
            await asyncio.sleep(HEARTBEAT_S / SLOTS)
            try:
                await self.tick(datetime.now(UTC), slot)
            except Exception:
                # one bad round must not stop the fleet; the next one rebuilds from the same footprints
                log.exception("simulator tick failed")
            slot = (slot + 1) % SLOTS
