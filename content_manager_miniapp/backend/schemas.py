"""
Pydantic schemas for Command Center API requests/responses.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── Auth ──

class AuthRequest(BaseModel):
    init_data: str


class UserInfo(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    is_admin: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


# ── Posts ──

class PostOut(BaseModel):
    id: int
    content: str
    post_type: str
    status: str
    segment: Optional[str] = None
    views_count: Optional[int] = 0
    reactions_count: Optional[int] = 0
    forwards_count: Optional[int] = 0
    engagement_rate: Optional[float] = None
    generated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    ai_model: Optional[str] = None

    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    posts: list[PostOut]
    total: int


class GenerateRequest(BaseModel):
    post_type: Optional[str] = None
    custom_topic: Optional[str] = None
    segment: Optional[str] = None


class ModerateRequest(BaseModel):
    action: str  # publish, reject, schedule
    scheduled_at: Optional[datetime] = None


class EditContentRequest(BaseModel):
    content: str


class RegenerateRequest(BaseModel):
    feedback: Optional[str] = None


class AiEditRequest(BaseModel):
    instructions: str


# ── Analytics ──

class TypeBreakdown(BaseModel):
    type: str
    count: int
    avg_engagement: Optional[float] = None


class DashboardResponse(BaseModel):
    total_posts: int
    published_today: int
    avg_engagement: Optional[float] = None
    pending_count: int
    type_breakdown: list[TypeBreakdown]


class TimelinePoint(BaseModel):
    date: str
    engagement_rate: Optional[float] = None
    posts_count: int


class EngagementResponse(BaseModel):
    timeline: list[TimelinePoint]


class TopPostOut(BaseModel):
    id: int
    post_type: str
    preview: str
    views: int
    reactions: int
    engagement_rate: Optional[float] = None


class TopPostsResponse(BaseModel):
    posts: list[TopPostOut]


# ── Traffic Engine ──

class AccountOut(BaseModel):
    id: int
    phone: str
    first_name: str
    username: Optional[str] = None
    segment: Optional[str] = None
    status: str
    daily_comments: int
    daily_invites: int
    daily_story_views: int
    daily_story_reactions: int
    last_used_at: Optional[datetime] = None
    warmup_completed: bool
    linked_channel_username: Optional[str] = None

    class Config:
        from_attributes = True


class TodayStats(BaseModel):
    comments_ok: int
    comments_fail: int
    stories: int
    invites: int
    replies: int


class LastComment(BaseModel):
    text: str
    channel: Optional[str] = None
    strategy: Optional[str] = None
    time: Optional[datetime] = None


class TrafficOverviewResponse(BaseModel):
    accounts: list[AccountOut]
    today_stats: TodayStats
    last_comment: Optional[LastComment] = None


class ErrorGroup(BaseModel):
    category: str
    count: int
    last_at: Optional[datetime] = None
    diagnosis: Optional[str] = None
    accounts: list[str]
    channels: list[str]


class TrafficErrorsResponse(BaseModel):
    total: int
    groups: list[ErrorGroup]


# ── Director ──

class PlanSlot(BaseModel):
    day: str
    post_type: str
    topic: Optional[str] = None
    status: str  # planned, generated, published


class PlanResponse(BaseModel):
    plan_id: Optional[int] = None
    week_start: Optional[str] = None
    slots: list[PlanSlot]
    used: int
    total: int


class ReviewResponse(BaseModel):
    posts_reviewed: int
    created_at: Optional[datetime] = None
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    topics: list[str]
    avoid: list[str]


class InsightItem(BaseModel):
    type: str
    avg_engagement: Optional[float] = None
    count: int


class InsightsResponse(BaseModel):
    type_performance: list[InsightItem]
    best_hours: list[int]
    recommended_type: Optional[str] = None


class CompetitorsResponse(BaseModel):
    trending_topics: list[str]
    winning_formats: list[str]
    hooks: list[str]
    our_angle: Optional[str] = None
    trend_context: Optional[str] = None


# ── Diary ──

class DiaryEntryOut(BaseModel):
    id: int
    entry_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class DiaryListResponse(BaseModel):
    entries: list[DiaryEntryOut]


class DiaryCreateRequest(BaseModel):
    text: str


# ── Schedule ──

class ScheduleOut(BaseModel):
    id: int
    post_type: str
    is_active: bool
    cron_expression: str
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    schedules: list[ScheduleOut]


class ScheduleUpdateRequest(BaseModel):
    is_active: bool
