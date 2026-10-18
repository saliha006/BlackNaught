"""Builds and runs the background workers inside the single uvicorn process."""
import asyncio
import logging
from datetime import UTC, datetime

from . import audit, cellpub
from .bus import EventBus, minute_of
from .config import read_secret, settings
from .db import Db
from .events import event_id
from .geocode import Geocoder
from .grading import Grader
from .health import SourceHealth
from .ingest.feeds import Outage
from .ingest.poller import Poller, new_client
from .ingest import ioda
from .ingest.sources import DNO, dno_poll, elexon_poll, ioda_poll
from .replay import Replay
from .sensors import SensorTracker
from .simulator import Simulator
from .sse import Broadcaster
from .survival import load
from .triage import Scorer
from .writer import Writer

log = logging.getLogger(__name__)

INTERVALS = {"ukpn": 120, "npg": 120, "ssen": 120, "elexon": 30, "ioda": 600}
COUNT_FLUSH_S = 60
SWEEP_S = 30
STATS_S = 5


class Runtime:
    def __init__(self) -> None:
        self.started_at = datetime.now(UTC)
        self.bus = EventBus()
        self.broadcaster = Broadcaster()
        self.sensors = SensorTracker(self.started_at)
        self.health = {s: SourceHealth(s, i) for s, i in INTERVALS.items()}
        self.ingest_db = Db("bn_ingest")
        self.writer = Writer(Db("bn_ingest"))
        self.simulator = Simulator(Db("bn_ingest"), self.bus)
        self.replay = Replay(Db("bn_ingest"), self.bus)
        self.client = new_client()
        self.geocoder = Geocoder(self.ingest_db, self.client)
        self.scorer = Scorer(Db("bn_agent"), load(settings().model_path), bytes.fromhex(read_secret("bidx_key")))
        self.grader = Grader(Db("bn_agent"))
        url = settings().signer_url
        self.signer = audit.HttpSigner(self.client, url, read_secret("signer_token_app")) if url else None
        self.checkpointer = audit.Checkpointer(self.grader.db, self.signer)
        self.scorer.on_ranked = lambda summary: self.broadcaster.publish("triage", summary)
        self.grader.on_graded = lambda n: self.broadcaster.publish("grade", {"graded": n})
        self.tasks: list[asyncio.Task] = []

    async def outages_changed(self, source: str, changed: list[tuple[int, Outage]]) -> None:
        now = datetime.now(UTC)
        for outage_id, o in changed:
            self.broadcaster.publish("outage", {"id": outage_id, "source": source, "status": o.status})
            await self.bus.publish({
                "event_id": event_id(source, o.source_ref, o.content_hash.hex()),
                "source": source, "observed_at": now, "received_at": now, "label": "LIVE",
                "payload": {"kind": "dno_fault", "outage_id": outage_id, "source_ref": o.source_ref,
                            "status": o.status, "postcodes": o.postcodes},
            })

    async def handle(self, event: dict) -> None:
        payload = event["payload"]
        kind = payload["kind"]
        if kind == "dno_fault":
            self.scorer.wake.set()  # re-rank now rather than waiting for the next 30 s tick
        elif kind in ("heartbeat", "last_gasp"):
            track = self.sensors.heartbeat if kind == "heartbeat" else self.sensors.last_gasp
            transition = track(payload["sensor_id"], payload["cell_l1"], event["label"], event["observed_at"])
            if transition:
                self.writer.put("sensor_transition", transition)

    async def housekeeping(self) -> None:
        """Dropout sweep every 30 s; per-minute event counts every 60 s; audit checkpoints when due."""
        model = self.scorer.model
        await audit.append(self.grader.db, "model_loaded", "system", model.model_id,
                           {"sha256": model.sha256, "label": model.label})
        ticks = 0
        while True:
            await asyncio.sleep(SWEEP_S)
            now = datetime.now(UTC)
            for transition in self.sensors.sweep(now):
                self.writer.put("sensor_transition", transition)
            ticks += 1
            if ticks * SWEEP_S % COUNT_FLUSH_S == 0:
                seen, dropped = self.bus.take_counts()
                for kind in seen.keys() | dropped.keys():
                    self.writer.put("event_counts", (minute_of(now), kind, seen[kind], dropped[kind]))
            checkpoint = await self.checkpointer.maybe_checkpoint(now)
            if checkpoint is not None:
                self.broadcaster.publish("audit_checkpoint", {"seq": checkpoint})

    async def stats(self) -> None:
        """Coalesced live numbers for the control room (one message every few seconds, not one per event)."""
        last_total = self.bus.total
        while True:
            await asyncio.sleep(STATS_S)
            total = self.bus.total
            self.broadcaster.publish("stats", {
                "events_per_s": round((total - last_total) / STATS_S, 1),
                "critical_q": self.bus.critical.qsize(), "bulk_q": self.bus.bulk.qsize(),
                "writer_lag": self.writer.lag, "dropped": sum(self.bus.dropped.values()),
            })
            last_total = total

    async def internet_dips(self, dips: list[ioda.Reading]) -> None:
        for d in dips:
            self.broadcaster.publish("ioda", {"country": d.country, "ratio": round(d.ratio, 3), "at": d.at})
            await self.bus.publish({
                "event_id": event_id("ioda", d.country, d.at.isoformat()), "source": "ioda",
                "observed_at": d.at, "received_at": datetime.now(UTC), "label": "LIVE",
                "payload": {"kind": "ioda_signal", "region": d.country, "datasource": ioda.DATASOURCE,
                            "value": d.ratio},
            })

    def source_changed(self, health: SourceHealth) -> None:
        self.broadcaster.publish("source_health", health.as_dict(datetime.now(UTC)))

    def pollers(self) -> list[Poller]:
        out = [Poller(self.health[s], dno_poll(s, self.client, self.ingest_db, self.geocoder, self.outages_changed),
                      on_status=self.source_changed) for s in DNO]
        out.append(Poller(self.health["elexon"], elexon_poll(self.client, self.writer), on_status=self.source_changed))
        out.append(Poller(self.health["ioda"], ioda_poll(self.client, self.internet_dips), on_status=self.source_changed))
        return out

    def start(self) -> None:
        self.tasks = [asyncio.create_task(self.writer.run(), name="writer")]
        self.tasks.append(asyncio.create_task(self.bus.consume(self.handle), name="bus"))
        self.tasks.append(asyncio.create_task(self.housekeeping(), name="housekeeping"))
        self.tasks.append(asyncio.create_task(self.scorer.run(), name="scorer"))
        self.tasks.append(asyncio.create_task(self.grader.run(), name="grader"))
        self.tasks.append(asyncio.create_task(self.stats(), name="stats"))
        self.tasks.append(asyncio.create_task(cellpub.run(self.grader.db), name="cells"))
        self.tasks.append(asyncio.create_task(self.simulator.run(), name="sim"))
        self.tasks.append(asyncio.create_task(self.replay.run(), name="replay"))
        self.tasks += [asyncio.create_task(p.run(), name=f"poll:{p.health.source}") for p in self.pollers()]

    async def stop(self) -> None:
        # the writer (tasks[0]) gets a sentinel instead of a cancel so rows already queued still reach the DB
        for task in self.tasks[1:]:
            task.cancel()
        self.writer.stop()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.client.aclose()
        self.ingest_db.close()
        self.writer.db.close()
        self.simulator.db.close()
        self.replay.db.close()
        self.scorer.db.close()
        self.grader.db.close()
