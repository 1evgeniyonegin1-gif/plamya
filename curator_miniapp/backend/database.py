"""
Curator Mini App Database Session Management

Использует общую инфраструктуру из shared/database/base.py
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.base import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии БД в FastAPI endpoints.

    Usage:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...

    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
