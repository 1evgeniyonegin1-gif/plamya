"""
Модели базы данных для AI-Куратора
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, BigInteger, Text, Integer, Boolean, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from shared.database.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Модель пользователя (партнера)"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))

    # Тип и квалификация
    user_type: Mapped[str] = mapped_column(String(20), default="lead")  # 'lead' или 'partner'
    # Квалификация партнёра по системе NL International
    # См. content/knowledge_base/business/plan_voznagrazhdeniya.md
    # Возможные значения: consultant, consultant_6, manager_9, senior_manager,
    # manager_15, director_21, M1, M2, M3, B1, B2, B3, TOP, TOP1-TOP5, AC1-AC6
    qualification: Mapped[str] = mapped_column(String(50), default="consultant")

    # Реферальная система
    referrer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    # Цели и активность
    current_goal: Mapped[Optional[str]] = mapped_column(Text)
    last_activity: Mapped[Optional[datetime]] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Прогресс обучения
    lessons_completed: Mapped[int] = mapped_column(Integer, default=0)

    # Воронка продаж
    user_intent: Mapped[Optional[str]] = mapped_column(String(50))  # client, business, curious
    pain_point: Mapped[Optional[str]] = mapped_column(String(100))  # weight, energy, immunity, beauty, kids, sport
    income_goal: Mapped[Optional[str]] = mapped_column(String(50))  # 10_30k, 50_100k, 200k_plus, unsure
    funnel_step: Mapped[int] = mapped_column(Integer, default=0)  # Текущий шаг воронки
    funnel_started_at: Mapped[Optional[datetime]] = mapped_column()  # Когда начал воронку
    email: Mapped[Optional[str]] = mapped_column(String(100))  # Email для рассылки
    lead_status: Mapped[str] = mapped_column(String(50), default="new")  # new, cold, qualified, hot, contact_requested, ordered, partner
    lead_score: Mapped[int] = mapped_column(Integer, default=0)  # Скоринг лида (0-100)

    # Traffic Engine: источник трафика
    traffic_source: Mapped[Optional[str]] = mapped_column(String(100), index=True)  # channel_zozh_1, channel_mama_1, etc.

    # Relationships
    messages: Mapped[List["ConversationMessage"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    context: Mapped[Optional["ConversationContext"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, name={self.first_name})>"


class ConversationMessage(Base, TimestampMixin):
    """История диалогов с куратором"""
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    message_text: Mapped[str] = mapped_column(Text)
    sender: Mapped[str] = mapped_column(String(20))  # 'user' или 'bot'
    timestamp: Mapped[datetime] = mapped_column(index=True)

    # AI метаданные
    ai_model: Mapped[Optional[str]] = mapped_column(String(50))
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    context_used: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<ConversationMessage(id={self.id}, user_id={self.user_id}, sender={self.sender})>"


class ConversationContext(Base, TimestampMixin):
    """
    Контекст диалогов для быстрого доступа.

    Хранит состояние диалоговой воронки для каждого пользователя.
    Раньше хранилось в RAM — теперь персистентно в БД.
    """
    __tablename__ = "conversation_contexts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    # Контекстная информация (старые поля)
    recent_topics: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    pending_actions: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    last_question: Mapped[Optional[str]] = mapped_column(Text)
    last_recommendation: Mapped[Optional[str]] = mapped_column(Text)

    # === ДИАЛОГОВАЯ ВОРОНКА ===
    # Этап воронки: greeting, discovery, deepening, solution_hint, solution, objection, closing, follow_up
    funnel_stage: Mapped[str] = mapped_column(String(50), default="greeting")

    # Намерение пользователя: product, business, skeptic, curious, support, unknown
    funnel_intent: Mapped[str] = mapped_column(String(50), default="unknown")

    # Температура лида: hot, warm, cold
    lead_temperature: Mapped[str] = mapped_column(String(20), default="warm")

    # Выявленные боли (список): energy, weight, skin, immunity, sleep, sport, kids, money
    pains: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=[])

    # Выявленные потребности
    needs: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=[])

    # Возражения (список): price, trust, time, delay
    objections: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=[])

    # Счётчики для определения готовности к предложению
    engagement_score: Mapped[int] = mapped_column(Integer, default=0)  # Насколько вовлечён (0-10)
    trust_score: Mapped[int] = mapped_column(Integer, default=0)       # Насколько доверяет (0-5)
    objection_count: Mapped[int] = mapped_column(Integer, default=0)   # Сколько возражений
    messages_count: Mapped[int] = mapped_column(Integer, default=0)    # Сколько сообщений в диалоге

    # Предложенные решения
    suggested_products: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=[])
    suggested_business: Mapped[bool] = mapped_column(Boolean, default=False)

    # Флаг: была ли уже дана ссылка (чтобы не дублировать)
    link_provided: Mapped[bool] = mapped_column(Boolean, default=False)

    # Таймстемпы воронки
    conversation_started_at: Mapped[Optional[datetime]] = mapped_column()
    last_funnel_activity: Mapped[Optional[datetime]] = mapped_column()

    # Relationships
    user: Mapped["User"] = relationship(back_populates="context")

    def __repr__(self) -> str:
        return f"<ConversationContext(id={self.id}, user_id={self.user_id}, stage={self.funnel_stage})>"


class KnowledgeBaseChunk(Base, TimestampMixin):
    """Фрагменты базы знаний для RAG"""
    __tablename__ = "knowledge_base_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_file: Mapped[str] = mapped_column(String(255))
    chunk_text: Mapped[str] = mapped_column(Text)

    # Векторное представление для поиска (используем pgvector)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(384), nullable=True)

    # Метаданные
    category: Mapped[str] = mapped_column(String(100), index=True)  # products, marketing_plan, sales_scripts, etc.
    meta_data: Mapped[Optional[dict]] = mapped_column(JSONB)  # Переименовано из metadata чтобы избежать конфликта

    def __repr__(self) -> str:
        return f"<KnowledgeBaseChunk(id={self.id}, category={self.category})>"


class UserReminder(Base, TimestampMixin):
    """Напоминания и задачи для партнеров"""
    __tablename__ = "user_reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    reminder_type: Mapped[str] = mapped_column(String(50))  # lesson, goal, activity, custom
    message: Mapped[str] = mapped_column(Text)

    scheduled_at: Mapped[datetime] = mapped_column(index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, sent, cancelled

    def __repr__(self) -> str:
        return f"<UserReminder(id={self.id}, user_id={self.user_id}, type={self.reminder_type})>"


class UserFeedback(Base, TimestampMixin):
    """Обратная связь от партнеров о качестве ответов"""
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message_id: Mapped[int] = mapped_column(ForeignKey("conversation_messages.id"))

    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    feedback_text: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<UserFeedback(id={self.id}, user_id={self.user_id}, rating={self.rating})>"


class UserOnboardingProgress(Base, TimestampMixin):
    """Прогресс онбординга пользователя (7-дневный чеклист)"""
    __tablename__ = "user_onboarding_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    # Текущий день онбординга (1-7)
    current_day: Mapped[int] = mapped_column(Integer, default=1)

    # Выполненные задачи (список task_id)
    completed_tasks: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=[])

    # Когда начал онбординг
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Последняя активность в онбординге
    last_activity: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Последнее отправленное напоминание (часы неактивности)
    last_reminder_hours: Mapped[int] = mapped_column(Integer, default=0)

    # Завершён ли онбординг
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<UserOnboardingProgress(user_id={self.user_id}, day={self.current_day})>"


class TrafficSource(Base, TimestampMixin):
    """
    Источник трафика для Traffic Engine.

    Каждый канал/источник имеет уникальный source_id (например: channel_zozh_1).
    Используется для отслеживания эффективности каналов.
    """
    __tablename__ = "traffic_sources"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Уникальный идентификатор источника (channel_zozh_1, channel_mama_1, etc.)
    source_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Название канала/источника для отображения
    name: Mapped[str] = mapped_column(String(255))

    # Тип источника: channel, group, ads, organic
    source_type: Mapped[str] = mapped_column(String(50), default="channel")

    # Сегмент аудитории: zozh, mama, business
    segment: Mapped[Optional[str]] = mapped_column(String(50))

    # Telegram username канала (если есть)
    channel_username: Mapped[Optional[str]] = mapped_column(String(100))

    # Персона канала (имя аватара): Карина, Марина, etc.
    persona_name: Mapped[Optional[str]] = mapped_column(String(100))

    # Активен ли источник
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Статистика (агрегированная)
    total_clicks: Mapped[int] = mapped_column(Integer, default=0)
    total_registrations: Mapped[int] = mapped_column(Integer, default=0)
    total_active_users: Mapped[int] = mapped_column(Integer, default=0)
    total_partners: Mapped[int] = mapped_column(Integer, default=0)

    # Метаданные (CTA, описание, etc.)
    # Названо extra_data т.к. 'metadata' зарезервировано в SQLAlchemy
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)

    def __repr__(self) -> str:
        return f"<TrafficSource(source_id={self.source_id}, name={self.name})>"

    @property
    def conversion_rate(self) -> float:
        """Конверсия клик → регистрация"""
        if self.total_clicks == 0:
            return 0.0
        return round(self.total_registrations / self.total_clicks * 100, 2)

    @property
    def partner_rate(self) -> float:
        """Конверсия регистрация → партнёр"""
        if self.total_registrations == 0:
            return 0.0
        return round(self.total_partners / self.total_registrations * 100, 2)


class TrafficClick(Base, TimestampMixin):
    """
    Клик по ссылке из канала (до регистрации).

    Записывается когда пользователь переходит по ссылке,
    но ещё не написал /start.
    """
    __tablename__ = "traffic_clicks"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Источник трафика
    source_id: Mapped[str] = mapped_column(String(100), index=True)

    # Telegram ID пользователя (если известен)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True)

    # IP / User Agent (если будет веб-страница)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))

    # Конвертировался ли в регистрацию
    converted: Mapped[bool] = mapped_column(Boolean, default=False)
    converted_at: Mapped[Optional[datetime]] = mapped_column()

    def __repr__(self) -> str:
        return f"<TrafficClick(source_id={self.source_id}, converted={self.converted})>"
