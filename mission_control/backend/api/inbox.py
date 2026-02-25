"""
Inbox API — list inter-agent messages from INBOX.md.
"""
from fastapi import APIRouter, Request
from typing import Optional

from ..schemas import InboxMessage, InboxResponse
from ..services.inbox_parser import parse_inbox_md
from ..services.status_parser import AGENT_NAME_TO_ID

router = APIRouter(prefix="/inbox", tags=["Inbox"])


@router.get("", response_model=InboxResponse)
async def list_inbox(
    request: Request,
    agent: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Return parsed INBOX.md messages.

    Query params:
      - agent: filter by agent ID (matches sender or recipient)
      - limit: max messages to return (default 50)
      - offset: skip first N messages (default 0)
    """
    file_watcher = request.app.state.file_watcher
    import os
    from ..config import settings

    inbox_path = os.path.join(settings.plamya_dir, "shared", "INBOX.md")
    raw = file_watcher.read_text(inbox_path)
    if not raw:
        return InboxResponse(messages=[], total=0)

    parsed = parse_inbox_md(raw)

    # Filter by agent if specified
    if agent:
        # Map agent ID back to Russian name for matching
        agent_upper = agent.upper()
        # Also check the Russian name
        russian_names = [
            name for name, aid in AGENT_NAME_TO_ID.items()
            if aid == agent
        ]
        match_names = {agent_upper}
        for rn in russian_names:
            match_names.add(rn.upper())

        filtered = []
        for msg in parsed:
            sender_upper = msg.sender.upper()
            recipient_upper = msg.recipient.upper()
            if any(mn in sender_upper or mn in recipient_upper for mn in match_names):
                filtered.append(msg)
        parsed = filtered

    total = len(parsed)

    # Apply offset + limit
    sliced = parsed[offset: offset + limit]

    messages = [
        InboxMessage(
            id=msg.id,
            timestamp=msg.timestamp,
            sender=msg.sender,
            recipient=msg.recipient,
            subject=msg.subject,
            preview=msg.preview,
            full_text=msg.full_text,
            priority=msg.priority,
        )
        for msg in sliced
    ]

    return InboxResponse(messages=messages, total=total)
