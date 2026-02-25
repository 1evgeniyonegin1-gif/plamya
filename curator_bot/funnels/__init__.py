"""
Модуль воронки продаж для AI-Куратора

Структура:
- referral_links.py - Генерация реферальных ссылок
- conversational_funnel.py - Диалоговая воронка (без кнопок)
- messages.py - Тексты для напоминаний
- keyboards.py - Клавиатуры для напоминаний (get_reminder_response_keyboard)
"""

from curator_bot.funnels.referral_links import (
    get_registration_link,
    get_shop_link,
    get_client_registration_link,
)
from curator_bot.funnels.conversational_funnel import (
    ConversationalFunnel,
    get_conversational_funnel,
    ConversationStage,
    UserIntent,
)

__all__ = [
    "get_registration_link",
    "get_shop_link",
    "get_client_registration_link",
    # Conversational funnel
    "ConversationalFunnel",
    "get_conversational_funnel",
    "ConversationStage",
    "UserIntent",
]
