"""
FileMonitor — background task that watches shared files for changes
and publishes events to the EventBus.

Checks mtime every 3 seconds. Only reads + parses when a file changes.
"""
import asyncio
import os
from typing import Optional

from ..config import settings
from .event_bus import EventBus


# Files to watch: (relative path from plamya_dir, event_type)
_WATCHED_FILES = [
    (("shared", "STATUS.md"), "agent_status"),
    (("shared", "INBOX.md"), "inbox"),
    (("shared", "COUNCIL.md"), "council"),
    (("shared", "TASKS.md"), "tasks"),
    (("cron", "jobs.json"), "cron"),
]

POLL_INTERVAL = 3.0  # seconds


class FileMonitor:
    """Watch shared files and publish change events."""

    def __init__(self, event_bus: EventBus, plamya_dir: Optional[str] = None):
        self._event_bus = event_bus
        self._base = plamya_dir or settings.plamya_dir
        self._mtimes: dict[str, float] = {}
        self._task: Optional[asyncio.Task] = None

    def _path(self, parts: tuple[str, ...]) -> str:
        return os.path.join(self._base, *parts)

    def start(self) -> None:
        """Start the background monitoring task."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._poll_loop())

    def stop(self) -> None:
        """Stop the background monitoring task."""
        if self._task and not self._task.done():
            self._task.cancel()

    async def _poll_loop(self) -> None:
        """Main polling loop — check file mtimes every POLL_INTERVAL."""
        # Initialize mtimes
        for parts, _ in _WATCHED_FILES:
            path = self._path(parts)
            try:
                self._mtimes[path] = os.path.getmtime(path)
            except OSError:
                self._mtimes[path] = 0

        while True:
            try:
                await asyncio.sleep(POLL_INTERVAL)
                for parts, event_type in _WATCHED_FILES:
                    path = self._path(parts)
                    try:
                        mtime = os.path.getmtime(path)
                    except OSError:
                        continue

                    prev = self._mtimes.get(path, 0)
                    if mtime > prev:
                        self._mtimes[path] = mtime
                        self._event_bus.publish(event_type, {"file": "/".join(parts)})

            except asyncio.CancelledError:
                break
            except Exception:
                # Don't crash the monitor on unexpected errors
                await asyncio.sleep(POLL_INTERVAL)
