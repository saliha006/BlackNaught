"""Server-sent events for the control room.

Only summaries are streamed (an outage changed, triage re-ranked, grades landed...), never raw sensor events:
at 1–2k events/s those would swamp a browser. Each client has a bounded queue; a slow client loses its own oldest
messages and is told to resync rather than holding everyone else up. A ring buffer lets a reconnecting browser
resume from Last-Event-ID.
"""
import asyncio
import json
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

RING = 2000
PER_CLIENT = 256
MAX_CLIENTS = 50
RESYNC = "resync"


@dataclass(eq=False)  # clients are compared by identity, so they can live in a set
class Client:
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(PER_CLIENT))
    behind: bool = False


class TooManyClients(RuntimeError):
    pass


class Broadcaster:
    def __init__(self) -> None:
        self.next_id = 1
        self.ring: deque[tuple[int, str, str]] = deque(maxlen=RING)
        self.clients: set[Client] = set()

    def publish(self, event: str, data: dict[str, Any]) -> int:
        message = (self.next_id, event, json.dumps(data, default=str))
        self.next_id += 1
        self.ring.append(message)
        for client in self.clients:
            if client.queue.full():
                client.queue.get_nowait()
                client.behind = True
            client.queue.put_nowait(message)
        return message[0]

    def subscribe(self, last_event_id: int | None) -> tuple[Client, list[tuple[int, str, str]]]:
        """Backlog to replay first; a single resync marker if the gap fell out of the ring."""
        if len(self.clients) >= MAX_CLIENTS:
            raise TooManyClients
        client = Client()
        self.clients.add(client)
        backlog: list[tuple[int, str, str]] = []
        if last_event_id is not None:
            oldest = self.ring[0][0] if self.ring else self.next_id
            if last_event_id + 1 < oldest:
                backlog = [(self.next_id - 1, RESYNC, "{}")]
            else:
                backlog = [m for m in self.ring if m[0] > last_event_id]
        return client, backlog

    def unsubscribe(self, client: Client) -> None:
        self.clients.discard(client)

    async def stream(self, client: Client, backlog: list[tuple[int, str, str]]) -> AsyncIterator[dict[str, Any]]:
        try:
            for message_id, event, data in backlog:
                yield {"id": message_id, "event": event, "data": data, "retry": 3000}
            while True:
                message_id, event, data = await client.queue.get()
                if client.behind:
                    client.behind = False
                    yield {"id": message_id, "event": RESYNC, "data": "{}"}
                yield {"id": message_id, "event": event, "data": data}
        finally:
            self.unsubscribe(client)
