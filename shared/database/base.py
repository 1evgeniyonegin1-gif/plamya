"""
Базовые модели и настройки для базы данных
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func
from typing import AsyncGenerator

from shared.config.settings import settings


# Создаем асинхронный движок БД
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class TimestampMixin:
    """Миксин для добавления timestamps к моделям"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Генератор сессий для dependency injection

    Yields:
        AsyncSession: Сессия базы данных
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Создает все таблицы в базе данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
