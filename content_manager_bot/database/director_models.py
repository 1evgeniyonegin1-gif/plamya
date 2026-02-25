"""
SQLAlchemy модели для AI Content Director.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, Date, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from shared.database.base import Base, TimestampMixin


class ContentPlan(Base, TimestampMixin):
    """Недельный план контента для сегмента."""
    __tablename__ = "content_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    segment: Mapped[str] = mapped_column(String(30), index=True)
    week_start: Mapped[datetime] = mapped_column(Date)
    plan_data: Mapped[dict] = mapped_column(JSONB, default=list)
    slots_used: Mapped[int] = mapped_column(Integer, default=0)
    slots_total: Mapped[int] = mapped_column(Integer, default=10)
    performance_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    ai_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<ContentPlan(id={self.id}, segment={self.segment}, week={self.week_start}, used={self.slots_used}/{self.slots_total})>"


class ChannelMemoryModel(Base):
    """Структурированная память канала (Mem0-стиль)."""
    __tablename__ = "channel_memory"

    id: Mapped[int] = mapped_column(primary_key=True)
    segment: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    state_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ChannelMemory(segment={self.segment})>"


class ContentSelfReview(Base):
    """Результат AI самоанализа контента."""
    __tablename__ = "content_self_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    segment: Mapped[str] = mapped_column(String(30), index=True)
    posts_reviewed: Mapped[int] = mapped_column(Integer, default=0)
    review_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    applied: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SelfReview(id={self.id}, segment={self.segment}, posts={self.posts_reviewed})>"
