"""
Analytics Models

Модели для аналитики Mini App
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

import sys
from pathlib import Path

# Добавляем корень проекта
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.base import Base


class ProductView(Base):
    """
    Просмотры продуктов в каталоге

    Трекаем когда пользователь открывает карточку продукта
    и переходит по реферальной ссылке
    """
    __tablename__ = "curator_product_views"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("curator_miniapp_users.id"), nullable=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    product_key = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=True)
    clicked_link = Column(Boolean, default=False)
    viewed_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ProductView(telegram_id={self.telegram_id}, product={self.product_key})>"


class BusinessInterest(Base):
    """
    Интерес к бизнесу

    Трекаем когда пользователь нажимает CTA в разделе бизнеса
    """
    __tablename__ = "curator_business_interests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("curator_miniapp_users.id"), nullable=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(50), nullable=False)  # 'telegram_chat', 'registration', 'view_business'
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BusinessInterest(telegram_id={self.telegram_id}, action={self.action})>"
