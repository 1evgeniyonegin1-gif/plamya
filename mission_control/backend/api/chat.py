"""
Chat API — send messages to agents via INBOX.md.
"""
import os
from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..services.status_parser import AGENT_ID_TO_NAME

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatSendRequest(BaseModel):
    agent_id: str = Field(..., description="Target agent ID (e.g. 'chappie', 'main')")
    message: str = Field(..., min_length=1, max_length=4000)
    subject: str | None = Field(None, max_length=200)


class ChatSendResponse(BaseModel):
    ok: bool
    timestamp: str


@router.post("/send", response_model=ChatSendResponse)
async def send_message(body: ChatSendRequest, request: Request):
    """Write a message to INBOX.md for the target agent.

    Format:
        ## [2026-02-17 14:30] ДАНИЛ → АГЕНТ
        **Subject**

        Message body

        ---
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]

    msk = ZoneInfo("Europe/Moscow")
    now = datetime.now(tz=msk)
    ts = now.strftime("%Y-%m-%d %H:%M")

    # Map agent_id to Cyrillic name
    agent_name = AGENT_ID_TO_NAME.get(body.agent_id, body.agent_id.upper())

    # Build the INBOX entry
    lines = [f"\n## [{ts}] ДАНИЛ → {agent_name}"]

    if body.subject:
        lines.append(f"**{body.subject}**")

    lines.append("")
    lines.append(body.message)
    lines.append("")
    lines.append("---")
    lines.append("")

    entry = "\n".join(lines)

    # Append to INBOX.md
    inbox_path = os.path.join(settings.plamya_dir, "shared", "INBOX.md")

    # Ensure directory exists
    os.makedirs(os.path.dirname(inbox_path), exist_ok=True)

    with open(inbox_path, "a", encoding="utf-8") as f:
        f.write(entry)

    return ChatSendResponse(ok=True, timestamp=ts)
