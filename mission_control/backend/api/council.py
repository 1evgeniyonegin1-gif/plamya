"""
Council API — multi-agent group discussions via COUNCIL.md.
"""
import os
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..services.council_service import (
    add_response,
    create_topic,
    parse_council_md,
    request_all_agents,
)
from ..services.status_parser import AGENT_ID_TO_NAME

router = APIRouter(prefix="/council", tags=["Council"])


# ── Schemas ──────────────────────────────────────────

class TopicResponse(BaseModel):
    agent_name: str
    agent_id: str
    timestamp: str
    text: str


class TopicSummary(BaseModel):
    id: int
    title: str
    author: str
    author_id: str
    created_at: str
    status: str
    response_count: int


class TopicDetail(BaseModel):
    id: int
    title: str
    author: str
    author_id: str
    created_at: str
    status: str
    responses: list[TopicResponse]


class TopicsListResponse(BaseModel):
    topics: list[TopicSummary]
    total: int


class CreateTopicRequest(BaseModel):
    author: str = Field(default="ДАНИЛ", max_length=50)
    title: str = Field(..., min_length=1, max_length=500)


class CreateTopicResponse(BaseModel):
    ok: bool
    topic_id: int


class AddReplyRequest(BaseModel):
    agent_id: str = Field(..., description="Agent ID or 'admin' for ДАНИЛ")
    text: str = Field(..., min_length=1, max_length=4000)


class AskAllResponse(BaseModel):
    ok: bool
    agents_notified: int


# ── Endpoints ────────────────────────────────────────

@router.get("/topics", response_model=TopicsListResponse)
async def list_topics(request: Request, limit: int = 20, offset: int = 0):
    """List all council topics (newest first)."""
    fw = request.app.state.file_watcher
    path = os.path.join(settings.plamya_dir, "shared", "COUNCIL.md")
    raw = fw.read_text(path) or ""
    topics = parse_council_md(raw)

    # Newest first
    topics.reverse()

    total = len(topics)
    page = topics[offset : offset + limit]

    return TopicsListResponse(
        topics=[
            TopicSummary(
                id=t.id,
                title=t.title,
                author=t.author,
                author_id=t.author_id,
                created_at=t.created_at,
                status=t.status,
                response_count=len(t.responses),
            )
            for t in page
        ],
        total=total,
    )


@router.get("/topics/{topic_id}", response_model=Optional[TopicDetail])
async def get_topic(topic_id: int, request: Request):
    """Get a single topic with all responses."""
    fw = request.app.state.file_watcher
    path = os.path.join(settings.plamya_dir, "shared", "COUNCIL.md")
    raw = fw.read_text(path) or ""
    topics = parse_council_md(raw)

    for t in topics:
        if t.id == topic_id:
            return TopicDetail(
                id=t.id,
                title=t.title,
                author=t.author,
                author_id=t.author_id,
                created_at=t.created_at,
                status=t.status,
                responses=[
                    TopicResponse(
                        agent_name=r.agent_name,
                        agent_id=r.agent_id,
                        timestamp=r.timestamp,
                        text=r.text,
                    )
                    for r in t.responses
                ],
            )
    return None


@router.post("/topics", response_model=CreateTopicResponse)
async def create_new_topic(body: CreateTopicRequest):
    """Create a new discussion topic."""
    topic_id = create_topic(body.author, body.title)
    return CreateTopicResponse(ok=True, topic_id=topic_id)


@router.post("/topics/{topic_id}/ask", response_model=AskAllResponse)
async def ask_all_agents(topic_id: int, request: Request):
    """Send INBOX messages to all agents asking them to respond."""
    fw = request.app.state.file_watcher
    path = os.path.join(settings.plamya_dir, "shared", "COUNCIL.md")
    raw = fw.read_text(path) or ""
    topics = parse_council_md(raw)

    title = ""
    for t in topics:
        if t.id == topic_id:
            title = t.title
            break

    if not title:
        return AskAllResponse(ok=False, agents_notified=0)

    count = request_all_agents(topic_id, title)
    return AskAllResponse(ok=True, agents_notified=count)


@router.post("/topics/{topic_id}/reply", response_model=dict)
async def reply_to_topic(topic_id: int, body: AddReplyRequest):
    """Add a response to a topic (from Данил or any agent)."""
    # Map agent_id to display name
    if body.agent_id == "admin":
        agent_name = "ДАНИЛ"
    else:
        agent_name = AGENT_ID_TO_NAME.get(body.agent_id, body.agent_id.upper())

    ok = add_response(topic_id, agent_name, body.text)
    return {"ok": ok}
