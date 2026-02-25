"""
Mission Control — Pydantic schemas for API request/response models.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────

class AuthRequest(BaseModel):
    init_data: str


class UserInfo(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    is_admin: bool = False


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


# ──────────────────────────────────────────────
# Agents
# ──────────────────────────────────────────────

class AgentStatus(BaseModel):
    id: str
    name: str
    model_primary: Optional[str] = None
    model_fallbacks: list[str] = Field(default_factory=list)
    status: Optional[str] = None
    status_emoji: Optional[str] = None
    last_heartbeat: Optional[str] = None
    current_task: Optional[str] = None
    cron_jobs_count: int = 0
    cron_errors: int = 0
    inbox_messages_count: int = 0
    api_usage: dict = Field(default_factory=dict)


class CronJob(BaseModel):
    id: str
    name: str
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    enabled: bool = True
    schedule_human: Optional[str] = None
    last_status: Optional[str] = None
    last_run_at: Optional[str] = None
    last_duration_ms: Optional[int] = None
    next_run_at: Optional[str] = None
    consecutive_errors: int = 0
    last_error: Optional[str] = None


class InboxMessage(BaseModel):
    id: int
    timestamp: str
    sender: str
    recipient: str
    subject: Optional[str] = None
    preview: str = ""
    full_text: str = ""
    priority: Optional[str] = None


class AgentDetail(AgentStatus):
    cron_jobs: list[CronJob] = Field(default_factory=list)
    recent_inbox: list[InboxMessage] = Field(default_factory=list)
    chappie_data: Optional[dict] = None
    producer_data: Optional[dict] = None
    hunter_data: Optional[dict] = None
    crm_summary: Optional[dict] = None


class AgentsResponse(BaseModel):
    agents: list[AgentStatus]
    total_cron_jobs: int = 0
    total_cron_errors: int = 0
    total_inbox_messages: int = 0
    last_updated: Optional[str] = None


# ──────────────────────────────────────────────
# Inbox
# ──────────────────────────────────────────────

class InboxResponse(BaseModel):
    messages: list[InboxMessage]
    total: int = 0


# ──────────────────────────────────────────────
# Cron
# ──────────────────────────────────────────────

class CronResponse(BaseModel):
    jobs: list[CronJob]
    total_enabled: int = 0
    total_errors: int = 0
    next_job_name: Optional[str] = None
    next_job_in: Optional[str] = None


# ──────────────────────────────────────────────
# Errors
# ──────────────────────────────────────────────

class ErrorItem(BaseModel):
    source: str  # "cron" | "api"
    job_name: Optional[str] = None
    agent: Optional[str] = None
    agent_name: Optional[str] = None
    provider: Optional[str] = None
    error: Optional[str] = None
    consecutive: int = 0
    last_at: Optional[str] = None
    severity: str = "info"  # "error" | "warning" | "info"


class ErrorsResponse(BaseModel):
    total_errors: int = 0
    groups: list[ErrorItem] = Field(default_factory=list)
