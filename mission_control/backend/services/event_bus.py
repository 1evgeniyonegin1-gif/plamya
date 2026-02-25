"""
EventBus — in-memory pub/sub for SSE real-time updates.

Publishes events when shared files change (STATUS.md, INBOX.md, etc.)
Subscribers are SSE connections from the frontend.
"""
import asyncio
import json
from dataclasses import dataclass
from typing import AsyncGenerator


@dataclass
class Event:
    type: str  # agent_status | inbox | council | tasks | cron
    data: dict


class EventBus:
    """Simple async pub/sub for SSE."""

    def __init__(self):
        self._queues: list[asyncio.Queue[Event]] = []

    def publish(self, event_type: str, data: dict | None = None) -> None:
        """Publish an event to all subscribers."""
        event = Event(type=event_type, data=data or {})
        dead: list[asyncio.Queue] = []
        for q in self._queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._queues.remove(q)

    async def subscribe(self) -> AsyncGenerator[Event, None]:
        """Subscribe to events. Yields events as they arrive."""
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=50)
        self._queues.append(q)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            if q in self._queues:
                self._queues.remove(q)

    @property
    def subscriber_count(self) -> int:
        return len(self._queues)
