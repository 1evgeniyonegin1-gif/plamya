"""
Модели базы данных для хранения каналов-образцов и их постов.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, func, BigInteger, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin


class StyleChannel(Base, TimestampMixin):
    """
    Канал-образец для анализа стиля контента.

    Бот будет следить за этими каналами и анализировать их посты
    для понимания стиля написания.
    """
    __tablename__ = "style_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Telegram данные
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # @username
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # Настройки
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1-10, выше = важнее

    # Описание (для чего этот канал)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Категория стиля (можно группировать каналы)
    style_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Например: "motivation", "product", "lifestyle", "business"

    # Статистика
    posts_count: Mapped[int] = mapped_column(Integer, default=0)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_post_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Связь с постами
    posts: Mapped[List["StylePost"]] = relationship(
        "StylePost",
        back_populates="channel",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_style_channels_active", "is_active"),
        Index("idx_style_channels_category", "style_category"),
    )

    def __repr__(self):
        return f"<StyleChannel(id={self.id}, title='{self.title}', username='{self.username}')>"


class StylePost(Base):
    """
    Пост из канала-образца.

    Хранит текст и метаданные поста для анализа стиля.
    """
    __tablename__ = "style_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Связь с каналом
    channel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("style_channels.id", ondelete="CASCADE"),
        nullable=False
    )
    channel: Mapped["StyleChannel"] = relationship("StyleChannel", back_populates="posts")

    # Telegram данные
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Контент
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Метаданные
    post_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    has_media: Mapped[bool] = mapped_column(Boolean, default=False)
    media_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # photo, video, document

    # Метрики вовлечённости (если доступны)
    views_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    forwards_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reactions_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Анализ
    is_analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    style_tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Например: {"tone": "friendly", "length": "short", "emoji_count": 3, "has_cta": true}

    # Оценка качества (0-10, ставится вручную или автоматически)
    quality_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Временные метки
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        Index("idx_style_posts_channel", "channel_id"),
        Index("idx_style_posts_date", "post_date"),
        Index("idx_style_posts_quality", "quality_score"),
        # Уникальность: один message_id на канал
        Index("idx_style_posts_unique", "channel_id", "message_id", unique=True),
    )

    def __repr__(self):
        return f"<StylePost(id={self.id}, channel_id={self.channel_id}, message_id={self.message_id})>"


class StyleAnalysis(Base, TimestampMixin):
    """
    Результат анализа стиля канала (агрегированная статистика).

    Пересчитывается периодически на основе постов.
    """
    __tablename__ = "style_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Связь с каналом
    channel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("style_channels.id", ondelete="CASCADE"),
        nullable=False
    )

    # Период анализа
    analysis_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    posts_analyzed: Mapped[int] = mapped_column(Integer, default=0)

    # Характеристики стиля
    avg_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # средняя длина поста
    avg_emoji_count: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    avg_paragraph_count: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)

    # Тональность (0-1)
    tone_formal: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    tone_friendly: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    tone_motivational: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)

    # Форматирование
    uses_bold: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)  # % постов с жирным
    uses_lists: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)  # % с списками
    uses_hashtags: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    uses_cta: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)  # % с призывом к действию

    # Часто используемые паттерны
    common_phrases: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Например: {"greeting": ["Привет!", "Доброе утро"], "cta": ["Пиши в лс", "Переходи по ссылке"]}

    # Примеры лучших постов (топ-5 по quality_score)
    best_posts_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_style_analyses_channel", "channel_id"),
        Index("idx_style_analyses_date", "analysis_date"),
    )


class SystemEvent(Base, TimestampMixin):
    """
    События в системе для межмодульной коммуникации.

    Используется для связи между curator_bot и content_manager_bot.
    Например, когда Content Manager публикует пост, он создаёт событие
    'post_published', которое Curator обрабатывает и рассылает уведомления
    целевой аудитории.
    """
    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Тип события (post_published, user_registered и т.д.)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Источник события (content_manager, curator)
    source: Mapped[str] = mapped_column(String(50), nullable=False)

    # Данные события в JSON формате
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Обработано ли событие
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Целевой модуль (curator, all, NULL для всех)
    target_module: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # Время истечения события (TTL)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_system_events_type_processed", "event_type", "processed"),
        Index("idx_system_events_target_processed", "target_module", "processed"),
    )
