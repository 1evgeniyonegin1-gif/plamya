"""
Модели для двухуровневой воронки каналов.

Архитектура:
- ChannelTier: иерархия каналов (публичные прогревающие → закрытый VIP)
- InviteLink: временные инвайт-ссылки с TTL для VIP канала
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, BigInteger, Text, Integer, Boolean, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from shared.database.base import Base, TimestampMixin


class TierLevel(enum.Enum):
    """Уровни воронки каналов"""
    PUBLIC_WARMUP = "public_warmup"  # Публичные прогревающие каналы
    PRIVATE_VIP = "private_vip"      # Закрытый VIP канал


class ChannelSegment(enum.Enum):
    """Сегменты контента"""
    UNIVERSAL = "universal"  # Общий контент
    ZOZH = "zozh"           # Здоровый образ жизни
    MAMA = "mama"           # Мамы, семья
    BUSINESS = "business"   # Бизнес, заработок
    STUDENTS = "students"   # Студенты/молодёжь (косметика, подработка)


class ChannelStatus(enum.Enum):
    """Статусы канала"""
    ACTIVE = "active"       # Активен
    PAUSED = "paused"       # На паузе
    ARCHIVED = "archived"   # В архиве


class InviteLinkStatus(enum.Enum):
    """Статусы инвайт-ссылки"""
    ACTIVE = "active"       # Активна
    EXPIRED = "expired"     # Истекла
    REVOKED = "revoked"     # Отозвана
    EXHAUSTED = "exhausted" # Исчерпан лимит


class ChannelTier(Base, TimestampMixin):
    """
    Канал в воронке.

    Уровни:
    - public_warmup: публичные каналы для прогрева аудитории
    - private_vip: закрытый VIP канал для партнёров
    """
    __tablename__ = "channel_tiers"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Основная информация
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    channel_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    channel_title: Mapped[str] = mapped_column(String(200), nullable=False)
    channel_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Уровень воронки: 'public_warmup' | 'private_vip'
    tier_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Сегмент: 'zozh', 'mama', 'business', 'universal'
    segment: Mapped[str] = mapped_column(String(20), default="universal", index=True)

    # Статус: 'active', 'paused', 'archived'
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    # Владелец (NULL = системный канал)
    owner_partner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("partners.id", ondelete="SET NULL"), nullable=True
    )

    # Настройки для публичных каналов
    is_traffic_source: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    allow_invite_posts: Mapped[bool] = mapped_column(Boolean, default=True)
    invite_post_frequency_days: Mapped[int] = mapped_column(Integer, default=3)

    # Ссылка на VIP канал (для публичных каналов)
    vip_channel_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("channel_tiers.id", ondelete="SET NULL"), nullable=True
    )

    # Статистика
    total_posts: Mapped[int] = mapped_column(Integer, default=0)
    total_subscribers: Mapped[int] = mapped_column(Integer, default=0)
    avg_engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    last_invite_post_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    vip_channel: Mapped[Optional["ChannelTier"]] = relationship(
        "ChannelTier", remote_side=[id], foreign_keys=[vip_channel_id]
    )
    invite_links: Mapped[list["InviteLink"]] = relationship(
        "InviteLink", back_populates="target_channel", foreign_keys="InviteLink.target_channel_id"
    )

    def __repr__(self) -> str:
        return f"<ChannelTier(id={self.id}, title={self.channel_title}, tier={self.tier_level})>"

    @property
    def is_public(self) -> bool:
        """Проверяет, является ли канал публичным"""
        return self.tier_level == TierLevel.PUBLIC_WARMUP.value

    @property
    def is_vip(self) -> bool:
        """Проверяет, является ли канал VIP"""
        return self.tier_level == TierLevel.PRIVATE_VIP.value

    def can_publish_invite(self, min_days: int = 2) -> bool:
        """Проверяет, можно ли публиковать инвайт-пост"""
        if not self.allow_invite_posts:
            return False
        if not self.last_invite_post_at:
            return True
        days_since_last = (datetime.utcnow() - self.last_invite_post_at).days
        return days_since_last >= min_days


class InviteLink(Base, TimestampMixin):
    """
    Временная инвайт-ссылка для VIP канала.

    Создаётся через Telethon API с ограничением по времени (TTL).
    После истечения срока пост автоудаляется.
    """
    __tablename__ = "invite_links"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Канал к которому ведёт ссылка
    target_channel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("channel_tiers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Telegram invite link
    invite_link: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    telegram_invite_hash: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invite_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Ограничения
    expire_date: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)
    usage_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Статус: 'active', 'expired', 'revoked', 'exhausted'
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    # Связанный пост (FK добавляется отдельно, чтобы избежать circular dependency)
    invite_post_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    published_channel_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("channel_tiers.id", ondelete="SET NULL"), nullable=True
    )

    # Статистика
    total_uses: Mapped[int] = mapped_column(Integer, default=0)
    total_joins: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    revoked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    target_channel: Mapped["ChannelTier"] = relationship(
        "ChannelTier", back_populates="invite_links", foreign_keys=[target_channel_id]
    )
    published_channel: Mapped[Optional["ChannelTier"]] = relationship(
        "ChannelTier", foreign_keys=[published_channel_id]
    )

    def __repr__(self) -> str:
        return f"<InviteLink(id={self.id}, link={self.invite_link[:30]}..., status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Проверяет, активна ли ссылка"""
        return self.status == InviteLinkStatus.ACTIVE.value

    @property
    def is_expired(self) -> bool:
        """Проверяет, истекла ли ссылка"""
        if self.status == InviteLinkStatus.EXPIRED.value:
            return True
        if self.expire_date and datetime.utcnow() > self.expire_date:
            return True
        return False

    @property
    def is_exhausted(self) -> bool:
        """Проверяет, исчерпан ли лимит использований"""
        if self.usage_limit is None:
            return False
        return self.total_uses >= self.usage_limit

    def mark_expired(self) -> None:
        """Помечает ссылку как истёкшую"""
        self.status = InviteLinkStatus.EXPIRED.value

    def mark_revoked(self) -> None:
        """Помечает ссылку как отозванную"""
        self.status = InviteLinkStatus.REVOKED.value
        self.revoked_at = datetime.utcnow()

    def increment_usage(self) -> None:
        """Увеличивает счётчик использований"""
        self.total_uses += 1
        self.last_used_at = datetime.utcnow()

        # Проверяем исчерпание лимита
        if self.is_exhausted:
            self.status = InviteLinkStatus.EXHAUSTED.value


class FunnelConversion(Base, TimestampMixin):
    """
    Конверсия воронки: пользователь перешёл из публичного канала в VIP.

    Трекинг:
    - Через какую инвайт-ссылку пришёл
    - Верифицирован ли как партнёр NL
    - Источник (какой пост привлёк)
    """
    __tablename__ = "funnel_conversions"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Пользователь
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Источник конверсии
    invite_link_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("invite_links.id", ondelete="SET NULL"), nullable=True
    )
    source_channel_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("channel_tiers.id", ondelete="SET NULL"), nullable=True
    )
    source_post_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Верификация партнёра NL
    is_verified_partner: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    partner_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Статус: joined, verified, rejected, left
    status: Mapped[str] = mapped_column(String(20), default="joined", index=True)

    # Активность после вступления
    messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    invite_link: Mapped[Optional["InviteLink"]] = relationship("InviteLink")
    source_channel: Mapped[Optional["ChannelTier"]] = relationship(
        "ChannelTier", foreign_keys=[source_channel_id]
    )

    def __repr__(self) -> str:
        return f"<FunnelConversion(user={self.user_id}, status={self.status}, verified={self.is_verified_partner})>"
