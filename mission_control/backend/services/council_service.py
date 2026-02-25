"""
CouncilService — parse and write to COUNCIL.md for multi-agent discussions.

Format:
    ## ТЕМА #1: Title — AUTHOR, 2026-02-17 14:00
    status: open

    ### АГЕНТ (14:05):
    Response text...

    ---
"""
import os
import re
from dataclasses import dataclass, field
from datetime import datetime

from ..config import settings
from .status_parser import AGENT_ID_TO_NAME, AGENT_NAME_TO_ID


@dataclass
class CouncilResponse:
    agent_name: str
    agent_id: str
    timestamp: str
    text: str


@dataclass
class CouncilTopic:
    id: int
    title: str
    author: str
    author_id: str
    created_at: str
    status: str  # "open" | "closed"
    responses: list[CouncilResponse] = field(default_factory=list)


def _now_msk() -> datetime:
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]
    return datetime.now(tz=ZoneInfo("Europe/Moscow"))


def _author_to_id(author: str) -> str:
    """Map author display name to agent_id."""
    upper = author.strip().upper()
    if upper in AGENT_NAME_TO_ID:
        return AGENT_NAME_TO_ID[upper]
    if upper == "ДАНИЛ":
        return "admin"
    return author.lower()


def _council_path() -> str:
    return os.path.join(settings.plamya_dir, "shared", "COUNCIL.md")


_TOPIC_RE = re.compile(
    r"^##\s+ТЕМА\s+#(\d+):\s+(.+?)\s+—\s+(.+?),\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})",
)
_STATUS_RE = re.compile(r"^status:\s*(open|closed)", re.IGNORECASE)
_RESPONSE_RE = re.compile(
    r"^###\s+(.+?)\s+\((\d{2}:\d{2})\):",
)


def parse_council_md(raw: str) -> list[CouncilTopic]:
    """Parse COUNCIL.md into structured topics with responses."""
    topics: list[CouncilTopic] = []
    current_topic: CouncilTopic | None = None
    current_response: CouncilResponse | None = None
    response_lines: list[str] = []

    def _flush_response():
        nonlocal current_response, response_lines
        if current_response and response_lines:
            current_response.text = "\n".join(response_lines).strip()
            if current_topic:
                current_topic.responses.append(current_response)
        current_response = None
        response_lines = []

    for line in raw.splitlines():
        # Topic header
        m = _TOPIC_RE.match(line)
        if m:
            _flush_response()
            if current_topic:
                topics.append(current_topic)
            topic_id = int(m.group(1))
            title = m.group(2).strip()
            author = m.group(3).strip()
            created_at = m.group(4).strip()
            current_topic = CouncilTopic(
                id=topic_id,
                title=title,
                author=author,
                author_id=_author_to_id(author),
                created_at=created_at,
                status="open",
            )
            continue

        # Status line
        sm = _STATUS_RE.match(line)
        if sm and current_topic:
            current_topic.status = sm.group(1).lower()
            continue

        # Response header
        rm = _RESPONSE_RE.match(line)
        if rm and current_topic:
            _flush_response()
            agent_name = rm.group(1).strip()
            ts = rm.group(2).strip()
            # Build full timestamp from topic date + response time
            date_part = current_topic.created_at.split(" ")[0] if current_topic else ""
            current_response = CouncilResponse(
                agent_name=agent_name,
                agent_id=_author_to_id(agent_name),
                timestamp=f"{date_part} {ts}" if date_part else ts,
                text="",
            )
            continue

        # Separator
        if line.strip() == "---":
            _flush_response()
            continue

        # Body text
        if current_response is not None:
            response_lines.append(line)

    _flush_response()
    if current_topic:
        topics.append(current_topic)

    return topics


def get_next_topic_id(raw: str) -> int:
    """Get the next available topic ID."""
    topics = parse_council_md(raw)
    if not topics:
        return 1
    return max(t.id for t in topics) + 1


def create_topic(author: str, title: str) -> int:
    """Create a new topic in COUNCIL.md. Returns the topic ID."""
    path = _council_path()
    raw = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()

    topic_id = get_next_topic_id(raw)
    now = _now_msk()
    ts = now.strftime("%Y-%m-%d %H:%M")

    entry = (
        f"\n## ТЕМА #{topic_id}: {title} — {author}, {ts}\n"
        f"status: open\n\n"
    )

    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)

    return topic_id


def add_response(topic_id: int, agent_name: str, text: str) -> bool:
    """Add a response to an existing topic. Returns True on success."""
    path = _council_path()
    if not os.path.isfile(path):
        return False

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    now = _now_msk()
    ts = now.strftime("%H:%M")

    # Find the topic and insert response before the next topic or end
    topic_header = f"## ТЕМА #{topic_id}:"
    if topic_header not in raw:
        return False

    response_entry = f"\n### {agent_name} ({ts}):\n{text}\n"

    # Find next topic or end of file to insert before
    idx = raw.index(topic_header)
    rest = raw[idx:]

    # Find next ## ТЕМА or end
    next_topic = rest.find("\n## ТЕМА #", 1)
    if next_topic == -1:
        # Append at end
        with open(path, "a", encoding="utf-8") as f:
            f.write(response_entry)
    else:
        # Insert before next topic
        insert_pos = idx + next_topic
        new_raw = raw[:insert_pos] + response_entry + raw[insert_pos:]
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_raw)

    return True


def request_all_agents(topic_id: int, title: str) -> int:
    """Write INBOX messages to all agents asking them to respond to a topic.

    Returns count of agents notified.
    """
    path = _council_path()
    inbox_path = os.path.join(settings.plamya_dir, "shared", "INBOX.md")

    now = _now_msk()
    ts = now.strftime("%Y-%m-%d %H:%M")

    # All agents except main (Альтрон sends the requests)
    agents = ["ХАНТЕР", "КОДЕР", "СКАНЕР", "ЧАППИ", "ЭМПАТ", "ПРОДЮСЕР"]

    entries = []
    for agent in agents:
        entry = (
            f"\n## [{ts}] АЛЬТРОН → {agent}\n"
            f"**СОВЕТ: тема #{topic_id}**\n\n"
            f"Зайди в `~/.plamya/shared/COUNCIL.md`, найди ТЕМУ #{topic_id}: \"{title}\".\n"
            f"Выскажи свою экспертную точку зрения (2-5 предложений) с позиции своей роли.\n"
            f"Добавь свой ответ в формате: `### ТВОЁ_ИМЯ (HH:MM):` + текст.\n\n"
            f"---\n"
        )
        entries.append(entry)

    os.makedirs(os.path.dirname(inbox_path), exist_ok=True)
    with open(inbox_path, "a", encoding="utf-8") as f:
        f.write("".join(entries))

    return len(agents)
