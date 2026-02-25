"""
Partner Panel Database Session Management

Использует общую инфраструктуру из shared/database/base.py
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.base import AsyncSessionLocal, get_session as shared_get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии БД в FastAPI endpoints.

    Используется как:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...

    Note: НЕ делаем автоматический commit здесь, т.к. FastAPI endpoints
    сами управляют транзакциями через await db.commit()

    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Альтернативный вариант для прямого использования
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Alias для get_db()"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
