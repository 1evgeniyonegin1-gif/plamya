"""
Partner Panel Database Models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

# Используем общий Base из shared
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.base import Base


class PartnerStatus(str, enum.Enum):
    """Partner account status"""
    PENDING = "pending"           # Ожидает подключения
    CONNECTING = "connecting"     # В процессе подключения
    ACTIVE = "active"             # Активен
    PAUSED = "paused"             # Приостановлен
    ERROR = "error"               # Ошибка
    BANNED = "banned"             # Заблокирован


class ChannelStatus(str, enum.Enum):
    """Channel status"""
    CREATING = "creating"         # Создаётся
    WARMING = "warming"           # Прогревается
    ACTIVE = "active"             # Активен
    PAUSED = "paused"             # Приостановлен
    BANNED = "banned"             # Заблокирован


class Partner(Base):
    """
    Партнёр NL International с доступом к системе
    """
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Telegram данные (из Mini App)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100))
    telegram_first_name: Mapped[Optional[str]] = mapped_column(String(100))
    telegram_last_name: Mapped[Optional[str]] = mapped_column(String(100))
    telegram_photo_url: Mapped[Optional[str]] = mapped_column(String(500))

    # NL данные (опционально)
    nl_partner_id: Mapped[Optional[str]] = mapped_column(String(50))
    nl_qualification: Mapped[Optional[str]] = mapped_column(String(20))  # M1, B1, etc.

    # Статус
    status: Mapped[PartnerStatus] = mapped_column(
        SQLEnum(PartnerStatus),
        default=PartnerStatus.PENDING
    )

    # Сегмент контента
    segment: Mapped[str] = mapped_column(String(20), default="zozh")  # zozh, mama, business

    # Статистика
    total_channels: Mapped[int] = mapped_column(Integer, default=0)
    total_posts: Mapped[int] = mapped_column(Integer, default=0)
    total_subscribers: Mapped[int] = mapped_column(Integer, default=0)
    total_leads: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    credentials: Mapped[list["PartnerCredentials"]] = relationship(
        "PartnerCredentials", back_populates="partner", cascade="all, delete-orphan"
    )
    channels: Mapped[list["PartnerChannel"]] = relationship(
        "PartnerChannel", back_populates="partner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Partner {self.telegram_id} ({self.status.value})>"


class PartnerCredentials(Base):
    """
    Credentials партнёра для Telegram аккаунтов
    """
    __tablename__ = "partner_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)

    # Telegram credentials
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    session_string: Mapped[str] = mapped_column(Text)  # Зашифровано

    # Telethon API (опционально, можно использовать дефолтные)
    api_id: Mapped[Optional[int]] = mapped_column(Integer)
    api_hash: Mapped[Optional[str]] = mapped_column(String(50))

    # Proxy
    proxy_type: Mapped[Optional[str]] = mapped_column(String(10))  # socks5, http
    proxy_host: Mapped[Optional[str]] = mapped_column(String(100))
    proxy_port: Mapped[Optional[int]] = mapped_column(Integer)
    proxy_username: Mapped[Optional[str]] = mapped_column(String(100))
    proxy_password: Mapped[Optional[str]] = mapped_column(String(100))

    # Статус аккаунта
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[Optional[str]] = mapped_column(String(500))

    # Прогрев
    warmup_day: Mapped[int] = mapped_column(Integer, default=0)
    warmup_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    partner: Mapped["Partner"] = relationship("Partner", back_populates="credentials")
    channels: Mapped[list["PartnerChannel"]] = relationship(
        "PartnerChannel", back_populates="credentials"
    )

    def __repr__(self) -> str:
        return f"<PartnerCredentials {self.phone}>"


class PartnerChannel(Base):
    """
    Telegram канал партнёра
    """
    __tablename__ = "partner_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)
    credentials_id: Mapped[int] = mapped_column(ForeignKey("partner_credentials.id"), index=True)

    # Telegram канал
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    channel_username: Mapped[Optional[str]] = mapped_column(String(100))
    channel_title: Mapped[str] = mapped_column(String(200))
    channel_description: Mapped[Optional[str]] = mapped_column(Text)

    # Настройки
    segment: Mapped[str] = mapped_column(String(20))  # zozh, mama, business
    persona_name: Mapped[str] = mapped_column(String(50))  # Марина, Анна, etc.
    status: Mapped[ChannelStatus] = mapped_column(
        SQLEnum(ChannelStatus),
        default=ChannelStatus.CREATING
    )

    # Автопостинг
    posting_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    posts_per_day: Mapped[int] = mapped_column(Integer, default=2)
    posting_times: Mapped[Optional[dict]] = mapped_column(JSON)  # ["10:00", "18:00"]

    # Реферальная ссылка партнёра (вставляется в посты)
    referral_link: Mapped[Optional[str]] = mapped_column(String(200))
    curator_deeplink: Mapped[Optional[str]] = mapped_column(String(200))  # t.me/bot?start=partner_123

    # Статистика
    subscribers_count: Mapped[int] = mapped_column(Integer, default=0)
    posts_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_views: Mapped[int] = mapped_column(Integer, default=0)
    total_clicks: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_post_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    partner: Mapped["Partner"] = relationship("Partner", back_populates="channels")
    credentials: Mapped["PartnerCredentials"] = relationship(
        "PartnerCredentials", back_populates="channels"
    )

    def __repr__(self) -> str:
        return f"<PartnerChannel {self.channel_title} ({self.status.value})>"
