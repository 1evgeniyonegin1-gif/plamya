"""
FileWatcher — caches file reads, re-parses only when mtime changes.

Avoids re-reading files on every API request. Each path is cached with its
last-known mtime; on subsequent reads the OS stat is compared and the file
is only re-parsed when it has actually changed on disk.
"""
import json
import os
from typing import Any, Callable, Optional


class FileWatcher:
    """Lightweight file cache keyed by (path, mtime)."""

    def __init__(self):
        # path -> (mtime, parsed_data)
        self._cache: dict[str, tuple[float, Any]] = {}

    def read_if_changed(
        self,
        path: str,
        parser: Callable[[str], Any],
    ) -> Optional[Any]:
        """Read and parse *path* only when its mtime has changed.

        Returns the parsed result, or ``None`` if the file does not exist.
        """
        if not os.path.isfile(path):
            # Remove stale cache entry if the file was deleted
            self._cache.pop(path, None)
            return None

        try:
            current_mtime = os.path.getmtime(path)
        except OSError:
            self._cache.pop(path, None)
            return None

        cached = self._cache.get(path)
        if cached is not None:
            cached_mtime, cached_data = cached
            if cached_mtime == current_mtime:
                return cached_data

        # File is new or has been modified — re-read
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            data = parser(raw)
            self._cache[path] = (current_mtime, data)
            return data
        except Exception as exc:
            print(f"[FileWatcher] Error reading {path}: {exc}")
            return None

    # ── convenience helpers ──────────────────────────

    def read_json(self, path: str) -> Optional[Any]:
        """Shortcut: parse file as JSON."""
        return self.read_if_changed(path, json.loads)

    def read_text(self, path: str) -> Optional[str]:
        """Shortcut: return raw text content."""
        return self.read_if_changed(path, lambda raw: raw)
