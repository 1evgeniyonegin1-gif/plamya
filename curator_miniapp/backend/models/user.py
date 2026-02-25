"""
Curator User Model

Используем существующую таблицу users из curator_bot
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base

import sys
from pathlib import Path

# Добавляем корень проекта
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.base import Base


class CuratorUser(Base):
    """
    Curator Mini App user

    Note: Это отдельная таблица для пользователей Mini App
    Связывается с основной users через telegram_id
    """
    __tablename__ = "curator_miniapp_users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username = Column(String(255), nullable=True)
    telegram_first_name = Column(String(255), nullable=True)
    telegram_last_name = Column(String(255), nullable=True)
    telegram_photo_url = Column(String(500), nullable=True)

    # Mini App specific
    is_partner = Column(Boolean, default=False)
    partner_registered_at = Column(DateTime, nullable=True)

    # Tracking
    products_viewed = Column(Integer, default=0)
    business_section_viewed = Column(Boolean, default=False)
    last_visit_at = Column(DateTime, nullable=True)
    visits_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CuratorUser(telegram_id={self.telegram_id}, username={self.telegram_username})>"
