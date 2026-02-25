"""
Command Center Database Session Management

Uses shared infrastructure from shared/database/base.py
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.base import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for DB session injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
