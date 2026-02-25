"""
Parse ~/.plamya/shared/STATUS.md — agent heartbeat table.

Expected format
---------------
| Агент | Статус | Последний heartbeat | Текущая задача |
|-------|--------|---------------------|----------------|
| АЛЬТРОН | 🟢 active | 2026-02-16 14:00 | Координация |
"""
import re
from dataclasses import dataclass, field
from typing import Optional


# Map Cyrillic agent names -> canonical IDs used in plamya.json
AGENT_NAME_TO_ID: dict[str, str] = {
    "АЛЬТРОН": "main",
    "ХАНТЕР": "hunter",
    "КОДЕР": "coder",
    "СКАНЕР": "scanner",
    "ЧАППИ": "chappie",
    "ЭМПАТ": "empat",
    "ПРОДЮСЕР": "producer",
}

# Reverse map
AGENT_ID_TO_NAME: dict[str, str] = {v: k for k, v in AGENT_NAME_TO_ID.items()}

EMOJI_PATTERN = re.compile(r"^([\U0001f300-\U0001fAFF\u2600-\u27BF\u200d]+)\s*")


@dataclass
class StatusEntry:
    agent_name: str
    agent_id: str
    status_emoji: Optional[str] = None
    status: Optional[str] = None
    last_heartbeat: Optional[str] = None
    current_task: Optional[str] = None


def parse_status_md(raw: str) -> list[StatusEntry]:
    """Parse the STATUS.md markdown table into structured entries."""
    entries: list[StatusEntry] = []
    lines = raw.strip().splitlines()

    for line in lines:
        line = line.strip()
        # Must start and end with pipe
        if not line.startswith("|") or not line.endswith("|"):
            continue
        # Skip header row
        if "Агент" in line and "Статус" in line:
            continue
        # Skip separator row (|---|---|...)
        if re.match(r"^\|[\s\-|]+\|$", line):
            continue

        cells = [c.strip() for c in line.split("|")]
        # split on "|" produces empty strings at edges: ['', 'АЛЬТРОН', ...]
        cells = [c for c in cells if c != "" or cells.index(c) not in (0, len(cells) - 1)]
        # Filter empty edge cells
        cells = [c for c in cells if c]

        if len(cells) < 4:
            continue

        agent_name_raw = cells[0].strip()
        status_raw = cells[1].strip()
        heartbeat_raw = cells[2].strip()
        task_raw = cells[3].strip()

        # Resolve agent ID
        agent_id = AGENT_NAME_TO_ID.get(agent_name_raw, agent_name_raw.lower())

        # Extract emoji from status
        status_emoji: Optional[str] = None
        status_text = status_raw
        emoji_match = EMOJI_PATTERN.match(status_raw)
        if emoji_match:
            status_emoji = emoji_match.group(1).strip()
            status_text = status_raw[emoji_match.end():].strip()

        # Normalize empty/dash values
        if heartbeat_raw in ("-", ""):
            heartbeat_raw = None
        if task_raw in ("-", ""):
            task_raw = None
        if status_text in ("-", ""):
            status_text = None

        entries.append(
            StatusEntry(
                agent_name=agent_name_raw,
                agent_id=agent_id,
                status_emoji=status_emoji,
                status=status_text,
                last_heartbeat=heartbeat_raw,
                current_task=task_raw,
            )
        )

    return entries
