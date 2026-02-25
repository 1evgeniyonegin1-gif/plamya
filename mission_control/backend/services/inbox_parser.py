"""
Parse ~/.plamya/shared/INBOX.md — inter-agent messages.

Each message block looks like:

    ## [2026-02-16 20:14] ЧАППИ -> КОДЕР
    **Запрос на фичу** (приоритет: high)

    Body text goes here ...

    ---
"""
import re
from dataclasses import dataclass
from typing import Optional

# Matches: ## [2026-02-16 20:14] SENDER -> RECIPIENT
# Also handles the arrow variants: ->, →
HEADER_RE = re.compile(
    r"^##\s+\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\]\s+(.+?)\s+(?:->|→)\s+(.+?)\s*$"
)

# Extract subject from first bold line: **Subject text**
SUBJECT_RE = re.compile(r"\*\*(.+?)\*\*")

# Extract priority: (приоритет: high)
PRIORITY_RE = re.compile(r"\(приоритет:\s*(high|medium|low)\)", re.IGNORECASE)

SEPARATOR_RE = re.compile(r"^---\s*$")


@dataclass
class ParsedInboxMessage:
    id: int
    timestamp: str
    sender: str
    recipient: str
    subject: Optional[str] = None
    preview: str = ""
    full_text: str = ""
    priority: Optional[str] = None


def parse_inbox_md(raw: str) -> list[ParsedInboxMessage]:
    """Parse INBOX.md into a list of messages, newest first."""
    messages: list[ParsedInboxMessage] = []
    lines = raw.splitlines()

    current_header: Optional[re.Match] = None
    current_body_lines: list[str] = []
    msg_id = 0

    def _flush():
        nonlocal msg_id, current_header, current_body_lines
        if current_header is None:
            current_body_lines = []
            return

        timestamp = current_header.group(1)
        sender = current_header.group(2).strip()
        recipient = current_header.group(3).strip()

        body = "\n".join(current_body_lines).strip()

        # Extract subject (first **bold** text)
        subject_match = SUBJECT_RE.search(body)
        subject = subject_match.group(1) if subject_match else None

        # Extract priority
        priority_match = PRIORITY_RE.search(body)
        priority = priority_match.group(1).lower() if priority_match else None

        # Build preview: first 200 chars of non-bold, non-header text
        preview_lines = []
        for bline in current_body_lines:
            stripped = bline.strip()
            # Skip bold-only lines and blank lines for preview
            if not stripped:
                continue
            if stripped.startswith("**") and stripped.endswith("**"):
                continue
            if PRIORITY_RE.search(stripped) and len(stripped) < 40:
                continue
            preview_lines.append(stripped)
        preview_text = " ".join(preview_lines)
        if len(preview_text) > 200:
            preview_text = preview_text[:200] + "..."

        msg_id += 1
        messages.append(
            ParsedInboxMessage(
                id=msg_id,
                timestamp=timestamp,
                sender=sender,
                recipient=recipient,
                subject=subject,
                preview=preview_text,
                full_text=body,
                priority=priority,
            )
        )

        current_header = None
        current_body_lines = []

    for line in lines:
        header_match = HEADER_RE.match(line.strip())
        if header_match:
            # Flush previous message
            _flush()
            current_header = header_match
            continue

        if SEPARATOR_RE.match(line.strip()):
            _flush()
            continue

        # Accumulate body lines
        if current_header is not None:
            current_body_lines.append(line)

    # Flush last message if file doesn't end with ---
    _flush()

    return messages
