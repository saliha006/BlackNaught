"""Accra replay (Ahmed, brief task 11): real sensors from nLine GridWatch, played into the live sensor path.

The data is one week (1-7 June 2021) of plug-in sensors in Accra reporting voltage and power state (CC BY-NC 4.0).
It is read once with the probe's loader and reduced to its 2-minute bins: a bin with any unpowered reading counts as
unpowered, which also merges the seconds-long flickers in the raw stream. Each bin plays as one event: a heartbeat
while the sensor has power, a last gasp when it loses it, and silence while it's off or not reporting. Events go on
the bus as source "accra_replay", label REPLAY, next to the GB simulator's SIMULATED ones.
"""
import asyncio
import logging
import multiprocessing
import os
from array import array
from bisect import bisect_left
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .bus import EventBus
from .cells import cell_id
from .db import Db
from .events import event_id
from .sensors import HEARTBEAT_S

log = logging.getLogger(__name__)

ACCRA_DIR = Path(os.environ.get("BN_ACCRA_DIR", "/data/raw/accra"))
# the data carries no coordinates, so the whole fleet sits in one cell at Accra's centre
ACCRA_CELL = cell_id(5.6037, -0.1870)
# 10x plays a real Accra day in 2.4 h. The fleet loses power about 42 times a real hour (7,030 times in the week's
# 2-minute bins), so a few outages show every wall minute, and each sensor's 2-minute report lands every 12 s: well
# inside the tracker's 3-minute dropout window, so only real reporting gaps of half an hour or more show as dropouts.
SPEED = 10
TICK_S = 5  # 50 real seconds at 10x, shorter than a bin, so a normal round never merges a sensor's bins


@dataclass(frozen=True)
class Week:
    sites: list[str]  # sensor ids; the bins' site numbers index into this
    minute: array     # each bin's start in minutes from the first midnight, ascending
    site: array
    powered: bytes    # 1 if every reading in the bin had power
    length_min: int


def build(folder: Path) -> Week:
    """Reads the week with the probe's loader and keeps only the bins. Meant for its own process: the loader's
    pandas frame needs about 1 GB, and none of it should stay in the app."""
    from . import probe_precursor as probe

    df = probe.load(folder)
    start = df["time"].min().normalize()
    minute = ((df["time"].dt.floor(probe.BIN) - start).dt.total_seconds() // 60).astype("int64")
    bins = df.assign(minute=minute).groupby(["minute", "site_id"])["powered"].min().reset_index()
    sites = sorted(bins["site_id"].unique().tolist())
    index = {s: i for i, s in enumerate(sites)}
    days = (df["time"].max().normalize() - start).days + 1
    return Week([f"acc-{s}" for s in sites], array("i", bins["minute"].tolist()),
                array("H", bins["site_id"].map(index).tolist()), bytes(bins["powered"].astype("uint8").tolist()),
                days * 24 * 60)


class Replay:
    def __init__(self, db: Db, bus: EventBus, folder: Path = ACCRA_DIR):
        self.db = db
        self.bus = bus
        self.folder = folder
        self.week: Week | None = None
        self.anchor: datetime | None = None
        self.start = 0
        self.played = 0  # the last replay minute played, counted from the week's first midnight
        self.powered: dict[int, bool] = {}

    def begin(self, week: Week, now: datetime) -> None:
        """Starts at the same time of day as now (Accra keeps UTC), so the first replayed hour matches the real one."""
        self.week, self.anchor = week, now
        self.start = now.hour * 60 + now.minute
        self.played = self.start - 1

    async def register(self) -> None:
        # GridWatch sites are anonymous premises, none of them a household on our register, so they're anchors
        # (sensors that watch a supply), not homes with an invented household
        await self.db.run(
            "INSERT INTO sensor (sensor_id, type, household_id, cell_l1) SELECT s, 'anchor', NULL, :cell"
            " FROM unnest(:ids::text[]) AS s ON CONFLICT DO NOTHING", ids=self.week.sites, cell=ACCRA_CELL)

    async def emit(self, kind: str, site: int, now: datetime) -> None:
        sensor_id = self.week.sites[site]
        await self.bus.publish({
            "event_id": event_id("accra_replay", sensor_id, kind, now.isoformat()), "source": "accra_replay",
            "observed_at": now, "received_at": now, "label": "REPLAY",
            "payload": {"kind": kind, "sensor_id": sensor_id, "cell_l1": ACCRA_CELL},
        })

    async def tick(self, now: datetime) -> int:
        """Plays every bin due by now and returns the events sent. Each sensor sends at most its newest bin, so a
        stalled loop catching up can't flood the bus with more than one event per sensor."""
        target = self.start + int((now - self.anchor).total_seconds() * SPEED // 60)
        first = max(self.played + 1, target - self.week.length_min + 1)  # never more than one pass of the week
        newest: dict[int, int] = {}
        while first <= target:
            at = first % self.week.length_min
            span = min(target - first + 1, self.week.length_min - at)
            for i in range(bisect_left(self.week.minute, at), bisect_left(self.week.minute, at + span)):
                newest[self.week.site[i]] = i
            first += span
        self.played = max(self.played, target)
        sent = 0
        for site, i in newest.items():
            on, was_on = bool(self.week.powered[i]), self.powered.get(site, True)
            self.powered[site] = on
            if on or was_on:
                await self.emit("heartbeat" if on else "last_gasp", site, now)
                sent += 1
        return sent

    async def run(self) -> None:
        # like the simulator, the first round waits one heartbeat; it also keeps app start-up light
        await asyncio.sleep(HEARTBEAT_S)
        if not any(self.folder.glob("accra_*.csv.gz")):
            log.info("no Accra data in %s; the replay stays off", self.folder)
            return
        pool = ProcessPoolExecutor(1, mp_context=multiprocessing.get_context("spawn"))
        try:
            week = await asyncio.get_running_loop().run_in_executor(pool, build, self.folder)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        self.begin(week, datetime.now(UTC))
        await self.register()
        log.info("accra replay: %d sensors, %d bins, %dx", len(week.sites), len(week.minute), SPEED)
        while True:
            await asyncio.sleep(TICK_S)
            try:
                await self.tick(datetime.now(UTC))
            except Exception:
                # one bad round must not stop the replay; its bins are skipped, like a missed report
                log.exception("accra replay tick failed")
